import pandas as pd
from django.contrib import messages
from django.db import IntegrityError
from django.db import transaction
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, redirect, render
from rest_framework import filters, viewsets
from .serializers import CandidateSerializer, NewVoteSerializer, VoterSerializer
from .forms import ExcelUploadForm, VoterForm
from .models import (
    Candidate,
    ElectionCategoryChoices,
    NewVote,
    StatusChoices,
    Voter,
)


def voter_list_view(request):
    voters = Voter.objects.all()
    total_voters_count = voters.count()
    active_count = voters.filter(status__iexact=StatusChoices.ACTIVE).count()
    inactive_count = voters.filter(status__iexact=StatusChoices.INACTIVE).count()

    if total_voters_count > 0:
        active_percentage = round((active_count / total_voters_count) * 100, 1)
        inactive_percentage = round((inactive_count / total_voters_count) * 100, 1)
    else:
        active_percentage = 0
        inactive_percentage = 0

    # पुरुष और महिला मतदाताओं की कुल संख्या
    male_count = voters.filter(
        Q(gender__iexact='M')
        | Q(gender__iexact='Male')
        | Q(gender__icontains='पुरुष')
    ).count()
    female_count = voters.filter(
        Q(gender__iexact='F')
        | Q(gender__iexact='Female')
        | Q(gender__icontains='महिला')
    ).count()

    # वर्गवार (Category-wise) आंकड़े
    def get_cat_stats(cat_name):
        cat_voters = voters.filter(category__iexact=cat_name)
        count = cat_voters.count()
        share = (
            round((count / total_voters_count) * 100, 1)
            if total_voters_count > 0
            else 0
        )
        m = cat_voters.filter(
            Q(gender__iexact='M')
            | Q(gender__iexact='Male')
            | Q(gender__icontains='पुरुष')
        ).count()
        f = cat_voters.filter(
            Q(gender__iexact='F')
            | Q(gender__iexact='Female')
            | Q(gender__icontains='महिला')
        ).count()
        return count, share, m, f

    general_count, general_share, general_male, general_female = get_cat_stats('General')
    obc_count, obc_share, obc_male, obc_female = get_cat_stats('OBC')
    sc_count, sc_share, sc_male, sc_female = get_cat_stats('SC')
    st_count, st_share, st_male, st_female = get_cat_stats('ST')

    # 🟢 जातिवार (Caste-wise) आंकड़े निकालने का फ़ंक्शन
    def get_caste_stats(caste_name):
        caste_voters = voters.filter(caste__iexact=caste_name)
        count = caste_voters.count()
        share = (
            round((count / total_voters_count) * 100, 1)
            if total_voters_count > 0
            else 0
        )
        m = caste_voters.filter(
            Q(gender__iexact='M')
            | Q(gender__iexact='Male')
            | Q(gender__icontains='पुरुष')
        ).count()
        f = caste_voters.filter(
            Q(gender__iexact='F')
            | Q(gender__iexact='Female')
            | Q(gender__icontains='महिला')
        ).count()
        return count, share, m, f

    # प्रमुख जातियों के आंकड़े
    bhumihar_count, bhumihar_share, bhumihar_male, bhumihar_female = get_caste_stats('Bhumihar')
    pandit_count, pandit_share, pandit_male, pandit_female = get_caste_stats('Pandit')
    lonia_count, lonia_share, lonia_male, lonia_female = get_caste_stats('Lonia')
    ahir_count, ahir_share, ahir_male, ahir_female = get_caste_stats('Ahir')
    muslim_count, muslim_share, muslim_male, muslim_female = get_caste_stats('Muslim')

    prasad_count, prasad_share, prasad_male, prasad_female = get_caste_stats('Prasad')
    teli_count, teli_share, teli_male, teli_female = get_caste_stats('Teli')
    patel_count, patel_share, patel_male, patel_female = get_caste_stats('Kurmi')
    nishad_count, nishad_share, nishad_male, nishad_female = get_caste_stats('Nishad')
    gosai_count, gosai_share, gosai_male, gosai_female = get_caste_stats('Gosai')
    kamkar_count, kamkar_share, kamkar_male, kamkar_female = get_caste_stats('Kamkar')
    gond_count, gond_share, gond_male, gond_female = get_caste_stats('Gond')

    if request.method == 'POST':
        form = ExcelUploadForm(request.POST, request.FILES)
        if form.is_valid():
            excel_file = request.FILES['excel_file']
            try:
                df = pd.read_excel(excel_file)
                df = df.dropna(how='all')
                for index, row in df.iterrows():

                    def clean_val(val):
                        return str(val).strip() if pd.notna(val) else None

                    def clean_int(val):
                        try:
                            return int(float(val)) if pd.notna(val) else None
                        except (ValueError, TypeError):
                            return None

                    sr_no = clean_val(row.iloc[0])
                    house_no = clean_val(row.iloc[1])
                    voter_name = clean_val(row.iloc[2])
                    guardian_name = clean_val(row.iloc[3])
                    svn_no = clean_val(row.iloc[4])

                    if (
                        not voter_name
                        or not svn_no
                        or voter_name == 'निर्वाचक का नाम'
                        or 'Voter' in voter_name
                    ):
                        continue

                    excel_caste = clean_val(row.iloc[8]) if len(row) > 8 else None
                    excel_category = clean_val(row.iloc[7]) if len(row) > 7 else None
                    excel_religion = clean_val(row.iloc[9]) if len(row) > 9 else 'Hindu'

                    caste = excel_caste
                    category = excel_category
                    religion = excel_religion

                    # आपके नियम (Rules)
                    if voter_name:
                        if (
                            'खातून' in voter_name
                            or 'Khatoon' in voter_name
                            or 'अली' in voter_name
                            or 'Ali' in voter_name
                            or 'नेशा' in voter_name
                            or 'Nesha' in voter_name
                            or 'हक' in voter_name
                            or 'अंसारी' in voter_name
                            or 'खातुन' in voter_name
                            or 'परवीन' in voter_name
                            or 'मेनूद्दीन' in voter_name
                            or 'अख्तर' in voter_name
                        ):
                            caste, category, religion = 'Muslim', 'OBC', 'Muslim'
                        elif 'राय' in voter_name or 'Rai' in voter_name:
                            caste, category, religion = 'Bhumihar', 'General', 'Hindu'
                        elif 'चौहान' in voter_name or 'Chauhan' in voter_name:
                            caste, category, religion = 'Lonia', 'OBC', 'Hindu'
                        elif 'यादव' in voter_name or 'Yadav' in voter_name:
                            caste, category, religion = 'Ahir', 'OBC', 'Hindu'
                        elif 'प्रसाद' in voter_name or 'Prasad' in voter_name:
                            caste, category, religion = 'Prasad', 'SC', 'Hindu'
                        elif 'गुप्ता' in voter_name or 'Gupta' in voter_name:
                            caste, category, religion = 'Teli', 'OBC', 'Hindu'
                        elif 'गोंड' in voter_name or 'Gond' in voter_name:
                            caste, category, religion = 'Gond', 'ST', 'Hindu'
                        elif 'कमकर' in voter_name or 'kamkar' in voter_name:
                            caste, category, religion = 'Kamkar', 'OBC', 'Hindu'
                        elif 'पटेल' in voter_name or 'patel' in voter_name:
                            caste, category, religion = 'Kurmi', 'OBC', 'Hindu'
                        elif 'गोसाई' in voter_name or 'gosai' in voter_name:
                            caste, category, religion = 'Gosai', 'OBC', 'Hindu'
                        elif 'निषाद' in voter_name or 'nishad' in voter_name:
                            caste, category, religion = 'Nishad', 'OBC', 'Hindu'
                        elif (
                            'मिश्रा' in voter_name
                            or 'Mishra' in voter_name
                            or 'पांडे' in voter_name
                            or 'Pandey' in voter_name
                        ):
                            caste, category, religion = 'Pandit', 'General', 'Hindu'

                    raw_status = clean_val(row.iloc[10]) if len(row) > 10 else None
                    if raw_status and raw_status.lower() == 'inactive':
                        status_val = StatusChoices.INACTIVE
                    else:
                        status_val = StatusChoices.ACTIVE

                    Voter.objects.update_or_create(
                        svn_no=svn_no,
                        defaults={
                            'sr_no': sr_no,
                            'house_no': house_no,
                            'voter_name': voter_name,
                            'guardian_name': guardian_name,
                            'gender': clean_val(row.iloc[5]) if len(row) > 5 else None,
                            'age': clean_int(row.iloc[6]) if len(row) > 6 else None,
                            'category': category,
                            'caste': caste,
                            'religion': religion,
                            'status': status_val,
                        },
                    )
                return redirect('voter_list')
            except Exception as e:
                print('EXCEL / DB ERROR:', e)
    else:
        form = ExcelUploadForm()

    context = {
        'voters': voters,
        'active_count': active_count,
        'inactive_count': inactive_count,
        'active_percentage': active_percentage,
        'inactive_percentage': inactive_percentage,
        'form': form,
        'total_voters_count': total_voters_count,
        'male_count': male_count,
        'female_count': female_count,
        # केटेगरी स्टैट्स
        'general_count': general_count,
        'general_share': general_share,
        'general_male': general_male,
        'general_female': general_female,
        'obc_count': obc_count,
        'obc_share': obc_share,
        'obc_male': obc_male,
        'obc_female': obc_female,
        'sc_count': sc_count,
        'sc_share': sc_share,
        'sc_male': sc_male,
        'sc_female': sc_female,
        'st_count': st_count,
        'st_share': st_share,
        'st_male': st_male,
        'st_female': st_female,
        # जातिवार स्टैट्स (Caste Stats)
        'bhumihar_count': bhumihar_count,
        'bhumihar_share': bhumihar_share,
        'bhumihar_male': bhumihar_male,
        'bhumihar_female': bhumihar_female,
        'pandit_count': pandit_count,
        'pandit_share': pandit_share,
        'pandit_male': pandit_male,
        'pandit_female': pandit_female,
        'lonia_count': lonia_count,
        'lonia_share': lonia_share,
        'lonia_male': lonia_male,
        'lonia_female': lonia_female,
        'ahir_count': ahir_count,
        'ahir_share': ahir_share,
        'ahir_male': ahir_male,
        'ahir_female': ahir_female,
        'muslim_count': muslim_count,
        'muslim_share': muslim_share,
        'muslim_male': muslim_male,
        'muslim_female': muslim_female,
        'turnout_percentage': 49.4,
        'survey_percentage': 75.4,
        'prasad_count': prasad_count,
        'prasad_share': prasad_share,
        'prasad_male': prasad_male,
        'prasad_female': prasad_female,
        'teli_count': teli_count,
        'teli_share': teli_share,
        'teli_male': teli_male,
        'teli_female': teli_female,
        'patel_count': patel_count,
        'patel_share': patel_share,
        'patel_male': patel_male,
        'patel_female': patel_female,
        'nishad_count': nishad_count,
        'nishad_share': nishad_share,
        'nishad_male': nishad_male,
        'nishad_female': nishad_female,
        'gosai_count': gosai_count,
        'gosai_share': gosai_share,
        'gosai_male': gosai_male,
        'gosai_female': gosai_female,
        'kamkar_count': kamkar_count,
        'kamkar_share': kamkar_share,
        'kamkar_male': kamkar_male,
        'kamkar_female': kamkar_female,
        'gond_count': gond_count,
        'gond_share': gond_share,
        'gond_male': gond_male,
        'gond_female': gond_female,
    }

    return render(request, 'voter_list.html', context)


