from django.db import models

from django.db.models import Sum, F, DecimalField
from django.core.exceptions import ValidationError 


class Pond(models.Model):
    name = models.CharField(max_length=100)
    size_in_acres = models.FloatField()
    water_source = models.CharField(max_length=100)
    location = models.CharField(max_length=150, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name 
    
class FishSpecies(models.Model):
    name = models.CharField(max_length=100)
    average_growth_days = models.IntegerField()

    def __str__(self):
        return self.name

class Stock(models.Model):
    pond = models.ForeignKey(
        'Pond',
        on_delete=models.CASCADE,
        related_name='stocks'
    )
    species = models.ForeignKey(
        'FishSpecies',
        on_delete=models.CASCADE,
        related_name='stocks'
    )
    quantity = models.PositiveIntegerField()
    stocking_date = models.DateField()
    cost = models.DecimalField(max_digits=12, decimal_places=2)

    created_at = models.DateTimeField(auto_now_add=True, null=True, blank=True) 

    class Meta:
        ordering = ['-stocking_date']

    def total_mortality(self):
        return self.mortalityrecord_set.aggregate(
            total=Sum('quantity_dead')
        )['total'] or 0

    def total_harvest(self):
        return self.harvest_set.aggregate(
            total=Sum('quantity_kg')
        )['total'] or 0

    def remaining_quantity(self):
        return self.quantity - self.total_mortality() - self.total_harvest()

    def __str__(self):
        return f"{self.species.name} - {self.pond.name}"
    
    def total_feed_cost(self):
        return FeedRecord.objects.filter(
            pond=self.pond
        ).aggregate(total=Sum('cost'))['total'] or 0

    def total_sale_revenue(self):
        return FishSale.objects.filter(
            harvest__stock=self
        ).aggregate(total=Sum(
            F('quantity_kg') * F('price_per_kg'),
            output_field=DecimalField()
        ))['total'] or 0

    def total_capital(self):
        return self.cost + self.total_feed_cost()

    def profit(self):
        return self.total_sale_revenue() - self.total_capital()
        

class FeedRecord(models.Model):
    pond = models.ForeignKey(Pond, on_delete=models.CASCADE)
    feed_type = models.CharField(max_length=100)
    quantity_kg = models.FloatField()
    cost = models.DecimalField(max_digits=10, decimal_places=2)
    date = models.DateField()

    def __str__(self):
        return f"{self.pond.name} - {self.feed_type}"

class MortalityRecord(models.Model):
    stock = models.ForeignKey(
        Stock,
        on_delete=models.CASCADE,
        related_name='mortalityrecord_set',
        null=True,   # ✅ allows existing rows to stay valid
        blank=True
    )
    quantity_dead = models.PositiveIntegerField()
    date = models.DateField()
    reason = models.TextField(blank=True)

    def clean(self):
        if self.stock and self.quantity_dead > self.stock.remaining_quantity():
            raise ValidationError("Mortality exceeds remaining stock.")

    def __str__(self):
        # ✅ safe display even if stock is null
        if self.stock:
            return f"{self.stock.species.name} - {self.quantity_dead}"
        return f"No Stock - {self.quantity_dead}"



class Harvest(models.Model):
    stock = models.ForeignKey(
        Stock,
        on_delete=models.CASCADE,
        related_name='harvest_set',
        null=True,          # ✅ Added
        blank=True          # ✅ Added
    )
    quantity_kg = models.PositiveIntegerField()
    harvest_date = models.DateField()

    def clean(self):
        if self.stock and self.quantity_kg > self.stock.remaining_quantity():
            raise ValidationError("Harvest exceeds remaining stock.")

    def __str__(self):
        return f"Harvest - {self.stock.pond.name if self.stock else 'No Stock'}"
    
class FishSale(models.Model):
    harvest = models.ForeignKey(
        Harvest,
        on_delete=models.CASCADE,
        related_name='sales'
    )
    quantity_kg = models.PositiveIntegerField(default=True)
    price_per_kg = models.DecimalField(max_digits=10, decimal_places=2)
    sale_date = models.DateField()

    created_at = models.DateTimeField(auto_now_add=True, null=True, blank=True)

    class Meta:
        ordering = ['-sale_date']

    def clean(self):
        if self.harvest:
            total_sold = self.harvest.sales.aggregate(
                total=Sum('quantity_kg')
            )['total'] or 0

            # Exclude current instance during update
            if self.pk:
                total_sold -= self.quantity_kg

            if total_sold + self.quantity_kg > self.harvest.quantity_kg:
                raise ValidationError("Sale exceeds harvested quantity.")

    @property
    def total_amount(self):
        return self.quantity_kg * self.price_per_kg

    def __str__(self):
        return f"Sale - {self.harvest.stock.pond.name}"

