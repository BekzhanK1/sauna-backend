from django.utils import timezone
from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView

from users.models import Bathhouse, Room
from django.db import transaction as db_transaction
from .models import Booking, BonusAccount, BonusTransaction, accrue_bonus_for_booking
from .serializers import BookingSerializer
from .utils import generate_random_4_digit_number
from users.permissions import IsBathAdminOrSuperAdmin
from users.services.telegram import send_message
from datetime import datetime
from zoneinfo import ZoneInfo
import html
from decimal import Decimal, ROUND_HALF_UP


class BookingViewSet(viewsets.ModelViewSet):
    queryset = Booking.objects.all()
    serializer_class = BookingSerializer

    def get_permissions(self):
        if self.action in [
            "update",
            "partial_update",
            "destroy",
            "confirm_booking",
            "retrieve",
            "confirm_booking_admin",
        ]:
            return [IsBathAdminOrSuperAdmin()]
        return [permissions.AllowAny()]

    def get_queryset(self):
        user = self.request.user

        if user.is_authenticated and user.role == "superadmin":
            return Booking.objects.all()

        elif user.is_authenticated and user.role == "bath_admin":
            bathhouse_id = self.request.query_params.get("bathhouse_id")

            if bathhouse_id:
                if bathhouse_id.isdigit():
                    bathhouse_id = int(bathhouse_id)
                    return Booking.objects.filter(
                        bathhouse_id=bathhouse_id, bathhouse__owner_id=user.pk
                    )
                else:
                    return Booking.objects.none()

            return Booking.objects.filter(bathhouse__owner_id=user.pk)

        return Booking.objects.all()

    def list(self, request, *args, **kwargs):
        user = self.request.user

        if not user.is_authenticated or user.is_anonymous:
            phone_number = request.query_params.get("phone_number")
            if not phone_number:
                return Response(
                    {"error": "Enter phone number to see your bookings"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            print(phone_number)
            bookings = Booking.objects.filter(phone=phone_number)
            serializer = self.get_serializer(bookings, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)

        # For authenticated users, optionally filter by bathhouse_id
        queryset = self.get_queryset()
        bathhouse_id = request.query_params.get("bathhouse_id")
        
        if bathhouse_id:
            try:
                bathhouse_id_int = int(bathhouse_id)
                queryset = queryset.filter(bathhouse_id=bathhouse_id_int)
            except (TypeError, ValueError):
                return Response(
                    {"error": "bathhouse_id must be an integer"},
                    status=status.HTTP_400_BAD_REQUEST,
                )
        
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(
        detail=True,
        methods=["post"],
        permission_classes=[IsBathAdminOrSuperAdmin],
        url_path="process-payment",
    )
    def process_payment(self, request, pk=None):
        """
        Confirm booking payment and optionally redeem bonus balance.

        Query params: bathhouse_id (int), phone (str)
        Body JSON: { "amount": number }  # amount of bonuses to redeem; can be 0
        """
        booking = self.get_object()
        bathhouse_id = request.query_params.get("bathhouse_id")
        phone = request.query_params.get("phone")
        amount = request.data.get("amount", 0)

        if not bathhouse_id or not phone:
            return Response(
                {"error": "bathhouse_id and phone are required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            bathhouse_id_int = int(bathhouse_id)
        except (TypeError, ValueError):
            return Response(
                {"error": "bathhouse_id must be an integer"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Basic checks
        if booking.bathhouse_id != bathhouse_id_int:
            return Response({"error": "Booking bathhouse mismatch"}, status=status.HTTP_400_BAD_REQUEST)
        if booking.phone != phone:
            return Response({"error": "Phone mismatch with booking"}, status=status.HTTP_400_BAD_REQUEST)
        if not booking.confirmed:
            return Response({"error": "Booking must be confirmed"}, status=status.HTTP_400_BAD_REQUEST)

        # Amount parsing
        try:
            amount_dec = Decimal(str(amount)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        except Exception:
            return Response({"error": "Invalid amount"}, status=status.HTTP_400_BAD_REQUEST)
        if amount_dec < 0:
            return Response({"error": "Amount must be >= 0"}, status=status.HTTP_400_BAD_REQUEST)

        final_price = Decimal(str(booking.get_final_price() or 0)).quantize(Decimal("0.01"))

        # amount == 0: no bonus usage, just mark as paid
        if amount_dec == 0:
            with db_transaction.atomic():
                booking.is_paid = True
                booking.save(update_fields=["is_paid"])
                accrue_bonus_for_booking(booking)

            existing_account = (
                BonusAccount.objects.filter(bathhouse_id=bathhouse_id_int, phone=phone)
                .only("balance")
                .first()
            )
            balance_str = str(existing_account.balance) if existing_account else "0.00"
            return Response(
                {
                    "booking_id": str(booking.id),
                    "is_paid": booking.is_paid,
                    "redeemed": "0.00",
                    "balance": balance_str,
                    "final_price": str(final_price),
                    "remaining_due": "0.00",
                },
                status=status.HTTP_200_OK,
            )

        # amount > 0: redeem from bonus account
        account, _ = BonusAccount.objects.get_or_create(
            bathhouse_id=bathhouse_id_int, phone=phone
        )

        if amount_dec > account.balance:
            return Response({"error": "Insufficient bonus balance"}, status=status.HTTP_400_BAD_REQUEST)
        if amount_dec > final_price:
            return Response({"error": "Amount cannot exceed booking price"}, status=status.HTTP_400_BAD_REQUEST)

        with db_transaction.atomic():
            new_balance = (account.balance - amount_dec).quantize(Decimal("0.01"))
            account.balance = new_balance
            account.save(update_fields=["balance", "updated_at"])

            BonusTransaction.objects.create(
                account=account,
                booking=booking,
                type=BonusTransaction.REDEMPTION,
                amount=amount_dec,
            )

            # Mark as paid regardless of whether bonuses cover fully; rest is handled offline
            booking.is_paid = True
            booking.save(update_fields=["is_paid"])
            accrue_bonus_for_booking(booking)

        return Response(
            {
                "booking_id": str(booking.id),
                "is_paid": booking.is_paid,
                "redeemed": str(amount_dec),
                "balance": str(account.balance),
                "final_price": str(final_price),
                "remaining_due": "0.00",
            },
            status=status.HTTP_200_OK,
        )

    def create(self, request, *args, **kwargs):
        response = super().create(request, *args, **kwargs)
        print(request.data)
        booking_data = request.data

        # Get related objects (raise 404 if not found — optional)
        bathhouse = Bathhouse.objects.get(id=booking_data.get("bathhouse"))
        room = Room.objects.get(id=booking_data.get("room"))

        # ---- Time handling (to Asia/Almaty) ----
        start_time_raw = booking_data.get("start_time", "")
        formatted_start_time = ""
        if start_time_raw:
            s = start_time_raw.strip()
            # Allow both "Z" and "+00:00" style; if naive, assume UTC
            if s.endswith("Z"):
                s = s[:-1] + "+00:00"
            try:
                dt = datetime.fromisoformat(s)
            except ValueError:
                dt = None
            if dt is not None:
                if dt.tzinfo is None:
                    # assume the backend sent UTC if naive
                    dt = dt.replace(tzinfo=ZoneInfo("UTC"))
                dt_almaty = dt.astimezone(ZoneInfo("Asia/Almaty"))
                formatted_start_time = dt_almaty.strftime("%d.%m.%y %H:%M")

        # ---- Extras formatting ----
        extra_items = booking_data.get("extra_items_data") or []
        extras_lines = (
            "\n".join(
                [
                    f"• ID: <code>{html.escape(str(x.get('item', '')))}</code> — Кол-во: <b>{html.escape(str(x.get('quantity', '')))}</b>"
                    for x in extra_items
                ]
            )
            or "—"
        )

        # ---- Escape user-supplied fields ----
        name = html.escape(booking_data.get("name", ""))
        phone = html.escape(booking_data.get("phone", ""))
        hours = html.escape(str(booking_data.get("hours", "")))
        bath_name = html.escape(str(bathhouse.name))
        room_type = "Сауна" if room.is_sauna else "Баня"

        # ---- Nicely formatted “card” ----
        text = (
            f"🧖 <b>Новая бронь</b>\n"
            f"<b>ID: </b> <code>{response.data.get('id')}</code> \n"
            "——————————————\n"
            f"👤 <b>Имя:</b> {name}\n"
            f"📞 <b>Телефон:</b> {phone}\n"
            f"🏛️ <b>Баня:</b> ID <code>{bathhouse.id}</code> — {bath_name}\n"
            f"🚪 <b>Комната:</b> ID <code>{room.id}</code> — {room_type}, № {html.escape(str(room.room_number))}\n"
            f"🕒 <b>Начало:</b> {formatted_start_time}\n"
            f"⏳ <b>Часы:</b> {hours}\n"
            f"🧺 <b>Доп. услуги:</b>\n{extras_lines}"
        )

        send_message(chat_type="notification", text=text)
        return response

    @action(
        detail=False,
        methods=["get"],
        permission_classes=[permissions.AllowAny],
        url_path="room-bookings",
    )
    def get_room_bookings(self, request):
        room_id = request.query_params.get("room_id")
        if not room_id:
            return Response(
                {"error": "Room ID is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        today = timezone.now().date()
        bookings = Booking.objects.filter(room_id=room_id, start_time__gte=today)
        serializer = self.get_serializer(bookings, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(
        detail=True,
        methods=["post"],
        permission_classes=[IsBathAdminOrSuperAdmin],
        url_path="confirm-booking-admin",
    )
    def confirm_booking_admin(self, request, pk=None):
        booking = self.get_object()
        booking.confirmed = True
        booking.save()
        return Response({"status": "Booking confirmed"}, status=status.HTTP_200_OK)

    @action(
        detail=True,
        methods=["post"],
        permission_classes=[permissions.AllowAny],
        url_path="confirm-booking-sms",
    )
    def confirm_booking_sms(self, request, pk=None):
        booking = self.get_object()
        sms_code = request.query_params.get("sms_code")
        if not sms_code:
            return Response(
                {"error": "You have to enter sms code to confirm booking"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if sms_code == booking.sms_code:
            booking.confirmed = True
            booking.save()
            return Response(
                {"message": "Booking confirmed successfully"}, status=status.HTTP_200_OK
            )
        else:
            return Response(
                {"error": "Sms code is incorrect"}, status=status.HTTP_400_BAD_REQUEST
            )

    @action(
        detail=True,
        methods=["get"],
        permission_classes=[permissions.AllowAny],
        url_path="request-cancel-booking-sms",
    )
    def request_cancel_booking_sms(self, request, pk=None):
        booking = self.get_object()
        if not booking.confirmed:
            return Response(
                {"error": "Booking is not confirmed, cannot cancel"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        sms_code = generate_random_4_digit_number()
        booking.sms_code = sms_code
        booking.save()

        print(sms_code)
        return Response(
            {"message": "Cancellation SMS sent successfully"}, status=status.HTTP_200_OK
        )

    @action(
        detail=True,
        methods=["post"],
        permission_classes=[permissions.AllowAny],
        url_path="cancel-booking-sms",
    )
    def cancel_booking_sms(self, request, pk=None):
        booking = self.get_object()
        sms_code = request.query_params.get("sms_code")
        if not sms_code:
            return Response(
                {"error": "You have to enter sms code to cancel booking"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if sms_code == booking.sms_code:
            booking.delete()
            return Response(
                {"message": "Booking cancelled successfully"}, status=status.HTTP_200_OK
            )
        else:
            return Response(
                {"error": "Sms code is incorrect"}, status=status.HTTP_400_BAD_REQUEST
            )


class BonusBalanceView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        bathhouse_id = request.query_params.get("bathhouse_id")
        phone = request.query_params.get("phone")

        if not bathhouse_id or not phone:
            return Response(
                {"error": "bathhouse_id and phone are required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            bathhouse_id_int = int(bathhouse_id)
        except (TypeError, ValueError):
            return Response(
                {"error": "bathhouse_id must be an integer"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        account = (
            BonusAccount.objects.filter(bathhouse_id=bathhouse_id_int, phone=phone)
            .only("id", "balance")
            .first()
        )

        balance = str(account.balance) if account else "0.00"
        return Response({"bathhouse_id": bathhouse_id_int, "phone": phone, "balance": balance})


class BonusTransactionsView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        bathhouse_id = request.query_params.get("bathhouse_id")
        phone = request.query_params.get("phone")

        if not bathhouse_id or not phone:
            return Response(
                {"error": "bathhouse_id and phone are required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            bathhouse_id_int = int(bathhouse_id)
        except (TypeError, ValueError):
            return Response(
                {"error": "bathhouse_id must be an integer"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        account = (
            BonusAccount.objects.filter(bathhouse_id=bathhouse_id_int, phone=phone)
            .only("id")
            .first()
        )

        if not account:
            return Response({"bathhouse_id": bathhouse_id_int, "phone": phone, "transactions": []})

        txs = (
            BonusTransaction.objects.filter(account=account)
            .order_by("-id")
            .values("type", "amount", "booking_id", "created_at")
        )

        data = [
            {
                "type": tx["type"],
                "amount": str(tx["amount"]),
                "booking": tx["booking_id"],
                "created_at": tx["created_at"],
            }
            for tx in txs
        ]

        return Response({"bathhouse_id": bathhouse_id_int, "phone": phone, "transactions": data})

    # Booking-related actions do not belong in this APIView.