# एडिट और अपडेट करने के लिए यह फंक्शन
def voter_update_view(request, pk):
    voter = get_object_or_404(Voter, pk=pk)

    if request.method == 'POST':
        form = VoterForm(request.POST, instance=voter)
        if form.is_valid():
            form.save()
            return redirect('voter_list')
    else:
        form = VoterForm(instance=voter)

    return render(request, 'voter_edit.html', {'form': form})


# ==========================================
# 🗳️ VOTING SYSTEM VIEWS (NewVote मॉडल के साथ)
# ==========================================

# 1. वोटर लॉगिन (SVN नंबर से वेरिफिकेशन)
def voter_login(request):
    if request.method == 'POST':
        svn_no = request.POST.get('svn_no', '').strip()
        try:
            voter = Voter.objects.get(svn_no__iexact=svn_no)
            if voter.status != StatusChoices.ACTIVE:
                messages.error(request, 'आपका वोटर स्टेटस Inactive है, आप वोट नहीं दे सकते।')
                return redirect('voter_login')

            request.session['voter_id'] = voter.id
            return redirect('voting_panel')
        except Voter.DoesNotExist:
            messages.error(request, 'गलत SVN नंबर! कृपया सही SVN नंबर दर्ज करें।')

    return render(request, 'voting/login.html')


