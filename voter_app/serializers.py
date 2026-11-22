from django.db import IntegrityError
from rest_framework import serializers
from .models import Candidate, ElectionCategoryChoices, NewVote, StatusChoices, Voter


class VoterSerializer(serializers.ModelSerializer):
    class Meta:
        model = Voter
        fields = [
            "id",
            "sr_no",
            "house_no",
            "voter_name",
            "guardian_name",
            "svn_no",
            "gender",
            "age",
            "category",
            "caste",
            "religion",
            "status",
        ]


class CandidateSerializer(serializers.ModelSerializer):
    vote_count = serializers.IntegerField(read_only=True)
    election_category_display = serializers.CharField(
        source="get_election_category_display", read_only=True
    )

    class Meta:
        model = Candidate
        fields = [
            "id",
            "name",
            "election_category",
            "election_category_display",
            "symbol_name",
            "photo",
            "vote_count",
        ]


class NewVoteSerializer(serializers.ModelSerializer):
    voter_svn_no = serializers.CharField(source="voter.svn_no", read_only=True)
    voter_name = serializers.CharField(source="voter.voter_name", read_only=True)
    candidate_name = serializers.CharField(source="candidate.name", read_only=True)

    class Meta:
        model = NewVote
        fields = [
            "id",
            "voter",
            "voter_svn_no",
            "voter_name",
            "candidate",
            "candidate_name",
            "election_category",
            "voted_at",
        ]
        read_only_fields = ["voted_at"]
        # Disable DRF's default UniqueTogetherValidator so our custom validation &
        # database constraint handle duplicate votes cleanly with clear error messages.
        validators = []

    def validate(self, attrs):
        voter = attrs.get("voter") or getattr(self.instance, "voter", None)
        candidate = attrs.get("candidate") or getattr(self.instance, "candidate", None)
        election_category = attrs.get("election_category")

        if voter and voter.status == StatusChoices.INACTIVE:
            raise serializers.ValidationError(
                {"voter": "Inactive voters are not permitted to cast a vote."}
            )

        if candidate:
            if election_category and election_category != candidate.election_category:
                raise serializers.ValidationError(
                    {
                        "election_category": (
                            f"Candidate belongs to '{candidate.election_category}', "
                            f"not '{election_category}'."
                        )
                    }
                )
            attrs["election_category"] = candidate.election_category
            election_category = candidate.election_category

        if voter and election_category:
            qs = NewVote.objects.filter(voter=voter, election_category=election_category)
            if self.instance:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise serializers.ValidationError(
                    {
                        "non_field_errors": [
                            f"Voter ({voter.svn_no}) has already voted in the "
                            f"'{election_category}' category."
                        ]
                    }
                )

        return attrs

    def create(self, validated_data):
        try:
            return super().create(validated_data)
        except IntegrityError:
            raise serializers.ValidationError(
                {
                    "non_field_errors": [
                        "Duplicate vote detected for this voter and election category."
                    ]
                }
            )