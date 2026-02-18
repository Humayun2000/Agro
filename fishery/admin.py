from django.contrib import admin
from django.db.models import Sum
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

    list_display = (
        'pond',
        'species',
        'quantity',
        'total_mortality',
        'total_harvest',
        'remaining_quantity',
        'stocking_date',
        'cost',
    )

    list_filter = (
        'pond',
        'species',
        'stocking_date',
    )

    search_fields = (
        'pond__name',
        'species__name',
    )

    date_hierarchy = 'stocking_date'

    ordering = ('-stocking_date',)

    readonly_fields = (
        'total_mortality',
        'total_harvest',
        'remaining_quantity',
        'created_at',
    )

    fieldsets = (
        ("Stock Information", {
            'fields': (
                'pond',
                'species',
                'quantity',
                'stocking_date',
                'cost',
            )
        }),
        ("Calculated Data", {
            'fields': (
                'total_mortality',
                'total_harvest',
                'remaining_quantity',
            )
        }),
        ("System Info", {
            'fields': ('created_at',)
        }),
    )

    def total_mortality(self, obj):
        return obj.mortalities.aggregate(
            total=Sum('quantity_dead')
        )['total'] or 0

    total_mortality.short_description = "Total Mortality"

    def total_harvest(self, obj):
        return obj.harvests.aggregate(
            total=Sum('quantity_kg')
        )['total'] or 0

    total_harvest.short_description = "Total Harvest"

    def remaining_quantity(self, obj):
        mortality = self.total_mortality(obj)
        harvest = self.total_harvest(obj)
        return obj.quantity - mortality - harvest

    remaining_quantity.short_description = "Remaining Stock"
@admin.register(FeedRecord)
class FeedRecordAdmin(admin.ModelAdmin):
    list_display = ('pond', 'feed_type', 'quantity_kg', 'cost', 'date')


@admin.register(MortalityRecord)
class MortalityRecordAdmin(admin.ModelAdmin):

    list_display = (
        'get_pond',
        'get_species',
        'quantity_dead',
        'date',
        'reason',
    )

    list_filter = (
        'stock__pond',
        'stock__species',
        'date',
    )

    search_fields = (
        'stock__pond__name',
        'stock__species__name',
        'reason',
    )

    date_hierarchy = 'date'

    list_select_related = ('stock__pond', 'stock__species')

    def get_pond(self, obj):
        return obj.stock.pond

    get_pond.short_description = "Pond"

    def get_species(self, obj):
        return obj.stock.species

    get_species.short_description = "Species"

@admin.register(Harvest)
class HarvestAdmin(admin.ModelAdmin):

    list_display = (
        'get_pond',
        'get_species',
        'quantity_kg',
        'harvest_date',
    )

    list_filter = (
        'stock__pond',
        'stock__species',
        'harvest_date',
    )

    search_fields = (
        'stock__pond__name',
        'stock__species__name',
    )

    date_hierarchy = 'harvest_date'

    list_select_related = ('stock__pond', 'stock__species')

    def get_pond(self, obj):
        return obj.stock.pond

    get_pond.short_description = "Pond"

    def get_species(self, obj):
        return obj.stock.species

    get_species.short_description = "Species"
# @admin.register(FishSale)
# class FishSaleAdmin(admin.ModelAdmin):
#     list_display = ('harvest', 'quantity_kg', 'sale_price_per_kg', 'sale_date')    

