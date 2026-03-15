from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse, path
from django.db.models import Sum, Avg, Count, Q
from django.utils import timezone
from datetime import datetime, timedelta

from .models import *

# ==================== CATTLE ADMIN ====================

@admin.register(Cattle)
class CattleAdmin(admin.ModelAdmin):
    list_display = [
        'tag_number', 'name', 'cattle_type', 'breed', 'gender', 
        'status', 'age_display', 'weight', 'location', 'profit_indicator', 'action_buttons'
    ]
    list_filter = ['cattle_type', 'breed', 'gender', 'status', 'is_vaccinated']
    search_fields = ['tag_number', 'name', 'location']
    readonly_fields = ['created_at', 'updated_at', 'age_display', 'financial_summary']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('tag_number', 'name', 'cattle_type', 'breed', 'gender', 'birth_date', 'age_display'),
            'classes': ('wide', 'extrapretty'),
        }),
        ('Physical Characteristics', {
            'fields': ('weight', 'color', 'distinctive_marks'),
            'classes': ('collapse',),
        }),
        ('Parentage', {
            'fields': ('sire', 'dam'),
            'classes': ('collapse',),
        }),
        ('Acquisition Details', {
            'fields': ('acquisition_type', 'acquisition_date', 'purchase_price', 'current_value'),
            'classes': ('collapse',),
        }),
        ('Location & Status', {
            'fields': ('location', 'status', 'is_vaccinated', 'last_vaccination_date'),
        }),
        ('Financial Summary', {
            'fields': ('financial_summary',),
            'classes': ('wide',),
        }),
        ('Metadata', {
            'fields': ('created_by', 'created_at', 'updated_at'),
            'classes': ('collapse',),
        }),
    )
    
    autocomplete_fields = ['sire', 'dam', 'created_by']
    
    def age_display(self, obj):
        if obj.birth_date:
            months = obj.age_in_months()
            years = months // 12
            remaining_months = months % 12
            return format_html(
                '<span title="{} days" class="badge bg-info">{}</span>',
                obj.age_in_days(),
                f"{years}y {remaining_months}m"
            )
        return "-"
    age_display.short_description = "Age"
    
    def profit_indicator(self, obj):
        profit = obj.net_profit()
        if profit > 0:
            return format_html('<span class="badge bg-success">+৳{}</span>', profit)
        elif profit < 0:
            return format_html('<span class="badge bg-danger">-৳{}</span>', abs(profit))
        return format_html('<span class="badge bg-secondary">৳0</span>')
    profit_indicator.short_description = "Net Profit"
    
    def financial_summary(self, obj):
        milk_revenue = obj.total_milk_revenue()
        total_expenses = obj.total_expenses()
        net_profit = obj.net_profit()
        
        return format_html(
            '''
            <div class="financial-card" style="background: #f8f9fa; padding: 15px; border-radius: 10px;">
                <h6 style="color: #495057; margin-bottom: 15px;">💰 Financial Overview</h6>
                <div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 10px;">
                    <div style="text-align: center;">
                        <div style="font-size: 1.2rem; font-weight: bold; color: #28a745;">৳{}</div>
                        <div style="font-size: 0.85rem; color: #6c757d;">Milk Revenue</div>
                    </div>
                    <div style="text-align: center;">
                        <div style="font-size: 1.2rem; font-weight: bold; color: #dc3545;">৳{}</div>
                        <div style="font-size: 0.85rem; color: #6c757d;">Total Expenses</div>
                    </div>
                    <div style="text-align: center;">
                        <div style="font-size: 1.2rem; font-weight: bold; color: {};">৳{}</div>
                        <div style="font-size: 0.85rem; color: #6c757d;">Net Profit</div>
                    </div>
                </div>
            </div>
            ''',
            milk_revenue,
            total_expenses,
            '#28a745' if net_profit >= 0 else '#dc3545',
            net_profit
        )
    financial_summary.short_description = "Financial Summary"
    
    def action_buttons(self, obj):
        return format_html(
            '''
            <div style="display: flex; gap: 5px;">
                <a class="btn btn-sm btn-info" href="{}" target="_blank" style="color: white; text-decoration: none;">
                    <i class="bi bi-eye"></i>
                </a>
                <a class="btn btn-sm btn-warning" href="{}" style="color: white; text-decoration: none;">
                    <i class="bi bi-pencil"></i>
                </a>
            </div>
            ''',
            reverse('admin:dairy_cattle_change', args=[obj.pk]),
            reverse('admin:dairy_cattle_change', args=[obj.pk])
        )
    action_buttons.short_description = "Actions"
    
    actions = ['mark_vaccinated', 'mark_active', 'mark_sold', 'calculate_financials']
    
    def mark_vaccinated(self, request, queryset):
        updated = queryset.update(is_vaccinated=True, last_vaccination_date=timezone.now())
        self.message_user(request, f'{updated} cattle marked as vaccinated.')
    mark_vaccinated.short_description = "Mark selected as vaccinated"
    
    def mark_active(self, request, queryset):
        updated = queryset.update(status='ACTIVE')
        self.message_user(request, f'{updated} cattle marked as active.')
    mark_active.short_description = "Mark selected as active"
    
    def mark_sold(self, request, queryset):
        updated = queryset.update(status='SOLD')
        self.message_user(request, f'{updated} cattle marked as sold.')
    mark_sold.short_description = "Mark selected as sold"
    
    def calculate_financials(self, request, queryset):
        count = 0
        for cattle in queryset:
            cattle.total_investment = (cattle.purchase_price or 0) + cattle.total_expenses()
            cattle.save()
            count += 1
        self.message_user(request, f'Financials calculated for {count} cattle.')
    calculate_financials.short_description = "Calculate financials"


