# cinema/urls.py
from rest_framework.routers import DefaultRouter
from .views import (
    ActorViewSet,
    CinemaHallViewSet,
    GenreViewSet,
    MovieViewSet,
    MovieSessionViewSet,
    OrderViewSet,
)

router = DefaultRouter()
router.register(r"actors", ActorViewSet)
router.register(r"genres", GenreViewSet)
router.register(r"cinema_halls", CinemaHallViewSet)
router.register(r"movies", MovieViewSet)
router.register(r"movie_sessions", MovieSessionViewSet, basename="movie-session")
router.register(r"orders", OrderViewSet, basename="order")

urlpatterns = router.urls
