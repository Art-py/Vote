"""API views for the votings application."""

from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import NotFound
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from .choices import VotingStatus
from .exceptions import Conflict
from .models import Participation, Voting
from .serializers import (
    ErrorSerializer,
    ParticipationSerializer,
    VoteRequestSerializer,
    VoteResponseSerializer,
    VotingSerializer,
    VotingStatusFilterSerializer,
)
from .services import VotingNotActiveError, cast_vote


@extend_schema_view(
    retrieve=extend_schema(
        summary="Получить голосование",
        responses={200: VotingSerializer, 404: ErrorSerializer},
        tags=["Голосования"],
    ),
)
class VotingViewSet(viewsets.ReadOnlyModelViewSet):
    """Read-only voting API with public actions for results and voting."""

    queryset = Voting.objects.all()
    serializer_class = VotingSerializer
    permission_classes = (AllowAny,)
    lookup_value_regex = r"\d+"

    def get_queryset(self):
        return Voting.objects.with_stats()

    def _paginated_response(self, queryset, serializer_class):
        page = self.paginate_queryset(queryset)
        context = self.get_serializer_context()
        if page is not None:
            serializer = serializer_class(page, many=True, context=context)
            return self.get_paginated_response(serializer.data)
        serializer = serializer_class(queryset, many=True, context=context)
        return Response(serializer.data)

    @extend_schema(
        summary="Получить список голосований",
        parameters=[VotingStatusFilterSerializer],
        responses={200: VotingSerializer(many=True), 400: ErrorSerializer},
        tags=["Голосования"],
    )
    def list(self, request, *args, **kwargs):
        filters = VotingStatusFilterSerializer(data=request.query_params)
        filters.is_valid(raise_exception=True)

        queryset = self.filter_queryset(self.get_queryset())
        voting_status = filters.validated_data.get("status")
        if voting_status:
            queryset = queryset.filter_by_status(voting_status)

        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    @extend_schema(
        summary="Получить участников голосования",
        responses={
            200: ParticipationSerializer(many=True),
            404: ErrorSerializer,
        },
        tags=["Голосования"],
    )
    @action(detail=True, methods=("get",))
    def participants(self, request, *args, **kwargs):
        voting = self.get_object()
        queryset = voting.participations.select_related("character")
        return self._paginated_response(queryset, ParticipationSerializer)

    @extend_schema(
        summary="Получить победителей голосования",
        responses={
            200: ParticipationSerializer(many=True),
            404: ErrorSerializer,
            409: ErrorSerializer,
        },
        tags=["Голосования"],
    )
    @action(detail=True, methods=("get",))
    def winners(self, request, *args, **kwargs):
        voting = self.get_object()
        if voting.status != VotingStatus.FINISHED:
            raise Conflict(
                detail="Голосование ещё не завершено.",
                code="voting_not_finished",
            )
        return self._paginated_response(
            voting.get_winners(),
            ParticipationSerializer,
        )

    @extend_schema(
        summary="Проголосовать за персонажа",
        request=VoteRequestSerializer,
        responses={
            200: VoteResponseSerializer,
            400: ErrorSerializer,
            404: ErrorSerializer,
            409: ErrorSerializer,
        },
        tags=["Голосования"],
    )
    @action(
        detail=True,
        methods=("post",),
        serializer_class=VoteRequestSerializer,
    )
    def vote(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            result = cast_vote(
                voting_id=self.kwargs[self.lookup_field],
                character_id=serializer.validated_data["character_id"],
            )
        except Voting.DoesNotExist as exc:
            raise NotFound(
                detail="Голосование не найдено.",
                code="not_found",
            ) from exc
        except Participation.DoesNotExist as exc:
            raise NotFound(
                detail="Персонаж не участвует в этом голосовании.",
                code="participant_not_found",
            ) from exc
        except VotingNotActiveError as exc:
            raise Conflict(
                detail="Голосование сейчас не активно.",
                code="voting_not_active",
            ) from exc

        response_serializer = VoteResponseSerializer(
            {
                "message": "Ваш голос учтен",
                "character_id": result.character_id,
                "vote_count": result.vote_count,
                "voting_status": result.voting_status,
            }
        )
        return Response(response_serializer.data, status=status.HTTP_200_OK)
