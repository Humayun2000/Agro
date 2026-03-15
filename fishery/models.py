from django.db import models
from django.utils import timezone
from django.db.models import Sum, F, DecimalField, ExpressionWrapper, Avg
from django.core.exceptions import ValidationError
from django.db import transaction
from decimal import Decimal
from django.contrib.auth import get_user_model
import uuid

User = get_user_model()


# ==================== LOCATION & FARM MANAGEMENT ====================

class Farm(models.Model):
    """Main farm/hatchery information"""
    
    name = models.CharField(max_length=200)
    registration_number = models.CharField(max_length=100, unique=True, blank=True)
    address = models.TextField()
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=100)
    country = models.CharField(max_length=100, default='Bangladesh')
    phone = models.CharField(max_length=20)
    email = models.EmailField(blank=True)
    website = models.URLField(blank=True)
    
    # GPS Coordinates
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    
    # Farm details
    total_area = models.FloatField(help_text="Total area in acres")
    active_ponds = models.IntegerField(default=0)
    employee_count = models.IntegerField(default=0)
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return self.name
    
    class Meta:
        verbose_name = "Farm"
        verbose_name_plural = "Farms"


class Pond(models.Model):
    """Enhanced pond management with water quality tracking"""
    
    POND_TYPES = [
        ('NURSERY', 'Nursery Pond'),
        ('GROWOUT', 'Grow-out Pond'),
        ('BROODSTOCK', 'Broodstock Pond'),
        ('QUARANTINE', 'Quarantine Pond'),
        ('RESERVOIR', 'Reservoir'),
    ]
    
    BOTTOM_TYPES = [
        ('CLAY', 'Clay'),
        ('MUD', 'Mud'),
        ('SANDY', 'Sandy'),
        ('CONCRETE', 'Concrete'),
        ('LINED', 'HDPE Lined'),
    ]
    
    farm = models.ForeignKey(Farm, on_delete=models.CASCADE, related_name='ponds')
    pond_id = models.CharField(max_length=50, unique=True, help_text="Unique pond identifier")
    name = models.CharField(max_length=100)
    pond_type = models.CharField(max_length=20, choices=POND_TYPES, default='GROWOUT')
    
    # Physical characteristics
    size_in_acres = models.FloatField(help_text="Area in acres")
    length = models.FloatField(help_text="Length in meters", null=True, blank=True)
    width = models.FloatField(help_text="Width in meters", null=True, blank=True)
    average_depth = models.FloatField(help_text="Average depth in feet", null=True, blank=True)
    max_depth = models.FloatField(help_text="Maximum depth in feet", null=True, blank=True)
    volume = models.FloatField(help_text="Water volume in cubic meters", null=True, blank=True)
    
    bottom_type = models.CharField(max_length=20, choices=BOTTOM_TYPES, default='CLAY')
    water_source = models.CharField(max_length=100)
    
    # Location within farm
    location = models.CharField(max_length=150, blank=True)
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    
    # Operational status
    is_active = models.BooleanField(default=True)
    status = models.CharField(max_length=20, choices=[
        ('PREPARING', 'Preparing'),
        ('FILLING', 'Filling'),
        ('STOCKED', 'Stocked'),
        ('HARVESTING', 'Harvesting'),
        ('DRYING', 'Drying'),
        ('MAINTENANCE', 'Maintenance'),
    ], default='PREPARING')
    
    # Water quality thresholds
    min_oxygen = models.FloatField(default=4.0, help_text="Minimum dissolved oxygen (mg/L)")
    max_ammonia = models.FloatField(default=0.5, help_text="Maximum ammonia (mg/L)")
    min_ph = models.FloatField(default=6.5, help_text="Minimum pH")
    max_ph = models.FloatField(default=9.0, help_text="Maximum pH")
    optimal_temp_min = models.FloatField(default=25, help_text="Minimum optimal temperature (°C)")
    optimal_temp_max = models.FloatField(default=32, help_text="Maximum optimal temperature (°C)")
    
    # Metadata
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['farm', 'name']
        unique_together = ['farm', 'name']
        indexes = [
            models.Index(fields=['pond_id']),
            models.Index(fields=['status']),
        ]

    def __str__(self):
        return f"{self.farm.name} - {self.name} ({self.pond_id})"

    def current_cycle(self):
        """Get current active production cycle"""
        return self.production_cycles.filter(status='RUNNING').first()

    def total_harvest_year(self, year=None):
        """Total harvest for given year"""
        year = year or timezone.now().year
        return Harvest.objects.filter(
            cycle__pond=self,
            harvest_date__year=year
        ).aggregate(total=Sum('quantity_kg'))['total'] or 0

    def latest_water_quality(self):
        """Get latest water quality reading"""
        return self.water_quality.order_by('-reading_date').first()


# ==================== FISH SPECIES & GENETICS ====================

class FishSpecies(models.Model):
    """Comprehensive fish species catalog"""
    
    CATEGORIES = [
        ('CARP', 'Carp (Rui, Catla, Mrigal)'),
        ('TILAPIA', 'Tilapia (GIFT, Monosex)'),
        ('CATFISH', 'Catfish (Pangas, Magur)'),
        ('PANGASIUS', 'Pangasius'),
        ('SHRIMP', 'Shrimp/Prawn'),
        ('KOI', 'Koi'),
        ('ORNAMENTAL', 'Ornamental'),
        ('OTHER', 'Other'),
    ]
    
    WATER_TYPES = [
        ('FRESH', 'Freshwater'),
        ('BRACKISH', 'Brackish Water'),
        ('MARINE', 'Marine'),
    ]
    
    name = models.CharField(max_length=100)
    scientific_name = models.CharField(max_length=200, blank=True)
    category = models.CharField(max_length=20, choices=CATEGORIES, default='CARP')
    water_type = models.CharField(max_length=10, choices=WATER_TYPES, default='FRESH')
    
    # Growth parameters
    average_growth_days = models.IntegerField(help_text="Average days to harvest")
    harvest_weight_min = models.FloatField(help_text="Minimum harvest weight (g)", null=True, blank=True)
    harvest_weight_max = models.FloatField(help_text="Maximum harvest weight (g)", null=True, blank=True)
    expected_fcr = models.FloatField(help_text="Expected Feed Conversion Ratio", null=True, blank=True)
    
    # Market information
    market_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    demand_season = models.CharField(max_length=100, blank=True, help_text="Peak demand seasons")
    
    # Breeding info
    breeding_season = models.CharField(max_length=100, blank=True)
    gestation_days = models.IntegerField(null=True, blank=True)
    
    # Image
    image = models.ImageField(upload_to='fish_species/', null=True, blank=True)
    description = models.TextField(blank=True)
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']
        verbose_name_plural = "Fish Species"
        indexes = [
            models.Index(fields=['category']),
        ]

    def __str__(self):
        return self.name


