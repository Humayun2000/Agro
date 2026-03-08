from django.db import models
from django.contrib.auth import get_user_model 
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone
from decimal import Decimal

User = get_user_model()

# ==================== CORE CATTLE MODEL ====================

class Cattle(models.Model):
    """Main Cattle Model for both Dairy and Beef"""
    
    GENDER_CHOICES = [
        ('M', 'Male'),
        ('F', 'Female'),
    ]
    
    STATUS_CHOICES = [
        ('ACTIVE', 'Active'),
        ('SOLD', 'Sold'),
        ('DECEASED', 'Deceased'),
        ('TRANSFERRED', 'Transferred'),
    ]
    
    BREED_TYPES = [
        ('HF', 'Holstein Friesian'),
        ('JF', 'Jersey'),
        ('BS', 'Brahman'),
        ('LM', 'Limousin'),
        ('AG', 'Angus'),
        ('LOC', 'Local'),
        ('MIX', 'Mixed'),
    ]
    
    CATTLE_TYPES = [
        ('DAIRY', 'Dairy Cattle'),
        ('BEEF', 'Beef Cattle'),
        ('DUAL', 'Dual Purpose'),
    ]
    
    # Basic Information
    tag_number = models.CharField(max_length=50, unique=True, verbose_name="Tag Number")
    name = models.CharField(max_length=100, blank=True, null=True, verbose_name="Animal Name")
    cattle_type = models.CharField(max_length=10, choices=CATTLE_TYPES, default='DAIRY')
    breed = models.CharField(max_length=20, choices=BREED_TYPES)
    gender = models.CharField(max_length=1, choices=GENDER_CHOICES)
    birth_date = models.DateField(verbose_name="Date of Birth")
    
    # Physical Characteristics
    weight = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, help_text="Weight in kg")
    color = models.CharField(max_length=100, blank=True)
    distinctive_marks = models.TextField(blank=True)
    
    # Parentage
    sire = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True, related_name='offspring_sire', verbose_name="Father")
    dam = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True, related_name='offspring_dam', verbose_name="Mother")
    
    # Acquisition
    PURCHASE_TYPE = [
        ('BORN', 'Born on Farm'),
        ('PURCHASED', 'Purchased'),
        ('GIFT', 'Received as Gift'),
    ]
    acquisition_type = models.CharField(max_length=10, choices=PURCHASE_TYPE, default='BORN')
    acquisition_date = models.DateField(default=timezone.now)
    purchase_price = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    
    # Location and Status
    location = models.CharField(max_length=200, blank=True, help_text="Barn/Shed/Paddock location")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='ACTIVE')
    
    # Medical
    is_vaccinated = models.BooleanField(default=False)
    last_vaccination_date = models.DateField(null=True, blank=True)
    
    # Financial
    current_value = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True, help_text="Estimated current value")
    total_investment = models.DecimalField(max_digits=12, decimal_places=2, default=0, help_text="Total money invested in this cattle")
    
    # Metadata
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='cattle_created')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name_plural = "Cattle"
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.tag_number} - {self.get_breed_display()} ({self.get_gender_display()})"
    
    def age_in_months(self):
        today = timezone.now().date()
        months = (today.year - self.birth_date.year) * 12 + (today.month - self.birth_date.month)
        return months
    
    def age_in_days(self):
        today = timezone.now().date()
        return (today - self.birth_date).days
    
    @property
    def is_dairy(self):
        return self.cattle_type in ['DAIRY', 'DUAL']
    
    @property
    def is_beef(self):
        return self.cattle_type in ['BEEF', 'DUAL']
    
    def total_milk_produced(self):
        """Total milk produced by this cattle"""
        return self.milk_records.aggregate(total=models.Sum('quantity'))['total'] or 0
    
    def total_milk_revenue(self):
        """Total revenue from milk sales - Not applicable per cattle"""
        # Milk sales are global, not attributed to individual cattle
        return 0
    
    def total_expenses(self):
        """Total expenses for this cattle"""
        # FIXED: Changed 'cost' to 'total_cost' for feeding records
        feed_cost = self.feeding_records.aggregate(total=models.Sum('total_cost'))['total'] or 0
        health_cost = self.health_records.aggregate(total=models.Sum('treatment_cost'))['total'] or 0
        return feed_cost + health_cost
    
    def net_profit(self):
        """Net profit from this cattle"""
        # Only include revenue from cattle sale, not milk sales
        revenue = 0
        if hasattr(self, 'sale_record'):
            revenue += self.sale_record.sale_price
        return revenue - self.total_expenses() - (self.purchase_price or 0)

# ==================== MILK PRODUCTION ====================

