import re
from datetime import date
from datetime import date as dt_date
from datetime import datetime

from django.db.models import Prefetch, QuerySet
from rest_framework import mixins, viewsets
from rest_framework.pagination import PageNumberPagination

from .models import (
    Actor,
    CinemaHall,
    Genre,
    Movie,
    MovieSession,
    Order,
)
from .serializers import (
    ActorDetailSerializer,
    ActorListSerializer,
    CinemaHallDetailSerializer,
    CinemaHallSerializer,
    GenreSerializer,
    MovieCreateUpdateSerializer,
    MovieDetailSerializer,
    MovieListSerializer,
    MovieSessionCreateUpdateSerializer,
    MovieSessionDetailSerializer,
    MovieSessionListSerializer,
    OrderSerializer,
)


class DefaultPageNumberPagination(PageNumberPagination):
    page_size = 100
    page_size_query_param = "page_size"
    max_page_size = 1000


# =========================
# ACTOR
# =========================

class ActorViewSet(viewsets.ModelViewSet):
    queryset = Actor.objects.all().order_by("id")
    pagination_class = None

    def get_serializer_class(self):
        if self.action in ("retrieve", "create", "update", "partial_update"):
            return ActorDetailSerializer
        return ActorListSerializer


# =========================
# GENRE
# =========================

class GenreViewSet(viewsets.ModelViewSet):
    queryset = Genre.objects.all().order_by("id")
    serializer_class = GenreSerializer
    pagination_class = None


# =========================
# CINEMA HALL
# =========================

class CinemaHallViewSet(viewsets.ModelViewSet):
    queryset = CinemaHall.objects.all().order_by("id")
    pagination_class = None

    def get_serializer_class(self):
        if self.action == "retrieve":
            return CinemaHallDetailSerializer
        return CinemaHallSerializer


# =========================
# MOVIE
# =========================

class MovieViewSet(viewsets.ModelViewSet):
    pagination_class = None

    def get_serializer_class(self):
        if self.action in ("create", "update", "partial_update"):
            return MovieCreateUpdateSerializer
        if self.action == "retrieve":
            return MovieDetailSerializer
        return MovieListSerializer

    def get_queryset(self):
        qs = Movie.objects.all().order_by("id").prefetch_related(
            Prefetch("genres", queryset=Genre.objects.all().order_by("id")),
            Prefetch("actors", queryset=Actor.objects.all().order_by("id")),
        )

        actor_id = self.request.query_params.get("actors")
        genre_id = self.request.query_params.get("genres")
        title = self.request.query_params.get("title")

        if actor_id:
            try:
                qs = qs.filter(actors__id=int(actor_id))
            except ValueError:
                pass

        if genre_id:
            try:
                qs = qs.filter(genres__id=int(genre_id))
            except ValueError:
                pass

        if title:
            qs = qs.filter(title__icontains=title)

        return qs


# =========================
# MOVIE SESSION
# =========================

def _parse_date_param(raw: str):
    if not raw:
        return None
    st = str(raw).strip().replace("Z", "+00:00")

    # 1) qualquer "YYYY-MM-DD" embutido
    mo = re.search(r"(\d{4})-(\d{2})-(\d{2})", st)
    if mo:
        return dt_date(int(mo.group(1)), int(mo.group(2)), int(mo.group(3)))

    # 2) "DD-MM-YYYY"
    mo = re.search(r"(\d{2})-(\d{2})-(\d{4})", st)
    if mo:
        return dt_date(int(mo.group(3)), int(mo.group(2)), int(mo.group(1)))

    # 3) barras "YYYY/MM/DD" ou "DD/MM/YYYY"
    mo = re.search(r"(\d{4})/(\d{2})/(\d{2})", st)
    if mo:
        return dt_date(int(mo.group(1)), int(mo.group(2)), int(mo.group(3)))
    mo = re.search(r"(\d{2})/(\d{2})/(\d{4})", st)
    if mo:
        return dt_date(int(mo.group(3)), int(mo.group(2)), int(mo.group(1)))

    # 4) ISO puro de date
    try:
        return dt_date.fromisoformat(st)
    except Exception:
        pass

    # 5) datetime ISO (com ou sem timezone)
    try:
        return datetime.fromisoformat(st).date()
    except Exception:
        pass

    # 6) último recurso: antes do espaço/T
    try:
        head = st.split("T")[0].split(" ")[0]
        return dt_date.fromisoformat(head)
    except Exception:
        return None


class MovieSessionViewSet(viewsets.ModelViewSet):
    queryset = MovieSession.objects.select_related("movie", "cinema_hall").all()
    pagination_class = None

    def get_serializer_class(self):
        if self.action in ("create", "update", "partial_update"):
            return MovieSessionCreateUpdateSerializer
        if self.action == "retrieve":
            return MovieSessionDetailSerializer
        return MovieSessionListSerializer

    def get_queryset(self) -> QuerySet:
        qs = super().get_queryset()
        params = getattr(self.request, "query_params", {})

        movie_param = params.get("movie")
        date_param = params.get("date")

        # Filtrar por movie id se válido
        if movie_param:
            try:
                movie_id = int(movie_param)
                qs = qs.filter(movie_id=movie_id)
            except (TypeError, ValueError):
                # Se não for inteiro, não retorna nada para manter semântica previsível
                qs = qs.none()

        # Filtrar por data (aceitando YYYY-MM-DD ou YYYY-M-D)
        if date_param:
            parsed_date = None
            # Tentar com zero à esquerda
            for fmt in ("%Y-%m-%d", "%Y-%m-%d"):
                try:
                    parsed_date = datetime.strptime(date_param, fmt).date()
                    break
                except ValueError:
                    pass
            if parsed_date is None:
                # Tentar formato flexível YYYY-M-D
                try:
                    y, m, d = date_param.split("-")
                    parsed_date = date(int(y), int(m), int(d))
                except Exception:
                    parsed_date = None
            if parsed_date is not None:
                qs = qs.filter(show_time__date=parsed_date)
            else:
                # Se data inválida, não retorna nada (evita passar registros indevidos)
                qs = qs.none()

        return qs


# =========================
# ORDER
# =========================

class OrderViewSet(mixins.ListModelMixin,
                   mixins.CreateModelMixin,
                   viewsets.GenericViewSet):
    queryset = Order.objects.all().order_by("id").prefetch_related(
        "tickets",
        "tickets__movie_session",
        "tickets__movie_session__movie",
        "tickets__movie_session__cinema_hall",
    )
    serializer_class = OrderSerializer
    pagination_class = DefaultPageNumberPagination