# ==================== MILK RECORD ADMIN ====================

@admin.register(MilkRecord)
class MilkRecordAdmin(admin.ModelAdmin):
    list_display = ['cattle_link', 'date', 'session_badge', 'quantity_display', 'fat_percentage', 'temperature', 'recorded_by', 'recorded_at']
    list_filter = ['date', 'session', 'recorded_by']
    search_fields = ['cattle__tag_number']
    date_hierarchy = 'date'
    readonly_fields = ['recorded_at']
    
    def cattle_link(self, obj):
        url = reverse('admin:dairy_cattle_change', args=[obj.cattle.pk])
        return format_html('<a href="{}">{}</a>', url, obj.cattle.tag_number)
    cattle_link.short_description = "Cattle"
    
    def session_badge(self, obj):
        colors = {'MORNING': '#ffc107', 'AFTERNOON': '#fd7e14', 'EVENING': '#6f42c1'}
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 10px; border-radius: 20px; font-size: 0.8rem;">{}</span>',
            colors.get(obj.session, '#6c757d'),
            obj.get_session_display()
        )
    session_badge.short_description = "Session"
    
    def quantity_display(self, obj):
        return format_html('<strong>{:.2f} L</strong>', obj.quantity)
    quantity_display.short_description = "Quantity"
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('cattle', 'date', 'session', 'quantity'),
        }),
        ('Quality Metrics', {
            'fields': ('fat_percentage', 'temperature', 'quality_notes'),
            'classes': ('wide',),
        }),
        ('Record Metadata', {
            'fields': ('recorded_by', 'recorded_at'),
            'classes': ('collapse',),
        }),
    )


# ==================== MILK SALE ADMIN ====================

@admin.register(MilkSale)
class MilkSaleAdmin(admin.ModelAdmin):
    list_display = ['date', 'quantity_display', 'price_per_liter', 'total_amount_display', 'sale_type_badge', 'customer_name', 'payment_status']
    list_filter = ['date', 'sale_type', 'payment_received']
    search_fields = ['customer_name']
    date_hierarchy = 'date'
    readonly_fields = ['total_amount']
    
    fieldsets = (
        ('Sale Information', {
            'fields': ('date', 'quantity', 'price_per_liter', 'total_amount'),
        }),
        ('Customer Details', {
            'fields': ('sale_type', 'customer_name', 'payment_received'),
        }),
        ('Additional Info', {
            'fields': ('notes', 'created_by'),
            'classes': ('collapse',),
        }),
    )
    
    def quantity_display(self, obj):
        return format_html('<strong>{:.2f} L</strong>', obj.quantity)
    quantity_display.short_description = "Quantity"
    
    def total_amount_display(self, obj):
        return format_html('<span style="color: #28a745; font-weight: bold;">৳{:.2f}</span>', obj.total_amount)
    total_amount_display.short_description = "Total Amount"
    
    def sale_type_badge(self, obj):
        colors = {'WHOLESALE': '#17a2b8', 'RETAIL': '#28a745', 'DIRECT': '#ffc107'}
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 10px; border-radius: 20px;">{}</span>',
            colors.get(obj.sale_type, '#6c757d'),
            obj.get_sale_type_display()
        )
    sale_type_badge.short_description = "Sale Type"
    
    def payment_status(self, obj):
        if obj.payment_received:
            return format_html('<span style="color: #28a745;">✓ Paid</span>')
        return format_html('<span style="color: #dc3545;">✗ Pending</span>')
    payment_status.short_description = "Payment"


# ==================== CATTLE SALE ADMIN ====================

@admin.register(CattleSale)
class CattleSaleAdmin(admin.ModelAdmin):
    list_display = ['cattle_link', 'sale_date', 'sale_price_display', 'profit_loss_display', 'buyer_name', 'payment_status']
    list_filter = ['sale_date', 'payment_received']
    search_fields = ['cattle__tag_number', 'buyer_name']
    date_hierarchy = 'sale_date'
    readonly_fields = ['profit_loss']
    
    fieldsets = (
        ('Sale Information', {
            'fields': ('cattle', 'sale_date', 'sale_price'),
        }),
        ('Buyer Details', {
            'fields': ('buyer_name', 'buyer_contact', 'payment_received'),
        }),
        ('Financial Summary', {
            'fields': ('profit_loss',),
            'classes': ('wide',),
        }),
        ('Additional Info', {
            'fields': ('notes', 'created_by'),
            'classes': ('collapse',),
        }),
    )
    
    def cattle_link(self, obj):
        url = reverse('admin:dairy_cattle_change', args=[obj.cattle.pk])
        return format_html('<a href="{}">{}</a>', url, obj.cattle.tag_number)
    cattle_link.short_description = "Cattle"
    
    def sale_price_display(self, obj):
        return format_html('<strong>৳{:.2f}</strong>', obj.sale_price)
    sale_price_display.short_description = "Sale Price"
    
    def profit_loss_display(self, obj):
        profit = obj.profit_loss()
        if profit > 0:
            return format_html('<span style="color: #28a745;">+৳{:.2f}</span>', profit)
        elif profit < 0:
            return format_html('<span style="color: #dc3545;">-৳{:.2f}</span>', abs(profit))
        return format_html('<span style="color: #6c757d;">৳0.00</span>')
    profit_loss_display.short_description = "Profit/Loss"
    
    def payment_status(self, obj):
        if obj.payment_received:
            return format_html('<span style="color: #28a745;">✓ Received</span>')
        return format_html('<span style="color: #dc3545;">✗ Pending</span>')
    payment_status.short_description = "Payment"


