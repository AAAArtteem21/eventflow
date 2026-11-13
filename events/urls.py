from rest_framework.routers import DefaultRouter
from .views import EventViewSets

router = DefaultRouter()

router.register(
    "events",
    EventViewSets,
    basename="event",
)
urlpatterns = router.urls
