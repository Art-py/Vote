"""Application services for state-changing voting operations."""

from dataclasses import dataclass

from django.db import transaction
from django.db.models import F

from .choices import VotingStatus
from .models import Participation, Voting


class VotingNotActiveError(Exception):
    """Raised when a vote is attempted outside the active period."""


@dataclass(frozen=True, slots=True)
class VoteResult:
    character_id: int
    vote_count: int
    voting_status: VotingStatus


@transaction.atomic
def cast_vote(*, voting_id: int, character_id: int) -> VoteResult:
    """Atomically add one anonymous vote after locking the voting."""
    voting = Voting.objects.select_for_update().get(pk=voting_id)
    if not voting.is_active:
        raise VotingNotActiveError

    participation = Participation.objects.get(
        voting=voting,
        character_id=character_id,
    )
    Participation.objects.filter(pk=participation.pk).update(
        vote_count=F("vote_count") + 1
    )
    participation.refresh_from_db(fields=("vote_count",))

    return VoteResult(
        character_id=participation.character_id,
        vote_count=participation.vote_count,
        voting_status=voting.status,
    )
