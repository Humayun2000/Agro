from django import forms
from django.utils import timezone
from datetime import datetime, timedelta
from .models import *

# ==================== BASE FORM WITH BOOTSTRAP ====================

class BootstrapFormMixin:
    """Mixin to add Bootstrap 5 styling to all form fields"""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name, field in self.fields.items():
            # Add Bootstrap classes to all fields
            if isinstance(field.widget, (forms.TextInput, forms.NumberInput, forms.EmailInput, forms.URLInput, forms.PasswordInput)):
                field.widget.attrs.update({'class': 'form-control'})
            elif isinstance(field.widget, (forms.Select, forms.SelectMultiple)):
                field.widget.attrs.update({'class': 'form-select'})
            elif isinstance(field.widget, forms.Textarea):
                field.widget.attrs.update({'class': 'form-control', 'rows': 3})
            elif isinstance(field.widget, forms.CheckboxInput):
                field.widget.attrs.update({'class': 'form-check-input'})
            elif isinstance(field.widget, forms.DateInput):
                field.widget.attrs.update({'class': 'form-control', 'type': 'date'})
            elif isinstance(field.widget, forms.TimeInput):
                field.widget.attrs.update({'class': 'form-control', 'type': 'time'})
            elif isinstance(field.widget, forms.DateTimeInput):
                field.widget.attrs.update({'class': 'form-control', 'type': 'datetime-local'})
            
            # Add placeholders
            if hasattr(field, 'placeholder'):
                field.widget.attrs.update({'placeholder': field.placeholder})
            else:
                field.widget.attrs.update({'placeholder': f'Enter {field.label.lower()}'})


# ==================== CATTLE FORM ====================