class FishBatch(models.Model):
    """Fish batch/genetics tracking"""
    
    SPECIES_GRADES = [
        ('A', 'Premium Grade'),
        ('B', 'Standard Grade'),
        ('C', 'Economy Grade'),
    ]
    
    SOURCES = [
        ('HATCHERY', 'Own Hatchery'),
        ('IMPORTED', 'Imported'),
        ('LOCAL', 'Local Supplier'),
    ]
    
    batch_number = models.CharField(max_length=100, unique=True)
    species = models.ForeignKey(FishSpecies, on_delete=models.CASCADE, related_name='batches')
    source = models.CharField(max_length=20, choices=SOURCES, default='LOCAL')
    supplier = models.CharField(max_length=200, blank=True)
    grade = models.CharField(max_length=1, choices=SPECIES_GRADES, default='B')
    
    # Genetic information
    generation = models.IntegerField(default=1, help_text="Generation number")
    origin = models.CharField(max_length=200, blank=True, help_text="Original source/breed")
    disease_resistance = models.TextField(blank=True, help_text="Known disease resistance")
    
    # Certification
    is_certified = models.BooleanField(default=False)
    certification_number = models.CharField(max_length=100, blank=True)
    certification_date = models.DateField(null=True, blank=True)
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.batch_number} - {self.species.name}"


# ==================== PRODUCTION CYCLE MANAGEMENT ====================

