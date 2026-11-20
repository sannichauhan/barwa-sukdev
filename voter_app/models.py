from django.db import models


class StatusChoices(models.TextChoices):
    ACTIVE = "active", "Active"
    INACTIVE = "inactive", "Inactive"


class ElectionCategoryChoices(models.TextChoices):
    GENERAL = "general", "General"
    OBC = "obc", "OBC"


class Voter(models.Model):
    sr_no = models.CharField(max_length=50, blank=True, null=True)          # क्र०सं०
    house_no = models.CharField(max_length=50, blank=True, null=True)       # मकान नं०
    voter_name = models.CharField(max_length=150)                           # निर्वाचक का नाम
    guardian_name = models.CharField(max_length=150, blank=True, null=True) # पिता/पति/माता का नाम
    svn_no = models.CharField(max_length=50, unique=True)                   # एस०वी०एन० (यूनिक)
    gender = models.CharField(max_length=20, blank=True, null=True)         # लिंग
    age = models.IntegerField(blank=True, null=True)                        # आयु
    category = models.CharField(max_length=50, blank=True, null=True)       # वर्ग (जैसे General)
    caste = models.CharField(max_length=50, blank=True, null=True)          # जाति (जैसे Bhumihar)
    religion = models.CharField(max_length=50, blank=True, null=True)       # धर्म (जैसे Hindu)
    status = models.CharField(
        max_length=50,
        choices=StatusChoices.choices,
        default=StatusChoices.ACTIVE,
    )                                                                       # उपलब्धता (जैसे Active)

    def __str__(self):
        return f"{self.voter_name} ({self.svn_no})"


class Candidate(models.Model):
    name = models.CharField(max_length=150)
    election_category = models.CharField(
        max_length=20,
        choices=ElectionCategoryChoices.choices
    )
    symbol_name = models.CharField(max_length=100, blank=True, null=True)
    photo = models.ImageField(upload_to="candidates/", blank=True, null=True)

    def __str__(self):
        return f"{self.name} ({self.get_election_category_display()})"


class NewVote(models.Model):
    voter = models.ForeignKey(Voter, on_delete=models.CASCADE, related_name="new_votes")
    candidate = models.ForeignKey(Candidate, on_delete=models.CASCADE, related_name="new_votes")
    election_category = models.CharField(
        max_length=20,
        choices=ElectionCategoryChoices.choices
    )
    voted_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["voter", "election_category"],
                name="unique_new_vote_per_voter_per_category"
            )
        ]

    def save(self, *args, **kwargs):
        if self.candidate_id:
            self.election_category = self.candidate.election_category
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.voter.svn_no} -> {self.candidate.name} ({self.election_category})"