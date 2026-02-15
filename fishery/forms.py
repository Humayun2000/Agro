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
class FishSpeciesForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = FishSpecies
        fields = '__all__'


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
            'date': forms.DateInput(attrs={'type': 'date'})
        }


# ---------- Mortality Form ----------
class MortalityRecordForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = MortalityRecord
        fields = '__all__'
        widgets = {
            'date': forms.DateInput(attrs={'type': 'date'})
        }


# ---------- Harvest Form ----------
class HarvestForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = Harvest
        fields = '__all__'
        widgets = {
            'harvest_date': forms.DateInput(attrs={'type': 'date'})
        }


# ---------- Sale Form ----------
class FishSaleForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = FishSale
        fields = '__all__'
        widgets = {
            'sale_date': forms.DateInput(attrs={'type': 'date'})
        }