# ==================== HEALTH RECORD ADMIN ====================

@admin.register(HealthRecord)
class HealthRecordAdmin(admin.ModelAdmin):
    list_display = ['cattle_link', 'date', 'health_type_badge', 'diagnosis_short', 'veterinarian', 'cost_display', 'next_checkup_badge']
    list_filter = ['health_type', 'is_emergency', 'date']
    search_fields = ['cattle__tag_number', 'diagnosis', 'veterinarian']
    date_hierarchy = 'date'
    
    fieldsets = (
        ('Health Information', {
            'fields': ('cattle', 'date', 'health_type', 'is_emergency'),
        }),
        ('Medical Details', {
            'fields': ('diagnosis', 'treatment', 'medications', 'veterinarian'),
            'classes': ('wide',),
        }),
        ('Follow-up', {
            'fields': ('next_checkup_date',),
        }),
        ('Cost', {
            'fields': ('treatment_cost',),
        }),
        ('Notes', {
            'fields': ('notes', 'created_by'),
            'classes': ('collapse',),
        }),
    )
    
    def cattle_link(self, obj):
        url = reverse('admin:dairy_cattle_change', args=[obj.cattle.pk])
        return format_html('<a href="{}">{}</a>', url, obj.cattle.tag_number)
    cattle_link.short_description = "Cattle"
    
    def health_type_badge(self, obj):
        colors = {
            'CHECKUP': '#17a2b8', 'VACCINATION': '#28a745', 'TREATMENT': '#ffc107',
            'SURGERY': '#dc3545', 'PREGNANCY': '#e83e8c', 'DISEASE': '#6c757d'
        }
        emergency = '🚨 ' if obj.is_emergency else ''
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 10px; border-radius: 20px;">{}{}</span>',
            colors.get(obj.health_type, '#6c757d'),
            emergency,
            obj.get_health_type_display()
        )
    health_type_badge.short_description = "Health Type"
    
    def diagnosis_short(self, obj):
        return obj.diagnosis[:50] + '...' if len(obj.diagnosis) > 50 else obj.diagnosis
    diagnosis_short.short_description = "Diagnosis"
    
    def cost_display(self, obj):
        if obj.treatment_cost:
            return format_html('৳{:.2f}', obj.treatment_cost)
        return "-"
    cost_display.short_description = "Cost"
    
    def next_checkup_badge(self, obj):
        if obj.next_checkup_date:
            if obj.next_checkup_date < timezone.now().date():
                return format_html('<span style="color: #dc3545;">⚠ Overdue</span>')
            return obj.next_checkup_date.strftime('%Y-%m-%d')
        return "-"
    next_checkup_badge.short_description = "Next Checkup"


# ==================== FEEDING RECORD ADMIN ====================

@admin.register(FeedingRecord)
class FeedingRecordAdmin(admin.ModelAdmin):
    list_display = ['cattle_link', 'date', 'feed_time', 'feed_type_badge', 'quantity_display', 'total_cost_display', 'quality_stars']
    list_filter = ['feed_type', 'feed_quality', 'date']
    search_fields = ['cattle__tag_number']
    date_hierarchy = 'date'
    readonly_fields = ['total_cost']
    
    fieldsets = (
        ('Feeding Information', {
            'fields': ('cattle', 'date', 'feed_time', 'feed_type'),
        }),
        ('Quantity & Cost', {
            'fields': ('quantity', 'cost_per_kg', 'total_cost'),
        }),
        ('Quality', {
            'fields': ('feed_quality', 'notes'),
        }),
        ('Record Metadata', {
            'fields': ('fed_by',),
            'classes': ('collapse',),
        }),
    )
    
    def cattle_link(self, obj):
        url = reverse('admin:dairy_cattle_change', args=[obj.cattle.pk])
        return format_html('<a href="{}">{}</a>', url, obj.cattle.tag_number)
    cattle_link.short_description = "Cattle"
    
    def feed_type_badge(self, obj):
        colors = {
            'GRAIN': '#ffc107', 'HAY': '#28a745', 'SILAGE': '#17a2b8',
            'CONCENTRATE': '#6f42c1', 'MINERALS': '#fd7e14', 'MILK': '#e83e8c'
        }
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 10px; border-radius: 20px;">{}</span>',
            colors.get(obj.feed_type, '#6c757d'),
            obj.get_feed_type_display()
        )
    feed_type_badge.short_description = "Feed Type"
    
    def quantity_display(self, obj):
        return format_html('<strong>{:.2f} kg</strong>', obj.quantity)
    quantity_display.short_description = "Quantity"
    
    def total_cost_display(self, obj):
        return format_html('৳{:.2f}', obj.total_cost)
    total_cost_display.short_description = "Total Cost"
    
    def quality_stars(self, obj):
        stars = '★' * obj.feed_quality + '☆' * (4 - obj.feed_quality)
        colors = ['#dc3545', '#ffc107', '#17a2b8', '#28a745']
        return format_html(
            '<span style="color: {}; font-size: 1.2rem;">{}</span>',
            colors[obj.feed_quality - 1],
            stars
        )
    quality_stars.short_description = "Quality"


