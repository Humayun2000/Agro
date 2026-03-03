from django.contrib import admin
from .models import Breed, Cow, MilkProduction


@admin.register(Breed)
class BreedAdmin(admin.ModelAdmin):
    list_display = ('name', 'origin_country', 'average_milk_per_day')
    search_fields = ('name',)


@admin.register(Cow)
class CowAdmin(admin.ModelAdmin):
    list_display = ('tag_number', 'name', 'breed', 'lactating', 'status')
    list_filter = ('status', 'lactating', 'breed')
    search_fields = ('tag_number', 'name')
    autocomplete_fields = ('breed', 'mother')


@admin.register(MilkProduction)
class MilkProductionAdmin(admin.ModelAdmin):
    list_display = ('cow', 'date', 'morning_milk', 'evening_milk', 'get_total')
    list_filter = ('date',)
    search_fields = ('cow__tag_number',)

    def get_total(self, obj):
        return obj.total_milk
    get_total.short_description = "Total Milk (L)"