class ProductionCycle(models.Model):
    """Complete production cycle management with advanced tracking"""
    
    CYCLE_TYPES = [
        ('NURSERY', 'Nursery Cycle'),
        ('GROWOUT', 'Grow-out Cycle'),
        ('BROODSTOCK', 'Broodstock Maintenance'),
    ]
    
    STATUS_CHOICES = [
        ('PLANNED', 'Planned'),
        ('PREPARING', 'Preparing Pond'),
        ('STOCKING', 'Stocking'),
        ('RUNNING', 'Running'),
        ('HARVESTING', 'Harvesting'),
        ('COMPLETED', 'Completed'),
        ('CANCELLED', 'Cancelled'),
        ('FAILED', 'Failed - Disease'),
    ]
    
    cycle_id = models.CharField(max_length=50, unique=True, default=uuid.uuid4, editable=False)
    cycle_type = models.CharField(max_length=20, choices=CYCLE_TYPES, default='GROWOUT')
    
    pond = models.ForeignKey(Pond, on_delete=models.CASCADE, related_name='production_cycles')
    species = models.ForeignKey(FishSpecies, on_delete=models.CASCADE, related_name='production_cycles')
    batch = models.ForeignKey(FishBatch, on_delete=models.SET_NULL, null=True, blank=True, related_name='cycles')
    
    # Stocking details
    stocking_date = models.DateField(default=timezone.now)
    stocking_time = models.TimeField(null=True, blank=True)
    initial_quantity = models.PositiveIntegerField(help_text="Number of fingerlings")
    initial_avg_weight = models.FloatField(help_text="Weight in grams at stocking")
    initial_avg_length = models.FloatField(help_text="Length in cm at stocking", null=True, blank=True)
    
    # Cost details
    fingerling_cost = models.DecimalField(max_digits=12, decimal_places=2, help_text="Total cost of fingerlings")
    cost_per_fingerling = models.DecimalField(max_digits=6, decimal_places=2, editable=False)
    
    # Expected harvest
    expected_harvest_date = models.DateField(null=True, blank=True)
    expected_harvest_weight = models.FloatField(help_text="Expected harvest weight in grams", null=True, blank=True)
    expected_yield_kg = models.FloatField(help_text="Expected yield in kg", null=True, blank=True)
    
    # Actual harvest (will be updated)
    actual_harvest_date = models.DateField(null=True, blank=True)
    actual_harvest_weight_avg = models.FloatField(null=True, blank=True)
    total_harvest_kg = models.FloatField(default=0)
    
    # Status
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PLANNED')
    
    # Goals
    target_fcr = models.FloatField(default=1.8, help_text="Target Feed Conversion Ratio")
    target_survival = models.FloatField(default=80, help_text="Target survival rate %")
    
    # Notes
    notes = models.TextField(blank=True, null=True)
    
    # Metadata
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='cycles_created')
    supervised_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='cycles_supervised')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-stocking_date']
        indexes = [
            models.Index(fields=['cycle_id']),
            models.Index(fields=['status']),
            models.Index(fields=['stocking_date']),
        ]

    def __str__(self):
        return f"{self.pond.name} - {self.species.name} (Stocked: {self.stocking_date})"

    def save(self, *args, **kwargs):
        if self.initial_quantity:
            self.cost_per_fingerling = self.fingerling_cost / self.initial_quantity
        super().save(*args, **kwargs)

    # -----------------------------
    # Production Metrics
    # -----------------------------
    @property
    def total_harvest(self):
        """Total harvested quantity in kg"""
        return self.harvests.aggregate(total=Sum('quantity_kg'))['total'] or 0

    @property
    def total_mortality(self):
        """Total mortality count"""
        return self.mortalities.aggregate(total=Sum('quantity_dead'))['total'] or 0

    @property
    def total_mortality_weight(self):
        """Estimated weight of mortality"""
        return self.total_mortality * (self.initial_avg_weight / 1000)  # Rough estimate

    @property
    def current_population(self):
        """Current estimated fish population"""
        return self.initial_quantity - self.total_mortality

    @property
    def survival_rate(self):
        """Calculate survival rate percentage"""
        if self.initial_quantity > 0:
            return round(((self.current_population) / self.initial_quantity) * 100, 2)
        return 0

    @property
    def survival_vs_target(self):
        """Compare survival rate with target"""
        if self.target_survival:
            return round((self.survival_rate / self.target_survival) * 100, 2)
        return 0

    @property
    def total_feed(self):
        """Total feed used in kg"""
        return self.feeds.aggregate(total=Sum('quantity_kg'))['total'] or 0

    @property
    def total_feed_cost(self):
        """Total feed cost"""
        return self.feeds.aggregate(total=Sum('cost'))['total'] or 0

    @property
    def fcr(self):
        """Feed Conversion Ratio"""
        if self.total_harvest > 0:
            return round(self.total_feed / self.total_harvest, 2)
        return 0

    @property
    def fcr_vs_target(self):
        """Compare FCR with target"""
        if self.target_fcr and self.fcr > 0:
            return round((self.target_fcr / self.fcr) * 100, 2)
        return 0

    @property
    def days_in_production(self):
        """Days since stocking"""
        if self.status == 'COMPLETED' and self.actual_harvest_date:
            return (self.actual_harvest_date - self.stocking_date).days
        return (timezone.now().date() - self.stocking_date).days

    @property
    def days_to_harvest(self):
        """Estimated days remaining to harvest"""
        if self.expected_harvest_date:
            remaining = (self.expected_harvest_date - timezone.now().date()).days
            return max(0, remaining)
        return 0

    @property
    def growth_per_day(self):
        """Average growth in grams per day"""
        if self.days_in_production > 0:
            if self.actual_harvest_weight_avg:
                return round((self.actual_harvest_weight_avg - self.initial_avg_weight) / self.days_in_production, 2)
            # Estimate based on expected
            elif self.expected_harvest_weight:
                return round((self.expected_harvest_weight - self.initial_avg_weight) / self.days_in_production, 2)
        return 0

    # -----------------------------
    # Financial Metrics
    # -----------------------------
    @property
    def total_medicine_cost(self):
        return self.expenses.filter(expense_type='MEDICINE').aggregate(total=Sum('amount'))['total'] or 0

    @property
    def total_labor_cost(self):
        return self.expenses.filter(expense_type='LABOR').aggregate(total=Sum('amount'))['total'] or 0

    @property
    def total_electricity_cost(self):
        return self.expenses.filter(expense_type='ELECTRICITY').aggregate(total=Sum('amount'))['total'] or 0

    @property
    def total_other_cost(self):
        return self.expenses.exclude(
            expense_type__in=['MEDICINE', 'LABOR', 'ELECTRICITY', 'FEED']
        ).aggregate(total=Sum('amount'))['total'] or 0

    @property
    def total_expense(self):
        return self.expenses.aggregate(total=Sum('amount'))['total'] or 0

    @property
    def total_operating_cost(self):
        """Total operating cost including feed and expenses"""
        return self.total_feed_cost + self.total_expense

    @property
    def total_investment(self):
        """Total investment including fingerlings and all costs"""
        return (self.fingerling_cost or 0) + self.total_operating_cost

    @property
    def total_sales(self):
        """Total revenue from sales"""
        return FishSale.objects.filter(
            harvest__cycle=self
        ).aggregate(
            total=Sum(
                ExpressionWrapper(
                    F('quantity_kg') * F('price_per_kg'),
                    output_field=DecimalField(max_digits=12, decimal_places=2)
                )
            )
        )['total'] or 0

    @property
    def average_sale_price(self):
        """Average price per kg"""
        total_kg = self.harvests.aggregate(total=Sum('quantity_kg'))['total'] or 0
        if total_kg > 0:
            return self.total_sales / total_kg
        return 0

    @property
    def net_profit(self):
        """Calculate net profit/loss"""
        return self.total_sales - self.total_investment

    @property
    def roi_percentage(self):
        """Return on Investment percentage"""
        if self.total_investment > 0:
            return round((self.net_profit / self.total_investment) * 100, 2)
        return 0

    @property
    def break_even_price(self):
        """Price per kg needed to break even"""
        total_kg = self.harvests.aggregate(total=Sum('quantity_kg'))['total'] or 0
        if total_kg > 0:
            return self.total_investment / total_kg
        return 0

    @property
    def profit_per_kg(self):
        """Profit per kilogram"""
        total_kg = self.harvests.aggregate(total=Sum('quantity_kg'))['total'] or 0
        if total_kg > 0:
            return self.net_profit / total_kg
        return 0

    # -----------------------------
    # Performance Dashboard Data
    # -----------------------------
    def get_performance_summary(self):
        """Get comprehensive performance summary for dashboard"""
        return {
            'survival_rate': self.survival_rate,
            'fcr': self.fcr,
            'total_harvest': self.total_harvest,
            'total_sales': float(self.total_sales),
            'total_investment': float(self.total_investment),
            'net_profit': float(self.net_profit),
            'roi': float(self.roi_percentage),
            'growth_per_day': self.growth_per_day,
            'days_in_production': self.days_in_production,
        }


# ==================== FEED MANAGEMENT ====================

