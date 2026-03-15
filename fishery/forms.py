# fishery/forms.py

from django import forms
from django.utils import timezone
from .models import *
from datetime import datetime, timedelta


class DateInput(forms.DateInput):
    input_type = 'date'


class TimeInput(forms.TimeInput):
    input_type = 'time'


class DateTimeInput(forms.DateTimeInput):
    input_type = 'datetime-local'


# ==================== FARM & POND FORMS ====================

class FarmForm(forms.ModelForm):
    """Form for farm management"""
    
    class Meta:
        model = Farm
        fields = '__all__'
        widgets = {
            'created_at': DateTimeInput(attrs={'readonly': 'readonly'}),
            'updated_at': DateTimeInput(attrs={'readonly': 'readonly'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields:
            self.fields[field].widget.attrs.update({'class': 'form-control'})
        self.fields['registration_number'].widget.attrs.update({'placeholder': 'e.g., FARM-2024-001'})
        self.fields['phone'].widget.attrs.update({'placeholder': 'e.g., +8801XXXXXXXXX'})


class PondForm(forms.ModelForm):
    """Form for pond management"""
    
    class Meta:
        model = Pond
        fields = '__all__'
        widgets = {
            'created_at': DateTimeInput(attrs={'readonly': 'readonly'}),
            'updated_at': DateTimeInput(attrs={'readonly': 'readonly'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields:
            self.fields[field].widget.attrs.update({'class': 'form-control'})
        
        # Only show active farms
        self.fields['farm'].queryset = Farm.objects.all()
        
        # Set help texts
        self.fields['pond_id'].widget.attrs.update({'placeholder': 'e.g., P-001'})
        self.fields['size_in_acres'].widget.attrs.update({'step': '0.01', 'min': '0'})
        self.fields['length'].widget.attrs.update({'step': '0.1', 'min': '0'})
        self.fields['width'].widget.attrs.update({'step': '0.1', 'min': '0'})
        self.fields['average_depth'].widget.attrs.update({'step': '0.1', 'min': '0'})
        self.fields['max_depth'].widget.attrs.update({'step': '0.1', 'min': '0'})
        self.fields['volume'].widget.attrs.update({'step': '0.1', 'min': '0'})
    
    def clean_pond_id(self):
        pond_id = self.cleaned_data.get('pond_id')
        if Pond.objects.filter(pond_id=pond_id).exclude(pk=self.instance.pk).exists():
            raise forms.ValidationError("This Pond ID already exists.")
        return pond_id


# ==================== FISH SPECIES FORMS ====================

class FishSpeciesForm(forms.ModelForm):
    """Form for fish species management"""
    
    class Meta:
        model = FishSpecies
        fields = '__all__'
        widgets = {
            'image': forms.FileInput(attrs={'class': 'form-control', 'accept': 'image/*'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields:
            self.fields[field].widget.attrs.update({'class': 'form-control'})
        
        self.fields['average_growth_days'].widget.attrs.update({'min': '1'})
        self.fields['harvest_weight_min'].widget.attrs.update({'step': '10', 'min': '0'})
        self.fields['harvest_weight_max'].widget.attrs.update({'step': '10', 'min': '0'})
        self.fields['expected_fcr'].widget.attrs.update({'step': '0.1', 'min': '0.5'})
        self.fields['market_price'].widget.attrs.update({'step': '0.01', 'min': '0'})


class FishBatchForm(forms.ModelForm):
    """Form for fish batch/genetics tracking"""
    
    class Meta:
        model = FishBatch
        fields = '__all__'
        widgets = {
            'certification_date': DateInput(),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields:
            self.fields[field].widget.attrs.update({'class': 'form-control'})
        
        self.fields['batch_number'].widget.attrs.update({'placeholder': 'e.g., BATCH-2024-001'})
        self.fields['supplier'].widget.attrs.update({'placeholder': 'Supplier name'})
        self.fields['generation'].widget.attrs.update({'min': '1'})
    
    def clean_batch_number(self):
        batch_number = self.cleaned_data.get('batch_number')
        if FishBatch.objects.filter(batch_number=batch_number).exclude(pk=self.instance.pk).exists():
            raise forms.ValidationError("This Batch Number already exists.")
        return batch_number


# ==================== PRODUCTION CYCLE FORMS ====================

class ProductionCycleForm(forms.ModelForm):
    """Form for production cycle management"""
    
    class Meta:
        model = ProductionCycle
        fields = '__all__'
        widgets = {
            'stocking_date': DateInput(),
            'stocking_time': TimeInput(),
            'expected_harvest_date': DateInput(),
            'actual_harvest_date': DateInput(),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields:
            self.fields[field].widget.attrs.update({'class': 'form-control'})
        
        # Filter querysets
        self.fields['pond'].queryset = Pond.objects.filter(is_active=True)
        self.fields['batch'].queryset = FishBatch.objects.all()
        
        # Numeric field attributes
        self.fields['initial_quantity'].widget.attrs.update({'min': '1'})
        self.fields['initial_avg_weight'].widget.attrs.update({'step': '1', 'min': '0.1'})
        self.fields['initial_avg_length'].widget.attrs.update({'step': '0.1', 'min': '0'})
        self.fields['fingerling_cost'].widget.attrs.update({'step': '0.01', 'min': '0'})
        self.fields['expected_harvest_weight'].widget.attrs.update({'step': '10', 'min': '0'})
        self.fields['expected_yield_kg'].widget.attrs.update({'step': '10', 'min': '0'})
        self.fields['target_fcr'].widget.attrs.update({'step': '0.1', 'min': '0.5'})
        self.fields['target_survival'].widget.attrs.update({'step': '1', 'min': '0', 'max': '100'})
    
    def clean(self):
        cleaned_data = super().clean()
        stocking_date = cleaned_data.get('stocking_date')
        expected_harvest_date = cleaned_data.get('expected_harvest_date')
        
        if stocking_date and expected_harvest_date:
            if expected_harvest_date <= stocking_date:
                raise forms.ValidationError("Expected harvest date must be after stocking date.")
        
        return cleaned_data


class ProductionCycleFilterForm(forms.Form):
    """Form for filtering production cycles"""
    
    pond = forms.ModelChoiceField(
        queryset=Pond.objects.all(),
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    species = forms.ModelChoiceField(
        queryset=FishSpecies.objects.all(),
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    status = forms.ChoiceField(
        choices=[('', 'All Status')] + ProductionCycle.STATUS_CHOICES,
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    date_from = forms.DateField(
        required=False,
        widget=DateInput(attrs={'class': 'form-control'})
    )
    date_to = forms.DateField(
        required=False,
        widget=DateInput(attrs={'class': 'form-control'})
    )


# ==================== FEED MANAGEMENT FORMS ====================

class FeedTypeForm(forms.ModelForm):
    """Form for feed type/inventory management"""
    
    class Meta:
        model = FeedType
        fields = '__all__'
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields:
            self.fields[field].widget.attrs.update({'class': 'form-control'})
        
        # Numeric fields
        self.fields['protein_percentage'].widget.attrs.update({'step': '0.1', 'min': '0', 'max': '100'})
        self.fields['fat_percentage'].widget.attrs.update({'step': '0.1', 'min': '0', 'max': '100'})
        self.fields['fiber_percentage'].widget.attrs.update({'step': '0.1', 'min': '0', 'max': '100'})
        self.fields['pellet_size_mm'].widget.attrs.update({'step': '0.1', 'min': '0'})
        self.fields['current_price'].widget.attrs.update({'step': '0.01', 'min': '0'})
        self.fields['current_stock'].widget.attrs.update({'step': '0.1', 'min': '0'})
        self.fields['reorder_level'].widget.attrs.update({'step': '0.1', 'min': '0'})
        self.fields['reorder_quantity'].widget.attrs.update({'step': '0.1', 'min': '0'})


class FeedPurchaseForm(forms.ModelForm):
    """Form for feed purchase records"""
    
    class Meta:
        model = FeedPurchase
        fields = '__all__'
        widgets = {
            'purchase_date': DateInput(),
            'expiry_date': DateInput(),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields:
            self.fields[field].widget.attrs.update({'class': 'form-control'})
        
        self.fields['quantity_kg'].widget.attrs.update({'step': '0.1', 'min': '0'})
        self.fields['price_per_kg'].widget.attrs.update({'step': '0.01', 'min': '0'})
        self.fields['batch_number'].widget.attrs.update({'placeholder': 'e.g., LOT-2024-001'})


class FeedRecordForm(forms.ModelForm):
    """Form for daily feed consumption"""
    
    class Meta:
        model = FeedRecord
        fields = '__all__'
        widgets = {
            'date': DateInput(),
            'feed_time': TimeInput(),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields:
            self.fields[field].widget.attrs.update({'class': 'form-control'})
        
        # Only show running cycles
        self.fields['cycle'].queryset = ProductionCycle.objects.filter(status='RUNNING')
        self.fields['feed_type'].queryset = FeedType.objects.filter(current_stock__gt=0)
        
        self.fields['quantity_kg'].widget.attrs.update({'step': '0.1', 'min': '0'})
        self.fields['water_temp'].widget.attrs.update({'step': '0.1'})
    
    def clean(self):
        cleaned_data = super().clean()
        feed_type = cleaned_data.get('feed_type')
        quantity = cleaned_data.get('quantity_kg')
        
        if feed_type and quantity:
            if feed_type.current_stock < quantity:
                raise forms.ValidationError(
                    f"Insufficient stock! Available: {feed_type.current_stock}kg"
                )
        
        return cleaned_data


# ==================== WATER QUALITY FORMS ====================

class WaterQualityForm(forms.ModelForm):
    """Form for water quality monitoring"""
    
    class Meta:
        model = WaterQuality
        fields = '__all__'
        widgets = {
            'reading_date': DateTimeInput(),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields:
            self.fields[field].widget.attrs.update({'class': 'form-control'})
        
        # Numeric fields with appropriate steps
        self.fields['temperature'].widget.attrs.update({'step': '0.1'})
        self.fields['ph_level'].widget.attrs.update({'step': '0.1', 'min': '0', 'max': '14'})
        self.fields['dissolved_oxygen'].widget.attrs.update({'step': '0.1', 'min': '0'})
        self.fields['ammonia'].widget.attrs.update({'step': '0.01', 'min': '0'})
        self.fields['nitrite'].widget.attrs.update({'step': '0.01', 'min': '0'})
        self.fields['nitrate'].widget.attrs.update({'step': '0.1', 'min': '0'})
        self.fields['alkalinity'].widget.attrs.update({'step': '1', 'min': '0'})
        self.fields['hardness'].widget.attrs.update({'step': '1', 'min': '0'})
        self.fields['transparency'].widget.attrs.update({'step': '1', 'min': '0'})


class WaterQualityFilterForm(forms.Form):
    """Form for filtering water quality readings"""
    
    pond = forms.ModelChoiceField(
        queryset=Pond.objects.all(),
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    date_from = forms.DateField(
        required=False,
        widget=DateInput(attrs={'class': 'form-control'})
    )
    date_to = forms.DateField(
        required=False,
        widget=DateInput(attrs={'class': 'form-control'})
    )
    alert_only = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )


# ==================== HEALTH & DISEASE FORMS ====================

class DiseaseRecordForm(forms.ModelForm):
    """Form for disease outbreak tracking"""
    
    class Meta:
        model = DiseaseRecord
        fields = '__all__'
        widgets = {
            'detection_date': DateInput(),
            'resolved_date': DateInput(),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields:
            self.fields[field].widget.attrs.update({'class': 'form-control'})
        
        self.fields['estimated_affected'].widget.attrs.update({'min': '0'})
        self.fields['mortality_count'].widget.attrs.update({'min': '0'})
        self.fields['treatment_cost'].widget.attrs.update({'step': '0.01', 'min': '0'})


class TreatmentRecordForm(forms.ModelForm):
    """Form for treatment applications"""
    
    class Meta:
        model = TreatmentRecord
        fields = '__all__'
        widgets = {
            'application_date': DateInput(),
            'next_application': DateInput(),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields:
            self.fields[field].widget.attrs.update({'class': 'form-control'})
        
        self.fields['quantity_used'].widget.attrs.update({'step': '0.1', 'min': '0'})
        self.fields['cost'].widget.attrs.update({'step': '0.01', 'min': '0'})


class MortalityRecordForm(forms.ModelForm):
    """Form for mortality tracking"""
    
    class Meta:
        model = MortalityRecord
        fields = '__all__'
        widgets = {
            'date': DateInput(),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields:
            self.fields[field].widget.attrs.update({'class': 'form-control'})
        
        # Only show running cycles
        self.fields['cycle'].queryset = ProductionCycle.objects.filter(status='RUNNING')
        self.fields['disease'].queryset = DiseaseRecord.objects.filter(is_resolved=False)
        
        self.fields['quantity_dead'].widget.attrs.update({'min': '1'})
    
    def clean(self):
        cleaned_data = super().clean()
        cycle = cleaned_data.get('cycle')
        quantity = cleaned_data.get('quantity_dead')
        
        if cycle and quantity:
            if quantity > cycle.current_population:
                raise forms.ValidationError(
                    f"Mortality exceeds current population! "
                    f"Current population: {cycle.current_population}"
                )
        
        return cleaned_data


# ==================== HARVEST FORMS ====================

class HarvestForm(forms.ModelForm):
    """Form for harvest management"""
    
    class Meta:
        model = Harvest
        fields = '__all__'
        widgets = {
            'harvest_date': DateInput(),
            'harvest_time': TimeInput(),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields:
            self.fields[field].widget.attrs.update({'class': 'form-control'})
        
        # Only show running cycles
        self.fields['cycle'].queryset = ProductionCycle.objects.filter(status='RUNNING')
        
        self.fields['quantity_kg'].widget.attrs.update({'step': '0.1', 'min': '0'})
        self.fields['piece_count'].widget.attrs.update({'min': '0'})
        self.fields['avg_weight'].widget.attrs.update({'step': '1', 'min': '0'})
        self.fields['duration_hours'].widget.attrs.update({'step': '0.5', 'min': '0'})
        self.fields['workers_count'].widget.attrs.update({'min': '0'})
        self.fields['labor_cost'].widget.attrs.update({'step': '0.01', 'min': '0'})
        self.fields['ice_used_kg'].widget.attrs.update({'step': '1', 'min': '0'})
    
    def clean(self):
        cleaned_data = super().clean()
        cycle = cleaned_data.get('cycle')
        quantity = cleaned_data.get('quantity_kg')
        
        if cycle and quantity:
            # Estimate maximum possible harvest (rough calculation)
            max_possible = (cycle.current_population * cycle.initial_avg_weight) / 1000
            if quantity > max_possible * 1.2:  # 20% margin for error
                raise forms.ValidationError(
                    f"Harvest quantity seems too high. Estimated maximum: {max_possible:.1f}kg"
                )
        
        return cleaned_data


# ==================== SALES FORMS ====================

class CustomerForm(forms.ModelForm):
    """Form for customer management"""
    
    class Meta:
        model = Customer
        fields = '__all__'
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields:
            self.fields[field].widget.attrs.update({'class': 'form-control'})
        
        self.fields['customer_id'].widget.attrs.update({'placeholder': 'e.g., CUST-001'})
        self.fields['phone'].widget.attrs.update({'placeholder': 'e.g., +8801XXXXXXXXX'})
        self.fields['credit_limit'].widget.attrs.update({'step': '0.01', 'min': '0'})
        self.fields['current_balance'].widget.attrs.update({'step': '0.01', 'min': '0'})
    
    def clean_customer_id(self):
        customer_id = self.cleaned_data.get('customer_id')
        if Customer.objects.filter(customer_id=customer_id).exclude(pk=self.instance.pk).exists():
            raise forms.ValidationError("This Customer ID already exists.")
        return customer_id


class FishSaleForm(forms.ModelForm):
    """Form for fish sales"""
    
    class Meta:
        model = FishSale
        fields = '__all__'
        widgets = {
            'sale_date': DateInput(),
            'delivery_date': DateInput(),
            'payment_date': DateInput(),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields:
            self.fields[field].widget.attrs.update({'class': 'form-control'})
        
        # Only show harvests with remaining quantity
        self.fields['harvest'].queryset = Harvest.objects.filter(
            quantity_kg__gt=F('sales__quantity_kg') or 0
        ).distinct()
        
        self.fields['quantity_kg'].widget.attrs.update({'step': '0.1', 'min': '0'})
        self.fields['price_per_kg'].widget.attrs.update({'step': '0.01', 'min': '0'})
        self.fields['transport_cost'].widget.attrs.update({'step': '0.01', 'min': '0'})
    
    def clean(self):
        cleaned_data = super().clean()
        harvest = cleaned_data.get('harvest')
        quantity = cleaned_data.get('quantity_kg')
        
        if harvest and quantity:
            if quantity > harvest.remaining_quantity:
                raise forms.ValidationError(
                    f"Sale exceeds available quantity! "
                    f"Available: {harvest.remaining_quantity}kg"
                )
        
        return cleaned_data


class SaleFilterForm(forms.Form):
    """Form for filtering sales"""
    
    customer = forms.ModelChoiceField(
        queryset=Customer.objects.all(),
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    species = forms.ModelChoiceField(
        queryset=FishSpecies.objects.all(),
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    date_from = forms.DateField(
        required=False,
        widget=DateInput(attrs={'class': 'form-control'})
    )
    date_to = forms.DateField(
        required=False,
        widget=DateInput(attrs={'class': 'form-control'})
    )
    payment_status = forms.ChoiceField(
        choices=[('', 'All')] + FishSale.SALE_STATUS,
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )


# ==================== EXPENSE FORMS ====================

class ExpenseForm(forms.ModelForm):
    """Form for expense tracking"""
    
    class Meta:
        model = Expense
        fields = '__all__'
        widgets = {
            'expense_date': DateInput(attrs={'type': 'date'}),
            'description': forms.Textarea(attrs={'rows': 2}),
            'notes': forms.Textarea(attrs={'rows': 3}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Add Bootstrap classes to all fields
        for field in self.fields:
            self.fields[field].widget.attrs.update({'class': 'form-control'})
        
        # Customize specific fields
        self.fields['amount'].widget.attrs.update({
            'step': '0.01', 
            'min': '0',
            'placeholder': 'Enter amount in BDT'
        })
        
        self.fields['receipt_number'].widget.attrs.update({
            'placeholder': 'Receipt/invoice number (optional)'
        })
        
        self.fields['paid_to'].widget.attrs.update({
            'placeholder': 'Person/company paid to'
        })
        
        self.fields['description'].widget.attrs.update({
            'placeholder': 'Brief description of the expense'
        })
        
        self.fields['notes'].widget.attrs.update({
            'placeholder': 'Additional details, payment terms, etc.'
        })
        
        # Set initial date to today if new record
        if not self.instance.pk:
            self.fields['expense_date'].initial = timezone.now().date()
        
        # Make cycle field show pond name and species
        if 'cycle' in self.fields:
            self.fields['cycle'].label_from_instance = self._cycle_label
        
        # Make feed_purchase field show informative label
        if 'feed_purchase' in self.fields:
            self.fields['feed_purchase'].label_from_instance = self._feed_purchase_label
    
    def _cycle_label(self, obj):
        """Custom label for cycle field"""
        return f"{obj.pond.name} - {obj.species.name} (Cycle: {obj.cycle_id[:8]})"
    
    def _feed_purchase_label(self, obj):
        """Custom label for feed purchase field"""
        return f"{obj.feed_type.name} - {obj.quantity_kg}kg (৳{obj.total_cost}) on {obj.purchase_date}"
    
    def clean_amount(self):
        """Validate amount is positive"""
        amount = self.cleaned_data.get('amount')
        if amount and amount <= 0:
            raise forms.ValidationError("Amount must be greater than 0")
        return amount
    
    def clean(self):
        """Cross-field validation"""
        cleaned_data = super().clean()
        expense_type = cleaned_data.get('expense_type')
        feed_purchase = cleaned_data.get('feed_purchase')
        
        # If expense type is FEED, suggest linking to feed purchase
        if expense_type == 'FEED' and not feed_purchase:
            # This is a warning, not an error
            from django.contrib import messages
            self.add_warning("Consider linking this feed expense to a feed purchase record")
        
        # If feed_purchase is selected and amount is empty, auto-fill
        if feed_purchase and not cleaned_data.get('amount'):
            cleaned_data['amount'] = feed_purchase.total_cost
            # Add a message that amount was auto-filled
            self.add_warning(f"Amount auto-filled from feed purchase: ৳{feed_purchase.total_cost}")
        
        return cleaned_data
    
    def add_warning(self, message):
        """Add a warning message to the form (non-blocking)"""
        if not hasattr(self, 'warnings'):
            self.warnings = []
        self.warnings.append(message)


# ==================== BUDGET FORMS ====================

class BudgetForm(forms.ModelForm):
    """Form for budget planning"""
    
    class Meta:
        model = Budget
        fields = '__all__'
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields:
            self.fields[field].widget.attrs.update({'class': 'form-control'})
        
        # All cost fields
        cost_fields = [
            'planned_fingerling_cost', 'planned_feed_cost', 'planned_medicine_cost',
            'planned_labor_cost', 'planned_other_cost'
        ]
        for field in cost_fields:
            self.fields[field].widget.attrs.update({'step': '0.01', 'min': '0'})
        
        self.fields['planned_harvest_kg'].widget.attrs.update({'step': '10', 'min': '0'})
        self.fields['planned_price_per_kg'].widget.attrs.update({'step': '0.01', 'min': '0'})
    
    def clean(self):
        cleaned_data = super().clean()
        cycle = cleaned_data.get('cycle')
        
        if cycle and hasattr(cycle, 'budget') and cycle.budget and cycle.budget != self.instance:
            raise forms.ValidationError("This cycle already has a budget.")
        
        return cleaned_data


# ==================== REPORT FORMS ====================

class ReportFilterForm(forms.Form):
    """Form for report filtering"""
    
    YEAR_CHOICES = [(y, y) for y in range(2020, timezone.now().year + 2)]
    
    year = forms.ChoiceField(
        choices=YEAR_CHOICES,
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    pond = forms.ModelChoiceField(
        queryset=Pond.objects.all(),
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    species = forms.ModelChoiceField(
        queryset=FishSpecies.objects.all(),
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    start_date = forms.DateField(
        required=False,
        widget=DateInput(attrs={'class': 'form-control'})
    )
    end_date = forms.DateField(
        required=False,
        widget=DateInput(attrs={'class': 'form-control'})
    )


class FinancialReportGenerateForm(forms.ModelForm):
    """Form for generating financial reports"""
    
    class Meta:
        model = FisheryFinancialReport
        fields = ['year']
        widgets = {
            'year': forms.NumberInput(attrs={'class': 'form-control', 'min': '2020', 'max': '2030'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['year'].initial = timezone.now().year
    
    def clean_year(self):
        year = self.cleaned_data.get('year')
        if FisheryFinancialReport.objects.filter(year=year).exists():
            raise forms.ValidationError(f"Report for year {year} already exists.")
        return year


# ==================== DASHBOARD FILTER FORMS ====================

class DashboardFilterForm(forms.Form):
    """Form for dashboard filters"""
    
    period = forms.ChoiceField(
        choices=[
            ('today', 'Today'),
            ('week', 'This Week'),
            ('month', 'This Month'),
            ('quarter', 'This Quarter'),
            ('year', 'This Year'),
        ],
        initial='month',
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    pond = forms.ModelChoiceField(
        queryset=Pond.objects.all(),
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )


# ==================== BULK OPERATION FORMS ====================

class BulkDeleteForm(forms.Form):
    """Form for bulk delete operations"""
    
    ids = forms.CharField(
        widget=forms.HiddenInput(),
        required=False
    )
    confirm = forms.BooleanField(
        required=True,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        label="I understand this action cannot be undone"
    )


class BulkStatusUpdateForm(forms.Form):
    """Form for bulk status updates"""
    
    ids = forms.CharField(
        widget=forms.HiddenInput(),
        required=False
    )
    new_status = forms.ChoiceField(
        choices=[],
        widget=forms.Select(attrs={'class': 'form-select'}),
        required=True
    )
    
    def __init__(self, *args, status_choices=None, **kwargs):
        super().__init__(*args, **kwargs)
        if status_choices:
            self.fields['new_status'].choices = status_choices


# ==================== IMPORT/EXPORT FORMS ====================

class ImportDataForm(forms.Form):
    """Form for importing data from CSV/Excel"""
    
    file = forms.FileField(
        widget=forms.FileInput(attrs={'class': 'form-control', 'accept': '.csv,.xlsx'}),
        required=True
    )
    model_name = forms.ChoiceField(
        choices=[
            ('pond', 'Ponds'),
            ('species', 'Fish Species'),
            ('cycle', 'Production Cycles'),
            ('feed', 'Feed Records'),
            ('harvest', 'Harvests'),
            ('sale', 'Sales'),
        ],
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    update_existing = forms.BooleanField(
        required=False,
        initial=True,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        label="Update existing records"
    )


class ExportDataForm(forms.Form):
    """Form for exporting data"""
    
    EXPORT_FORMATS = [
        ('csv', 'CSV'),
        ('excel', 'Excel'),
        ('pdf', 'PDF'),
    ]
    
    format = forms.ChoiceField(
        choices=EXPORT_FORMATS,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    include_related = forms.BooleanField(
        required=False,
        initial=True,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        label="Include related data"
    )
    date_from = forms.DateField(
        required=False,
        widget=DateInput(attrs={'class': 'form-control'})
    )
    date_to = forms.DateField(
        required=False,
        widget=DateInput(attrs={'class': 'form-control'})
    )