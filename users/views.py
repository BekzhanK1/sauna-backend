from rest_framework import viewsets, permissions
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from rest_framework.response import Response
from .models import ExtraItem, Room, User, Bathhouse
from .serializers import (
    ExtraItemSerializer,
    RoomSerializer,
    UserSerializer,
    BathhouseSerializer,
)
from .permissions import IsSuperAdmin, IsBathAdminOrSuperAdmin


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