# 2. वोटिंग पैनल (OBC और General वोटिंग)
def voting_panel(request):
    voter_id = request.session.get('voter_id')
    if not voter_id:
        return redirect('voter_login')

    voter = get_object_or_404(Voter, id=voter_id)

    # चेक करें कि वोटर पहले किन कैटेगरी में वोट दे चुका है
    already_voted_categories = NewVote.objects.filter(voter=voter).values_list(
        'election_category', flat=True
    )

    general_candidates = Candidate.objects.filter(
        election_category=ElectionCategoryChoices.GENERAL
    )
    obc_candidates = Candidate.objects.filter(
        election_category=ElectionCategoryChoices.OBC
    )

    if request.method == 'POST':
        candidate_id = request.POST.get('candidate_id')
        candidate = get_object_or_404(Candidate, id=candidate_id)

        try:
            NewVote.objects.create(
                voter=voter,
                candidate=candidate,
                election_category=candidate.election_category,
            )
            messages.success(
                request,
                f'{candidate.get_election_category_display()} कैटेगरी में आपका वोट सफलतापूर्वक दर्ज हो गया है!',
            )
        except IntegrityError:
            messages.error(
                request,
                f'आप {candidate.get_election_category_display()} कैटेगरी में पहले ही वोट दे चुके हैं!',
            )

        return redirect('voting_panel')

    context = {
        'voter': voter,
        'general_candidates': general_candidates,
        'obc_candidates': obc_candidates,
        'voted_general': ElectionCategoryChoices.GENERAL in already_voted_categories,
        'voted_obc': ElectionCategoryChoices.OBC in already_voted_categories,
    }
    return render(request, 'voting/panel.html', context)


