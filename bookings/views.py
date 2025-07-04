from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from .models import Booking
from .serializers import BookingSerializer
from users.permissions import IsBathAdminOrSuperAdmin


class BookingViewSet(viewsets.ModelViewSet):
    queryset = Booking.objects.all()
    serializer_class = BookingSerializer

    def get_permissions(self):
        if self.action in ["update", "partial_update", "destroy", "confirm_booking"]:
            return [IsBathAdminOrSuperAdmin()]
        return [permissions.AllowAny()]

    def get_queryset(self):
        user = self.request.user
        if user.is_authenticated and user.role == "superadmin":
            return Booking.objects.all()
        elif user.is_authenticated and user.role == "bath_admin":
            return Booking.objects.filter(bathhouse__owner=user)
        else:
            return Booking.objects.filter(
                sms_code=self.request.query_params.get("sms_code", "")
            )

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

    @action(
        detail=True,
        methods=["post"],
        permission_classes=[IsBathAdminOrSuperAdmin],
        url_name="confirm-booking-admin",
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
        print(pk)
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