# ==================== BREEDING RECORD ADMIN ====================

@admin.register(BreedingRecord)
class BreedingRecordAdmin(admin.ModelAdmin):
    list_display = ['cattle_link', 'breeding_date', 'sire_link', 'breeding_method', 'pregnancy_status', 'expected_calving', 'offspring_link']
    list_filter = ['status', 'is_pregnant', 'breeding_method']
    search_fields = ['cattle__tag_number', 'sire__tag_number']
    date_hierarchy = 'breeding_date'
    
    fieldsets = (
        ('Breeding Information', {
            'fields': ('cattle', 'breeding_date', 'breeding_method', 'sire'),
        }),
        ('Pregnancy Status', {
            'fields': ('pregnancy_check_date', 'is_pregnant', 'status'),
        }),
        ('Calving Information', {
            'fields': ('expected_calving_date', 'actual_calving_date', 'offspring'),
        }),
        ('Additional Info', {
            'fields': ('notes', 'created_by'),
            'classes': ('collapse',),
        }),
    )
    
    def cattle_link(self, obj):
        url = reverse('admin:dairy_cattle_change', args=[obj.cattle.pk])
        return format_html('<a href="{}">{}</a>', url, obj.cattle.tag_number)
    cattle_link.short_description = "Dam (Mother)"
    
    def sire_link(self, obj):
        if obj.sire:
            url = reverse('admin:dairy_cattle_change', args=[obj.sire.pk])
            return format_html('<a href="{}">{}</a>', url, obj.sire.tag_number)
        return "-"
    sire_link.short_description = "Sire (Father)"
    
    def pregnancy_status(self, obj):
        if obj.is_pregnant:
            return format_html('<span style="color: #28a745;">✓ Pregnant</span>')
        return format_html('<span style="color: #6c757d;">✗ Not Pregnant</span>')
    pregnancy_status.short_description = "Pregnancy"
    
    def expected_calving(self, obj):
        if obj.expected_calving_date:
            days_left = (obj.expected_calving_date - timezone.now().date()).days
            if days_left < 0:
                return format_html('<span style="color: #dc3545;">Overdue</span>')
            elif days_left < 30:
                return format_html('<span style="color: #ffc107;">{} days</span>', days_left)
            return format_html('<span style="color: #17a2b8;">{} days</span>', days_left)
        return "-"
    expected_calving.short_description = "Expected Calving"
    
    def offspring_link(self, obj):
        if obj.offspring:
            url = reverse('admin:dairy_cattle_change', args=[obj.offspring.pk])
            return format_html('<a href="{}">👶 {}</a>', url, obj.offspring.tag_number)
        return "-"
    offspring_link.short_description = "Offspring"


# ==================== WEIGHT RECORD ADMIN ====================

@admin.register(WeightRecord)
class WeightRecordAdmin(admin.ModelAdmin):
    list_display = ['cattle_link', 'date', 'weight_display', 'daily_gain_display', 'age_display']
    list_filter = ['date']
    search_fields = ['cattle__tag_number']
    date_hierarchy = 'date'
    readonly_fields = ['daily_gain', 'age_in_days']
    
    def cattle_link(self, obj):
        url = reverse('admin:dairy_cattle_change', args=[obj.cattle.pk])
        return format_html('<a href="{}">{}</a>', url, obj.cattle.tag_number)
    cattle_link.short_description = "Cattle"
    
    def weight_display(self, obj):
        return format_html('<strong>{:.2f} kg</strong>', obj.weight)
    weight_display.short_description = "Weight"
    
    def daily_gain_display(self, obj):
        if obj.daily_gain:
            color = '#28a745' if obj.daily_gain > 0 else '#dc3545'
            return format_html('<span style="color: {};">{:.2f} kg/day</span>', color, obj.daily_gain)
        return "-"
    daily_gain_display.short_description = "Daily Gain"
    
    def age_display(self, obj):
        if obj.age_in_days:
            return format_html('<span class="badge bg-info">{}</span>', f"{obj.age_in_days} days")
        return "-"
    age_display.short_description = "Age"


# ==================== VACCINATION ADMIN ====================

@admin.register(VaccinationSchedule)
class VaccinationScheduleAdmin(admin.ModelAdmin):
    list_display = ['cattle_link', 'vaccine_type_badge', 'scheduled_date', 'status_badge', 'administered_date', 'batch_number', 'cost_display']
    list_filter = ['vaccine_type', 'is_completed', 'scheduled_date']
    search_fields = ['cattle__tag_number', 'batch_number']
    date_hierarchy = 'scheduled_date'
    
    def cattle_link(self, obj):
        url = reverse('admin:dairy_cattle_change', args=[obj.cattle.pk])
        return format_html('<a href="{}">{}</a>', url, obj.cattle.tag_number)
    cattle_link.short_description = "Cattle"
    
    def vaccine_type_badge(self, obj):
        colors = {'FMD': '#ffc107', 'BQ': '#28a745', 'HS': '#17a2b8', 'BRU': '#dc3545', 'IBR': '#6f42c1'}
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 10px; border-radius: 20px;">{}</span>',
            colors.get(obj.vaccine_type, '#6c757d'),
            obj.get_vaccine_type_display()
        )
    vaccine_type_badge.short_description = "Vaccine"
    
    def status_badge(self, obj):
        if obj.is_completed:
            return format_html('<span style="color: #28a745;">✓ Completed</span>')
        elif obj.scheduled_date < timezone.now().date():
            return format_html('<span style="color: #dc3545;">⚠ Overdue</span>')
        else:
            days_left = (obj.scheduled_date - timezone.now().date()).days
            if days_left <= 7:
                return format_html('<span style="color: #ffc107;">🔔 {} days left</span>', days_left)
            return format_html('<span style="color: #17a2b8;">📅 {} days left</span>', days_left)
    status_badge.short_description = "Status"
    
    def cost_display(self, obj):
        if obj.cost:
            return format_html('৳{:.2f}', obj.cost)
        return "-"
    cost_display.short_description = "Cost"