# 3. लाइव चुनाव परिणाम (Results)
def election_results(request):
    general_results = (
        Candidate.objects.filter(election_category=ElectionCategoryChoices.GENERAL)
        .annotate(total_votes=Count('new_votes'))
        .order_by('-total_votes')
    )

    obc_results = (
        Candidate.objects.filter(election_category=ElectionCategoryChoices.OBC)
        .annotate(total_votes=Count('new_votes'))
        .order_by('-total_votes')
    )

    return render(
        request,
        'voting/results.html',
        {
            'general_results': general_results,
            'obc_results': obc_results,
        },
    )


# 4. वोटर लॉगआउट
def voter_logout(request):
    request.session.flush()
    return redirect('voter_login')


def survey_view(request):
    # 1. URL से category लें (Default: 'general')
    selected_category = request.GET.get("category", ElectionCategoryChoices.GENERAL)
    
    # Validate category
    if selected_category not in [ElectionCategoryChoices.GENERAL, ElectionCategoryChoices.OBC]:
        selected_category = ElectionCategoryChoices.GENERAL

    # 2. सिर्फ चुनी हुई category के Candidates लाएं
    candidates = Candidate.objects.filter(election_category=selected_category)

    # 3. उन Voters की ID निकालें जिनका इस category में पहले ही सर्वे हो चुका है
    already_voted_voter_ids = NewVote.objects.filter(
        election_category=selected_category
    ).values_list("voter_id", flat=True)

    # 4. सिर्फ Active और बचे हुए (Unvoted) Voters की लिस्ट लाएं
    available_voters = Voter.objects.filter(
        status=StatusChoices.ACTIVE
    ).exclude(id__in=already_voted_voter_ids).order_by("house_no", "sr_no")

    # 5. Form Submit (POST Request) हैंडल करें
    if request.method == "POST":
        category = request.POST.get("election_category")
        candidate_id = request.POST.get("candidate")
        selected_voter_ids = request.POST.getlist("voters")  # Multiple voters list

        if not candidate_id or not selected_voter_ids:
            messages.error(request, "कृपया Candidate और कम से कम एक Voter चुनें।")
            return redirect(f"{request.path}?category={category}")

        try:
            candidate = Candidate.objects.get(id=candidate_id, election_category=category)
            
            # Bulk create के लिए list तैयार करें
            votes_to_create = []
            for voter_id in selected_voter_ids:
                # Double check कि इस voter का पहले से इस category में डेटा न हो
                if not NewVote.objects.filter(voter_id=voter_id, election_category=category).exists():
                    votes_to_create.append(
                        NewVote(
                            voter_id=voter_id,
                            candidate=candidate,
                            election_category=category
                        )
                    )

            # एक साथ Database में सेव करें
            with transaction.atomic():
                NewVote.objects.bulk_create(votes_to_create)

            messages.success(request, f"{len(votes_to_create)} Voters का सर्वे सफलतापूर्वक सेव हो गया!")
            return redirect(f"{request.path}?category={category}")

        except Candidate.DoesNotExist:
            messages.error(request, "गलत Candidate चुना गया है।")
        except Exception as e:
            messages.error(request, f"Error: {str(e)}")

    context = {
        "selected_category": selected_category,
        "categories": ElectionCategoryChoices.choices,
        "candidates": candidates,
        "voters": available_voters,
    }
    return render(request, "survey.html", context)

