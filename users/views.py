from rest_framework import viewsets, permissions
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from rest_framework.response import Response
from .models import BathhouseItem, ExtraItem, MenuCategory, Room, User, Bathhouse
from .serializers import (
    BathhouseItemSerializer,
    ExtraItemSerializer,
    MenuCategorySerializer,
    RoomSerializer,
    UserSerializer,
    BathhouseSerializer,
)
from .permissions import IsSuperAdmin, IsBathAdminOrSuperAdmin
from .services.telegram import send_message
import html


class MeView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        serializer = UserSerializer(user)
        return Response(serializer.data)


class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [IsSuperAdmin]


class BathhouseViewSet(viewsets.ModelViewSet):
    queryset = Bathhouse.objects.all()
    serializer_class = BathhouseSerializer

    def get_permissions(self):
        if self.action in ["create"]:
            return [IsSuperAdmin()]
        elif self.action in ["update", "partial_update", "destroy"]:
            return [IsBathAdminOrSuperAdmin()]
        return [permissions.AllowAny()]

    def get_queryset(self):
        user = self.request.user
        if user.is_authenticated:
            if user.role == "superadmin":
                return Bathhouse.objects.all()
            return Bathhouse.objects.filter(owner=user)
        else:
            return Bathhouse.objects.all()

    def update(self, request, *args, **kwargs):
        response = super().update(request, *args, **kwargs)
        print(response.data)
        bathhouse_data = response.data

        text = (
            "<b>ОБНОВЛЕНИЕ БАНИ</b>\n"
            f"🆔 <b>ID:</b> {bathhouse_data['id']}\n"
            f"🏢 <b>Название:</b> {html.escape(bathhouse_data['name'])!s}\n"
            f"📝 <b>Описание:</b> {html.escape(bathhouse_data['description'] or '')}\n"
            f"📍 <b>Адрес:</b> {html.escape(bathhouse_data['address'] or '')}\n"
            f"📞 <b>Телефон:</b> {html.escape(bathhouse_data['phone'] or '')}\n"
            f"⏰ <b>Круглосуточно:</b> {'Да' if bathhouse_data['is_24_hours'] else 'Нет'}\n"
            f"🕒 <b>Часы работы:</b> {bathhouse_data['start_of_work']} – {bathhouse_data['end_of_work']}\n"
            f"👤 <b>Владелец:</b> {html.escape(bathhouse_data['owner']['username'] or '')}\n"
        )
        send_message(text=text)
        return response


class RoomViewSet(viewsets.ModelViewSet):
    queryset = Room.objects.all()
    serializer_class = RoomSerializer

    def get_permissions(self):
        if self.action in ["create"]:
            return [IsBathAdminOrSuperAdmin()]
        elif self.action in ["update", "partial_update", "destroy"]:
            return [IsBathAdminOrSuperAdmin()]
        return [permissions.AllowAny()]

    def get_queryset(self):
        user = self.request.user
        queryset = Room.objects.all()

        if user.is_authenticated and user.role == "superadmin":
            queryset = Room.objects.all()
        elif user.is_authenticated and user.role == "bath_admin":
            queryset = Room.objects.filter(bathhouse__owner=user)
        else:
            queryset = Room.objects.filter(is_available=True)

        bathhouse_id = self.request.query_params.get("bathhouse_id")
        if bathhouse_id:
            queryset = queryset.filter(bathhouse_id=bathhouse_id)

        return queryset


class BathhouseItemViewSet(viewsets.ModelViewSet):
    queryset = BathhouseItem.objects.all()
    serializer_class = BathhouseItemSerializer

    def get_permissions(self):
        if self.action in ["create"]:
            return [IsBathAdminOrSuperAdmin()]
        elif self.action in ["update", "partial_update", "destroy"]:
            return [IsBathAdminOrSuperAdmin()]
        return [permissions.AllowAny()]

    def get_queryset(self):
        user = self.request.user
        queryset = BathhouseItem.objects.all()

        if user.is_authenticated and user.role == "superadmin":
            queryset = BathhouseItem.objects.all()
        elif user.is_authenticated and user.role == "bath_admin":
            queryset = BathhouseItem.objects.filter(bathhouse__owner=user)
        else:
            queryset = BathhouseItem.objects.filter(is_available=True)

        bathhouse_id = self.request.query_params.get("bathhouse_id")
        if bathhouse_id:
            queryset = queryset.filter(bathhouse_id=bathhouse_id)

        return queryset


class ExtraItemViewSet(viewsets.ModelViewSet):
    queryset = ExtraItem.objects.all()
    serializer_class = ExtraItemSerializer

    def get_permissions(self):
        if self.action in ["create"]:
            return [IsBathAdminOrSuperAdmin()]
        elif self.action in ["update", "partial_update", "destroy"]:
            return [IsBathAdminOrSuperAdmin()]
        return [permissions.AllowAny()]

    def get_queryset(self):
        user = self.request.user
        if user.role == "superadmin":
            return ExtraItem.objects.all()
        return ExtraItem.objects.filter(bathhouse__owner=user)


class MenuCategoryViewSet(viewsets.ModelViewSet):
    queryset = MenuCategory.objects.all()
    serializer_class = MenuCategorySerializer

    def get_permissions(self):
        if self.action in ["create"]:
            return [IsBathAdminOrSuperAdmin()]
        elif self.action in ["update", "partial_update", "destroy"]:
            return [IsBathAdminOrSuperAdmin()]
        return [permissions.AllowAny()]

    def get_queryset(self):
        user = self.request.user
        queryset = MenuCategory.objects.all()

        if user.is_authenticated and user.role == "superadmin":
            queryset = MenuCategory.objects.all()
        elif user.is_authenticated and user.role == "bath_admin":
            queryset = MenuCategory.objects.filter(bathhouse__owner=user)
        else:
            queryset = MenuCategory.objects.all()

        bathhouse_id = self.request.query_params.get("bathhouse_id")
        if bathhouse_id:
            queryset = queryset.filter(bathhouse_id=bathhouse_id)

        return queryset