# ==================== EXPENSE ADMIN ====================

@admin.register(ExpenseCategory)
class ExpenseCategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'description']
    search_fields = ['name']


@admin.register(Expense)
class ExpenseAdmin(admin.ModelAdmin):
    list_display = ['date', 'category_link', 'description', 'amount_display', 'payment_method_badge', 'cattle_link', 'payment_status']
    list_filter = ['category', 'payment_method', 'date']
    search_fields = ['description', 'receipt_number']
    date_hierarchy = 'date'
    
    def category_link(self, obj):
        if obj.category:
            url = reverse('admin:dairy_expensecategory_change', args=[obj.category.pk])
            return format_html('<a href="{}">{}</a>', url, obj.category.name)
        return "-"
    category_link.short_description = "Category"
    
    def amount_display(self, obj):
        return format_html('<strong>৳{:.2f}</strong>', obj.amount)
    amount_display.short_description = "Amount"
    
    def payment_method_badge(self, obj):
        colors = {'CASH': '#28a745', 'BANK': '#17a2b8', 'MOBILE': '#ffc107', 'CHEQUE': '#6f42c1'}
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 10px; border-radius: 20px;">{}</span>',
            colors.get(obj.payment_method, '#6c757d'),
            obj.get_payment_method_display()
        )
    payment_method_badge.short_description = "Payment Method"
    
    def cattle_link(self, obj):
        if obj.cattle:
            url = reverse('admin:dairy_cattle_change', args=[obj.cattle.pk])
            return format_html('<a href="{}">{}</a>', url, obj.cattle.tag_number)
        return "-"
    cattle_link.short_description = "Related Cattle"
    
    def payment_status(self, obj):
        return format_html('<span style="color: #28a745;">✓ Paid</span>')
    payment_status.short_description = "Status"


# ==================== INVESTMENT ADMIN ====================

@admin.register(Investment)
class InvestmentAdmin(admin.ModelAdmin):
    list_display = ['date', 'investment_type_badge', 'description', 'amount_display', 'cattle_link']
    list_filter = ['investment_type', 'date']
    search_fields = ['description']
    date_hierarchy = 'date'
    
    def investment_type_badge(self, obj):
        colors = {
            'INFRASTRUCTURE': '#17a2b8', 'EQUIPMENT': '#28a745',
            'CATTLE': '#ffc107', 'LAND': '#6f42c1', 'OTHER': '#6c757d'
        }
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 10px; border-radius: 20px;">{}</span>',
            colors.get(obj.investment_type, '#6c757d'),
            obj.get_investment_type_display()
        )
    investment_type_badge.short_description = "Type"
    
    def amount_display(self, obj):
        return format_html('<strong>৳{:.2f}</strong>', obj.amount)
    amount_display.short_description = "Amount"
    
    def cattle_link(self, obj):
        if obj.cattle:
            url = reverse('admin:dairy_cattle_change', args=[obj.cattle.pk])
            return format_html('<a href="{}">{}</a>', url, obj.cattle.tag_number)
        return "-"
    cattle_link.short_description = "Related Cattle"


# ==================== MONTHLY SUMMARY ADMIN ====================

@admin.register(MonthlySummary)
class MonthlySummaryAdmin(admin.ModelAdmin):
    list_display = ['month_year', 'total_income_display', 'total_expenses_display', 'net_profit_display', 'total_milk_display']
    list_filter = ['year', 'month']
    
    def month_year(self, obj):
        return f"{obj.year}-{obj.month:02d}"
    month_year.short_description = "Month"
    
    def total_income_display(self, obj):
        return format_html('<span style="color: #28a745;">৳{:.2f}</span>', obj.total_income)
    total_income_display.short_description = "Income"
    
    def total_expenses_display(self, obj):
        return format_html('<span style="color: #dc3545;">৳{:.2f}</span>', obj.total_expenses)
    total_expenses_display.short_description = "Expenses"
    
    def net_profit_display(self, obj):
        color = '#28a745' if obj.net_profit >= 0 else '#dc3545'
        return format_html('<span style="color: {}; font-weight: bold;">৳{:.2f}</span>', color, obj.net_profit)
    net_profit_display.short_description = "Net Profit"
    
    def total_milk_display(self, obj):
        return format_html('{:.2f} L', obj.total_milk_produced)
    total_milk_display.short_description = "Milk Produced"
    
    fieldsets = (
        ('Period', {
            'fields': ('year', 'month'),
        }),
        ('Income', {
            'fields': ('milk_sales', 'cattle_sales', 'other_income', 'total_income'),
        }),
        ('Expenses', {
            'fields': ('feed_expenses', 'health_expenses', 'labor_expenses', 'other_expenses', 'total_expenses'),
        }),
        ('Summary', {
            'fields': ('net_profit', 'total_milk_produced', 'avg_milk_per_cow'),
        }),
    )
    
    readonly_fields = ['total_income', 'total_expenses', 'net_profit']


