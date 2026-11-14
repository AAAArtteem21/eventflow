from rest_framework.routers import DefaultRouter

from .views import DeliveryAttemptViewSet, DeliveryViewSet

router = DefaultRouter()

router.register(
    r"deliveries",
    DeliveryViewSet,
    basename="delivery",
)

router.register(
    r"delivery-attempts",
    DeliveryAttemptViewSet,
    basename="delivery-attempt",
)

urlpatterns = router.urls