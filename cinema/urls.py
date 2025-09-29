from django.urls import path, include
from rest_framework.routers import DefaultRouter

from cinema.views import MovieViewSet, MovieSessionViewSet, OrderViewSet

router = DefaultRouter()
router.register("movies", MovieViewSet, basename="movie")
router.register("movie_sessions", MovieSessionViewSet, basename="movie-session")
router.register("orders", OrderViewSet, basename="order")

urlpatterns = [
    path("", include(router.urls)),
]