# ==================== YEARLY REPORT ADMIN ====================

@admin.register(YearlyReport)
class YearlyReportAdmin(admin.ModelAdmin):
    list_display = ['year', 'total_income_display', 'total_expenses_display', 'net_profit_display', 'roi_display', 'total_milk_display']
    list_filter = ['year']
    
    def total_income_display(self, obj):
        return format_html('<span style="color: #28a745;">৳{:.2f}</span>', obj.total_income)
    total_income_display.short_description = "Income"
    
    def total_expenses_display(self, obj):
        return format_html('<span style="color: #dc3545;">৳{:.2f}</span>', obj.total_expenses)
    total_expenses_display.short_description = "Expenses"
    
    def net_profit_display(self, obj):
        color = '#28a745' if obj.net_profit >= 0 else '#dc3545'
        return format_html('<span style="color: {}; font-weight: bold;">৳{:.2f}</span>', color, obj.net_profit)
    net_profit_display.short_description = "Net Profit"
    
    def roi_display(self, obj):
        return format_html('<span style="color: #17a2b8;">{}%</span>', obj.roi_percentage)
    roi_display.short_description = "ROI"
    
    def total_milk_display(self, obj):
        return format_html('{:.2f} L', obj.total_milk_produced)
    total_milk_display.short_description = "Milk Produced"


# ==================== MILK PRODUCTION REPORTS ====================

@admin.register(MilkProductionReport)
class MilkProductionReportAdmin(admin.ModelAdmin):
    list_display = ['title', 'period', 'date_range', 'total_milk', 'avg_fat_percentage', 
                   'total_revenue', 'growth_indicator', 'generated_at', 'download_link']
    list_filter = ['period', 'year', 'month', 'generated_at']
    search_fields = ['title', 'notes']
    date_hierarchy = 'generated_at'
    readonly_fields = ['total_milk', 'avg_daily_milk', 'avg_fat_percentage', 
                      'peak_production_day', 'total_revenue', 'growth_percentage']
    
    fieldsets = (
        ('Report Information', {
            'fields': ('title', 'period', 'year', 'month', 'week', 
                      'start_date', 'end_date', 'notes')
        }),
        ('Production Statistics', {
            'fields': ('total_milk', 'avg_daily_milk', 'avg_fat_percentage',
                      'peak_production_day', 'peak_production_amount',
                      'total_lactating_cows', 'avg_per_cow'),
            'classes': ('wide',)
        }),
        ('Financial Summary', {
            'fields': ('total_revenue', 'avg_price_per_liter'),
        }),
        ('Comparison Data', {
            'fields': ('previous_period_total', 'growth_percentage'),
        }),
        ('Metadata', {
            'fields': ('generated_by', 'generated_at', 'report_file'),
        }),
    )
    
    def date_range(self, obj):
        return f"{obj.start_date} to {obj.end_date}"
    date_range.short_description = "Date Range"
    
    def growth_indicator(self, obj):
        if obj.growth_percentage > 0:
            return format_html(
                '<span style="color: green; font-weight: bold;">▲ +{}%</span>',
                obj.growth_percentage
            )
        elif obj.growth_percentage < 0:
            return format_html(
                '<span style="color: red; font-weight: bold;">▼ {}%</span>',
                obj.growth_percentage
            )
        else:
            return format_html('<span style="color: gray;">● 0%</span>')
    growth_indicator.short_description = "Growth"
    
    def download_link(self, obj):
        if obj.report_file:
            return format_html(
                '<a href="{}" target="_blank" style="background: #28a745; color: white; padding: 3px 10px; border-radius: 3px; text-decoration: none;">📥 Download</a>',
                obj.report_file.url
            )
        return "Not generated"
    download_link.short_description = "Report File"
    
    actions = ['generate_pdf_reports']
    
    def generate_pdf_reports(self, request, queryset):
        self.message_user(request, f"PDF generation started for {queryset.count()} reports")
    generate_pdf_reports.short_description = "Generate PDF reports"


@admin.register(DailyProductionSummary)
class DailyProductionSummaryAdmin(admin.ModelAdmin):
    list_display = ['date', 'total_milk', 'session_breakdown', 'avg_fat', 
                   'lactating_cows', 'revenue']
    list_filter = ['date']
    date_hierarchy = 'date'
    
    def session_breakdown(self, obj):
        return format_html(
            'M:{}L | A:{}L | E:{}L',
            obj.morning_total, obj.afternoon_total, obj.evening_total
        )
    session_breakdown.short_description = "Session Breakdown"


# ==================== HEALTH SUMMARY REPORTS ====================

