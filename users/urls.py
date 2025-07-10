from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import UserViewSet, BathhouseViewSet, RoomViewSet, ExtraItemViewSet, MeView
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

router = DefaultRouter()
router.register(r"users", UserViewSet)
router.register(r"bathhouses", BathhouseViewSet)
router.register(r"rooms", RoomViewSet)
router.register(r"extra-items", ExtraItemViewSet)

urlpatterns = [
    path("", include(router.urls)),
    path("token/", TokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    path("me/", MeView.as_view(), name="me"),
]
