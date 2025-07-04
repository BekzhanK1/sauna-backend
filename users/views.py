from rest_framework import viewsets, permissions
from .models import ExtraItem, Room, User, Bathhouse
from .serializers import ExtraItemSerializer, RoomSerializer, UserSerializer, BathhouseSerializer
from .permissions import IsSuperAdmin, IsBathAdminOrSuperAdmin

class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [IsSuperAdmin]

class BathhouseViewSet(viewsets.ModelViewSet):
    queryset = Bathhouse.objects.all()
    serializer_class = BathhouseSerializer

    def get_permissions(self):
        if self.action in ['create']:
            return [IsSuperAdmin()]
        elif self.action in ['update', 'partial_update', 'destroy']:
            return [IsBathAdminOrSuperAdmin()]
        return [permissions.IsAuthenticated()]
    
    def get_queryset(self):
        user = self.request.user
        if user.role == 'superadmin':
            return Bathhouse.objects.all()
        return Bathhouse.objects.filter(owner=user)

class RoomViewSet(viewsets.ModelViewSet):
    queryset = Room.objects.all()
    serializer_class = RoomSerializer

    def get_permissions(self):
        if self.action in ['create']:
            return [IsBathAdminOrSuperAdmin()]
        elif self.action in ['update', 'partial_update', 'destroy']:
            return [IsBathAdminOrSuperAdmin()]
        return [permissions.IsAuthenticated()]
    
    def get_queryset(self):
        user = self.request.user
        if user.role == 'superadmin':
            return Room.objects.all()
        return Room.objects.filter(bathhouse__owner=user)
    


class ExtraItemViewSet(viewsets.ModelViewSet):
    queryset = ExtraItem.objects.all()
    serializer_class = ExtraItemSerializer

    def get_permissions(self):
        if self.action in ['create']:
            return [IsBathAdminOrSuperAdmin()]
        elif self.action in ['update', 'partial_update', 'destroy']:
            return [IsBathAdminOrSuperAdmin()]
        return [permissions.IsAuthenticated()]
    
    def get_queryset(self):
        user = self.request.user
        if user.role == 'superadmin':
            return ExtraItem.objects.all()
        return ExtraItem.objects.filter(bathhouse__owner=user)