from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import BookingViewSet, BonusBalanceView, BonusTransactionsView

router = DefaultRouter()
router.register(r'bookings', BookingViewSet)

urlpatterns = [
    path('', include(router.urls)),
    path('bonus/balance/', BonusBalanceView.as_view(), name='bonus-balance'),
    path('bonus/transactions/', BonusTransactionsView.as_view(), name='bonus-transactions'),
]
