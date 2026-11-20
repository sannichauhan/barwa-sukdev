# forms.py
from django import forms
from .models import Voter

class ExcelUploadForm(forms.Form):
    excel_file = forms.FileField(label="Excel फाइल चुनें (.xlsx)")


class VoterForm(forms.ModelForm):

  class Meta:
    model = Voter
    fields = [
        'sr_no',
        'house_no',
        'voter_name',
        'guardian_name',
        'svn_no',
        'gender',
        'age',
        'category',
        'caste',
        'religion',
        'status',
    ]