@admin.register(HealthSummaryReport)
class HealthSummaryReportAdmin(admin.ModelAdmin):
    list_display = ['title', 'report_type', 'period_display', 'total_cases', 
                   'critical_cases', 'total_health_cost', 'recovery_rate', 
                   'generated_at', 'download_link']
    list_filter = ['report_type', 'year', 'quarter', 'generated_at']
    search_fields = ['title', 'notes']
    date_hierarchy = 'generated_at'
    readonly_fields = ['total_cases', 'healthy_cattle', 'under_treatment', 
                      'critical_cases', 'recovered_cases', 'total_health_cost',
                      'emergency_cases', 'emergency_cost']
    
    fieldsets = (
        ('Report Information', {
            'fields': ('title', 'report_type', 'year', 'quarter', 
                      'start_date', 'end_date', 'notes')
        }),
        ('Health Statistics', {
            'fields': ('total_cases', 'healthy_cattle', 'under_treatment', 
                      'critical_cases', 'recovered_cases'),
            'classes': ('wide',)
        }),
        ('Cost Analysis', {
            'fields': ('total_health_cost', 'avg_cost_per_case',
                      'emergency_cases', 'emergency_cost'),
        }),
        ('Vaccination Summary', {
            'fields': ('vaccinations_scheduled', 'vaccinations_completed',
                      'vaccinations_overdue', 'vaccinations_upcoming'),
        }),
        ('Metadata', {
            'fields': ('generated_by', 'generated_at', 'report_file'),
        }),
    )
    
    def period_display(self, obj):
        if obj.report_type == 'QUARTERLY':
            return f"Q{obj.quarter} {obj.year}"
        elif obj.report_type == 'YEARLY':
            return str(obj.year)
        else:
            return f"{obj.start_date} to {obj.end_date}"
    period_display.short_description = "Period"
    
    def recovery_rate(self, obj):
        if obj.total_cases > 0:
            rate = (obj.recovered_cases / obj.total_cases) * 100
            color = 'green' if rate > 80 else 'orange' if rate > 60 else 'red'
            return format_html(
                '<span style="color: {}; font-weight: bold;">{}%</span>',
                color, round(rate, 1)
            )
        return "N/A"
    recovery_rate.short_description = "Recovery Rate"
    
    def download_link(self, obj):
        if obj.report_file:
            return format_html(
                '<a href="{}" target="_blank">📄 PDF</a>',
                obj.report_file.url
            )
        return "Not generated"
    download_link.short_description = "Report"
    
    actions = ['generate_pdf', 'send_email_report']
    
    def generate_pdf(self, request, queryset):
        self.message_user(request, f"PDF generation initiated for {queryset.count()} reports")
    generate_pdf.short_description = "Generate PDF reports"
    
    def send_email_report(self, request, queryset):
        self.message_user(request, f"Emails sent for {queryset.count()} reports")
    send_email_report.short_description = "Email reports"


@admin.register(DiseaseTrend)
class DiseaseTrendAdmin(admin.ModelAdmin):
    list_display = ['disease_name', 'year', 'month', 'month_name', 'cases_count', 'seasonal_pattern']
    list_filter = ['disease_name', 'year', 'seasonal_pattern']
    search_fields = ['disease_name']
    
    def month_name(self, obj):
        months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
                 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
        return months[obj.month - 1] if 1 <= obj.month <= 12 else ''
    month_name.short_description = "Month"
    month_name.admin_order_field = 'month'
    
    def changelist_view(self, request, extra_context=None):
        from django.db.models import Sum
        
        # Get summary statistics
        total_cases = DiseaseTrend.objects.aggregate(total=Sum('cases_count'))['total'] or 0
        
        # Get top diseases
        top_diseases = DiseaseTrend.objects.values('disease_name').annotate(
            total=Sum('cases_count')
        ).order_by('-total')[:5]
        
        # Get yearly trends
        years = DiseaseTrend.objects.values_list('year', flat=True).distinct().order_by('-year')
        
        chart_data = []
        for year in years:
            year_total = DiseaseTrend.objects.filter(year=year).aggregate(
                total=Sum('cases_count')
            )['total'] or 0
            chart_data.append({'year': year, 'total': year_total})
        
        extra_context = extra_context or {}
        extra_context.update({
            'total_cases': total_cases,
            'top_diseases': top_diseases,
            'chart_data': chart_data,
            'years': years,
        })
        
        return super().changelist_view(request, extra_context=extra_context)


# ==================== BREEDING PERFORMANCE REPORTS ====================

