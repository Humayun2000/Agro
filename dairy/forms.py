from django import forms
from .models import Breed, Cow, MilkProduction


class BreedForm(forms.ModelForm):
    class Meta:
        model = Breed
        fields = '__all__'


class CowForm(forms.ModelForm):
    class Meta:
        model = Cow
        fields = '__all__'


class MilkProductionForm(forms.ModelForm):
    class Meta:
        model = MilkProduction
        fields = ['cow', 'date', 'morning_milk', 'evening_milk', 'notes']