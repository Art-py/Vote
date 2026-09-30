"""Serializers for the public voting API."""

from rest_framework import serializers

from .choices import VotingStatus
from .models import Character, Participation, Voting


class CharacterSerializer(serializers.ModelSerializer):
    full_name = serializers.CharField(read_only=True)

    class Meta:
        model = Character
        fields = (
            "id",
            "last_name",
            "first_name",
            "patronymic",
            "full_name",
            "photo",
            "age",
            "bio",
        )


class VotingSerializer(serializers.ModelSerializer):
    status = serializers.ChoiceField(choices=VotingStatus.choices, read_only=True)
    participant_count = serializers.IntegerField(read_only=True)
    total_votes = serializers.IntegerField(read_only=True)

    class Meta:
        model = Voting
        fields = (
            "id",
            "title",
            "start_date",
            "end_date",
            "early_finish_votes",
            "status",
            "participant_count",
            "total_votes",
        )


class ParticipationSerializer(serializers.ModelSerializer):
    character = CharacterSerializer(read_only=True)

    class Meta:
        model = Participation
        fields = ("character", "vote_count")


class VotingStatusFilterSerializer(serializers.Serializer):
    status = serializers.ChoiceField(
        choices=VotingStatus.choices,
        required=False,
    )


class VoteRequestSerializer(serializers.Serializer):
    character_id = serializers.IntegerField(min_value=1)


class VoteResponseSerializer(serializers.Serializer):
    message = serializers.CharField()
    character_id = serializers.IntegerField()
    vote_count = serializers.IntegerField()
    voting_status = serializers.ChoiceField(choices=VotingStatus.choices)


class ErrorSerializer(serializers.Serializer):
    code = serializers.CharField()
    detail = serializers.CharField()
    errors = serializers.JSONField(required=False)
