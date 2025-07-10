from django.utils import timezone
from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from .models import Booking
from .serializers import BookingSerializer
from .utils import generate_random_4_digit_number
from users.permissions import IsBathAdminOrSuperAdmin


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

        return super().list(request, *args, **kwargs)

    def create(self, request, *args, **kwargs):
        print(request.data)
        return super().create(request, *args, **kwargs)

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
        # Here you would typically send an SMS with a cancellation code
        # For simplicity, we will just return a success message
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
        print(pk)
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
