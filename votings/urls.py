"""Routes for the public voting API."""

from rest_framework.routers import SimpleRouter

from .views import VotingViewSet

app_name = "votings"

router = SimpleRouter()
router.register("votings", VotingViewSet, basename="voting")

urlpatterns = router.urls