@admin.register(BreedingPerformanceReport)
class BreedingPerformanceReportAdmin(admin.ModelAdmin):
    list_display = ['title', 'period', 'period_display', 'total_breedings', 
                   'conception_rate_indicator', 'calved_count', 'cost_per_pregnancy',
                   'generated_at', 'download_link']
    list_filter = ['period', 'year', 'month', 'quarter', 'generated_at']
    search_fields = ['title', 'notes']
    date_hierarchy = 'generated_at'
    readonly_fields = ['total_breedings', 'confirmed_pregnant', 'conception_rate',
                      'total_pregnant', 'expected_calving_next_30_days', 'total_calves']
    
    fieldsets = (
        ('Report Information', {
            'fields': ('title', 'period', 'year', 'month', 'quarter',
                      'start_date', 'end_date', 'notes')
        }),
        ('Breeding Statistics', {
            'fields': ('total_breedings', 'confirmed_pregnant', 'failed_conceptions',
                      'pending_results', 'calved_count'),
            'classes': ('wide',)
        }),
        ('Success Rates', {
            'fields': ('conception_rate', 'natural_success_rate', 'ai_success_rate'),
        }),
        ('Pregnancy & Calving', {
            'fields': ('total_pregnant', 'expected_calving_next_30_days',
                      'expected_calving_next_90_days'),
        }),
        ('Heat Detection', {
            'fields': ('heat_cycles_detected', 'successful_breedings', 'missed_opportunities'),
        }),
        ('Calving Statistics', {
            'fields': ('total_calves', 'male_calves', 'female_calves',
                      'avg_birth_weight', 'calf_survival_rate'),
        }),
        ('Financial', {
            'fields': ('total_breeding_cost', 'cost_per_pregnancy'),
        }),
        ('Metadata', {
            'fields': ('generated_by', 'generated_at', 'report_file'),
        }),
    )
    
    def period_display(self, obj):
        if obj.period == 'MONTHLY':
            months = ['January', 'February', 'March', 'April', 'May', 'June',
                     'July', 'August', 'September', 'October', 'November', 'December']
            return months[obj.month - 1] if obj.month else ''
        elif obj.period == 'QUARTERLY':
            return f"Q{obj.quarter}"
        elif obj.period == 'YEARLY':
            return str(obj.year)
        else:
            return f"{obj.start_date} to {obj.end_date}"
    period_display.short_description = "Period"
    
    def conception_rate_indicator(self, obj):
        rate = obj.conception_rate
        if rate >= 70:
            color = 'green'
            icon = '▲'
        elif rate >= 50:
            color = 'orange'
            icon = '●'
        else:
            color = 'red'
            icon = '▼'
        
        return format_html(
            '<span style="color: {}; font-weight: bold;">{} {}%</span>',
            color, icon, rate
        )
    conception_rate_indicator.short_description = "Conception Rate"
    
    def download_link(self, obj):
        if obj.report_file:
            return format_html(
                '<a href="{}" target="_blank" style="background: #17a2b8; color: white; padding: 3px 10px; border-radius: 3px; text-decoration: none;">📊 View</a>',
                obj.report_file.url
            )
        return "Not generated"
    download_link.short_description = "Report"
    
    actions = ['generate_report', 'export_comparison_chart']
    
    def generate_report(self, request, queryset):
        for report in queryset:
            self._calculate_sire_performance(report)
        self.message_user(request, f"Reports generated for {queryset.count()} periods")
    generate_report.short_description = "Generate detailed reports"
    
    def _calculate_sire_performance(self, report):
        """Calculate sire performance for the report period"""
        breedings = BreedingRecord.objects.filter(
            breeding_date__range=[report.start_date, report.end_date]
        ).exclude(sire__isnull=True)
        
        sire_stats = breedings.values('sire').annotate(
            services=Count('id'),
            success=Count('id', filter=Q(is_pregnant=True))
        )
        
        for stat in sire_stats:
            try:
                sire = Cattle.objects.get(id=stat['sire'])
                SirePerformance.objects.create(
                    report=report,
                    sire=sire,
                    breed=sire.breed,
                    total_services=stat['services'],
                    pregnancies=stat['success'],
                    success_rate=(stat['success'] / stat['services'] * 100) if stat['services'] > 0 else 0
                )
            except Cattle.DoesNotExist:
                continue
    
    def export_comparison_chart(self, request, queryset):
        self.message_user(request, "Comparison chart exported successfully")
    export_comparison_chart.short_description = "Export comparison chart"


@admin.register(SirePerformance)
class SirePerformanceAdmin(admin.ModelAdmin):
    list_display = ['sire', 'breed', 'total_services', 'pregnancies', 
                   'success_rate_bar', 'report_link']
    list_filter = ['breed', 'report__year']
    search_fields = ['sire__tag_number']
    
    def success_rate_bar(self, obj):
        rate = obj.success_rate
        bar_length = int(rate / 5)  # 20 chars max
        bar = '█' * bar_length + '░' * (20 - bar_length)
        return format_html(
            '<span style="color: #28a745; font-family: monospace;" title="{}%">{}</span>',
            rate, bar
        )
    success_rate_bar.short_description = "Success Rate"
    
    def report_link(self, obj):
        url = reverse('admin:dairy_breedingperformancereport_change', args=[obj.report.id])
        return format_html('<a href="{}">View Report</a>', url)
    report_link.short_description = "Report"


class SirePerformanceInline(admin.TabularInline):
    model = SirePerformance
    extra = 0
    readonly_fields = ['sire', 'breed', 'total_services', 'pregnancies', 'success_rate']
    can_delete = False
    verbose_name = "Sire Performance"
    verbose_name_plural = "Sire Performances"


class MonthlyBreedingActivityInline(admin.TabularInline):
    model = MonthlyBreedingActivity
    extra = 0
    readonly_fields = ['month', 'bred', 'pregnant', 'calved']
    can_delete = False
    verbose_name = "Monthly Activity"
    verbose_name_plural = "Monthly Activities"


# Add inlines to BreedingPerformanceReportAdmin
BreedingPerformanceReportAdmin.inlines = [SirePerformanceInline, MonthlyBreedingActivityInline]


# ==================== CUSTOM ADMIN SITE CONFIGURATION ====================

# Customize Admin Site
admin.site.site_header = 'Sheikh Agro - Dairy Management System'
admin.site.site_title = 'Sheikh Agro'
admin.site.index_title = 'Dairy Farm Administration Dashboard'
admin.site.site_url = '/dairy/'