class FeedType(models.Model):
    """Feed inventory management"""
    
    CATEGORIES = [
        ('STARTER', 'Starter Feed'),
        ('GROWER', 'Grower Feed'),
        ('FINISHER', 'Finisher Feed'),
        ('BROODSTOCK', 'Broodstock Feed'),
        ('SUPPLEMENT', 'Supplement'),
    ]
    
    name = models.CharField(max_length=100)
    category = models.CharField(max_length=20, choices=CATEGORIES)
    brand = models.CharField(max_length=100)
    protein_percentage = models.FloatField(help_text="Protein %")
    fat_percentage = models.FloatField(help_text="Fat %", null=True, blank=True)
    fiber_percentage = models.FloatField(help_text="Fiber %", null=True, blank=True)
    
    # Pellet size
    pellet_size_mm = models.FloatField(help_text="Pellet size in mm")
    
    # Price tracking
    current_price = models.DecimalField(max_digits=10, decimal_places=2, help_text="Price per kg")
    
    # Inventory
    current_stock = models.DecimalField(max_digits=10, decimal_places=2, default=0, help_text="Current stock in kg")
    reorder_level = models.DecimalField(max_digits=10, decimal_places=2, default=0, help_text="Reorder level in kg")
    reorder_quantity = models.DecimalField(max_digits=10, decimal_places=2, default=0, help_text="Reorder quantity in kg")
    
    # Supplier
    supplier = models.CharField(max_length=200, blank=True)
    supplier_contact = models.CharField(max_length=100, blank=True)
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.name} ({self.brand})"

    @property
    def needs_reorder(self):
        return self.current_stock <= self.reorder_level


class FeedPurchase(models.Model):
    """Feed purchase records"""
    
    feed_type = models.ForeignKey(FeedType, on_delete=models.CASCADE, related_name='purchases')
    purchase_date = models.DateField(default=timezone.now)
    quantity_kg = models.DecimalField(max_digits=10, decimal_places=2)
    price_per_kg = models.DecimalField(max_digits=10, decimal_places=2)
    total_cost = models.DecimalField(max_digits=12, decimal_places=2, editable=False)
    
    invoice_number = models.CharField(max_length=100, blank=True)
    supplier = models.CharField(max_length=200)
    batch_number = models.CharField(max_length=100, blank=True)
    expiry_date = models.DateField(null=True, blank=True)
    
    notes = models.TextField(blank=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)

    def save(self, *args, **kwargs):
        self.total_cost = self.quantity_kg * self.price_per_kg
        super().save(*args, **kwargs)
        # Update inventory
        self.feed_type.current_stock += self.quantity_kg
        self.feed_type.save()

    def __str__(self):
        return f"{self.feed_type.name} - {self.quantity_kg}kg on {self.purchase_date}"


class FeedRecord(models.Model):
    """Daily feed consumption tracking"""
    
    FEED_TIMES = [
        ('MORNING', 'Morning (6-8 AM)'),
        ('LATE_MORNING', 'Late Morning (9-11 AM)'),
        ('AFTERNOON', 'Afternoon (12-2 PM)'),
        ('EVENING', 'Evening (4-6 PM)'),
        ('NIGHT', 'Night (8-10 PM)'),
    ]
    
    FEED_METHODS = [
        ('MANUAL', 'Manual Spreading'),
        ('AUTO_FEEDER', 'Automatic Feeder'),
        ('BROADCAST', 'Broadcast'),
    ]
    
    cycle = models.ForeignKey(ProductionCycle, on_delete=models.CASCADE, related_name='feeds')
    feed_type = models.ForeignKey(FeedType, on_delete=models.CASCADE, related_name='consumption_records')
    
    date = models.DateField(default=timezone.now)
    feed_time = models.CharField(max_length=20, choices=FEED_TIMES, default='MORNING')
    feeding_method = models.CharField(max_length=20, choices=FEED_METHODS, default='MANUAL')
    
    quantity_kg = models.FloatField(help_text="Quantity in kilograms")
    cost = models.DecimalField(max_digits=10, decimal_places=2, help_text="Total cost")
    
    # Observation
    feed_consumption_rate = models.CharField(max_length=20, choices=[
        ('ALL', 'All Consumed'),
        ('MOST', 'Mostly Consumed'),
        ('PARTIAL', 'Partially Consumed'),
        ('LITTLE', 'Little Consumed'),
    ], default='ALL')
    
    water_temp = models.FloatField(null=True, blank=True, help_text="Water temperature at feeding")
    
    # Metadata
    recorded_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ['-date', '-feed_time']
        indexes = [
            models.Index(fields=['date']),
        ]

    def __str__(self):
        return f"{self.cycle.pond.name} - {self.feed_type.name} ({self.quantity_kg}kg)"

    @property
    def cost_per_kg(self):
        if self.quantity_kg > 0:
            return self.cost / self.quantity_kg
        return 0


# ==================== WATER QUALITY MONITORING ====================

class WaterQuality(models.Model):
    """Real-time water quality monitoring"""
    
    pond = models.ForeignKey(Pond, on_delete=models.CASCADE, related_name='water_quality')
    reading_date = models.DateTimeField(default=timezone.now)
    recorded_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    
    # Physical parameters
    temperature = models.FloatField(help_text="Water temperature (°C)")
    ph_level = models.FloatField(help_text="pH level")
    dissolved_oxygen = models.FloatField(help_text="Dissolved Oxygen (mg/L)")
    
    # Chemical parameters
    ammonia = models.FloatField(help_text="Ammonia (mg/L)", null=True, blank=True)
    nitrite = models.FloatField(help_text="Nitrite (mg/L)", null=True, blank=True)
    nitrate = models.FloatField(help_text="Nitrate (mg/L)", null=True, blank=True)
    alkalinity = models.FloatField(help_text="Alkalinity (mg/L)", null=True, blank=True)
    hardness = models.FloatField(help_text="Hardness (mg/L)", null=True, blank=True)
    
    # Visual parameters
    water_color = models.CharField(max_length=50, blank=True, help_text="Water color")
    transparency = models.FloatField(help_text="Secchi disk depth (cm)", null=True, blank=True)
    
    # Alerts
    alert_generated = models.BooleanField(default=False)
    alert_message = models.TextField(blank=True)
    
    class Meta:
        ordering = ['-reading_date']
        verbose_name = "Water Quality"
        verbose_name_plural = "Water Quality"
        indexes = [
            models.Index(fields=['reading_date']),
        ]

    def __str__(self):
        return f"{self.pond.name} - {self.reading_date.strftime('%Y-%m-%d %H:%M')}"

    def save(self, *args, **kwargs):
        # Generate alerts if parameters are outside thresholds
        alerts = []
        
        if self.dissolved_oxygen < self.pond.min_oxygen:
            alerts.append(f"Low oxygen: {self.dissolved_oxygen} mg/L (min: {self.pond.min_oxygen})")
        
        if self.ph_level < self.pond.min_ph or self.ph_level > self.pond.max_ph:
            alerts.append(f"pH out of range: {self.ph_level} (range: {self.pond.min_ph}-{self.pond.max_ph})")
        
        if self.ammonia and self.ammonia > self.pond.max_ammonia:
            alerts.append(f"High ammonia: {self.ammonia} mg/L (max: {self.pond.max_ammonia})")
        
        if alerts:
            self.alert_generated = True
            self.alert_message = "; ".join(alerts)
        
        super().save(*args, **kwargs)