class MilkRecord(models.Model):
    """Daily Milk Production Records"""
    
    SESSION_CHOICES = [
        ('MORNING', 'Morning'),
        ('AFTERNOON', 'Afternoon'),
        ('EVENING', 'Evening'),
    ]
    
    cattle = models.ForeignKey(Cattle, on_delete=models.CASCADE, related_name='milk_records', limit_choices_to={'cattle_type__in': ['DAIRY', 'DUAL']})
    date = models.DateField(default=timezone.now)
    session = models.CharField(max_length=10, choices=SESSION_CHOICES)
    quantity = models.DecimalField(max_digits=10, decimal_places=2, help_text="Quantity in liters")
    fat_percentage = models.DecimalField(max_digits=4, decimal_places=2, null=True, blank=True, validators=[MinValueValidator(0), MaxValueValidator(100)])
    
    # Quality Notes
    quality_notes = models.TextField(blank=True)
    temperature = models.DecimalField(max_digits=4, decimal_places=1, null=True, blank=True, help_text="Temperature in °C")
    
    recorded_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    recorded_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-date', '-session']
        unique_together = ['cattle', 'date', 'session']
    
    def __str__(self):
        return f"{self.cattle.tag_number} - {self.date} {self.session}: {self.quantity}L"


# ==================== MILK SALES ====================

