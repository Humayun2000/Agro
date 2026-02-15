from django.db import models

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
    pond = models.ForeignKey(Pond, on_delete=models.CASCADE)
    species = models.ForeignKey(FishSpecies, on_delete=models.CASCADE)
    quantity = models.IntegerField()
    stocking_date = models.DateField()
    cost = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        return f"{self.species.name} - {self.pond.name}"


class FeedRecord(models.Model):
    pond = models.ForeignKey(Pond, on_delete=models.CASCADE)
    feed_type = models.CharField(max_length=100)
    quantity_kg = models.FloatField()
    cost = models.DecimalField(max_digits=10, decimal_places=2)
    date = models.DateField()

    def __str__(self):
        return f"{self.pond.name} - {self.feed_type}"

class MortalityRecord(models.Model):
    pond = models.ForeignKey(Pond, on_delete=models.CASCADE)
    species = models.ForeignKey(FishSpecies, on_delete=models.CASCADE)
    quantity_dead = models.IntegerField()
    date = models.DateField()
    reason = models.TextField(blank=True)

    def __str__(self):
        return f"{self.species.name} - {self.quantity_dead}"

class Harvest(models.Model):
    pond = models.ForeignKey(Pond, on_delete=models.CASCADE)
    species = models.ForeignKey(FishSpecies, on_delete=models.CASCADE)
    quantity_kg = models.FloatField()
    harvest_date = models.DateField()

    def __str__(self):
        return f"Harvest - {self.pond.name}"

class FishSale(models.Model):
    harvest = models.ForeignKey(Harvest, on_delete=models.CASCADE)
    buyer_name = models.CharField(max_length=100)
    price_per_kg = models.DecimalField(max_digits=10, decimal_places=2)
    total_amount = models.DecimalField(max_digits=12, decimal_places=2)
    sale_date = models.DateField()

    def __str__(self):
        return f"Sale - {self.buyer_name}"