class VoterViewSet(viewsets.ModelViewSet):
    queryset = Voter.objects.all().order_by("id")
    serializer_class = VoterSerializer
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["voter_name", "svn_no", "house_no", "sr_no", "caste", "category"]
    ordering_fields = ["id", "sr_no", "voter_name", "age"]

    def get_queryset(self):
        qs = super().get_queryset()
        svn_no = self.request.query_params.get("svn_no")
        status = self.request.query_params.get("status")
        category = self.request.query_params.get("category")

        if svn_no:
            qs = qs.filter(svn_no__iexact=svn_no)
        if status:
            qs = qs.filter(status=status)
        if category:
            qs = qs.filter(category__iexact=category)
        return qs


class CandidateViewSet(viewsets.ModelViewSet):
    serializer_class = CandidateSerializer
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["name", "symbol_name"]
    ordering_fields = ["id", "name", "vote_count"]

    def get_queryset(self):
        qs = Candidate.objects.annotate(vote_count=Count("new_votes")).order_by("id")
        election_category = self.request.query_params.get("election_category")
        if election_category:
            qs = qs.filter(election_category=election_category)
        return qs


class NewVoteViewSet(viewsets.ModelViewSet):
    queryset = NewVote.objects.select_related("voter", "candidate").order_by("-voted_at")
    serializer_class = NewVoteSerializer
    filter_backends = [filters.OrderingFilter]
    ordering_fields = ["id", "voted_at"]

    def get_queryset(self):
        qs = super().get_queryset()
        voter_id = self.request.query_params.get("voter")
        svn_no = self.request.query_params.get("svn_no")
        election_category = self.request.query_params.get("election_category")

        if voter_id:
            qs = qs.filter(voter_id=voter_id)
        if svn_no:
            qs = qs.filter(voter__svn_no__iexact=svn_no)
        if election_category:
            qs = qs.filter(election_category=election_category)
        return qs