# ==================== HEALTH & DISEASE MANAGEMENT ====================

class DiseaseRecord(models.Model):
    """Disease outbreak tracking"""
    
    DISEASE_TYPES = [
        ('BACTERIAL', 'Bacterial'),
        ('VIRAL', 'Viral'),
        ('FUNGAL', 'Fungal'),
        ('PARASITIC', 'Parasitic'),
        ('ENVIRONMENTAL', 'Environmental'),
        ('NUTRITIONAL', 'Nutritional'),
    ]
    
    SEVERITY = [
        ('LOW', 'Low - Sporadic'),
        ('MEDIUM', 'Medium - Spreading'),
        ('HIGH', 'High - Widespread'),
        ('CRITICAL', 'Critical - Emergency'),
    ]
    
    cycle = models.ForeignKey(ProductionCycle, on_delete=models.CASCADE, related_name='diseases')
    disease_name = models.CharField(max_length=200)
    disease_type = models.CharField(max_length=20, choices=DISEASE_TYPES)
    severity = models.CharField(max_length=10, choices=SEVERITY, default='MEDIUM')
    
    detection_date = models.DateField(default=timezone.now)
    symptoms = models.TextField()
    
    # Affected population
    estimated_affected = models.IntegerField(help_text="Estimated number affected", null=True, blank=True)
    mortality_count = models.IntegerField(default=0, help_text="Mortality due to this disease")
    
    # Treatment
    treatment_applied = models.TextField()
    medication_used = models.CharField(max_length=200, blank=True)
    treatment_cost = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    
    # Resolution
    resolved_date = models.DateField(null=True, blank=True)
    is_resolved = models.BooleanField(default=False)
    
    # Metadata
    diagnosed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='diagnosed_diseases')
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ['-detection_date']

    def __str__(self):
        return f"{self.cycle.pond.name} - {self.disease_name} ({self.detection_date})"


class TreatmentRecord(models.Model):
    """Medical treatments applied"""
    
    TREATMENT_TYPES = [
        ('ANTIBIOTIC', 'Antibiotic'),
        ('ANTIPARASITIC', 'Antiparasitic'),
        ('FUNGICIDE', 'Fungicide'),
        ('VACCINE', 'Vaccine'),
        ('PROBIOTIC', 'Probiotic'),
        ('DISINFECTANT', 'Disinfectant'),
    ]
    
    APPLICATION_METHODS = [
        ('BATH', 'Bath Treatment'),
        ('ORAL', 'Oral (in feed)'),
        ('INJECTION', 'Injection'),
        ('POND', 'Pond Application'),
    ]
    
    cycle = models.ForeignKey(ProductionCycle, on_delete=models.CASCADE, related_name='treatments')
    disease = models.ForeignKey(DiseaseRecord, on_delete=models.SET_NULL, null=True, blank=True, related_name='treatments')
    
    treatment_type = models.CharField(max_length=20, choices=TREATMENT_TYPES)
    medication_name = models.CharField(max_length=200)
    application_method = models.CharField(max_length=20, choices=APPLICATION_METHODS)
    dosage = models.CharField(max_length=100, help_text="e.g., 5mg/L, 10g/kg feed")
    
    application_date = models.DateField()
    next_application = models.DateField(null=True, blank=True)
    
    quantity_used = models.FloatField(help_text="Quantity used")
    unit = models.CharField(max_length=20, default="ml")
    cost = models.DecimalField(max_digits=10, decimal_places=2)
    
    applied_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    notes = models.TextField(blank=True)
    
    class Meta:
        ordering = ['-application_date']


class MortalityRecord(models.Model):
    """Enhanced mortality tracking"""
    
    MORTALITY_REASONS = [
        ('DISEASE', 'Disease'),
        ('PREDATOR', 'Predator Attack'),
        ('OXYGEN', 'Low Oxygen'),
        ('WATER_QUALITY', 'Poor Water Quality'),
        ('STRESS', 'Stress'),
        ('CANNIBALISM', 'Cannibalism'),
        ('HANDLING', 'Handling Injury'),
        ('OLD_AGE', 'Old Age'),
        ('UNKNOWN', 'Unknown'),
    ]
    
    cycle = models.ForeignKey(ProductionCycle, on_delete=models.CASCADE, related_name='mortalities')
    disease = models.ForeignKey(DiseaseRecord, on_delete=models.SET_NULL, null=True, blank=True)
    
    date = models.DateField(default=timezone.now)
    quantity_dead = models.PositiveIntegerField(help_text="Number of dead fish")
    reason = models.CharField(max_length=20, choices=MORTALITY_REASONS, default='UNKNOWN')
    
    # If disease-related
    symptoms_observed = models.TextField(blank=True)
    
    # Disposal method
    disposal_method = models.CharField(max_length=50, blank=True, help_text="Burial, composting, etc.")
    
    # Metadata
    recorded_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ['-date']
        indexes = [
            models.Index(fields=['date']),
        ]

    def __str__(self):
        return f"{self.cycle.pond.name} - {self.quantity_dead} dead ({self.date})"

    def clean(self):
        """Validate mortality doesn't exceed current population"""
        if self.cycle and self.pk is None:  # Only for new records
            current_pop = self.cycle.current_population
            
            if self.quantity_dead > current_pop:
                raise ValidationError(f"Mortality ({self.quantity_dead}) exceeds current population ({current_pop})")


