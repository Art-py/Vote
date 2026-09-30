"""Admin registrations for the votings application."""

from django.contrib import admin
from django.db.models import Count, IntegerField, Max, Sum, Value
from django.db.models.functions import Coalesce

from .choices import VotingStatus
from .models import Character, Participation, Voting


class ParticipationInline(admin.TabularInline):
    model = Participation
    fields = ("character", "vote_count")
    readonly_fields = ("vote_count",)
    autocomplete_fields = ("character",)
    extra = 1


@admin.register(Voting)
class VotingAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "start_date",
        "end_date",
        "status_display",
        "participant_count_display",
        "total_votes_display",
    )
    search_fields = ("title",)
    date_hierarchy = "start_date"
    readonly_fields = (
        "status_display",
        "participant_count_display",
        "total_votes_display",
    )
    fieldsets = (
        (None, {"fields": ("title",)}),
        (
            "Период и завершение",
            {"fields": ("start_date", "end_date", "early_finish_votes")},
        ),
        (
            "Текущее состояние",
            {
                "fields": (
                    "status_display",
                    "participant_count_display",
                    "total_votes_display",
                )
            },
        ),
    )
    inlines = (ParticipationInline,)

    def get_queryset(self, request):
        return (
            super()
            .get_queryset(request)
            .annotate(
                _admin_participant_count=Count("participations"),
                _admin_total_votes=Coalesce(
                    Sum("participations__vote_count"),
                    Value(0),
                    output_field=IntegerField(),
                ),
                _admin_max_vote_count=Coalesce(
                    Max("participations__vote_count"),
                    Value(0),
                    output_field=IntegerField(),
                ),
            )
        )

    @admin.display(description="Статус")
    def status_display(self, obj: Voting | None) -> str:
        if obj is None:
            return "—"
        return VotingStatus(obj.status).label

    @admin.display(description="Участников", ordering="_admin_participant_count")
    def participant_count_display(self, obj: Voting | None) -> int:
        return obj.participant_count if obj is not None else 0

    @admin.display(description="Всего голосов", ordering="_admin_total_votes")
    def total_votes_display(self, obj: Voting | None) -> int:
        return obj.total_votes if obj is not None else 0


@admin.register(Character)
class CharacterAdmin(admin.ModelAdmin):
    list_display = ("last_name", "first_name", "patronymic", "age", "has_photo")
    search_fields = ("last_name", "first_name", "patronymic")
    ordering = ("last_name", "first_name", "patronymic")

    @admin.display(boolean=True, description="Фото")
    def has_photo(self, obj: Character) -> bool:
        return bool(obj.photo)
