from django.db import IntegrityError, transaction
from rest_framework import serializers

from cinema.models import (
    Genre,
    Actor,
    Movie,
    CinemaHall,
    MovieSession,
    Ticket,
    Order,
)

# ---------------------------------------------------------------------
# Base serializers para uso aninhado
# ---------------------------------------------------------------------


class GenreNameSerializer(serializers.ModelSerializer):
    class Meta:
        model = Genre
        fields = ("name",)


class ActorNameSerializer(serializers.ModelSerializer):
    class Meta:
        model = Actor
        fields = ("first_name", "last_name")

    def to_representation(self, instance):
        # Exibe "F L" como no enunciado
        return f"{instance.first_name} {instance.last_name}".strip()


# ---------------------------------------------------------------------
# CRUD simples (read/write) para Genre e Actor
# ---------------------------------------------------------------------

class GenreSerializer(serializers.ModelSerializer):
    class Meta:
        model = Genre
        fields = ("id", "name")


class ActorSerializer(serializers.ModelSerializer):
    class Meta:
        model = Actor
        fields = ("id", "first_name", "last_name")


# ---------------------------------------------------------------------
# Movies
#   - leitura com nomes
#   - escrita com IDs (PKs)
# ---------------------------------------------------------------------

class MovieSerializer(serializers.ModelSerializer):
    genres = serializers.SlugRelatedField(
        many=True, read_only=True, slug_field="name"
    )
    actors = ActorNameSerializer(many=True, read_only=True)

    class Meta:
        model = Movie
        fields = ("id", "title", "description", "duration", "genres", "actors")


class MovieWriteSerializer(serializers.ModelSerializer):
    genres = serializers.PrimaryKeyRelatedField(
        queryset=Genre.objects.all(), many=True
    )
    actors = serializers.PrimaryKeyRelatedField(
        queryset=Actor.objects.all(), many=True
    )

    class Meta:
        model = Movie
        fields = ("id", "title", "description", "duration", "genres", "actors")


# ---------------------------------------------------------------------
# Cinema Hall
#   - capacity é somente leitura (propriedade do model). Removido source='capacity'
# ---------------------------------------------------------------------

class CinemaHallSerializer(serializers.ModelSerializer):
    # capacity é uma @property no model → apenas leitura
    capacity = serializers.IntegerField(read_only=True)

    class Meta:
        model = CinemaHall
        fields = ("id", "name", "rows", "seats_in_row", "capacity")


# ---------------------------------------------------------------------
# MovieSession
#   - list/detail para leitura
#   - write com PKs
# ---------------------------------------------------------------------


class MovieSessionListSerializer(serializers.ModelSerializer):
    movie_title = serializers.CharField(source="movie.title", read_only=True)
    cinema_hall_name = serializers.CharField(
        source="cinema_hall.name", read_only=True
    )
    cinema_hall_capacity = serializers.IntegerField(
        source="cinema_hall.capacity", read_only=True
    )
    tickets_available = serializers.SerializerMethodField()

    class Meta:
        model = MovieSession
        fields = (
            "id",
            "show_time",
            "movie_title",
            "cinema_hall_name",
            "cinema_hall_capacity",
            "tickets_available",
        )

    def get_tickets_available(self, obj: MovieSession) -> int:
        taken = obj.tickets.count()
        return obj.cinema_hall.capacity - taken


class MovieSessionDetailSerializer(serializers.ModelSerializer):
    movie = MovieSerializer(read_only=True)
    cinema_hall = CinemaHallSerializer(read_only=True)
    taken_places = serializers.SerializerMethodField()

    class Meta:
        model = MovieSession
        fields = ("id", "show_time", "movie", "cinema_hall", "taken_places")

    def get_taken_places(self, obj: MovieSession):
        return list(
            obj.tickets.values("row", "seat").order_by("row", "seat")
        )


class MovieSessionWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = MovieSession
        fields = ("id", "movie", "cinema_hall", "show_time")


# ---------------------------------------------------------------------
# Tickets / Orders
# ---------------------------------------------------------------------

class TicketReadSerializer(serializers.ModelSerializer):
    movie_session = MovieSessionListSerializer(read_only=True)

    class Meta:
        model = Ticket
        fields = ("id", "row", "seat", "movie_session")


class TicketWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Ticket
        fields = ("row", "seat", "movie_session")

    def validate(self, attrs):
        ms: MovieSession = attrs["movie_session"]
        row = attrs["row"]
        seat = attrs["seat"]

        # 1) Dentro dos limites do hall
        if not (1 <= row <= ms.cinema_hall.rows):
            raise serializers.ValidationError(
                {"row": "Row out of range for this hall."}
            )
        if not (1 <= seat <= ms.cinema_hall.seats_in_row):
            raise serializers.ValidationError(
                {"seat": "Seat out of range for this hall."}
            )

        # 2) Lugar já ocupado?
        taken = Ticket.objects.filter(
            movie_session=ms, row=row, seat=seat
        ).exists()
        if taken:
            raise serializers.ValidationError("This place is already taken.")

        return attrs


class OrderReadSerializer(serializers.ModelSerializer):
    tickets = TicketReadSerializer(many=True, read_only=True)

    class Meta:
        model = Order
        fields = ("id", "tickets", "created_at")


class OrderWriteSerializer(serializers.ModelSerializer):
    tickets = TicketWriteSerializer(many=True)

    class Meta:
        model = Order
        fields = ("tickets",)

    def create(self, validated_data):
        user = self.context["request"].user
        tickets_data = validated_data.pop("tickets", [])

        # valida duplicidades dentro do mesmo payload
        seen = set()
        for ticket_data in tickets_data:
            key = (
                ticket_data["movie_session"].id,
                ticket_data["row"],
                ticket_data["seat"],
            )
            if key in seen:
                raise serializers.ValidationError(
                    "Duplicate tickets in request."
                )
            seen.add(key)

        try:
            # tudo ou nada: se der IntegrityError, nem o Order é criado
            with transaction.atomic():
                order = Order.objects.create(user=user)
                Ticket.objects.bulk_create(
                    [Ticket(order=order, **ticket_data) for ticket_data in tickets_data]
                )
        except IntegrityError:
            # traduz erro de unicidade/concorrência para 400
            raise serializers.ValidationError(
                "Some of these seats are already taken."
            )

        return order