# ==================== HARVEST & SALES MANAGEMENT ====================

class Harvest(models.Model):
    """Enhanced harvest management"""
    
    HARVEST_METHODS = [
        ('PARTIAL', 'Partial Harvest'),
        ('FINAL', 'Final Harvest'),
        ('SELECTIVE', 'Selective Harvest'),
    ]
    
    QUALITY_GRADES = [
        ('A', 'Grade A - Premium'),
        ('B', 'Grade B - Standard'),
        ('C', 'Grade C - Economy'),
        ('REJECT', 'Reject'),
    ]
    
    cycle = models.ForeignKey(ProductionCycle, on_delete=models.CASCADE, related_name='harvests')
    harvest_method = models.CharField(max_length=20, choices=HARVEST_METHODS, default='FINAL')
    
    # Quantity
    quantity_kg = models.FloatField(help_text="Harvest quantity in kg")
    piece_count = models.IntegerField(help_text="Number of fish harvested", null=True, blank=True)
    avg_weight = models.FloatField(help_text="Average weight in grams", null=True, blank=True)
    
    # Quality
    grade = models.CharField(max_length=10, choices=QUALITY_GRADES, default='B')
    condition = models.TextField(blank=True, help_text="Overall condition of harvest")
    
    # Harvest details
    harvest_date = models.DateField(default=timezone.now)
    harvest_time = models.TimeField(null=True, blank=True)
    duration_hours = models.FloatField(help_text="Harvest duration in hours", null=True, blank=True)
    
    # Labor
    workers_count = models.IntegerField(null=True, blank=True)
    labor_cost = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    
    # Post-harvest
    ice_used_kg = models.FloatField(help_text="Ice used in kg", null=True, blank=True)
    storage_location = models.CharField(max_length=100, blank=True)
    
    # Metadata
    harvested_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ['-harvest_date']
        indexes = [
            models.Index(fields=['harvest_date']),
        ]

    def __str__(self):
        return f"{self.cycle.pond.name} - {self.quantity_kg}kg ({self.harvest_date})"

    def save(self, *args, **kwargs):
        if self.piece_count and self.quantity_kg:
            self.avg_weight = (self.quantity_kg * 1000) / self.piece_count
        super().save(*args, **kwargs)

    @property
    def total_sales(self):
        """Total revenue from this harvest"""
        return self.sales.aggregate(
            total=Sum(
                ExpressionWrapper(
                    F('quantity_kg') * F('price_per_kg'),
                    output_field=DecimalField(max_digits=12, decimal_places=2)
                )
            )
        )['total'] or 0

    @property
    def remaining_quantity(self):
        """Remaining unsold quantity from this harvest"""
        sold = self.sales.aggregate(total=Sum('quantity_kg'))['total'] or 0
        return self.quantity_kg - sold

    @property
    def average_sale_price(self):
        """Average price achieved for this harvest"""
        if self.total_sales and self.quantity_kg:
            return self.total_sales / self.quantity_kg
        return 0


class Customer(models.Model):
    """Customer management for fish sales"""
    
    CUSTOMER_TYPES = [
        ('WHOLESALER', 'Wholesaler'),
        ('RETAILER', 'Retailer'),
        ('RESTAURANT', 'Restaurant'),
        ('HOTEL', 'Hotel'),
        ('EXPORTER', 'Exporter'),
        ('INDIVIDUAL', 'Individual'),
    ]
    
    customer_id = models.CharField(max_length=50, unique=True)
    name = models.CharField(max_length=200)
    customer_type = models.CharField(max_length=20, choices=CUSTOMER_TYPES, default='RETAILER')
    
    phone = models.CharField(max_length=20)
    alternate_phone = models.CharField(max_length=20, blank=True)
    email = models.EmailField(blank=True)
    
    address = models.TextField()
    city = models.CharField(max_length=100)
    
    # Business details
    business_name = models.CharField(max_length=200, blank=True)
    tax_number = models.CharField(max_length=100, blank=True)
    
    # Credit
    credit_limit = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    current_balance = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    
    # Preferences
    preferred_species = models.CharField(max_length=200, blank=True)
    preferred_payment = models.CharField(max_length=50, blank=True)
    
    is_active = models.BooleanField(default=True)
    notes = models.TextField(blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name


class FishSale(models.Model):
    """Enhanced fish sales tracking"""
    
    SALE_STATUS = [
        ('PENDING', 'Pending'),
        ('CONFIRMED', 'Confirmed'),
        ('DELIVERED', 'Delivered'),
        ('PAID', 'Paid'),
        ('CANCELLED', 'Cancelled'),
    ]
    
    PAYMENT_METHODS = [
        ('CASH', 'Cash'),
        ('BANK_TRANSFER', 'Bank Transfer'),
        ('MOBILE', 'Mobile Banking (bkash/Nagad)'),
        ('CHEQUE', 'Cheque'),
        ('CREDIT', 'Credit'),
    ]
    
    sale_number = models.CharField(max_length=50, unique=True, default=uuid.uuid4, editable=False)
    
    harvest = models.ForeignKey(Harvest, on_delete=models.CASCADE, related_name='sales')
    customer = models.ForeignKey(Customer, on_delete=models.SET_NULL, null=True, blank=True, related_name='purchases')
    
    # Sale details
    quantity_kg = models.FloatField(help_text="Quantity sold in kg")
    price_per_kg = models.DecimalField(max_digits=10, decimal_places=2)
    total_amount = models.DecimalField(max_digits=12, decimal_places=2, editable=False)
    
    sale_date = models.DateField(default=timezone.now)
    delivery_date = models.DateField(null=True, blank=True)
    
    # Customer details (if no customer record)
    customer_name = models.CharField(max_length=200, blank=True)
    customer_phone = models.CharField(max_length=20, blank=True)
    
    # Payment
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHODS, default='CASH')
    payment_status = models.CharField(max_length=20, choices=SALE_STATUS, default='PENDING')
    payment_date = models.DateField(null=True, blank=True)
    payment_reference = models.CharField(max_length=100, blank=True)
    
    # Transport
    vehicle_number = models.CharField(max_length=50, blank=True)
    transport_cost = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    
    # Metadata
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ['-sale_date']
        indexes = [
            models.Index(fields=['sale_number']),
            models.Index(fields=['sale_date']),
            models.Index(fields=['payment_status']),
        ]

    def __str__(self):
        return f"{self.sale_number} - {self.quantity_kg}kg @ ৳{self.price_per_kg}"

    def save(self, *args, **kwargs):
        self.total_amount = (Decimal(str(self.quantity_kg)) * self.price_per_kg).quantize(Decimal('0.01'))
        super().save(*args, **kwargs)

    @property
    def pond(self):
        return self.harvest.cycle.pond if self.harvest else None

    @property
    def species(self):
        return self.harvest.cycle.species if self.harvest else None

    def clean(self):
        """Ensure sale doesn't exceed harvest remaining quantity"""
        if self.harvest:
            total_sold = self.harvest.sales.exclude(pk=self.pk).aggregate(
                total=Sum('quantity_kg')
            )['total'] or 0
            if self.quantity_kg > (self.harvest.quantity_kg - total_sold):
                raise ValidationError(
                    f"Sale exceeds remaining harvest quantity. "
                    f"Available: {self.harvest.quantity_kg - total_sold}kg"
                )


