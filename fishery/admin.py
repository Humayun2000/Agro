# fishery/admin.py

from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse, path
from django.db.models import Sum, Avg, Count, Q, F
from django.utils import timezone
from datetime import datetime, timedelta
from .models import *

# ==================== FARM & POND ADMIN ====================

@admin.register(Farm)
class FarmAdmin(admin.ModelAdmin):
    list_display = ['name', 'registration_number', 'city', 'total_area', 'active_ponds', 'phone', 'email', 'status_indicator', 'action_buttons']
    list_filter = ['city', 'country']
    search_fields = ['name', 'registration_number', 'phone', 'email']
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'registration_number', 'address', 'city', 'state', 'country')
        }),
        ('Contact Details', {
            'fields': ('phone', 'email', 'website')
        }),
        ('Location & GPS', {
            'fields': ('latitude', 'longitude'),
            'classes': ('collapse',)
        }),
        ('Farm Details', {
            'fields': ('total_area', 'active_ponds', 'employee_count')
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def status_indicator(self, obj):
        if obj.active_ponds > 0:
            return format_html('<span style="color: #28a745;">● Active</span>')
        return format_html('<span style="color: #dc3545;">○ Inactive</span>')
    status_indicator.short_description = "Status"
    
    def action_buttons(self, obj):
        return format_html(
            '<div style="display: flex; gap: 5px;">'
            '<a class="btn btn-sm btn-info" href="{}" target="_blank" style="color: white; text-decoration: none; padding: 3px 8px; border-radius: 4px; background: #17a2b8;">👁️</a>'
            '<a class="btn btn-sm btn-warning" href="{}" style="color: white; text-decoration: none; padding: 3px 8px; border-radius: 4px; background: #ffc107;">✏️</a>'
            '</div>',
            reverse('admin:fishery_farm_change', args=[obj.pk]),
            reverse('admin:fishery_farm_change', args=[obj.pk])
        )
    action_buttons.short_description = "Actions"


@admin.register(Pond)
class PondAdmin(admin.ModelAdmin):
    list_display = ['pond_id', 'name', 'farm_link', 'pond_type', 'size_in_acres', 'status_badge', 'current_cycle_info', 'water_quality_status', 'action_buttons']
    list_filter = ['farm', 'pond_type', 'status', 'is_active', 'bottom_type', 'water_source']
    search_fields = ['name', 'pond_id', 'location']
    readonly_fields = ['created_at', 'updated_at', 'volume_calculated']
    
    fieldsets = (
        ('Identification', {
            'fields': ('farm', 'pond_id', 'name', 'pond_type')
        }),
        ('Physical Characteristics', {
            'fields': ('size_in_acres', 'length', 'width', 'average_depth', 'max_depth', 'volume', 'bottom_type'),
            'classes': ('wide',)
        }),
        ('Location & Water', {
            'fields': ('location', 'latitude', 'longitude', 'water_source')
        }),
        ('Operational Status', {
            'fields': ('is_active', 'status')
        }),
        ('Water Quality Thresholds', {
            'fields': ('min_oxygen', 'max_ammonia', 'min_ph', 'max_ph', 'optimal_temp_min', 'optimal_temp_max'),
            'classes': ('collapse',)
        }),
        ('Metadata', {
            'fields': ('created_by', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def farm_link(self, obj):
        if obj.farm:
            url = reverse('admin:fishery_farm_change', args=[obj.farm.pk])
            return format_html('<a href="{}">{}</a>', url, obj.farm.name)
        return "-"
    farm_link.short_description = "Farm"
    
    def status_badge(self, obj):
        colors = {
            'PREPARING': '#ffc107',
            'FILLING': '#17a2b8',
            'STOCKED': '#28a745',
            'HARVESTING': '#fd7e14',
            'DRYING': '#6c757d',
            'MAINTENANCE': '#6f42c1'
        }
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 10px; border-radius: 20px; font-size: 0.8rem;">{}</span>',
            colors.get(obj.status, '#6c757d'),
            obj.get_status_display()
        )
    status_badge.short_description = "Status"
    
    def volume_calculated(self, obj):
        if obj.length and obj.width and obj.average_depth:
            volume = (obj.length * obj.width * obj.average_depth * 0.3048)  # Convert to cubic meters
            return f"{volume:.2f} m³"
        return "Not calculated"
    volume_calculated.short_description = "Calculated Volume"
    
    def current_cycle_info(self, obj):
        cycle = obj.current_cycle()
        if cycle:
            url = reverse('admin:fishery_productioncycle_change', args=[cycle.pk])
            return format_html(
                '<a href="{}">{} - {} days</a>',
                url, cycle.species.name, cycle.days_in_production
            )
        return "-"
    current_cycle_info.short_description = "Current Cycle"
    
    def water_quality_status(self, obj):
        latest = obj.latest_water_quality()
        if latest:
            if latest.alert_generated:
                return format_html('<span style="color: #dc3545;">⚠ Alert</span>')
            return format_html('<span style="color: #28a745;">✓ Good</span>')
        return format_html('<span style="color: #6c757d;">No data</span>')
    water_quality_status.short_description = "Water Quality"
    
    def action_buttons(self, obj):
        return format_html(
            '<div style="display: flex; gap: 5px;">'
            '<a class="btn btn-sm btn-info" href="{}" style="color: white; text-decoration: none; padding: 3px 8px; border-radius: 4px; background: #17a2b8;">👁️</a>'
            '<a class="btn btn-sm btn-warning" href="{}" style="color: white; text-decoration: none; padding: 3px 8px; border-radius: 4px; background: #ffc107;">✏️</a>'
            '</div>',
            reverse('admin:fishery_pond_change', args=[obj.pk]),
            reverse('admin:fishery_pond_change', args=[obj.pk])
        )
    action_buttons.short_description = "Actions"
    
    actions = ['activate_ponds', 'deactivate_ponds', 'update_status']
    
    def activate_ponds(self, request, queryset):
        updated = queryset.update(is_active=True)
        self.message_user(request, f'{updated} ponds activated.')
    activate_ponds.short_description = "Activate selected ponds"
    
    def deactivate_ponds(self, request, queryset):
        updated = queryset.update(is_active=False)
        self.message_user(request, f'{updated} ponds deactivated.')
    deactivate_ponds.short_description = "Deactivate selected ponds"
    
    def update_status(self, request, queryset):
        for pond in queryset:
            if pond.status != 'STOCKED' and pond.current_cycle():
                pond.status = 'STOCKED'
                pond.save()
        self.message_user(request, f'Status updated for {queryset.count()} ponds.')
    update_status.short_description = "Update pond status"


# ==================== FISH SPECIES ADMIN ====================

@admin.register(FishSpecies)
class FishSpeciesAdmin(admin.ModelAdmin):
    list_display = ['name', 'scientific_name', 'category', 'water_type', 'average_growth_days', 'market_price', 'image_preview', 'cycle_count']
    list_filter = ['category', 'water_type']
    search_fields = ['name', 'scientific_name']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'scientific_name', 'category', 'water_type')
        }),
        ('Growth Parameters', {
            'fields': ('average_growth_days', 'harvest_weight_min', 'harvest_weight_max', 'expected_fcr')
        }),
        ('Market Information', {
            'fields': ('market_price', 'demand_season')
        }),
        ('Breeding', {
            'fields': ('breeding_season', 'gestation_days'),
            'classes': ('collapse',)
        }),
        ('Media', {
            'fields': ('image', 'description')
        }),
    )
    
    def image_preview(self, obj):
        if obj.image:
            return format_html('<img src="{}" style="max-height: 50px; max-width: 50px; border-radius: 5px;" />', obj.image.url)
        return "-"
    image_preview.short_description = "Image"
    
    def cycle_count(self, obj):
        return obj.production_cycles.count()
    cycle_count.short_description = "Total Cycles"


@admin.register(FishBatch)
class FishBatchAdmin(admin.ModelAdmin):
    list_display = ['batch_number', 'species_link', 'source', 'supplier', 'grade', 'generation', 'is_certified']
    list_filter = ['species', 'source', 'grade', 'is_certified']
    search_fields = ['batch_number', 'supplier']
    
    def species_link(self, obj):
        url = reverse('admin:fishery_fishspecies_change', args=[obj.species.pk])
        return format_html('<a href="{}">{}</a>', url, obj.species.name)
    species_link.short_description = "Species"
    
    fieldsets = (
        ('Batch Information', {
            'fields': ('batch_number', 'species', 'source', 'supplier', 'grade')
        }),
        ('Genetic Information', {
            'fields': ('generation', 'origin', 'disease_resistance')
        }),
        ('Certification', {
            'fields': ('is_certified', 'certification_number', 'certification_date')
        }),
    )


# ==================== PRODUCTION CYCLE ADMIN ====================

class FeedRecordInline(admin.TabularInline):
    model = FeedRecord
    extra = 0
    fields = ['date', 'feed_type', 'quantity_kg', 'cost']
    readonly_fields = ['cost']
    can_delete = True


class MortalityRecordInline(admin.TabularInline):
    model = MortalityRecord
    extra = 0
    fields = ['date', 'quantity_dead', 'reason', 'notes']
    can_delete = True


class HarvestInline(admin.TabularInline):
    model = Harvest
    extra = 0
    fields = ['harvest_date', 'quantity_kg', 'piece_count', 'avg_weight', 'grade']
    can_delete = True


class ExpenseInline(admin.TabularInline):
    model = Expense
    extra = 0
    fields = ['expense_date', 'expense_type', 'description', 'amount']
    can_delete = True


@admin.register(ProductionCycle)
class ProductionCycleAdmin(admin.ModelAdmin):
    list_display = ['cycle_id', 'pond_link', 'species_link', 'stocking_date', 'initial_quantity', 'status_badge', 'survival_rate_display', 'fcr_display', 'profit_indicator', 'action_buttons']
    list_filter = ['status', 'cycle_type', 'pond__farm', 'stocking_date']
    search_fields = ['cycle_id', 'pond__name', 'species__name', 'notes']
    readonly_fields = ['cycle_id', 'created_at', 'updated_at', 'cost_per_fingerling', 'total_harvest', 'total_mortality', 'current_population', 'survival_rate', 'total_feed', 'fcr', 'days_in_production', 'total_sales', 'total_investment', 'net_profit', 'roi_percentage', 'performance_summary']
    
    fieldsets = (
        ('Cycle Identification', {
            'fields': ('cycle_id', 'cycle_type', 'pond', 'species', 'batch')
        }),
        ('Stocking Details', {
            'fields': ('stocking_date', 'stocking_time', 'initial_quantity', 'initial_avg_weight', 'initial_avg_length', 'fingerling_cost', 'cost_per_fingerling')
        }),
        ('Expected Harvest', {
            'fields': ('expected_harvest_date', 'expected_harvest_weight', 'expected_yield_kg')
        }),
        ('Actual Harvest', {
            'fields': ('actual_harvest_date', 'actual_harvest_weight_avg', 'total_harvest')
        }),
        ('Status & Goals', {
            'fields': ('status', 'target_fcr', 'target_survival')
        }),
        ('Performance Metrics', {
            'fields': ('survival_rate', 'fcr', 'days_in_production', 'total_feed', 'total_mortality', 'current_population')
        }),
        ('Financial Summary', {
            'fields': ('total_sales', 'total_investment', 'net_profit', 'roi_percentage')
        }),
        ('Performance Dashboard', {
            'fields': ('performance_summary',),
            'classes': ('wide',)
        }),
        ('Notes', {
            'fields': ('notes',)
        }),
        ('Metadata', {
            'fields': ('created_by', 'supervised_by', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    inlines = [FeedRecordInline, MortalityRecordInline, HarvestInline, ExpenseInline]
    
    def pond_link(self, obj):
        url = reverse('admin:fishery_pond_change', args=[obj.pond.pk])
        return format_html('<a href="{}">{}</a>', url, obj.pond.name)
    pond_link.short_description = "Pond"
    
    def species_link(self, obj):
        url = reverse('admin:fishery_fishspecies_change', args=[obj.species.pk])
        return format_html('<a href="{}">{}</a>', url, obj.species.name)
    species_link.short_description = "Species"
    
    def status_badge(self, obj):
        colors = {
            'PLANNED': '#6c757d',
            'PREPARING': '#ffc107',
            'STOCKING': '#17a2b8',
            'RUNNING': '#28a745',
            'HARVESTING': '#fd7e14',
            'COMPLETED': '#0d6efd',
            'CANCELLED': '#dc3545',
            'FAILED': '#dc3545'
        }
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 10px; border-radius: 20px; font-size: 0.8rem;">{}</span>',
            colors.get(obj.status, '#6c757d'),
            obj.get_status_display()
        )
    status_badge.short_description = "Status"
    
    def survival_rate_display(self, obj):
        rate = obj.survival_rate
        if rate >= obj.target_survival:
            color = '#28a745'
        elif rate >= obj.target_survival * 0.8:
            color = '#ffc107'
        else:
            color = '#dc3545'
        return format_html('<span style="color: {}; font-weight: bold;">{}%</span>', color, rate)
    survival_rate_display.short_description = "Survival"
    
    def fcr_display(self, obj):
        fcr = obj.fcr
        if fcr <= obj.target_fcr:
            color = '#28a745'
        elif fcr <= obj.target_fcr * 1.2:
            color = '#ffc107'
        else:
            color = '#dc3545'
        return format_html('<span style="color: {}; font-weight: bold;">{}</span>', color, fcr)
    fcr_display.short_description = "FCR"
    
    def profit_indicator(self, obj):
        profit = obj.net_profit
        if profit > 0:
            return format_html('<span style="color: #28a745;">+৳{}</span>', profit)
        elif profit < 0:
            return format_html('<span style="color: #dc3545;">-৳{}</span>', abs(profit))
        return format_html('<span style="color: #6c757d;">৳0</span>')
    profit_indicator.short_description = "Net Profit"
    
    def performance_summary(self, obj):
        summary = obj.get_performance_summary()
        return format_html(
            '''
            <div style="background: #f8f9fa; padding: 15px; border-radius: 10px;">
                <div style="display: grid; grid-template-columns: repeat(4, 1fr); gap: 10px;">
                    <div style="text-align: center;">
                        <div style="font-size: 1.2rem; font-weight: bold; color: #28a745;">{}%</div>
                        <div style="font-size: 0.85rem;">Survival</div>
                    </div>
                    <div style="text-align: center;">
                        <div style="font-size: 1.2rem; font-weight: bold; color: #17a2b8;">{}</div>
                        <div style="font-size: 0.85rem;">FCR</div>
                    </div>
                    <div style="text-align: center;">
                        <div style="font-size: 1.2rem; font-weight: bold; color: #ffc107;">{} days</div>
                        <div style="font-size: 0.85rem;">Duration</div>
                    </div>
                    <div style="text-align: center;">
                        <div style="font-size: 1.2rem; font-weight: bold; color: #fd7e14;">{} g/day</div>
                        <div style="font-size: 0.85rem;">Growth</div>
                    </div>
                </div>
                <div style="margin-top: 15px; display: grid; grid-template-columns: repeat(3, 1fr); gap: 10px;">
                    <div style="text-align: center; background: #e9ecef; padding: 8px; border-radius: 5px;">
                        <div>Total Harvest</div>
                        <div style="font-weight: bold;">{} kg</div>
                    </div>
                    <div style="text-align: center; background: #e9ecef; padding: 8px; border-radius: 5px;">
                        <div>Total Sales</div>
                        <div style="font-weight: bold;">৳{}</div>
                    </div>
                    <div style="text-align: center; background: #e9ecef; padding: 8px; border-radius: 5px;">
                        <div>ROI</div>
                        <div style="font-weight: bold; color: {};">{}%</div>
                    </div>
                </div>
            </div>
            ''',
            summary['survival_rate'],
            summary['fcr'],
            summary['days_in_production'],
            summary['growth_per_day'],
            summary['total_harvest'],
            summary['total_sales'],
            '#28a745' if summary['roi'] > 0 else '#dc3545',
            summary['roi']
        )
    performance_summary.short_description = "Performance Summary"
    
    def action_buttons(self, obj):
        return format_html(
            '<div style="display: flex; gap: 5px;">'
            '<a class="btn btn-sm btn-info" href="{}" style="color: white; text-decoration: none; padding: 3px 8px; border-radius: 4px; background: #17a2b8;">👁️</a>'
            '<a class="btn btn-sm btn-warning" href="{}" style="color: white; text-decoration: none; padding: 3px 8px; border-radius: 4px; background: #ffc107;">✏️</a>'
            '</div>',
            reverse('admin:fishery_productioncycle_change', args=[obj.pk]),
            reverse('admin:fishery_productioncycle_change', args=[obj.pk])
        )
    action_buttons.short_description = "Actions"
    
    actions = ['mark_running', 'mark_completed', 'calculate_financials']
    
    def mark_running(self, request, queryset):
        updated = queryset.update(status='RUNNING')
        self.message_user(request, f'{updated} cycles marked as running.')
    mark_running.short_description = "Mark as Running"
    
    def mark_completed(self, request, queryset):
        updated = queryset.update(status='COMPLETED', actual_harvest_date=timezone.now().date())
        self.message_user(request, f'{updated} cycles marked as completed.')
    mark_completed.short_description = "Mark as Completed"
    
    def calculate_financials(self, request, queryset):
        count = 0
        for cycle in queryset:
            # Trigger recalculation
            cycle.save()
            count += 1
        self.message_user(request, f'Financials recalculated for {count} cycles.')
    calculate_financials.short_description = "Recalculate Financials"


# ==================== FEED MANAGEMENT ADMIN ====================

@admin.register(FeedType)
class FeedTypeAdmin(admin.ModelAdmin):
    list_display = ['name', 'brand', 'category', 'protein_percentage', 'pellet_size_mm', 'current_price', 'stock_indicator', 'needs_reorder_indicator']
    list_filter = ['category', 'brand']
    search_fields = ['name', 'brand']
    
    def stock_indicator(self, obj):
        if obj.current_stock <= obj.reorder_level:
            return format_html('<span style="color: #dc3545;">{} kg (Low)</span>', obj.current_stock)
        return format_html('<span style="color: #28a745;">{} kg</span>', obj.current_stock)
    stock_indicator.short_description = "Stock"
    
    def needs_reorder_indicator(self, obj):
        if obj.needs_reorder:
            return format_html('<span style="color: #dc3545; font-weight: bold;">⚠ Reorder</span>')
        return format_html('<span style="color: #6c757d;">-</span>')
    needs_reorder_indicator.short_description = "Reorder"


@admin.register(FeedPurchase)
class FeedPurchaseAdmin(admin.ModelAdmin):
    list_display = ['feed_type_link', 'purchase_date', 'quantity_kg', 'price_per_kg', 'total_cost_display', 'batch_number', 'expiry_status']
    list_filter = ['feed_type', 'purchase_date', 'supplier']
    search_fields = ['invoice_number', 'batch_number']
    date_hierarchy = 'purchase_date'
    readonly_fields = ['total_cost']
    
    def feed_type_link(self, obj):
        url = reverse('admin:fishery_feedtype_change', args=[obj.feed_type.pk])
        return format_html('<a href="{}">{}</a>', url, obj.feed_type.name)
    feed_type_link.short_description = "Feed Type"
    
    def total_cost_display(self, obj):
        return format_html('৳{}', obj.total_cost)
    total_cost_display.short_description = "Total Cost"
    
    def expiry_status(self, obj):
        if obj.expiry_date:
            days_left = (obj.expiry_date - timezone.now().date()).days
            if days_left < 0:
                return format_html('<span style="color: #dc3545;">Expired</span>')
            elif days_left < 30:
                return format_html('<span style="color: #ffc107;">{} days left</span>', days_left)
            return format_html('<span style="color: #28a745;">Valid</span>')
        return "-"
    expiry_status.short_description = "Status"


@admin.register(FeedRecord)
class FeedRecordAdmin(admin.ModelAdmin):
    list_display = ['cycle_link', 'date', 'feed_time', 'feed_type', 'quantity_kg', 'cost_display', 'consumption_rate_badge']
    list_filter = ['date', 'feed_type', 'feed_consumption_rate']
    search_fields = ['cycle__pond__name', 'notes']
    date_hierarchy = 'date'
    
    def cycle_link(self, obj):
        url = reverse('admin:fishery_productioncycle_change', args=[obj.cycle.pk])
        return format_html('<a href="{}">{}</a>', url, obj.cycle.pond.name)
    cycle_link.short_description = "Pond/Cycle"
    
    def cost_display(self, obj):
        return format_html('৳{}', obj.cost)
    cost_display.short_description = "Cost"
    
    def consumption_rate_badge(self, obj):
        colors = {
            'ALL': '#28a745',
            'MOST': '#17a2b8',
            'PARTIAL': '#ffc107',
            'LITTLE': '#dc3545'
        }
        return format_html(
            '<span style="background-color: {}; color: white; padding: 2px 8px; border-radius: 12px;">{}</span>',
            colors.get(obj.feed_consumption_rate, '#6c757d'),
            obj.get_feed_consumption_rate_display()
        )
    consumption_rate_badge.short_description = "Consumption"


# ==================== WATER QUALITY ADMIN ====================

@admin.register(WaterQuality)
class WaterQualityAdmin(admin.ModelAdmin):
    list_display = ['pond_link', 'reading_date', 'temperature', 'ph_level', 'dissolved_oxygen', 'alert_indicator', 'recorded_by']
    list_filter = ['pond', 'alert_generated', 'reading_date']
    search_fields = ['pond__name', 'notes']
    date_hierarchy = 'reading_date'
    
    def pond_link(self, obj):
        url = reverse('admin:fishery_pond_change', args=[obj.pond.pk])
        return format_html('<a href="{}">{}</a>', url, obj.pond.name)
    pond_link.short_description = "Pond"
    
    def alert_indicator(self, obj):
        if obj.alert_generated:
            return format_html('<span style="color: #dc3545; font-weight: bold;">⚠ Alert</span>')
        return format_html('<span style="color: #28a745;">✓ Good</span>')
    alert_indicator.short_description = "Status"


# ==================== HEALTH & DISEASE ADMIN ====================

@admin.register(DiseaseRecord)
class DiseaseRecordAdmin(admin.ModelAdmin):
    list_display = ['cycle_link', 'disease_name', 'disease_type', 'severity_badge', 'detection_date', 'estimated_affected', 'mortality_count', 'is_resolved']
    list_filter = ['disease_type', 'severity', 'is_resolved', 'detection_date']
    search_fields = ['disease_name', 'symptoms']
    date_hierarchy = 'detection_date'
    
    def cycle_link(self, obj):
        url = reverse('admin:fishery_productioncycle_change', args=[obj.cycle.pk])
        return format_html('<a href="{}">{}</a>', url, obj.cycle.pond.name)
    cycle_link.short_description = "Pond/Cycle"
    
    def severity_badge(self, obj):
        colors = {
            'LOW': '#28a745',
            'MEDIUM': '#ffc107',
            'HIGH': '#fd7e14',
            'CRITICAL': '#dc3545'
        }
        return format_html(
            '<span style="background-color: {}; color: white; padding: 2px 8px; border-radius: 12px;">{}</span>',
            colors.get(obj.severity, '#6c757d'),
            obj.get_severity_display()
        )
    severity_badge.short_description = "Severity"


@admin.register(TreatmentRecord)
class TreatmentRecordAdmin(admin.ModelAdmin):
    list_display = ['cycle_link', 'treatment_type', 'medication_name', 'application_date', 'next_application', 'cost_display', 'applied_by']
    list_filter = ['treatment_type', 'application_date']
    search_fields = ['medication_name', 'notes']
    
    def cycle_link(self, obj):
        url = reverse('admin:fishery_productioncycle_change', args=[obj.cycle.pk])
        return format_html('<a href="{}">{}</a>', url, obj.cycle.pond.name)
    cycle_link.short_description = "Pond/Cycle"
    
    def cost_display(self, obj):
        return format_html('৳{}', obj.cost)
    cost_display.short_description = "Cost"


@admin.register(MortalityRecord)
class MortalityRecordAdmin(admin.ModelAdmin):
    list_display = ['cycle_link', 'date', 'quantity_dead', 'reason', 'disease_link', 'recorded_by']
    list_filter = ['reason', 'date']
    search_fields = ['notes']
    date_hierarchy = 'date'
    
    def cycle_link(self, obj):
        url = reverse('admin:fishery_productioncycle_change', args=[obj.cycle.pk])
        return format_html('<a href="{}">{}</a>', url, obj.cycle.pond.name)
    cycle_link.short_description = "Pond/Cycle"
    
    def disease_link(self, obj):
        if obj.disease:
            url = reverse('admin:fishery_diseaserecord_change', args=[obj.disease.pk])
            return format_html('<a href="{}">{}</a>', url, obj.disease.disease_name)
        return "-"
    disease_link.short_description = "Related Disease"


# ==================== HARVEST ADMIN ====================

@admin.register(Harvest)
class HarvestAdmin(admin.ModelAdmin):
    list_display = ['cycle_link', 'harvest_date', 'quantity_kg', 'piece_count', 'avg_weight', 'grade_badge', 'total_sales_display', 'remaining_display']
    list_filter = ['harvest_date', 'grade', 'harvest_method']
    search_fields = ['cycle__pond__name', 'notes']
    date_hierarchy = 'harvest_date'
    
    def cycle_link(self, obj):
        url = reverse('admin:fishery_productioncycle_change', args=[obj.cycle.pk])
        return format_html('<a href="{}">{}</a>', url, obj.cycle.pond.name)
    cycle_link.short_description = "Pond/Cycle"
    
    def grade_badge(self, obj):
        colors = {
            'A': '#28a745',
            'B': '#17a2b8',
            'C': '#ffc107',
            'REJECT': '#dc3545'
        }
        return format_html(
            '<span style="background-color: {}; color: white; padding: 2px 8px; border-radius: 12px;">{}</span>',
            colors.get(obj.grade, '#6c757d'),
            obj.get_grade_display()
        )
    grade_badge.short_description = "Grade"
    
    def total_sales_display(self, obj):
        return format_html('৳{}', obj.total_sales)
    total_sales_display.short_description = "Total Sales"
    
    def remaining_display(self, obj):
        remaining = obj.remaining_quantity
        if remaining > 0:
            return format_html('<span style="color: #28a745;">{} kg</span>', remaining)
        return format_html('<span style="color: #6c757d;">Sold Out</span>')
    remaining_display.short_description = "Remaining"


# ==================== SALES ADMIN ====================

@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = ['customer_id', 'name', 'customer_type', 'phone', 'city', 'credit_info', 'is_active']
    list_filter = ['customer_type', 'city', 'is_active']
    search_fields = ['name', 'customer_id', 'phone', 'email']
    
    def credit_info(self, obj):
        if obj.credit_limit > 0:
            return format_html(
                '<span style="color: {};">৳{} / ৳{}</span>',
                '#dc3545' if obj.current_balance > obj.credit_limit * 0.8 else '#28a745',
                obj.current_balance, obj.credit_limit
            )
        return "-"
    credit_info.short_description = "Credit Balance"


@admin.register(FishSale)
class FishSaleAdmin(admin.ModelAdmin):
    list_display = ['sale_number', 'harvest_link', 'customer_name', 'quantity_kg', 'price_per_kg', 'total_amount_display', 'sale_date', 'payment_status_badge']
    list_filter = ['payment_status', 'sale_date', 'payment_method']
    search_fields = ['sale_number', 'customer_name', 'customer_phone']
    date_hierarchy = 'sale_date'
    readonly_fields = ['sale_number', 'total_amount', 'created_at']
    
    fieldsets = (
        ('Sale Information', {
            'fields': ('sale_number', 'harvest', 'customer', 'quantity_kg', 'price_per_kg', 'total_amount')
        }),
        ('Customer Details', {
            'fields': ('customer_name', 'customer_phone')
        }),
        ('Date & Delivery', {
            'fields': ('sale_date', 'delivery_date', 'vehicle_number', 'transport_cost')
        }),
        ('Payment Information', {
            'fields': ('payment_method', 'payment_status', 'payment_date', 'payment_reference')
        }),
        ('Additional Info', {
            'fields': ('notes', 'created_by', 'created_at'),
            'classes': ('collapse',)
        }),
    )
    
    def harvest_link(self, obj):
        if obj.harvest:
            url = reverse('admin:fishery_harvest_change', args=[obj.harvest.pk])
            return format_html('<a href="{}">{}</a>', url, obj.harvest.cycle.pond.name)
        return "-"
    harvest_link.short_description = "Pond/Harvest"
    
    def total_amount_display(self, obj):
        return format_html('<strong>৳{}</strong>', obj.total_amount)
    total_amount_display.short_description = "Total Amount"
    
    def payment_status_badge(self, obj):
        colors = {
            'PENDING': '#ffc107',
            'CONFIRMED': '#17a2b8',
            'DELIVERED': '#0d6efd',
            'PAID': '#28a745',
            'CANCELLED': '#dc3545'
        }
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 10px; border-radius: 20px;">{}</span>',
            colors.get(obj.payment_status, '#6c757d'),
            obj.get_payment_status_display()
        )
    payment_status_badge.short_description = "Payment Status"


# ==================== EXPENSE ADMIN ====================

@admin.register(Expense)
class ExpenseAdmin(admin.ModelAdmin):
    list_display = ['cycle_link', 'expense_date', 'expense_type_badge', 'description', 'amount_display', 'payment_method', 'receipt_number']
    list_filter = ['expense_type', 'payment_method', 'expense_date']
    search_fields = ['description', 'receipt_number', 'paid_to']
    date_hierarchy = 'expense_date'
    
    def cycle_link(self, obj):
        if obj.cycle:
            url = reverse('admin:fishery_productioncycle_change', args=[obj.cycle.pk])
            return format_html('<a href="{}">{}</a>', url, obj.cycle.pond.name)
        return "-"
    cycle_link.short_description = "Pond/Cycle"
    
    def expense_type_badge(self, obj):
        colors = {
            'FEED': '#28a745',
            'FINGERLING': '#17a2b8',
            'MEDICINE': '#dc3545',
            'LABOR': '#ffc107',
            'ELECTRICITY': '#fd7e14',
            'FUEL': '#6f42c1',
            'MAINTENANCE': '#6c757d',
            'TRANSPORT': '#20c997',
            'EQUIPMENT': '#0dcaf0',
            'TAX': '#d63384',
            'OTHER': '#6c757d'
        }
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 10px; border-radius: 20px;">{}</span>',
            colors.get(obj.expense_type, '#6c757d'),
            obj.get_expense_type_display()
        )
    expense_type_badge.short_description = "Expense Type"
    
    def amount_display(self, obj):
        return format_html('৳{}', obj.amount)
    amount_display.short_description = "Amount"


# ==================== BUDGET ADMIN ====================

@admin.register(Budget)
class BudgetAdmin(admin.ModelAdmin):
    list_display = ['cycle_link', 'planned_investment', 'planned_revenue_display', 'planned_profit_display', 'planned_roi_display', 'variance_indicator']
    
    def cycle_link(self, obj):
        url = reverse('admin:fishery_productioncycle_change', args=[obj.cycle.pk])
        return format_html('<a href="{}">{}</a>', url, obj.cycle.pond.name)
    cycle_link.short_description = "Pond/Cycle"
    
    def planned_investment(self, obj):
        total = obj.planned_fingerling_cost + obj.planned_feed_cost + obj.planned_medicine_cost + obj.planned_labor_cost + obj.planned_other_cost
        return format_html('৳{}', total)
    planned_investment.short_description = "Planned Investment"
    
    def planned_revenue_display(self, obj):
        return format_html('৳{}', obj.planned_revenue)
    planned_revenue_display.short_description = "Planned Revenue"
    
    def planned_profit_display(self, obj):
        color = '#28a745' if obj.planned_profit >= 0 else '#dc3545'
        return format_html('<span style="color: {};">৳{}</span>', color, obj.planned_profit)
    planned_profit_display.short_description = "Planned Profit"
    
    def planned_roi_display(self, obj):
        color = '#28a745' if obj.planned_roi >= 0 else '#dc3545'
        return format_html('<span style="color: {};">{}%</span>', color, obj.planned_roi)
    planned_roi_display.short_description = "Planned ROI"
    
    def variance_indicator(self, obj):
        if obj.cycle.status == 'COMPLETED':
            actual_profit = obj.cycle.net_profit
            variance = ((actual_profit - obj.planned_profit) / obj.planned_profit * 100) if obj.planned_profit != 0 else 0
            if variance > 10:
                return format_html('<span style="color: #28a745;">▲ +{}%</span>', round(variance, 1))
            elif variance < -10:
                return format_html('<span style="color: #dc3545;">▼ {}%</span>', round(variance, 1))
            else:
                return format_html('<span style="color: #ffc107;">● {}%</span>', round(variance, 1))
        return "-"
    variance_indicator.short_description = "Variance"


# ==================== FINANCIAL REPORT ADMIN ====================

@admin.register(FisheryFinancialReport)
class FisheryFinancialReportAdmin(admin.ModelAdmin):
    list_display = ['year', 'total_investment_display', 'total_sales_revenue_display', 'net_profit_display', 'roi_display', 'total_harvest_kg', 'avg_fcr', 'generated_at']
    list_filter = ['year']
    
    fieldsets = (
        ('Report Year', {
            'fields': ('year', 'generated_by', 'generated_at')
        }),
        ('Investment Breakdown', {
            'fields': ('total_fingerling_cost', 'total_feed_cost', 'total_medicine_cost', 'total_labor_cost', 'total_electricity_cost', 'total_transport_cost', 'total_other_expenses', 'total_investment')
        }),
        ('Revenue & Profit', {
            'fields': ('total_sales_revenue', 'total_harvest_kg', 'avg_selling_price', 'net_profit', 'roi_percentage')
        }),
        ('Production Metrics', {
            'fields': ('total_cycles_completed', 'avg_cycle_days', 'avg_survival_rate', 'avg_fcr', 'total_pond_area', 'productivity_per_acre')
        }),
    )
    
    readonly_fields = ['total_investment', 'net_profit', 'roi_percentage']
    
    def total_investment_display(self, obj):
        return format_html('৳{}', obj.total_investment)
    total_investment_display.short_description = "Total Investment"
    
    def total_sales_revenue_display(self, obj):
        return format_html('৳{}', obj.total_sales_revenue)
    total_sales_revenue_display.short_description = "Total Revenue"
    
    def net_profit_display(self, obj):
        color = '#28a745' if obj.net_profit >= 0 else '#dc3545'
        return format_html('<span style="color: {}; font-weight: bold;">৳{}</span>', color, obj.net_profit)
    net_profit_display.short_description = "Net Profit"
    
    def roi_display(self, obj):
        color = '#28a745' if obj.roi_percentage >= 0 else '#dc3545'
        return format_html('<span style="color: {};">{}%</span>', color, obj.roi_percentage)
    roi_display.short_description = "ROI"
    
    actions = ['generate_report']
    
    def generate_report(self, request, queryset):
        for report in queryset:
            report.calculate_totals()
        self.message_user(request, f'Reports recalculated for {queryset.count()} years.')
    generate_report.short_description = "Recalculate Report Totals"


# ==================== CUSTOM ADMIN SITE CONFIGURATION ====================

# Customize Admin Site
admin.site.site_header = 'Sheikh Agro - Fishery Management System'
admin.site.site_title = 'Sheikh Agro Fishery'
admin.site.index_title = 'Fishery Farm Administration Dashboard'
admin.site.site_url = '/fishery/'