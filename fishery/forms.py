from django import forms
from django.forms import DateInput, NumberInput, Textarea
from .models import (
    Pond,
    FishSpecies,
    Stock,
    FeedRecord,
    MortalityRecord,
    Harvest,
    FishSale,
    ProductionCycle, 
    Expense
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
        fields = ['harvest', 'quantity_kg', 'price_per_kg', 'sale_date']
        widgets = {
            'harvest': forms.Select(attrs={'class': 'form-select'}),
            'quantity_kg': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': 1
            }),
            'price_per_kg': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01',
                'min': 0
            }),
            'sale_date': forms.DateInput(attrs={
                'type': 'date',
                'class': 'form-control'
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Only show harvests that have remaining quantity
        self.fields['harvest'].queryset = Harvest.objects.annotate(
            total_sold=F('sales__quantity_kg')
        ).select_related(
            'stock',
            'stock__pond',
            'cycle',
            'cycle__species'
        ).filter(quantity_kg__gt=F('total_sold'))

    def clean_quantity_kg(self):
        quantity = self.cleaned_data.get('quantity_kg')
        if quantity <= 0:
            raise forms.ValidationError("Quantity must be greater than zero.")

        harvest = self.cleaned_data.get('harvest')
        if harvest:
            total_sold = harvest.sales.aggregate(total=forms.models.Sum('quantity_kg'))['total'] or 0
            remaining = harvest.quantity_kg - total_sold
            if quantity > remaining:
                raise forms.ValidationError(f"Quantity exceeds remaining harvest ({remaining} kg).")
        return quantity
# ---------- Production Cycle Form ----------

# ------------------------
# ProductionCycle Form
# ------------------------
class ProductionCycleForm(forms.ModelForm):
    class Meta:
        model = ProductionCycle
        fields = [
            'pond', 
            'species', 
            'stocking_date', 
            'initial_quantity', 
            'initial_avg_weight',
            'expected_harvest_date',
            'status', 
            'notes'
        ]
        widgets = {
            'pond': forms.Select(attrs={'class': 'form-select'}),
            'species': forms.Select(attrs={'class': 'form-select'}),
            'stocking_date': DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'expected_harvest_date': DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'initial_quantity': NumberInput(attrs={'class': 'form-control', 'min': 0}),
            'initial_avg_weight': NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': 0}),
            'status': forms.Select(attrs={'class': 'form-select'}),
            'notes': Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Optional notes...'}),
        }

# ------------------------
# Expense Form
# ------------------------
class ExpenseForm(forms.ModelForm):
    class Meta:
        model = Expense
        fields = ['cycle', 'description', 'amount', 'expense_date']
        widgets = {
            'cycle': forms.Select(attrs={'class': 'form-select'}),
            'description': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Expense description'}),
            'amount': NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': 0}),
            'expense_date': DateInput(attrs={'class': 'form-control', 'type': 'date'}),
        }