# ==================== FINANCIAL MANAGEMENT ====================

class Expense(models.Model):
    """Comprehensive expense tracking"""
    
    EXPENSE_TYPES = [
        ('FEED', 'Feed'),
        ('FINGERLING', 'Fingerling'),
        ('MEDICINE', 'Medicine/Probiotics'),
        ('LABOR', 'Labor'),
        ('ELECTRICITY', 'Electricity'),
        ('FUEL', 'Fuel'),
        ('MAINTENANCE', 'Maintenance'),
        ('TRANSPORT', 'Transport'),
        ('EQUIPMENT', 'Equipment'),
        ('TAX', 'Tax/License'),
        ('OTHER', 'Other'),
    ]
    
    PAYMENT_METHODS = [
        ('CASH', 'Cash'),
        ('BANK', 'Bank Transfer'),
        ('MOBILE', 'Mobile Banking'),
        ('CREDIT', 'Credit'),
    ]
    
    cycle = models.ForeignKey(
        'ProductionCycle', 
        on_delete=models.CASCADE, 
        related_name='expenses'
    )
    expense_type = models.CharField(
        max_length=20, 
        choices=EXPENSE_TYPES, 
        default='OTHER'
    )
    
    description = models.CharField(max_length=200)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    expense_date = models.DateField(default=timezone.now)
    
    # Payment
    payment_method = models.CharField(
        max_length=20, 
        choices=PAYMENT_METHODS, 
        default='CASH'
    )
    paid_to = models.CharField(max_length=200, blank=True)
    receipt_number = models.CharField(max_length=100, blank=True)
    
    # If related to specific feed purchase
    feed_purchase = models.ForeignKey(
        'FeedPurchase', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='related_expenses'
    )
    
    # Metadata - FIXED: Added unique related_name to avoid conflict with dairy app
    created_by = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True,
        related_name='fishery_expenses'  # Unique related_name to avoid clash
    )
    notes = models.TextField(blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-expense_date']
        indexes = [
            models.Index(fields=['expense_date']),
            models.Index(fields=['expense_type']),
            models.Index(fields=['created_by']),
        ]
        verbose_name = "Expense"
        verbose_name_plural = "Expenses"

    def __str__(self):
        return f"{self.get_expense_type_display()} - ৳{self.amount} ({self.expense_date})"
    
    def save(self, *args, **kwargs):
        """Auto-update timestamps"""
        if not self.id:
            self.created_at = timezone.now()
        self.updated_at = timezone.now()
        super().save(*args, **kwargs)
    
    @property
    def formatted_amount(self):
        """Return formatted amount with currency symbol"""
        return f"৳{self.amount:,.2f}"
    
    @property
    def is_high_value(self):
        """Check if expense is high value (> 50,000 BDT)"""
        return self.amount > 50000
    
    @property
    def vat_amount(self):
        """Calculate 15% VAT (if applicable)"""
        return self.amount * Decimal('0.15')
    
    @property
    def total_with_vat(self):
        """Total including 15% VAT"""
        return self.amount + self.vat_amount
    
    def get_expense_type_color(self):
        """Return color class for expense type badges"""
        colors = {
            'FEED': 'primary',
            'FINGERLING': 'success',
            'MEDICINE': 'danger',
            'LABOR': 'warning',
            'ELECTRICITY': 'info',
            'FUEL': 'secondary',
            'MAINTENANCE': 'dark',
            'TRANSPORT': 'info',
            'EQUIPMENT': 'primary',
            'TAX': 'danger',
            'OTHER': 'secondary',
        }
        return colors.get(self.expense_type, 'secondary')
    
    def get_payment_method_color(self):
        """Return color class for payment method badges"""
        colors = {
            'CASH': 'success',
            'BANK': 'primary',
            'MOBILE': 'info',
            'CREDIT': 'warning',
        }
        return colors.get(self.payment_method, 'secondary')

class Budget(models.Model):
    """Budget planning for production cycles"""
    
    cycle = models.OneToOneField(ProductionCycle, on_delete=models.CASCADE, related_name='budget')
    
    # Planned costs
    planned_fingerling_cost = models.DecimalField(max_digits=12, decimal_places=2)
    planned_feed_cost = models.DecimalField(max_digits=12, decimal_places=2)
    planned_medicine_cost = models.DecimalField(max_digits=12, decimal_places=2)
    planned_labor_cost = models.DecimalField(max_digits=12, decimal_places=2)
    planned_other_cost = models.DecimalField(max_digits=12, decimal_places=2)
    
    # Planned revenue
    planned_harvest_kg = models.FloatField()
    planned_price_per_kg = models.DecimalField(max_digits=10, decimal_places=2)
    planned_revenue = models.DecimalField(max_digits=12, decimal_places=2, editable=False)
    
    # Planned profit
    planned_profit = models.DecimalField(max_digits=12, decimal_places=2, editable=False)
    planned_roi = models.DecimalField(max_digits=6, decimal_places=2, editable=False)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        self.planned_revenue = Decimal(str(self.planned_harvest_kg)) * self.planned_price_per_kg
        total_cost = (
            self.planned_fingerling_cost +
            self.planned_feed_cost +
            self.planned_medicine_cost +
            self.planned_labor_cost +
            self.planned_other_cost
        )
        self.planned_profit = self.planned_revenue - total_cost
        if total_cost > 0:
            self.planned_roi = (self.planned_profit / total_cost * 100).quantize(Decimal('0.01'))
        super().save(*args, **kwargs)


# ==================== REPORTS & ANALYTICS ====================

class FisheryFinancialReport(models.Model):
    """Comprehensive yearly financial report"""
    
    year = models.PositiveIntegerField(unique=True)
    generated_at = models.DateTimeField(auto_now_add=True)
    generated_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)

    # Investment (Costs)
    total_fingerling_cost = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total_feed_cost = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total_medicine_cost = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total_labor_cost = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total_electricity_cost = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total_transport_cost = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total_other_expenses = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total_investment = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    
    # Revenue
    total_sales_revenue = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total_harvest_kg = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    avg_selling_price = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    
    # Profitability
    net_profit = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    roi_percentage = models.DecimalField(max_digits=6, decimal_places=2, default=0)
    
    # Production Metrics
    total_cycles_completed = models.IntegerField(default=0)
    avg_cycle_days = models.IntegerField(default=0)
    avg_survival_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    avg_fcr = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    
    # Pond utilization
    total_pond_area = models.FloatField(default=0)
    productivity_per_acre = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    class Meta:
        ordering = ['-year']
        verbose_name = "Fishery Financial Report"
        verbose_name_plural = "Fishery Financial Reports"

    def __str__(self):
        return f"Fishery Report - {self.year}"

    def calculate_totals(self):
        """Calculate all totals for the year"""
        
        # Get all cycles for the year
        cycles = ProductionCycle.objects.filter(stocking_date__year=self.year)
        
        # Fingerling cost
        self.total_fingerling_cost = cycles.aggregate(
            total=Sum('fingerling_cost')
        )['total'] or 0
        
        # Feed cost
        self.total_feed_cost = FeedRecord.objects.filter(
            cycle__in=cycles
        ).aggregate(total=Sum('cost'))['total'] or 0
        
        # Expenses by type
        expenses = Expense.objects.filter(cycle__in=cycles)
        self.total_medicine_cost = expenses.filter(expense_type='MEDICINE').aggregate(
            total=Sum('amount')
        )['total'] or 0
        self.total_labor_cost = expenses.filter(expense_type='LABOR').aggregate(
            total=Sum('amount')
        )['total'] or 0
        self.total_electricity_cost = expenses.filter(expense_type='ELECTRICITY').aggregate(
            total=Sum('amount')
        )['total'] or 0
        self.total_transport_cost = expenses.filter(expense_type='TRANSPORT').aggregate(
            total=Sum('amount')
        )['total'] or 0
        self.total_other_expenses = expenses.exclude(
            expense_type__in=['MEDICINE', 'LABOR', 'ELECTRICITY', 'TRANSPORT', 'FEED']
        ).aggregate(total=Sum('amount'))['total'] or 0
        
        # Total investment
        self.total_investment = (
            self.total_fingerling_cost +
            self.total_feed_cost +
            self.total_medicine_cost +
            self.total_labor_cost +
            self.total_electricity_cost +
            self.total_transport_cost +
            self.total_other_expenses
        )
        
        # Sales revenue
        sales = FishSale.objects.filter(harvest__cycle__in=cycles)
        self.total_sales_revenue = sales.aggregate(
            total=Sum(
                ExpressionWrapper(
                    F('quantity_kg') * F('price_per_kg'),
                    output_field=DecimalField(max_digits=12, decimal_places=2)
                )
            )
        )['total'] or 0
        
        # Total harvest
        harvests = Harvest.objects.filter(cycle__in=cycles)
        self.total_harvest_kg = harvests.aggregate(total=Sum('quantity_kg'))['total'] or 0
        
        # Average selling price
        if self.total_harvest_kg > 0:
            self.avg_selling_price = (self.total_sales_revenue / self.total_harvest_kg).quantize(Decimal('0.01'))
        
        # Net profit
        self.net_profit = self.total_sales_revenue - self.total_investment
        
        # ROI
        if self.total_investment > 0:
            self.roi_percentage = (self.net_profit / self.total_investment * 100).quantize(Decimal('0.01'))
        
        # Production metrics
        self.total_cycles_completed = cycles.filter(status='COMPLETED').count()
        
        # Average cycle days
        completed_cycles = cycles.filter(status='COMPLETED', actual_harvest_date__isnull=False)
        if completed_cycles.exists():
            total_days = sum([(c.actual_harvest_date - c.stocking_date).days for c in completed_cycles])
            self.avg_cycle_days = total_days // completed_cycles.count()
        
        # Average survival rate
        survival_rates = [c.survival_rate for c in cycles if c.survival_rate > 0]
        if survival_rates:
            self.avg_survival_rate = sum(survival_rates) / len(survival_rates)
        
        # Average FCR
        fcr_values = [c.fcr for c in cycles if c.fcr > 0]
        if fcr_values:
            self.avg_fcr = sum(fcr_values) / len(fcr_values)
        
        # Pond area
        ponds = Pond.objects.filter(farm__isnull=False).distinct()
        self.total_pond_area = sum([p.size_in_acres for p in ponds])
        
        # Productivity per acre
        if self.total_pond_area > 0:
            self.productivity_per_acre = (self.total_harvest_kg / self.total_pond_area).quantize(Decimal('0.01'))
        
        self.save()
        return self