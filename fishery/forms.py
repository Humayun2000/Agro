from django import forms
from .models import (
    Pond,
    FishSpecies,
    Stock,
    FeedRecord,
    MortalityRecord,
    Harvest,
    FishSale
)

# ---------- Base Style Mixin ----------
class BootstrapFormMixin:
    """
    Adds Bootstrap classes to all form fields automatically.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        for field_name, field in self.fields.items():
            field.widget.attrs.update({
                'class': 'form-control',
            })


# ---------- Pond Form ----------
class PondForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = Pond
        fields = '__all__'


# ---------- Fish Species Form ----------
class FishSpeciesForm(forms.ModelForm):
    class Meta:
        model = FishSpecies
        fields = ['name', 'average_growth_days']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter fish species name'
            }),
            'average_growth_days': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'Average growth duration (days)'
            }),
        }

    def clean_average_growth_days(self):
        days = self.cleaned_data.get('average_growth_days')
        if days <= 0:
            raise forms.ValidationError("Growth days must be greater than zero.")
        return days


# ---------- Stock Form ----------
class StockForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = Stock
        fields = '__all__'
        widgets = {
            'stocking_date': forms.DateInput(attrs={'type': 'date'})
        }


# ---------- Feed Record Form ----------
class FeedRecordForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = FeedRecord
        fields = '__all__'
        widgets = {
            'date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'pond': forms.Select(attrs={'class': 'form-select'}),
            'feed_type': forms.TextInput(attrs={'class': 'form-control'}),
            'quantity_kg': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'cost': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
        }


# ---------- Mortality Form ----------
class MortalityRecordForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = MortalityRecord
        fields = '__all__'
        widgets = {
            'stock': forms.Select(attrs={'class': 'form-select'}),
            'quantity_dead': forms.NumberInput(attrs={'class': 'form-control'}),
            'date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'reason': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }


# ---------- Harvest Form ----------
class HarvestForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = Harvest
        fields = '__all__'
        widgets = {
            'stock': forms.Select(attrs={'class': 'form-select'}),
            'quantity_kg': forms.NumberInput(attrs={'class': 'form-control'}),
            'harvest_date': forms.DateInput(attrs={
                'type': 'date',
                'class': 'form-control'
            }),
        }

# ---------- Sale Form ----------
class FishSaleForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = FishSale
        fields = '__all__'
        widgets = {
            'sale_date': forms.DateInput(attrs={'type': 'date'})
        }
