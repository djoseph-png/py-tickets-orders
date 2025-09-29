# cinema/views.py
from datetime import date as date_cls

from rest_framework import permissions, viewsets

from .models import (
    Genre,
    Actor,
    Movie,
    CinemaHall,
    MovieSession,
    Order,
)
from .serializers import (
    GenreSerializer,
    ActorSerializer,
    MovieSerializer,
    MovieWriteSerializer,
    CinemaHallSerializer,
    MovieSessionListSerializer,
    MovieSessionDetailSerializer,
    MovieSessionWriteSerializer,
    OrderReadSerializer,
    OrderWriteSerializer,
)


class GenreViewSet(viewsets.ModelViewSet):
    queryset = Genre.objects.all()
    serializer_class = GenreSerializer
    # permissions.AllowAny já é o padrão (via settings), mas deixo explícito:
    permission_classes = [permissions.AllowAny]


class ActorViewSet(viewsets.ModelViewSet):
    queryset = Actor.objects.all()
    serializer_class = ActorSerializer
    permission_classes = [permissions.AllowAny]


class MovieViewSet(viewsets.ModelViewSet):
    queryset = Movie.objects.prefetch_related("genres", "actors").all()
    permission_classes = [permissions.AllowAny]

    def get_serializer_class(self):
        if self.action in ("create", "update", "partial_update"):
            return MovieWriteSerializer
        return MovieSerializer

    def get_queryset(self):
        qs = super().get_queryset()

        title = self.request.query_params.get("title")
        if title:
            qs = qs.filter(title__icontains=title)

        genres = self.request.query_params.get("genres")
        if genres:
            try:
                ids = [int(x) for x in genres.split(",") if x.strip()]
                if ids:
                    qs = qs.filter(genres__id__in=ids)
            except ValueError:
                pass

        actors = self.request.query_params.get("actors")
        if actors:
            try:
                ids = [int(x) for x in actors.split(",") if x.strip()]
                if ids:
                    qs = qs.filter(actors__id__in=ids)
            except ValueError:
                pass

        return qs.distinct()


class CinemaHallViewSet(viewsets.ModelViewSet):
    queryset = CinemaHall.objects.all()
    serializer_class = CinemaHallSerializer
    permission_classes = [permissions.AllowAny]


class MovieSessionViewSet(viewsets.ModelViewSet):
    queryset = (
        MovieSession.objects.select_related("movie", "cinema_hall")
        .prefetch_related("tickets")
        .all()
    )
    permission_classes = [permissions.AllowAny]
    # IMPORTANT: sem paginação aqui para os testes não quebrarem com KeyError: 0
    pagination_class = None

    def get_serializer_class(self):
        if self.action == "list":
            return MovieSessionListSerializer
        if self.action == "retrieve":
            return MovieSessionDetailSerializer
        return MovieSessionWriteSerializer

    def get_queryset(self):
        qs = super().get_queryset()

        movie_id = self.request.query_params.get("movie")
        if movie_id and movie_id.isdigit():
            qs = qs.filter(movie_id=int(movie_id))

        date_str = self.request.query_params.get("date")
        if date_str:
            try:
                date = date_cls.fromisoformat(date_str)  # YYYY-MM-DD
                qs = qs.filter(show_time__date=date)
            except ValueError:
                pass  # data inválida -> ignora filtro

        return qs


class OrderViewSet(viewsets.ModelViewSet):
    """
    Lista/cria pedidos do usuário autenticado.
    Mantém protegido, mesmo com DEFAULT AllowAny.
    """
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return (
            Order.objects.filter(user=self.request.user)
            .prefetch_related(
                "tickets",
                "tickets__movie_session",
                "tickets__movie_session__movie",
                "tickets__movie_session__cinema_hall",
            )
            .order_by("-created_at")
        )

    def get_serializer_class(self):
        if self.action == "create":
            return OrderWriteSerializer
        return OrderReadSerializer
