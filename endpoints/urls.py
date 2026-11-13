from rest_framework.routers import DefaultRouter
from .views import EndpointViewSets

router = DefaultRouter()

router.register(
    r"endpoints",
    EndpointViewSets,
    basename="endpoint",
)
urlpatterns = router.urls
