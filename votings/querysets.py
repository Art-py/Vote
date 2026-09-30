"""Reusable querysets for the votings domain."""

from django.db import models
from django.db.models.functions import Coalesce
from django.utils import timezone

from .choices import VotingStatus


class VotingQuerySet(models.QuerySet):
    def with_stats(self):
        """Annotate voting counters used by the admin and public API."""
        return self.annotate(
            participant_count=models.Count("participations"),
            total_votes=Coalesce(
                models.Sum("participations__vote_count"),
                models.Value(0),
                output_field=models.BigIntegerField(),
            ),
            max_vote_count=Coalesce(
                models.Max("participations__vote_count"),
                models.Value(0),
                output_field=models.IntegerField(),
            ),
        ).order_by("-start_date", "-pk")

    def filter_by_status(self, status: VotingStatus | str, *, at=None):
        """Filter by a dynamically calculated voting status."""
        status = VotingStatus(status)
        at = at or timezone.now()
        queryset = self.with_stats()

        if status == VotingStatus.SCHEDULED:
            return queryset.filter(start_date__gte=at)

        started = models.Q(start_date__lt=at)
        threshold_reached = models.Q(early_finish_votes__isnull=False) & models.Q(
            max_vote_count__gte=models.F("early_finish_votes")
        )

        if status == VotingStatus.ACTIVE:
            threshold_not_reached = models.Q(
                early_finish_votes__isnull=True
            ) | models.Q(max_vote_count__lt=models.F("early_finish_votes"))
            return queryset.filter(
                started,
                models.Q(end_date__gte=at),
                threshold_not_reached,
            )

        return queryset.filter(
            started,
            models.Q(end_date__lt=at) | threshold_reached,
        )
