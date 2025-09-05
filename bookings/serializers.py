from rest_framework import serializers
from .models import CONFIRMATION_TIMEOUT_MINUTES, Booking
from users.serializers import ExtraItemInputSerializer, ExtraItemSerializer
from users.models import BathhouseItem, ExtraItem, Room
from datetime import timedelta
from django.utils import timezone
from datetime import timezone as dt_timezone
from .utils import generate_random_4_digit_number
from .tasks import delete_unconfirmed_booking
import pytz


class BookingSerializer(serializers.ModelSerializer):
    extra_items_data = ExtraItemInputSerializer(
        many=True, write_only=True, required=False
    )
    extra_items = ExtraItemSerializer(many=True, read_only=True)

    class Meta:
        model = Booking
        fields = "__all__"

    def validate(self, data):
        room = data.get("room")
        start_time = data.get("start_time")
        hours = data.get("hours")
        phone = data.get("phone")

        if not all([room, start_time, hours, phone]):
            raise serializers.ValidationError("Все поля обязательны для заполнения.")

        now = timezone.now()

        if start_time < now:
            raise serializers.ValidationError("Нельзя бронировать на прошедшее время.")

        # Проверяем, что нельзя бронировать более чем за 15 дней
        max_days_ahead = 15
        latest_allowed = now + timedelta(days=max_days_ahead)
        if start_time > latest_allowed:
            raise serializers.ValidationError(
                f"Нельзя бронировать более чем за {max_days_ahead} дня вперёд."
            )

        if not isinstance(hours, int) or hours <= 0:
            raise serializers.ValidationError(
                "Количество часов должно быть положительным целым числом."
            )

        bathhouse = room.bathhouse
        if not bathhouse:
            raise serializers.ValidationError("Комната не принадлежит ни одной бане.")

        if not bathhouse.is_24_hours:
            # Convert UTC start_time to local time (UTC+5)
            local_tz = pytz.timezone("Asia/Almaty")  # Or your specific timezone
            local_start_time = timezone.localtime(start_time, timezone=local_tz)
            booking_time = local_start_time.time()

            work_start = bathhouse.start_of_work  # Already in local time (UTC+5)
            work_end = bathhouse.end_of_work  # Already in local time (UTC+5)

            if work_start < work_end:
                if not (work_start <= booking_time <= work_end):
                    raise serializers.ValidationError(
                        "Бронь должна быть в рабочее время бани."
                    )
            else:  # Overnight working hours
                if not (booking_time >= work_start or booking_time <= work_end):
                    raise serializers.ValidationError(
                        "Бронь должна быть в рабочее время бани."
                    )

        new_end_time = start_time + timedelta(hours=hours)

        # Проверяем пересечение с другими бронями в комнате
        for booking in Booking.objects.filter(room=room):
            existing_start = booking.start_time
            existing_end = booking.start_time + timedelta(hours=booking.hours)

            if start_time < existing_end and new_end_time > existing_start:
                raise serializers.ValidationError(
                    "Это время уже занято для этой комнаты."
                )

        # Проверяем активные бронирования по телефону
        active_bookings = Booking.objects.filter(
            phone=phone, start_time__lt=new_end_time
        ).exclude(start_time__gte=new_end_time)

        for booking in active_bookings:
            booking_end = booking.start_time + timedelta(hours=booking.hours)
            if booking_end > now:
                raise serializers.ValidationError(
                    "У вас уже есть активная бронь, пока она не закончится — нельзя бронировать новую."
                )

        extra_items_data = data.get("extra_items_data", [])
        # print(extra_items_data)
        if extra_items_data:
            for item_data in extra_items_data:
                # print(item_data)
                item_instance = item_data.get("item")
                if not item_instance:
                    raise serializers.ValidationError(
                        "Каждый товар должен быть указан с ID."
                    )
                if item_instance.bathhouse != bathhouse:
                    raise serializers.ValidationError(
                        "Товары должны принадлежать той же бане, что и комната."
                    )

        return data

    def create(self, validated_data):
        extra_items_data = validated_data.pop("extra_items_data", [])
        instance = Booking.objects.create(**validated_data)

        for item_data in extra_items_data:
            quantity = item_data["quantity"]

            bathhouse_item = item_data["item"]

            # Создаём ExtraItem
            ExtraItem.objects.create(
                item=bathhouse_item, quantity=quantity, booking=instance
            )

        # Calculate and save the final price
        instance.final_price = instance.calculate_final_price()

        sms_code = generate_random_4_digit_number()
        print(sms_code)
        instance.sms_code = sms_code
        instance.save()

        delete_unconfirmed_booking.apply_async(
            (instance.id,), countdown=60 * CONFIRMATION_TIMEOUT_MINUTES
        )

        return instance

    def to_representation(self, instance):
        representation = super().to_representation(instance)

        representation["bathhouse"] = {
            "id": instance.bathhouse.id,
            "name": instance.bathhouse.name,
        }
        representation["room"] = {
            "id": instance.room.id,
            "room_number": instance.room.room_number,
            "capacity": instance.room.capacity,
            "price_per_hour": str(instance.room.price_per_hour),
        }
        representation["room_full_price"] = str(
            instance.room.price_per_hour * instance.hours
        )
        # Use the saved final price if available, otherwise calculate dynamically
        representation["final_price"] = str(instance.get_final_price())

        return representation
