from rest_framework import serializers
from .models import ExtraItem, MenuCategory, Room, User, Bathhouse, BathhouseItem


class ExtraItemInputSerializer(serializers.Serializer):
    item = serializers.PrimaryKeyRelatedField(queryset=BathhouseItem.objects.all())
    quantity = serializers.IntegerField(min_value=1)


class RoomSerializer(serializers.ModelSerializer):
    class Meta:
        model = Room
        fields = "__all__"


class BathhouseItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = BathhouseItem
        fields = "__all__"


class ExtraItemSerializer(serializers.ModelSerializer):
    item = BathhouseItemSerializer(read_only=True)
    price_sum = serializers.SerializerMethodField()

    def get_price_sum(self, obj):
        return obj.item.price * obj.quantity if obj.item else 0

    class Meta:
        model = ExtraItem
        fields = "__all__"


class BathhouseSerializer(serializers.ModelSerializer):
    rooms = RoomSerializer(many=True, read_only=True)
    extra_items = ExtraItemSerializer(many=True, read_only=True)

    def validate(self, data):
        is_24_hours = data.get("is_24_hours")
        start_of_work = data.get("start_of_work")
        end_of_work = data.get("end_of_work")

        if is_24_hours is False:
            if not start_of_work or not end_of_work:
                raise serializers.ValidationError(
                    "Для режима не 24/7 необходимо указать время начала и окончания работы."
                )

        return data

    class Meta:
        model = Bathhouse
        fields = "__all__"

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        representation["owner"] = (
            {
                "id": instance.owner.id if instance.owner else None,
                "username": instance.owner.username if instance.owner else None,
                "email": instance.owner.email if instance.owner else None,
            }
            if instance.owner
            else None
        )
        return representation


class UserSerializer(serializers.ModelSerializer):
    bathhouses = BathhouseSerializer(many=True, read_only=True)
    password = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = ["id", "username", "email", "role", "bathhouses", "password"]

    def create(self, validated_data):
        password = validated_data.pop("password")
        user = User.objects.create_user(password=password, **validated_data)
        return user


class MenuCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = MenuCategory
        fields = "__all__"