class MilkSale(models.Model):
    """Milk Sales Records"""
    
    SALE_TYPE = [
        ('WHOLESALE', 'Wholesale'),
        ('RETAIL', 'Retail'),
        ('DIRECT', 'Direct Customer'),
    ]
    
    date = models.DateField(default=timezone.now)
    quantity = models.DecimalField(max_digits=10, decimal_places=2, help_text="Quantity in liters")
    price_per_liter = models.DecimalField(max_digits=10, decimal_places=2)
    total_amount = models.DecimalField(max_digits=12, decimal_places=2, editable=False)
    sale_type = models.CharField(max_length=10, choices=SALE_TYPE, default='RETAIL')
    customer_name = models.CharField(max_length=200, blank=True, null=True)
    payment_received = models.BooleanField(default=True)
    notes = models.TextField(blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    
    class Meta:
        ordering = ['-date']
    
    def save(self, *args, **kwargs):
        self.total_amount = self.quantity * self.price_per_liter
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"Milk Sale - {self.date} - {self.quantity}L @ ৳{self.price_per_liter}"


# ==================== CATTLE SALES ====================

class CattleSale(models.Model):
    """Cattle Sales Records"""
    
    cattle = models.OneToOneField(Cattle, on_delete=models.CASCADE, related_name='sale_record')
    sale_date = models.DateField(default=timezone.now)
    sale_price = models.DecimalField(max_digits=12, decimal_places=2)
    buyer_name = models.CharField(max_length=200)
    buyer_contact = models.CharField(max_length=100, blank=True)
    payment_received = models.BooleanField(default=True)
    notes = models.TextField(blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    
    class Meta:
        ordering = ['-sale_date']
    
    def profit_loss(self):
        """Calculate profit or loss on sale"""
        return self.sale_price - (self.cattle.purchase_price or 0) - self.cattle.total_expenses()
    
    def __str__(self):
        return f"Sale: {self.cattle.tag_number} - ৳{self.sale_price}"


# ==================== HEALTH RECORDS ====================

class HealthRecord(models.Model):
    """Health and Medical Records"""
    
    HEALTH_TYPES = [
        ('CHECKUP', 'Regular Checkup'),
        ('VACCINATION', 'Vaccination'),
        ('TREATMENT', 'Treatment'),
        ('SURGERY', 'Surgery'),
        ('PREGNANCY', 'Pregnancy Check'),
        ('DISEASE', 'Disease/Illness'),
    ]
    
    cattle = models.ForeignKey(Cattle, on_delete=models.CASCADE, related_name='health_records')
    health_type = models.CharField(max_length=20, choices=HEALTH_TYPES)
    date = models.DateField(default=timezone.now)
    
    # Medical Details
    diagnosis = models.CharField(max_length=500)
    treatment = models.TextField(blank=True)
    medications = models.TextField(blank=True, help_text="Medications prescribed")
    veterinarian = models.CharField(max_length=200)
    
    # Follow-up
    next_checkup_date = models.DateField(null=True, blank=True)
    is_emergency = models.BooleanField(default=False)
    
    # Cost
    treatment_cost = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    
    notes = models.TextField(blank=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-date']
    
    def __str__(self):
        return f"{self.cattle.tag_number} - {self.get_health_type_display()} on {self.date}"


# ==================== FEEDING RECORDS ====================

class FeedingRecord(models.Model):
    """Feeding and Nutrition Records"""
    
    FEED_TYPES = [
        ('GRAIN', 'Grain Mix'),
        ('HAY', 'Hay'),
        ('SILAGE', 'Silage'),
        ('CONCENTRATE', 'Concentrate'),
        ('MINERALS', 'Minerals/Supplements'),
        ('MILK', 'Milk (for calves)'),
    ]
    
    cattle = models.ForeignKey(Cattle, on_delete=models.CASCADE, related_name='feeding_records')
    date = models.DateField(default=timezone.now)
    feed_type = models.CharField(max_length=20, choices=FEED_TYPES, default= "GRAIN" , blank=True, null=True)
    
    # Feeding Details
    quantity = models.DecimalField(max_digits=10, decimal_places=2, help_text="Quantity in kg")
    cost_per_kg = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total_cost = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    feed_time = models.TimeField()
    
    # Quality
    feed_quality = models.IntegerField(choices=[(1, 'Poor'), (2, 'Fair'), (3, 'Good'), (4, 'Excellent')], default=3)
    
    notes = models.TextField(blank=True)
    fed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    
    class Meta:
        ordering = ['-date', '-feed_time']
    
    def save(self, *args, **kwargs):
        self.total_cost = self.quantity * self.cost_per_kg
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"{self.cattle.tag_number} - {self.feed_type}: {self.quantity}kg on {self.date}"


# ==================== BREEDING RECORDS ====================

class BreedingRecord(models.Model):
    """Breeding and Reproduction Records"""
    
    BREEDING_STATUS = [
        ('BRED', 'Bred'),
        ('CONFIRMED', 'Pregnancy Confirmed'),
        ('CALVED', 'Calved'),
        ('FAILED', 'Failed/Aborted'),
    ]
    
    cattle = models.ForeignKey(Cattle, on_delete=models.CASCADE, related_name='breeding_records', limit_choices_to={'gender': 'F'})
    breeding_date = models.DateField()
    breeding_method = models.CharField(max_length=100, help_text="Natural/AI")
    sire = models.ForeignKey(Cattle, on_delete=models.SET_NULL, null=True, related_name='sired_offspring', limit_choices_to={'gender': 'M'})
    
    # Pregnancy
    pregnancy_check_date = models.DateField(null=True, blank=True)
    is_pregnant = models.BooleanField(default=False)
    expected_calving_date = models.DateField(null=True, blank=True)
    actual_calving_date = models.DateField(null=True, blank=True)
    
    status = models.CharField(max_length=10, choices=BREEDING_STATUS, default='BRED')
    
    # Result
    offspring = models.ForeignKey(Cattle, on_delete=models.SET_NULL, null=True, blank=True, related_name='born_from')
    notes = models.TextField(blank=True)
    
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-breeding_date']
    
    def gestation_period(self):
        """Calculate gestation period in days"""
        if self.actual_calving_date and self.breeding_date:
            return (self.actual_calving_date - self.breeding_date).days
        return None
    
    def __str__(self):
        return f"{self.cattle.tag_number} bred on {self.breeding_date}"


# ==================== WEIGHT RECORDS ====================

class WeightRecord(models.Model):
    """Weight tracking for beef cattle"""
    
    cattle = models.ForeignKey(Cattle, on_delete=models.CASCADE, related_name='weight_records')
    date = models.DateField(default=timezone.now)
    weight = models.DecimalField(max_digits=10, decimal_places=2, help_text="Weight in kg")
    
    # Growth metrics
    daily_gain = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True, help_text="Daily weight gain in kg")
    age_in_days = models.IntegerField(null=True, blank=True)
    
    notes = models.TextField(blank=True)
    recorded_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    
    class Meta:
        ordering = ['-date']
        unique_together = ['cattle', 'date']
    
    def save(self, *args, **kwargs):
        # Calculate age in days
        self.age_in_days = (self.date - self.cattle.birth_date).days
        
        # Calculate daily gain if there's a previous record
        previous = WeightRecord.objects.filter(cattle=self.cattle, date__lt=self.date).order_by('-date').first()
        if previous:
            days_diff = (self.date - previous.date).days
            weight_diff = self.weight - previous.weight
            if days_diff > 0:
                self.daily_gain = weight_diff / days_diff
        
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"{self.cattle.tag_number} - {self.date}: {self.weight}kg"


# ==================== VACCINATION SCHEDULE ====================

class VaccinationSchedule(models.Model):
    """Preventive vaccination schedule"""
    
    VACCINE_TYPES = [
        ('FMD', 'Foot and Mouth Disease'),
        ('BQ', 'Black Quarter'),
        ('HS', 'Hemorrhagic Septicemia'),
        ('BRU', 'Brucellosis'),
        ('IBR', 'Infectious Bovine Rhinotracheitis'),
    ]
    
    cattle = models.ForeignKey(Cattle, on_delete=models.CASCADE, related_name='vaccinations')
    vaccine_type = models.CharField(max_length=20, choices=VACCINE_TYPES)
    scheduled_date = models.DateField()
    administered_date = models.DateField(null=True, blank=True)
    is_completed = models.BooleanField(default=False)
    
    dosage = models.CharField(max_length=50, blank=True)
    batch_number = models.CharField(max_length=100, blank=True)
    cost = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    
    notes = models.TextField(blank=True)
    administered_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    
    class Meta:
        ordering = ['scheduled_date']
    
    def __str__(self):
        return f"{self.cattle.tag_number} - {self.get_vaccine_type_display()} on {self.scheduled_date}"


# ==================== EXPENSE TRACKING ====================

class ExpenseCategory(models.Model):
    """Categories for expenses"""
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    
    def __str__(self):
        return self.name


class Expense(models.Model):
    """General farm expenses"""
    
    PAYMENT_METHODS = [
        ('CASH', 'Cash'),
        ('BANK', 'Bank Transfer'),
        ('MOBILE', 'Mobile Banking'),
        ('CHEQUE', 'Cheque'),
    ]
    
    date = models.DateField(default=timezone.now)
    category = models.ForeignKey(ExpenseCategory, on_delete=models.SET_NULL, null=True)
    description = models.CharField(max_length=200)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    payment_method = models.CharField(max_length=10, choices=PAYMENT_METHODS, default='CASH')
    receipt_number = models.CharField(max_length=100, blank=True)
    notes = models.TextField(blank=True)
    
    # Optional link to specific cattle
    cattle = models.ForeignKey(Cattle, on_delete=models.SET_NULL, null=True, blank=True, related_name='expenses')
    
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    
    class Meta:
        ordering = ['-date']
    
    def __str__(self):
        return f"{self.date} - {self.description}: ৳{self.amount}"


# ==================== INVESTMENT TRACKING ====================

class Investment(models.Model):
    """Farm investments"""
    
    INVESTMENT_TYPES = [
        ('INFRASTRUCTURE', 'Infrastructure'),
        ('EQUIPMENT', 'Equipment'),
        ('CATTLE', 'Cattle Purchase'),
        ('LAND', 'Land'),
        ('OTHER', 'Other'),
    ]
    
    date = models.DateField(default=timezone.now)
    investment_type = models.CharField(max_length=20, choices=INVESTMENT_TYPES)
    description = models.CharField(max_length=200)
    amount = models.DecimalField(max_digits=14, decimal_places=2)
    
    # Optional link to specific cattle
    cattle = models.ForeignKey(Cattle, on_delete=models.SET_NULL, null=True, blank=True, related_name='investments')
    
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    
    class Meta:
        ordering = ['-date']
    
    def __str__(self):
        return f"{self.date} - {self.get_investment_type_display()}: ৳{self.amount}"


# ==================== MONTHLY SUMMARY ====================

class MonthlySummary(models.Model):
    """Monthly financial summary"""
    
    year = models.IntegerField()
    month = models.IntegerField(validators=[MinValueValidator(1), MaxValueValidator(12)])
    
    # Income
    milk_sales = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    cattle_sales = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    other_income = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    total_income = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    
    # Expenses
    feed_expenses = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    health_expenses = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    labor_expenses = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    other_expenses = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    total_expenses = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    
    # Summary
    net_profit = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    
    # Production
    total_milk_produced = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    avg_milk_per_cow = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    
    class Meta:
        unique_together = ['year', 'month']
        ordering = ['-year', '-month']
    
    def __str__(self):
        return f"{self.year}-{self.month:02d} Summary"
    
    def save(self, *args, **kwargs):
        self.total_income = self.milk_sales + self.cattle_sales + self.other_income
        self.total_expenses = self.feed_expenses + self.health_expenses + self.labor_expenses + self.other_expenses
        self.net_profit = self.total_income - self.total_expenses
        super().save(*args, **kwargs)


# ==================== YEARLY REPORT ====================

class YearlyReport(models.Model):
    """Yearly financial report"""
    
    year = models.IntegerField(unique=True)
    
    # Income
    total_milk_sales = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    total_cattle_sales = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    total_other_income = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    total_income = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    
    # Expenses
    total_feed_expenses = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    total_health_expenses = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    total_labor_expenses = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    total_other_expenses = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    total_expenses = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    
    # Summary
    net_profit = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    roi_percentage = models.DecimalField(max_digits=6, decimal_places=2, default=0, help_text="Return on Investment %")
    
    # Production
    total_milk_produced = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    avg_daily_milk = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    calves_born = models.IntegerField(default=0)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-year']
    
    def __str__(self):
        return f"{self.year} Annual Report"