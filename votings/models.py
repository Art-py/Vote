"""Domain models for the votings application."""

from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models
from django.db.models import Max, QuerySet, Sum
from django.utils import timezone

from .choices import VotingStatus


class Character(models.Model):
    """A candidate who can participate in multiple votings."""

    last_name = models.CharField("фамилия", max_length=150)
    first_name = models.CharField("имя", max_length=150)
    patronymic = models.CharField("отчество", max_length=150, blank=True)
    photo = models.ImageField(
        "фотография",
        upload_to="characters/",
        blank=True,
    )
    age = models.PositiveSmallIntegerField(
        "возраст",
        validators=[MinValueValidator(1)],
    )
    bio = models.TextField("биография")

    class Meta:
        ordering = ("last_name", "first_name", "patronymic")
        verbose_name = "персонаж"
        verbose_name_plural = "персонажи"
        constraints = [
            models.CheckConstraint(
                condition=models.Q(age__gt=0),
                name="character_age_positive",
            ),
        ]

    @property
    def full_name(self) -> str:
        return " ".join(
            part for part in (self.last_name, self.first_name, self.patronymic) if part
        )

    def __str__(self) -> str:
        return self.full_name


class Voting(models.Model):
    """A time-limited voting containing a set of characters."""

    title = models.CharField("название", max_length=255)
    start_date = models.DateTimeField("дата начала")
    end_date = models.DateTimeField("дата окончания")
    early_finish_votes = models.PositiveIntegerField(
        "порог досрочного завершения",
        null=True,
        blank=True,
        validators=[MinValueValidator(1)],
        help_text="Пустое значение отключает досрочное завершение.",
    )
    characters = models.ManyToManyField(
        Character,
        through="Participation",
        related_name="votings",
        verbose_name="персонажи",
    )

    class Meta:
        ordering = ("-start_date", "-pk")
        verbose_name = "голосование"
        verbose_name_plural = "голосования"
        constraints = [
            models.CheckConstraint(
                condition=models.Q(start_date__lt=models.F("end_date")),
                name="voting_start_before_end",
            ),
            models.CheckConstraint(
                condition=(
                    models.Q(early_finish_votes__isnull=True)
                    | models.Q(early_finish_votes__gt=0)
                ),
                name="voting_early_finish_positive",
            ),
        ]

    def clean(self) -> None:
        super().clean()
        if self.start_date and self.end_date and self.start_date >= self.end_date:
            raise ValidationError(
                {"end_date": "Дата окончания должна быть позже даты начала."}
            )

    def _maximum_vote_count(self) -> int:
        if hasattr(self, "_admin_max_vote_count"):
            return self._admin_max_vote_count
        if not self.pk:
            return 0
        return (
            self.participations.aggregate(max_votes=Max("vote_count"))["max_votes"] or 0
        )

    @property
    def has_reached_early_finish(self) -> bool:
        return (
            self.early_finish_votes is not None
            and self._maximum_vote_count() >= self.early_finish_votes
        )

    @property
    def status(self) -> VotingStatus:
        now = timezone.now()
        if now <= self.start_date:
            return VotingStatus.SCHEDULED
        if now > self.end_date or self.has_reached_early_finish:
            return VotingStatus.FINISHED
        return VotingStatus.ACTIVE

    @property
    def is_active(self) -> bool:
        return self.status == VotingStatus.ACTIVE

    @property
    def participant_count(self) -> int:
        if hasattr(self, "_admin_participant_count"):
            return self._admin_participant_count
        if not self.pk:
            return 0
        return self.participations.count()

    @property
    def total_votes(self) -> int:
        if hasattr(self, "_admin_total_votes"):
            return self._admin_total_votes
        if not self.pk:
            return 0
        return self.participations.aggregate(total=Sum("vote_count"))["total"] or 0

    def get_winners(self) -> QuerySet["Participation"]:
        """Return all leaders of a finished voting, excluding a zero-vote tie."""
        if not self.pk or self.status != VotingStatus.FINISHED:
            return Participation.objects.none()

        maximum_vote_count = self._maximum_vote_count()
        if maximum_vote_count == 0:
            return self.participations.none()

        return self.participations.filter(vote_count=maximum_vote_count).select_related(
            "character"
        )

    def __str__(self) -> str:
        return self.title


class Participation(models.Model):
    """A character's participation and vote counter within one voting."""

    voting = models.ForeignKey(
        Voting,
        on_delete=models.CASCADE,
        related_name="participations",
        verbose_name="голосование",
    )
    character = models.ForeignKey(
        Character,
        on_delete=models.PROTECT,
        related_name="participations",
        verbose_name="персонаж",
    )
    vote_count = models.PositiveIntegerField("количество голосов", default=0)

    class Meta:
        ordering = ("-vote_count", "character__last_name", "character__first_name")
        verbose_name = "участник"
        verbose_name_plural = "участники"
        constraints = [
            models.UniqueConstraint(
                fields=("voting", "character"),
                name="unique_voting_character",
            ),
            models.CheckConstraint(
                condition=models.Q(vote_count__gte=0),
                name="participation_vote_count_nonnegative",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.character} — {self.voting}"
