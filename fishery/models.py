from django.db import models
from django.utils import timezone
from django.db.models import Sum, F, DecimalField, ExpressionWrapper
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
    cycle = models.ForeignKey('ProductionCycle', on_delete=models.CASCADE,related_name='feeds', blank=True, null=True)
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
    cycle = models.ForeignKey('ProductionCycle', on_delete=models.CASCADE,related_name='mortalities', blank=True, null=True)
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
    cycle = models.ForeignKey('ProductionCycle', on_delete=models.CASCADE, related_name='harvests', blank=True, null=True)  
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
    quantity_kg = models.PositiveIntegerField()
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


# production cycle models for fishery management, including ponds,
# fish species, stocking, feed records, mortality records, harvests, and sales.
# Each model includes relevant fields and methods to calculate totals and profits. 
# Validation is implemented to ensure data integrity.      


class ProductionCycle(models.Model):

    STATUS_CHOICES = (
        ('Running', 'Running'),
        ('Completed', 'Completed'),
    )

    pond = models.ForeignKey('Pond', on_delete=models.CASCADE)
    species = models.ForeignKey('FishSpecies', on_delete=models.CASCADE)

    stocking_date = models.DateField(default=timezone.now)

    initial_quantity = models.PositiveIntegerField()
    initial_avg_weight = models.FloatField(help_text="Weight in grams")

    expected_harvest_date = models.DateField(null=True, blank=True)

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='Running'
    )

    notes = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"{self.pond.name} - {self.species.name} ({self.status})"


    @property
    def total_sales(self):
        result = FishSale.objects.filter(
            harvest__cycle=self
        ).aggregate(
            total=Sum(
                ExpressionWrapper(
                    F('quantity_kg') * F('price_per_kg'),
                    output_field=DecimalField()
                )
            )
        )['total']

        return result or 0


    @property
    def total_expense(self):
        return self.expenses.aggregate(
            total=Sum('amount')
        )['total'] or 0


    @property
    def net_profit(self):
        return self.total_sales - self.total_expense  

class Expense(models.Model):
    cycle = models.ForeignKey(
        ProductionCycle,
        on_delete=models.CASCADE,
        related_name='expenses'
    )
    description = models.CharField(max_length=200)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    expense_date = models.DateField(default=timezone.now)

    def __str__(self):
        return f"{self.description} - {self.amount}"


# yearly report model to aggregate data across production cycles,
#  providing insights into overall performance and profitability.


class FisheryFinancialReport(models.Model):
    year = models.PositiveIntegerField(default=timezone.now().year)
    created_at = models.DateTimeField(auto_now_add=True)

    # Totals will be computed dynamically
    # Optional: store cached totals
    total_fish_purchase = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total_feed_purchase = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total_medicine_purchase = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total_other_expenses = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total_investment = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total_sales_revenue = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    net_profit = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    class Meta:
        verbose_name = "Fishery Financial Report"
        verbose_name_plural = "Fishery Financial Reports"

    def __str__(self):
        return f"Fishery Report - {self.year}"

    # ================================
    # Computed Properties / Methods
    # ================================

    def calculate_totals(self):
        """Calculate all totals based on existing models for the given year"""
        # Filter by year for Stocks
        stocks = Stock.objects.filter(stocking_date__year=self.year)
        feeds = FeedRecord.objects.filter(date__year=self.year)
        harvests = Harvest.objects.filter(harvest_date__year=self.year)
        sales = FishSale.objects.filter(sale_date__year=self.year)
        expenses = Expense.objects.filter(cycle__stocking_date__year=self.year)  # All other expenses linked to cycles

        # -----------------------
        # Fish purchase cost
        # -----------------------
        self.total_fish_purchase = stocks.aggregate(
            total=Sum('cost')
        )['total'] or 0

        # -----------------------
        # Feed purchase cost
        # -----------------------
        self.total_feed_purchase = feeds.aggregate(
            total=Sum('cost')
        )['total'] or 0

        # -----------------------
        # Medicine / Other cost
        # You can filter Expenses by description if needed
        self.total_medicine_purchase = expenses.filter(description__icontains='medicine').aggregate(
            total=Sum('amount')
        )['total'] or 0

        # -----------------------
        # Other expenses
        self.total_other_expenses = expenses.exclude(description__icontains='medicine').aggregate(
            total=Sum('amount')
        )['total'] or 0

        # -----------------------
        # Total Investment = fish + feed + medicine + other
        self.total_investment = self.total_fish_purchase + self.total_feed_purchase + self.total_medicine_purchase + self.total_other_expenses

        # -----------------------
        # Sales revenue
        self.total_sales_revenue = sales.aggregate(
            total=Sum(
                ExpressionWrapper(
                    F('quantity_kg') * F('price_per_kg'),
                    output_field=DecimalField(max_digits=12, decimal_places=2)
                )
            )
        )['total'] or 0

        # -----------------------
        # Net profit
        self.net_profit = self.total_sales_revenue - self.total_investment

        # Save computed totals
        self.save()

        return {
            "total_fish_purchase": self.total_fish_purchase,
            "total_feed_purchase": self.total_feed_purchase,
            "total_medicine_purchase": self.total_medicine_purchase,
            "total_other_expenses": self.total_other_expenses,
            "total_investment": self.total_investment,
            "total_sales_revenue": self.total_sales_revenue,
            "net_profit": self.net_profit
        }