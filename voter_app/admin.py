from django import forms
from django.contrib import admin, messages
from django.shortcuts import render, redirect
from django.db import transaction
from .models import Voter, Candidate, NewVote, ElectionCategoryChoices


# 1. Admin Action के लिए Custom Form (Single Category + Candidate)
class BulkSurveyForm(forms.Form):
    _selected_action = forms.CharField(widget=forms.MultipleHiddenInput)
    election_category = forms.ChoiceField(
        choices=ElectionCategoryChoices.choices,
        label="1. चुनाव वर्ग चुनें (Category)"
    )
    candidate = forms.ModelChoiceField(
        queryset=Candidate.objects.all(),
        label="2. प्रत्याशी चुनें (Candidate)"
    )


# 2. Voter Admin (यहाँ से Multiple Voters सेलेक्ट करके Survey कर सकते हैं)
@admin.register(Voter)
class VoterAdmin(admin.ModelAdmin):
    list_display = ("sr_no", "house_no", "voter_name", "guardian_name", "svn_no", "caste", "category", "status")
    list_filter = ("status", "category", "caste", "gender")
    search_fields = ("voter_name", "guardian_name", "svn_no", "house_no")
    actions = ["conduct_bulk_survey"]

    @admin.action(description="चुने गए Voters का Survey करें (Assign Candidate)")
    def conduct_bulk_survey(self, request, queryset):
        # अगर फॉर्म सबमिट हो चुका है
        if "apply" in request.POST:
            form = BulkSurveyForm(request.POST)
            if form.is_valid():
                category = form.cleaned_data["election_category"]
                candidate = form.cleaned_data["candidate"]

                # Validate कि Candidate उसी Category का है या नहीं
                if candidate.election_category != category:
                    self.message_user(
                        request,
                        f"Error: {candidate.name} '{category}' वर्ग का प्रत्याशी नहीं है!",
                        level=messages.ERROR
                    )
                    return redirect(request.get_full_path())

                votes_to_create = []
                skipped_count = 0

                for voter in queryset:
                    # Check कि पहले से इस category में सर्वे तो नहीं हुआ
                    if not NewVote.objects.filter(voter=voter, election_category=category).exists():
                        votes_to_create.append(
                            NewVote(
                                voter=voter,
                                candidate=candidate,
                                election_category=category
                            )
                        )
                    else:
                        skipped_count += 1

                with transaction.atomic():
                    NewVote.objects.bulk_create(votes_to_create)

                msg = f"{len(votes_to_create)} Voters का सर्वे ({candidate.name} - {category.upper()}) सफलतापूर्वक सेव हो गया।"
                if skipped_count > 0:
                    msg += f" ({skipped_count} Voters का सर्वे इस वर्ग में पहले से हो चुका था, उन्हें छोड़ दिया गया।)"
                
                self.message_user(request, msg, level=messages.SUCCESS)
                return redirect(request.get_full_path())

        # पहली बार Action चुनने पर Form दिखाएं
        form = BulkSurveyForm(
            initial={"_selected_action": queryset.values_list("id", flat=True)}
        )
        return render(
            request,
            "admin/bulk_survey_action.html",
            {
                "voters": queryset,
                "form": form,
                "title": "Bulk Election Survey",
            },
        )


# 3. Candidate Admin
@admin.register(Candidate)
class CandidateAdmin(admin.ModelAdmin):
    list_display = ("name", "election_category", "symbol_name", "total_votes")
    list_filter = ("election_category",)
    search_fields = ("name", "symbol_name")

    @admin.display(description="कुल सर्वे वोट")
    def total_votes(self, obj):
        return obj.new_votes.count()


# 4. NewVote Admin (Single Form से Multiple Voters जोड़ने के लिए)
class NewVoteMultiVoterForm(forms.ModelForm):
    voters = forms.ModelMultipleChoiceField(
        queryset=Voter.objects.filter(status="active"),
        widget=admin.widgets.FilteredSelectMultiple("Voters", is_stacked=False),
        label="Voters चुनें (Multiple Select)",
        required=True
    )

    class Meta:
        model = NewVote
        fields = ["election_category", "candidate", "voters"]

    def clean(self):
        cleaned_data = super().clean()
        category = cleaned_data.get("election_category")
        candidate = cleaned_data.get("candidate")

        if candidate and category and candidate.election_category != category:
            raise forms.ValidationError(
                f"चुना गया प्रत्याशी '{candidate.name}' {category.upper()} वर्ग का नहीं है।"
            )
        return cleaned_data


@admin.register(NewVote)
class NewVoteAdmin(admin.ModelAdmin):
    list_display = ("voter", "candidate", "election_category", "voted_at")
    list_filter = ("election_category", "candidate")
    search_fields = ("voter__voter_name", "voter__svn_no", "candidate__name")

    def get_form(self, request, obj=None, **kwargs):
        # नया रिकॉर्ड बनाते समय (Add) Multiple Voters वाला फॉर्म दिखाएं
        if obj is None:
            return NewVoteMultiVoterForm
        return super().get_form(request, obj, **kwargs)

    def save_model(self, request, obj, form, change):
        if not change and "voters" in form.cleaned_data:
            voters = form.cleaned_data["voters"]
            candidate = form.cleaned_data["candidate"]
            category = form.cleaned_data["election_category"]

            votes_to_create = [
                NewVote(voter=voter, candidate=candidate, election_category=category)
                for voter in voters
                if not NewVote.objects.filter(voter=voter, election_category=category).exists()
            ]
            NewVote.objects.bulk_create(votes_to_create)
        else:
            super().save_model(request, obj, form, change)