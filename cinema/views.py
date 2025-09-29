from datetime import datetime
from rest_framework import viewsets, mixins
from rest_framework.permissions import IsAuthenticated
from django.db.models import Prefetch, Count, Q

from cinema.models import Movie, MovieSession, Order, Ticket
from cinema.serializers import (
    MovieSerializer,
    MovieSessionListSerializer, MovieSessionDetailSerializer,
    OrderReadSerializer, OrderWriteSerializer
)


# ----- Movies -----

class MovieViewSet(mixins.ListModelMixin,
                   mixins.RetrieveModelMixin,
                   viewsets.GenericViewSet):
    queryset = Movie.objects.prefetch_related("genres", "actors").all()
    serializer_class = MovieSerializer

    def get_queryset(self):
        qs = super().get_queryset()

        # ?title=string (icontains)
        title = self.request.query_params.get("title")
        if title:
            qs = qs.filter(title__icontains=title)

        # ?genres=1,2,3 (IDs)
        genres = self.request.query_params.get("genres")
        if genres:
            ids = [int(x) for x in genres.split(",") if x.isdigit()]
            if ids:
                qs = qs.filter(genres__id__in=ids).distinct()

        # ?actors=4,5 (IDs)
        actors = self.request.query_params.get("actors")
        if actors:
            ids = [int(x) for x in actors.split(",") if x.isdigit()]
            if ids:
                qs = qs.filter(actors__id__in=ids).distinct()

        return qs


# ----- Movie Sessions -----

class MovieSessionViewSet(mixins.ListModelMixin,
                          mixins.RetrieveModelMixin,
                          viewsets.GenericViewSet):
    queryset = (
        MovieSession.objects
        .select_related("movie", "cinema_hall")
        .prefetch_related("tickets")
        .all()
    )

    def get_serializer_class(self):
        if self.action == "retrieve":
            return MovieSessionDetailSerializer
        return MovieSessionListSerializer

    def get_queryset(self):
        qs = super().get_queryset()

        # ?movie=<id>
        movie_id = self.request.query_params.get("movie")
        if movie_id and movie_id.isdigit():
            qs = qs.filter(movie_id=int(movie_id))

        # ?date=YYYY-MM-DD  (não dividir a data; comparar a parte de data)
        date_str = self.request.query_params.get("date")
        if date_str:
            qs = qs.filter(show_time__date=date_str)

        return qs


# ----- Orders -----

class OrderViewSet(mixins.ListModelMixin,
                   mixins.CreateModelMixin,
                   viewsets.GenericViewSet):
    permission_classes = (IsAuthenticated,)

    def get_queryset(self):
        return (
            Order.objects
            .filter(user=self.request.user)
            .prefetch_related(
                "tickets",
                "tickets__movie_session__movie",
                "tickets__movie_session__cinema_hall",
            )
            .order_by("id")
        )

    def get_serializer_class(self):
        return OrderWriteSerializer if self.action == "create" else OrderReadSerializer