class CattleForm(BootstrapFormMixin, forms.ModelForm):
    """Cattle form with Bootstrap styling and DOM manipulation"""
    
    class Meta:
        model = Cattle
        fields = '__all__'
        exclude = ['created_by', 'created_at', 'updated_at', 'total_investment']
        widgets = {
            'birth_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'acquisition_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'last_vaccination_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Filter parent choices
        self.fields['sire'].queryset = Cattle.objects.filter(gender='M', status='ACTIVE')
        self.fields['dam'].queryset = Cattle.objects.filter(gender='F', status='ACTIVE')
        
        # Add help texts
        self.fields['tag_number'].help_text = 'Unique identifier for the animal'
        self.fields['purchase_price'].help_text = 'Initial purchase price in BDT'
        self.fields['current_value'].help_text = 'Estimated current market value'
    
    def clean_tag_number(self):
        tag_number = self.cleaned_data.get('tag_number')
        if tag_number:
            return tag_number.upper()
        return tag_number


# ==================== MILK RECORD FORM ====================

class MilkRecordForm(BootstrapFormMixin, forms.ModelForm):
    """Milk record form with live calculations"""
    
    class Meta:
        model = MilkRecord
        fields = '__all__'
        exclude = ['recorded_by', 'recorded_at']
        widgets = {
            'date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'quantity': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'data-calculate': 'true'}),
            'fat_percentage': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0', 'max': '100'}),
            'temperature': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.1'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['cattle'].queryset = Cattle.objects.filter(
            cattle_type__in=['DAIRY', 'DUAL'], 
            status='ACTIVE'
        ).order_by('tag_number')
        
        # Set today's date as default
        if not self.instance.pk:
            self.initial['date'] = timezone.now().date()
            self.initial['session'] = self.get_default_session()
    
    def get_default_session(self):
        """Determine default session based on current time"""
        current_hour = timezone.now().hour
        if current_hour < 10:
            return 'MORNING'
        elif current_hour < 15:
            return 'AFTERNOON'
        else:
            return 'EVENING'


# ==================== MILK SALE FORM ====================

class MilkSaleForm(BootstrapFormMixin, forms.ModelForm):
    """Milk sale form with automatic total calculation"""
    
    class Meta:
        model = MilkSale
        fields = '__all__'
        exclude = ['created_by', 'total_amount']
        widgets = {
            'date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'quantity': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'id': 'id_quantity', 'data-calculate': 'true'}),
            'price_per_liter': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'id': 'id_price', 'data-calculate': 'true'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not self.instance.pk:
            self.initial['date'] = timezone.now().date()
    
    def clean(self):
        cleaned_data = super().clean()
        quantity = cleaned_data.get('quantity')
        price = cleaned_data.get('price_per_liter')
        
        if quantity and quantity <= 0:
            self.add_error('quantity', 'Quantity must be greater than 0')
        
        if price and price <= 0:
            self.add_error('price_per_liter', 'Price must be greater than 0')
        
        return cleaned_data


# ==================== CATTLE SALE FORM ====================

class CattleSaleForm(BootstrapFormMixin, forms.ModelForm):
    """Cattle sale form with profit preview"""
    
    class Meta:
        model = CattleSale
        fields = '__all__'
        exclude = ['created_by']
        widgets = {
            'sale_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'sale_price': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'id': 'id_sale_price'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['cattle'].queryset = Cattle.objects.filter(status='ACTIVE')
        
        if not self.instance.pk:
            self.initial['sale_date'] = timezone.now().date()
    
    def clean(self):
        cleaned_data = super().clean()
        cattle = cleaned_data.get('cattle')
        
        if cattle and cattle.status == 'SOLD':
            self.add_error('cattle', 'This cattle is already sold')
        
        return cleaned_data


# ==================== HEALTH RECORD FORM ====================

class HealthRecordForm(BootstrapFormMixin, forms.ModelForm):
    """Health record form with emergency toggle"""
    
    class Meta:
        model = HealthRecord
        fields = '__all__'
        exclude = ['created_by', 'created_at']
        widgets = {
            'date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'next_checkup_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'treatment_cost': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'is_emergency': forms.CheckboxInput(attrs={'class': 'form-check-input', 'id': 'emergency_toggle'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['cattle'].queryset = Cattle.objects.filter(status='ACTIVE')
        
        if not self.instance.pk:
            self.initial['date'] = timezone.now().date()


# ==================== FEEDING RECORD FORM ====================

class FeedingRecordForm(BootstrapFormMixin, forms.ModelForm):
    """Feeding record form with cost calculation"""
    
    class Meta:
        model = FeedingRecord
        fields = '__all__'
        exclude = ['fed_by', 'total_cost']
        widgets = {
            'date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'feed_time': forms.TimeInput(attrs={'type': 'time', 'class': 'form-control'}),
            'quantity': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'id': 'id_quantity', 'data-calculate': 'true'}),
            'cost_per_kg': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'id': 'id_cost', 'data-calculate': 'true'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['cattle'].queryset = Cattle.objects.filter(status='ACTIVE')
        
        if not self.instance.pk:
            self.initial['date'] = timezone.now().date()
            self.initial['feed_time'] = timezone.now().time()


# ==================== WEIGHT RECORD FORM ====================

class WeightRecordForm(BootstrapFormMixin, forms.ModelForm):
    """Weight record form with growth calculation"""
    
    class Meta:
        model = WeightRecord
        fields = '__all__'
        exclude = ['recorded_by', 'daily_gain', 'age_in_days']
        widgets = {
            'date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'weight': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'id': 'id_weight'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['cattle'].queryset = Cattle.objects.filter(status='ACTIVE')
        
        if not self.instance.pk:
            self.initial['date'] = timezone.now().date()
    
    def clean(self):
        cleaned_data = super().clean()
        weight = cleaned_data.get('weight')
        
        if weight and weight > 2000:
            self.add_error('weight', 'Weight seems too high for a cattle')
        elif weight and weight < 10:
            self.add_error('weight', 'Weight seems too low for a cattle')
        
        return cleaned_data


# ==================== BREEDING RECORD FORM ====================

class BreedingRecordForm(BootstrapFormMixin, forms.ModelForm):
    """Breeding record form with gestation calculator"""
    
    class Meta:
        model = BreedingRecord
        fields = '__all__'
        exclude = ['created_by', 'created_at']
        widgets = {
            'breeding_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control', 'id': 'breeding_date'}),
            'pregnancy_check_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'expected_calving_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control', 'readonly': 'readonly', 'id': 'expected_date'}),
            'actual_calving_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'is_pregnant': forms.CheckboxInput(attrs={'class': 'form-check-input', 'id': 'pregnant_toggle'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['cattle'].queryset = Cattle.objects.filter(gender='F', status='ACTIVE')
        self.fields['sire'].queryset = Cattle.objects.filter(gender='M', status='ACTIVE')
        self.fields['offspring'].queryset = Cattle.objects.all()
        
        if not self.instance.pk:
            self.initial['breeding_date'] = timezone.now().date()
    
    def clean(self):
        cleaned_data = super().clean()
        breeding_date = cleaned_data.get('breeding_date')
        is_pregnant = cleaned_data.get('is_pregnant')
        
        if is_pregnant and breeding_date:
            # Auto-calculate expected calving (280 days)
            expected = breeding_date + timedelta(days=280)
            cleaned_data['expected_calving_date'] = expected
        
        return cleaned_data


# ==================== VACCINATION FORM ====================

class VaccinationForm(BootstrapFormMixin, forms.ModelForm):
    """Vaccination form with completion toggle"""
    
    class Meta:
        model = VaccinationSchedule
        fields = '__all__'
        exclude = ['administered_by']
        widgets = {
            'scheduled_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'administered_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'cost': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'is_completed': forms.CheckboxInput(attrs={'class': 'form-check-input', 'id': 'complete_toggle'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['cattle'].queryset = Cattle.objects.filter(status='ACTIVE')
        
        if not self.instance.pk:
            self.initial['scheduled_date'] = timezone.now().date()
    
    def clean(self):
        cleaned_data = super().clean()
        is_completed = cleaned_data.get('is_completed')
        administered_date = cleaned_data.get('administered_date')
        
        if is_completed and not administered_date:
            self.add_error('administered_date', 'Administration date is required when marking as completed')
        
        return cleaned_data


# ==================== EXPENSE FORM ====================

class ExpenseForm(BootstrapFormMixin, forms.ModelForm):
    """Expense form with category selection"""
    
    class Meta:
        model = Expense
        fields = '__all__'
        exclude = ['created_by', 'created_at']
        widgets = {
            'date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'amount': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['cattle'].queryset = Cattle.objects.filter(status='ACTIVE')
        
        if not self.instance.pk:
            self.initial['date'] = timezone.now().date()


# ==================== INVESTMENT FORM ====================

class InvestmentForm(BootstrapFormMixin, forms.ModelForm):
    """Investment form with type selection"""
    
    class Meta:
        model = Investment
        fields = '__all__'
        exclude = ['created_by', 'created_at']
        widgets = {
            'date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'amount': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['cattle'].queryset = Cattle.objects.filter(status='ACTIVE')
        
        if not self.instance.pk:
            self.initial['date'] = timezone.now().date()


# ==================== SEARCH FORMS ====================

class CattleSearchForm(forms.Form):
    """Advanced search form for cattle"""
    
    search = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Search by tag, name, location...'
        })
    )
    
    cattle_type = forms.ChoiceField(
        required=False,
        choices=[('', 'All Types')] + Cattle.CATTLE_TYPES,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    status = forms.ChoiceField(
        required=False,
        choices=[('', 'All Status')] + Cattle.STATUS_CHOICES,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    gender = forms.ChoiceField(
        required=False,
        choices=[('', 'All Genders')] + Cattle.GENDER_CHOICES,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    breed = forms.ChoiceField(
        required=False,
        choices=[('', 'All Breeds')] + Cattle.BREED_TYPES,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    age_from = forms.IntegerField(
        required=False,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': 'Min age (months)'
        })
    )
    
    age_to = forms.IntegerField(
        required=False,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': 'Max age (months)'
        })
    )
    
    price_from = forms.DecimalField(
        required=False,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': 'Min price'
        })
    )
    
    price_to = forms.DecimalField(
        required=False,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': 'Max price'
        })
    )


class DateRangeForm(forms.Form):
    """Date range filter form"""
    
    start_date = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date'
        })
    )
    
    end_date = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date'
        })
    )
    
    def clean(self):
        cleaned_data = super().clean()
        start = cleaned_data.get('start_date')
        end = cleaned_data.get('end_date')
        
        if start and end and start > end:
            self.add_error('end_date', 'End date must be after start date')
        
        return cleaned_data