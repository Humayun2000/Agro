from django.contrib import admin
from .models import Pond, FishSpecies, Stock, FeedRecord, MortalityRecord, Harvest, FishSale

@admin.register(Pond)
class PondAdmin(admin.ModelAdmin):
    list_display = ('name', 'size_in_acres', 'water_source', 'created_at')
    search_fields = ('name',)

@admin.register(FishSpecies)
class FishSpeciesAdmin(admin.ModelAdmin):
    list_display = ('name', 'average_growth_days')


@admin.register(Stock)
class StockAdmin(admin.ModelAdmin):
    list_display = ('pond', 'species', 'quantity', 'stocking_date', 'cost')

@admin.register(FeedRecord)
class FeedRecordAdmin(admin.ModelAdmin):
    list_display = ('pond', 'feed_type', 'quantity_kg', 'cost', 'date')


@admin.register(MortalityRecord)
class MortalityRecordAdmin(admin.ModelAdmin):
    list_display = ('pond', 'species', 'quantity_dead', 'date', 'reason')

@admin.register(Harvest)
class HarvestAdmin(admin.ModelAdmin):
    list_display = ('pond', 'species', 'quantity_kg', 'harvest_date')

# @admin.register(FishSale)
# class FishSaleAdmin(admin.ModelAdmin):
#     list_display = ('harvest', 'quantity_kg', 'sale_price_per_kg', 'sale_date')    

