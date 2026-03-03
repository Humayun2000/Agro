from django.db import models
from django.utils import timezone


# -------------------------
# 1️⃣ Breed Model
# -------------------------

class Breed(models.Model):
    name = models.CharField(max_length=100, unique=True)
    origin_country = models.CharField(max_length=100, blank=True, null=True)
    average_milk_per_day = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        blank=True,
        null=True,
        help_text="Average milk production per day (liters)"
    )
    notes = models.TextField(blank=True, null=True)

    def __str__(self):
        return self.name


# -------------------------
# 2️⃣ Cow Model
# -------------------------

class Cow(models.Model):

    STATUS_CHOICES = [
        ('active', 'Active'),
        ('sold', 'Sold'),
        ('dead', 'Dead'),
    ]

    tag_number = models.CharField(max_length=50, unique=True)
    name = models.CharField(max_length=100, blank=True, null=True)
    breed = models.ForeignKey(
        Breed,
        on_delete=models.SET_NULL,
        null=True,
        related_name='cows'
    )

    date_of_birth = models.DateField(blank=True, null=True)
    purchase_date = models.DateField(blank=True, null=True)
    purchase_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        blank=True,
        null=True
    )

    current_weight = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        blank=True,
        null=True,
        help_text="Weight in KG"
    )

    lactating = models.BooleanField(default=False)
    status = models.CharField(
        max_length=10,
        choices=STATUS_CHOICES,
        default='active'
    )

    mother = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='calves'
    )

    notes = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.tag_number} - {self.name or 'No Name'}"


# -------------------------
# 3️⃣ Milk Production Model
# -------------------------

class MilkProduction(models.Model):

    cow = models.ForeignKey(
        Cow,
        on_delete=models.CASCADE,
        related_name='milk_records'
    )

    date = models.DateField(default=timezone.now)

    morning_milk = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        default=0
    )

    evening_milk = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        default=0
    )

    notes = models.TextField(blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('cow', 'date')
        ordering = ['-date']

    @property
    def total_milk(self):
        return (self.morning_milk or 0) + (self.evening_milk or 0)

    def __str__(self):
        return f"{self.cow.tag_number} - {self.date}"