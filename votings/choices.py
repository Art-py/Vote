"""Reusable choices for the votings domain."""

from django.db import models


class VotingStatus(models.TextChoices):
    SCHEDULED = "scheduled", "Запланировано"
    ACTIVE = "active", "Активно"
    FINISHED = "finished", "Завершено"
