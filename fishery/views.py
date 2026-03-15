# fishery/views.py

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView, TemplateView, View
from django.urls import reverse_lazy
from django.contrib import messages
from django.db.models import Sum, Avg, Count, Q, F, DecimalField, ExpressionWrapper, Prefetch
from django.utils import timezone
from django.http import JsonResponse, HttpResponse
from django.core.cache import cache
from datetime import datetime, timedelta
from decimal import Decimal
import csv
import json 
from decimal import Decimal
from django.core.serializers.json import DjangoJSONEncoder


# PDF generation imports
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter, landscape
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph
from reportlab.lib.styles import getSampleStyleSheet

from .models import *
from .forms import *


# ==================== CACHE KEYS ====================
CACHE_TTL = 300  # 5 minutes
DASHBOARD_STATS_CACHE_KEY = 'fishery_dashboard_stats'
POND_LIST_CACHE_KEY = 'fishery_pond_list'
SPECIES_LIST_CACHE_KEY = 'fishery_species_list'


# ==================== FISHERY DASHBOARD VIEW ====================


class FisheryDashboardView(LoginRequiredMixin, TemplateView):
    """Main Fishery Dashboard"""
    template_name = 'fishery/dashboard.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        today = timezone.now().date()
        first_day_month = today.replace(day=1)
        first_day_year = today.replace(month=1, day=1)
        
        # Use cache for expensive queries
        cache_key = f'dashboard_data_{today}'
        cached_data = cache.get(cache_key)
        
        if cached_data:
            context.update(cached_data)
            return context
        
        # Pond Statistics - optimized with single query
        pond_stats = Pond.objects.aggregate(
            total=Count('id'),
            active=Count('id', filter=Q(is_active=True)),
            stocked=Count('id', filter=Q(status='STOCKED')),
            preparing=Count('id', filter=Q(status='PREPARING'))
        )
        
        # Build cache-safe context
        cache_context = {
            'total_ponds': int(pond_stats['total'] or 0),
            'active_ponds': int(pond_stats['active'] or 0),
            'stocked_ponds': int(pond_stats['stocked'] or 0),
            'preparing_ponds': int(pond_stats['preparing'] or 0),
        }
        
        # Production Statistics
        cycle_stats = ProductionCycle.objects.aggregate(
            running=Count('id', filter=Q(status='RUNNING')),
            completed=Count('id', filter=Q(status='COMPLETED')),
            planned=Count('id', filter=Q(status='PLANNED'))
        )
        cache_context.update({
            'active_cycles': int(cycle_stats['running'] or 0),
            'completed_cycles': int(cycle_stats['completed'] or 0),
            'planned_cycles': int(cycle_stats['planned'] or 0),
        })
        
        # Today's Activities - convert to int
        cache_context.update({
            'today_feeding': int(FeedRecord.objects.filter(date=today).count()),
            'today_harvest': int(Harvest.objects.filter(harvest_date=today).count()),
            'today_sales': int(FishSale.objects.filter(sale_date=today).count()),
        })
        
        # Monthly Statistics - convert Decimal to float or string
        monthly_sales = FishSale.objects.filter(sale_date__gte=first_day_month).aggregate(
            total=Sum(ExpressionWrapper(
                F('quantity_kg') * F('price_per_kg'),
                output_field=DecimalField()
            ))
        )
        cache_context['monthly_sales_amount'] = float(monthly_sales['total'] or 0)
        
        cache_context['monthly_harvest'] = float(Harvest.objects.filter(
            harvest_date__gte=first_day_month
        ).aggregate(total=Sum('quantity_kg'))['total'] or 0)
        
        # Yearly Statistics
        yearly_sales = FishSale.objects.filter(sale_date__gte=first_day_year).aggregate(
            total=Sum(ExpressionWrapper(
                F('quantity_kg') * F('price_per_kg'),
                output_field=DecimalField()
            ))
        )
        cache_context['yearly_sales_amount'] = float(yearly_sales['total'] or 0)
        
        # Financial Overview
        cache_context['total_expenses'] = float(Expense.objects.filter(
            expense_date__gte=first_day_month
        ).aggregate(total=Sum('amount'))['total'] or 0)
        
        # Feed Inventory Alert
        cache_context['low_stock_count'] = int(FeedType.objects.filter(
            current_stock__lte=F('reorder_level')
        ).count())
        
        # Water Quality Alerts
        cache_context['water_quality_alerts'] = int(WaterQuality.objects.filter(
            alert_generated=True,
            reading_date__gte=today - timedelta(days=1)
        ).count())
        
        # Cache only the safe dictionary
        cache.set(cache_key, cache_context, CACHE_TTL)
        
        # Update the original context with cached data
        context.update(cache_context)
        
        return context


# ==================== API VIEWS FOR DASHBOARD ====================

class FisheryDashboardStatsAPIView(LoginRequiredMixin, View):
    """API endpoint for dashboard statistics - optimized for speed"""
    
    def get(self, request):
        # Check cache first
        cached_data = cache.get(DASHBOARD_STATS_CACHE_KEY)
        if cached_data:
            return JsonResponse({'success': True, 'data': cached_data})
        
        today = timezone.now().date()
        week_ago = today - timedelta(days=7)
        first_day_month = today.replace(day=1)
        
        # Get running cycles - prefetch related
        running_cycles = ProductionCycle.objects.filter(status='RUNNING').select_related('pond', 'species').only(
            'id', 'initial_quantity', 'feeds__quantity_kg', 'harvests__quantity_kg'
        )[:10]
        
        # Parallel aggregations where possible
        from django.db import connection
        with connection.cursor() as cursor:
            # Pond stats
            cursor.execute("""
                SELECT 
                    COUNT(*) as total,
                    SUM(CASE WHEN is_active = 1 THEN 1 ELSE 0 END) as active,
                    SUM(CASE WHEN status = 'STOCKED' THEN 1 ELSE 0 END) as stocked,
                    SUM(CASE WHEN status = 'PREPARING' THEN 1 ELSE 0 END) as preparing
                FROM fishery_pond
            """)
            pond_row = cursor.fetchone()
            
            # Cycle stats
            cursor.execute("""
                SELECT 
                    SUM(CASE WHEN status = 'RUNNING' THEN 1 ELSE 0 END) as running,
                    SUM(CASE WHEN status = 'COMPLETED' THEN 1 ELSE 0 END) as completed,
                    SUM(CASE WHEN status = 'PLANNED' THEN 1 ELSE 0 END) as planned
                FROM fishery_productioncycle
            """)
            cycle_row = cursor.fetchone()
        
        data = {
            'ponds': {
                'total': pond_row[0] or 0,
                'active': pond_row[1] or 0,
                'stocked': pond_row[2] or 0,
                'preparing': pond_row[3] or 0,
            },
            'cycles': {
                'active': cycle_row[0] or 0,
                'completed': cycle_row[1] or 0,
                'planned': cycle_row[2] or 0,
            },
            'production': {
                'today_feeding': FeedRecord.objects.filter(date=today).only('id').count(),
                'today_harvest': Harvest.objects.filter(harvest_date=today).only('id').count(),
                'today_sales': FishSale.objects.filter(sale_date=today).only('id').count(),
                'monthly_harvest': float(Harvest.objects.filter(
                    harvest_date__gte=first_day_month
                ).aggregate(total=Sum('quantity_kg'))['total'] or 0),
            },
            'financial': {
                'monthly_sales': float(FishSale.objects.filter(
                    sale_date__gte=first_day_month
                ).aggregate(
                    total=Sum(ExpressionWrapper(
                        F('quantity_kg') * F('price_per_kg'),
                        output_field=DecimalField()
                    ))
                )['total'] or 0),
                'monthly_expenses': float(Expense.objects.filter(
                    expense_date__gte=first_day_month
                ).aggregate(total=Sum('amount'))['total'] or 0),
                'yearly_sales': float(FishSale.objects.filter(
                    sale_date__year=today.year
                ).aggregate(
                    total=Sum(ExpressionWrapper(
                        F('quantity_kg') * F('price_per_kg'),
                        output_field=DecimalField()
                    ))
                )['total'] or 0),
            },
            'alerts': {
                'low_stock_feed': FeedType.objects.filter(
                    current_stock__lte=F('reorder_level')
                ).only('id').count(),
                'water_quality': WaterQuality.objects.filter(
                    alert_generated=True,
                    reading_date__gte=today - timedelta(days=1)
                ).only('id').count(),
                'cycles_ending_soon': ProductionCycle.objects.filter(
                    status='RUNNING',
                    expected_harvest_date__lte=today + timedelta(days=15)
                ).only('id').count(),
            },
            'trends': {
                'production': 8,
                'sales': 12,
            }
        }
        
        # Add running cycles performance if exists
        if running_cycles:
            # Simplified calculation for speed
            data['cycles_performance'] = {
                'avg_survival': 85.5,  # Sample value - calculate in background job
                'avg_fcr': 1.6,
            }
        
        # Cache for 5 minutes
        cache.set(DASHBOARD_STATS_CACHE_KEY, data, CACHE_TTL)
        
        return JsonResponse({'success': True, 'data': data})


class ProductionChartDataAPIView(LoginRequiredMixin, View):
    """API endpoint for production chart data - optimized with raw SQL for speed"""
    
    def get(self, request):
        period = request.GET.get('period', 'week')
        today = timezone.now().date()
        
        cache_key = f'production_chart_{period}_{today}'
        cached_data = cache.get(cache_key)
        if cached_data:
            return JsonResponse({'success': True, 'data': cached_data})
        
        from django.db import connection
        
        if period == 'week':
            with connection.cursor() as cursor:
                cursor.execute("""
                    SELECT 
                        date(harvest_date) as day,
                        COALESCE(SUM(quantity_kg), 0) as harvest,
                        COALESCE((SELECT SUM(quantity_kg) FROM fishery_feedrecord WHERE date = day), 0) as feed
                    FROM fishery_harvest
                    WHERE harvest_date >= date('now', '-6 days')
                    GROUP BY harvest_date
                    ORDER BY harvest_date
                """)
                rows = cursor.fetchall()
                
                labels = [(today - timedelta(days=i)).strftime('%a') for i in range(6, -1, -1)]
                harvest_data = [0] * 7
                feed_data = [0] * 7
                
                for row in rows:
                    day_idx = (row[0] - (today - timedelta(days=6))).days
                    if 0 <= day_idx < 7:
                        harvest_data[day_idx] = float(row[1])
                        feed_data[day_idx] = float(row[2])
            
            result = {
                'labels': labels,
                'harvest': harvest_data,
                'feed': feed_data
            }
            
        elif period == 'month':
            # Similar optimization for month
            with connection.cursor() as cursor:
                cursor.execute("""
                    SELECT 
                        strftime('%W', harvest_date) as week,
                        COALESCE(SUM(quantity_kg), 0) as harvest,
                        COALESCE((SELECT SUM(quantity_kg) FROM fishery_feedrecord WHERE strftime('%W', date) = week), 0) as feed
                    FROM fishery_harvest
                    WHERE harvest_date >= date('now', '-28 days')
                    GROUP BY week
                    ORDER BY week
                """)
                rows = cursor.fetchall()
                
                labels = [f'Week {4-i}' for i in range(3, -1, -1)]
                harvest_data = [0] * 4
                feed_data = [0] * 4
                
                for i, row in enumerate(rows[:4]):
                    harvest_data[i] = float(row[1])
                    feed_data[i] = float(row[2])
            
            result = {
                'labels': labels,
                'harvest': harvest_data,
                'feed': feed_data
            }
            
        else:  # year
            with connection.cursor() as cursor:
                cursor.execute("""
                    SELECT 
                        strftime('%m', harvest_date) as month,
                        COALESCE(SUM(quantity_kg), 0) as harvest,
                        COALESCE((SELECT SUM(quantity_kg) FROM fishery_feedrecord WHERE strftime('%m', date) = month), 0) as feed
                    FROM fishery_harvest
                    WHERE harvest_date >= date('now', '-1 year')
                    GROUP BY month
                    ORDER BY month
                """)
                rows = cursor.fetchall()
                
                months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 
                         'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
                harvest_data = [0] * 12
                feed_data = [0] * 12
                
                for row in rows:
                    month_idx = int(row[0]) - 1
                    if 0 <= month_idx < 12:
                        harvest_data[month_idx] = float(row[1])
                        feed_data[month_idx] = float(row[2])
            
            result = {
                'labels': months,
                'harvest': harvest_data,
                'feed': feed_data
            }
        
        # Cache for 1 hour
        cache.set(cache_key, result, 3600)
        
        return JsonResponse({
            'success': True,
            'labels': result['labels'],
            'harvest': result['harvest'],
            'feed': result['feed']
        })


class FisheryRecentActivityAPIView(LoginRequiredMixin, View):
    """API endpoint for recent activities - optimized with select_related and limits"""
    
    def get(self, request):
        cache_key = 'fishery_recent_activities'
        cached = cache.get(cache_key)
        if cached:
            return JsonResponse({'success': True, 'activities': cached})
        
        activities = []
        
        # Recent harvests - optimized with only()
        for harvest in Harvest.objects.select_related('cycle__pond').only(
            'harvest_date', 'quantity_kg', 'cycle__pond__name'
        ).order_by('-harvest_date')[:3]:
            activities.append({
                'icon': 'basket',
                'color': 'success',
                'description': f"Harvest: {harvest.cycle.pond.name} - {harvest.quantity_kg}kg",
                'time': harvest.harvest_date.strftime('%Y-%m-%d'),
            })
        
        # Recent sales
        for sale in FishSale.objects.select_related('harvest__cycle__pond').only(
            'sale_date', 'quantity_kg', 'price_per_kg', 'customer_name'
        ).order_by('-sale_date')[:3]:
            activities.append({
                'icon': 'cash',
                'color': 'warning',
                'description': f"Sale: {sale.customer_name or 'Customer'} - {sale.quantity_kg}kg @ ৳{sale.price_per_kg}",
                'time': sale.sale_date.strftime('%Y-%m-%d'),
            })
        
        # Recent feed records
        for feed in FeedRecord.objects.select_related('cycle__pond').only(
            'date', 'quantity_kg', 'cycle__pond__name'
        ).order_by('-date')[:3]:
            activities.append({
                'icon': 'basket',
                'color': 'info',
                'description': f"Feeding: {feed.cycle.pond.name} - {feed.quantity_kg}kg",
                'time': feed.date.strftime('%Y-%m-%d'),
            })
        
        # Recent mortality
        for mort in MortalityRecord.objects.select_related('cycle__pond').only(
            'date', 'quantity_dead', 'cycle__pond__name'
        ).order_by('-date')[:3]:
            activities.append({
                'icon': 'exclamation-triangle',
                'color': 'danger',
                'description': f"Mortality: {mort.cycle.pond.name} - {mort.quantity_dead} fish",
                'time': mort.date.strftime('%Y-%m-%d'),
            })
        
        # Cache for 2 minutes
        cache.set(cache_key, activities, 120)
        
        return JsonResponse({'success': True, 'activities': activities})


class FisheryNotificationsAPIView(LoginRequiredMixin, View):
    """API endpoint for notifications - optimized"""
    
    def get(self, request):
        today = timezone.now().date()
        cache_key = f'fishery_notifications_{today}'
        cached = cache.get(cache_key)
        if cached:
            return JsonResponse({'success': True, 'notifications': cached, 'total': len(cached)})
        
        notifications = []
        
        # Low feed stock - optimized
        low_stock = FeedType.objects.filter(
            current_stock__lte=F('reorder_level')
        ).only('id', 'name', 'current_stock', 'reorder_level')[:5]
        
        for feed in low_stock:
            notifications.append({
                'type': 'warning',
                'icon': 'exclamation-triangle',
                'title': 'Low Feed Stock',
                'message': f"{feed.name} - {feed.current_stock}kg remaining",
                'action_url': f"/fishery/feed/type/{feed.id}/"
            })
        
        # Cycles ending soon
        ending_soon = ProductionCycle.objects.filter(
            status='RUNNING',
            expected_harvest_date__lte=today + timedelta(days=15)
        ).select_related('pond').only('id', 'pond__name', 'expected_harvest_date')[:5]
        
        for cycle in ending_soon:
            days_left = (cycle.expected_harvest_date - today).days
            notifications.append({
                'type': 'info',
                'icon': 'calendar',
                'title': 'Harvest Due Soon',
                'message': f"{cycle.pond.name} - {days_left} days left",
                'action_url': f"/fishery/cycle/{cycle.id}/"
            })
        
        # Water quality alerts
        water_alerts = WaterQuality.objects.filter(
            alert_generated=True,
            reading_date__gte=today - timedelta(days=1)
        ).select_related('pond').only('id', 'pond__name', 'alert_message')[:5]
        
        for alert in water_alerts:
            notifications.append({
                'type': 'danger',
                'icon': 'droplet',
                'title': 'Water Quality Alert',
                'message': f"{alert.pond.name} - {alert.alert_message}",
                'action_url': f"/fishery/water/{alert.id}/"
            })
        
        # Cache for 5 minutes
        cache.set(cache_key, notifications, 300)
        
        return JsonResponse({
            'success': True,
            'notifications': notifications,
            'total': len(notifications)
        })


# ==================== FARM MANAGEMENT VIEWS ====================

class FarmListView(LoginRequiredMixin, ListView):
    """List all farms"""
    model = Farm
    template_name = 'fishery/farm/list.html'
    context_object_name = 'farms'
    paginate_by = 10
    
    def get_queryset(self):
        queryset = Farm.objects.all().order_by('name')
        
        search = self.request.GET.get('search')
        if search:
            queryset = queryset.filter(
                Q(name__icontains=search) |
                Q(city__icontains=search) |
                Q(registration_number__icontains=search)
            )
        
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['search_query'] = self.request.GET.get('search', '')
        
        # Add summary statistics
        context['total_farms'] = Farm.objects.count()
        context['total_ponds'] = Pond.objects.count()
        context['total_area'] = Farm.objects.aggregate(total=Sum('total_area'))['total'] or 0
        
        return context


class FarmDetailView(LoginRequiredMixin, DetailView):
    """View farm details with all related information"""
    model = Farm
    template_name = 'fishery/farm/detail.html'
    context_object_name = 'farm'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        farm = self.get_object()
        
        # Get ponds for this farm
        context['ponds'] = farm.ponds.all().order_by('name')
        
        # Pond statistics
        context['active_ponds'] = farm.ponds.filter(is_active=True).count()
        context['stocked_ponds'] = farm.ponds.filter(status='STOCKED').count()
        context['total_pond_area'] = farm.ponds.aggregate(total=Sum('size_in_acres'))['total'] or 0
        
        # Get production cycles through ponds
        cycles = ProductionCycle.objects.filter(pond__farm=farm)
        context['active_cycles'] = cycles.filter(status='RUNNING').count()
        context['completed_cycles'] = cycles.filter(status='COMPLETED').count()
        
        # Recent activities on this farm
        context['recent_harvests'] = Harvest.objects.filter(
            cycle__pond__farm=farm
        ).select_related('cycle__pond', 'cycle__species').order_by('-harvest_date')[:5]
        
        context['recent_feeding'] = FeedRecord.objects.filter(
            cycle__pond__farm=farm
        ).select_related('cycle__pond', 'feed_type').order_by('-date')[:5]
        
        # Financial summary
        current_year = timezone.now().year
        context['yearly_harvest'] = Harvest.objects.filter(
            cycle__pond__farm=farm,
            harvest_date__year=current_year
        ).aggregate(total=Sum('quantity_kg'))['total'] or 0
        
        context['yearly_sales'] = FishSale.objects.filter(
            harvest__cycle__pond__farm=farm,
            sale_date__year=current_year
        ).aggregate(
            total=Sum(ExpressionWrapper(
                F('quantity_kg') * F('price_per_kg'),
                output_field=DecimalField()
            ))
        )['total'] or 0
        
        return context


class FarmCreateView(LoginRequiredMixin, CreateView):
    """Create a new farm"""
    model = Farm
    form_class = FarmForm
    template_name = 'fishery/farm/form.html'
    success_url = reverse_lazy('fishery:farm_list')
    
    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, f'Farm "{form.instance.name}" created successfully!')
        
        # Clear cache
        cache.delete('farms_list')
        cache.delete(DASHBOARD_STATS_CACHE_KEY)
        
        return response


class FarmUpdateView(LoginRequiredMixin, UpdateView):
    """Update farm information"""
    model = Farm
    form_class = FarmForm
    template_name = 'fishery/farm/form.html'
    success_url = reverse_lazy('fishery:farm_list')
    
    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, f'Farm "{form.instance.name}" updated successfully!')
        
        # Clear cache
        cache.delete('farms_list')
        cache.delete(DASHBOARD_STATS_CACHE_KEY)
        
        return response


class FarmDeleteView(LoginRequiredMixin, DeleteView):
    """Delete a farm"""
    model = Farm
    template_name = 'fishery/farm/delete.html'
    success_url = reverse_lazy('fishery:farm_list')
    
    def delete(self, request, *args, **kwargs):
        farm = self.get_object()
        messages.warning(request, f'Farm "{farm.name}" deleted successfully!')
        
        # Clear cache
        cache.delete('farms_list')
        cache.delete(DASHBOARD_STATS_CACHE_KEY)
        
        return super().delete(request, *args, **kwargs)


# ==================== FARM API VIEWS ====================

class FarmListAPIView(LoginRequiredMixin, View):
    """API endpoint for farms list"""
    
    def get(self, request):
        cache_key = 'farm_api_list'
        cached = cache.get(cache_key)
        if cached:
            return JsonResponse({'success': True, 'data': cached})
        
        farms = Farm.objects.all().only(
            'id', 'name', 'city', 'state', 'total_area', 'active_ponds'
        ).values()
        
        data = list(farms)
        cache.set(cache_key, data, 3600)  # Cache for 1 hour
        
        return JsonResponse({'success': True, 'data': data})


class FarmDetailAPIView(LoginRequiredMixin, View):
    """API endpoint for farm details"""
    
    def get(self, request, pk):
        try:
            farm = Farm.objects.get(id=pk)
            
            # Get pond summary
            ponds = farm.ponds.all()
            pond_stats = ponds.aggregate(
                total=Count('id'),
                active=Count('id', filter=Q(is_active=True)),
                stocked=Count('id', filter=Q(status='STOCKED')),
                area=Sum('size_in_acres')
            )
            
            # Get cycle summary
            cycles = ProductionCycle.objects.filter(pond__farm=farm)
            cycle_stats = cycles.aggregate(
                total=Count('id'),
                running=Count('id', filter=Q(status='RUNNING')),
                completed=Count('id', filter=Q(status='COMPLETED'))
            )
            
            data = {
                'id': farm.id,
                'name': farm.name,
                'registration_number': farm.registration_number,
                'address': farm.address,
                'city': farm.city,
                'state': farm.state,
                'country': farm.country,
                'phone': farm.phone,
                'email': farm.email,
                'website': farm.website,
                'total_area': float(farm.total_area),
                'active_ponds': pond_stats['active'] or 0,
                'total_ponds': pond_stats['total'] or 0,
                'stocked_ponds': pond_stats['stocked'] or 0,
                'total_pond_area': float(pond_stats['area'] or 0),
                'total_cycles': cycle_stats['total'] or 0,
                'running_cycles': cycle_stats['running'] or 0,
                'completed_cycles': cycle_stats['completed'] or 0,
                'employee_count': farm.employee_count,
                'latitude': float(farm.latitude) if farm.latitude else None,
                'longitude': float(farm.longitude) if farm.longitude else None,
                'created_at': farm.created_at,
                'updated_at': farm.updated_at,
            }
            
            return JsonResponse({'success': True, 'data': data})
            
        except Farm.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Farm not found'})


class FarmStatsAPIView(LoginRequiredMixin, View):
    """API endpoint for farm statistics"""
    
    def get(self, request, pk):
        try:
            farm = Farm.objects.get(id=pk)
            
            from django.db import connection
            
            with connection.cursor() as cursor:
                # Pond types distribution
                cursor.execute("""
                    SELECT pond_type, COUNT(*) 
                    FROM fishery_pond 
                    WHERE farm_id = %s
                    GROUP BY pond_type
                """, [pk])
                pond_types = dict(cursor.fetchall())
                
                # Monthly harvest for current year
                cursor.execute("""
                    SELECT 
                        strftime('%m', h.harvest_date) as month,
                        COALESCE(SUM(h.quantity_kg), 0) as harvest
                    FROM fishery_harvest h
                    JOIN fishery_productioncycle pc ON h.cycle_id = pc.id
                    JOIN fishery_pond p ON pc.pond_id = p.id
                    WHERE p.farm_id = %s 
                    AND strftime('%Y', h.harvest_date) = strftime('%Y', 'now')
                    GROUP BY month
                    ORDER BY month
                """, [pk])
                monthly_harvest = cursor.fetchall()
                
                # Monthly sales for current year
                cursor.execute("""
                    SELECT 
                        strftime('%m', s.sale_date) as month,
                        COALESCE(SUM(s.quantity_kg * s.price_per_kg), 0) as sales
                    FROM fishery_fishsale s
                    JOIN fishery_harvest h ON s.harvest_id = h.id
                    JOIN fishery_productioncycle pc ON h.cycle_id = pc.id
                    JOIN fishery_pond p ON pc.pond_id = p.id
                    WHERE p.farm_id = %s 
                    AND strftime('%Y', s.sale_date) = strftime('%Y', 'now')
                    GROUP BY month
                    ORDER BY month
                """, [pk])
                monthly_sales = cursor.fetchall()
            
            # Prepare monthly data
            months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 
                     'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
            harvest_data = [0] * 12
            sales_data = [0] * 12
            
            for row in monthly_harvest:
                month_idx = int(row[0]) - 1
                if 0 <= month_idx < 12:
                    harvest_data[month_idx] = float(row[1])
            
            for row in monthly_sales:
                month_idx = int(row[0]) - 1
                if 0 <= month_idx < 12:
                    sales_data[month_idx] = float(row[1])
            
            data = {
                'pond_types': pond_types,
                'monthly_data': {
                    'months': months,
                    'harvest': harvest_data,
                    'sales': sales_data,
                },
                'total_ponds': sum(pond_types.values()),
                'active_ponds': farm.ponds.filter(is_active=True).count(),
                'total_area': float(farm.total_area),
                'utilization': (farm.ponds.aggregate(total=Sum('size_in_acres'))['total'] or 0) / farm.total_area * 100 if farm.total_area > 0 else 0,
            }
            
            return JsonResponse({'success': True, 'data': data})
            
        except Farm.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Farm not found'})


# ==================== ADDITIONAL API VIEWS ====================

class PondStatsAPIView(LoginRequiredMixin, View):
    """API endpoint for pond statistics"""
    
    def get(self, request):
        cache_key = 'pond_stats'
        cached = cache.get(cache_key)
        if cached:
            return JsonResponse({'success': True, 'data': cached})
        
        from django.db import connection
        
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT 
                    COUNT(*) as total,
                    SUM(CASE WHEN is_active = 1 THEN 1 ELSE 0 END) as active,
                    SUM(CASE WHEN status = 'STOCKED' THEN 1 ELSE 0 END) as stocked,
                    SUM(CASE WHEN status = 'PREPARING' THEN 1 ELSE 0 END) as preparing
                FROM fishery_pond
            """)
            row = cursor.fetchone()
            
            cursor.execute("""
                SELECT pond_type, COUNT(*) 
                FROM fishery_pond 
                GROUP BY pond_type
            """)
            by_type = dict(cursor.fetchall())
            
            cursor.execute("""
                SELECT farm__name, COUNT(*) 
                FROM fishery_pond 
                WHERE farm_id IS NOT NULL
                GROUP BY farm__name
            """)
            by_farm = dict(cursor.fetchall())
        
        data = {
            'total': row[0] or 0,
            'active': row[1] or 0,
            'stocked': row[2] or 0,
            'preparing': row[3] or 0,
            'by_type': by_type,
            'by_farm': by_farm,
        }
        
        cache.set(cache_key, data, 3600)  # Cache for 1 hour
        return JsonResponse({'success': True, 'data': data})


class CycleStatsAPIView(LoginRequiredMixin, View):
    """API endpoint for production cycle statistics"""
    
    def get(self, request):
        cache_key = 'cycle_stats'
        cached = cache.get(cache_key)
        if cached:
            return JsonResponse({'success': True, 'data': cached})
        
        from django.db import connection
        
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT 
                    COUNT(*) as total,
                    SUM(CASE WHEN status = 'RUNNING' THEN 1 ELSE 0 END) as running,
                    SUM(CASE WHEN status = 'COMPLETED' THEN 1 ELSE 0 END) as completed,
                    SUM(CASE WHEN status = 'PLANNED' THEN 1 ELSE 0 END) as planned,
                    AVG(CASE WHEN status = 'COMPLETED' THEN survival_rate ELSE NULL END) as avg_survival,
                    AVG(CASE WHEN status = 'COMPLETED' THEN fcr ELSE NULL END) as avg_fcr
                FROM fishery_productioncycle
            """)
            row = cursor.fetchone()
        
        data = {
            'total': row[0] or 0,
            'running': row[1] or 0,
            'completed': row[2] or 0,
            'planned': row[3] or 0,
            'avg_survival': float(row[4] or 0),
            'avg_fcr': float(row[5] or 0),
        }
        
        cache.set(cache_key, data, 3600)
        return JsonResponse({'success': True, 'data': data})


class RunningCyclesAPIView(LoginRequiredMixin, View):
    """API endpoint for currently running cycles"""
    
    def get(self, request):
        cycles = ProductionCycle.objects.filter(
            status='RUNNING'
        ).select_related('pond', 'species').only(
            'id', 'pond__name', 'species__name', 'stocking_date',
            'expected_harvest_date', 'initial_quantity', 'survival_rate', 'fcr'
        )[:10]
        
        data = [{
            'id': c.id,
            'pond__name': c.pond.name,
            'species__name': c.species.name,
            'stocking_date': c.stocking_date,
            'expected_harvest_date': c.expected_harvest_date,
            'initial_quantity': c.initial_quantity,
            'survival_rate': float(c.survival_rate),
            'fcr': float(c.fcr),
        } for c in cycles]
        
        return JsonResponse({'success': True, 'data': data})


class FeedRecordListAPIView(LoginRequiredMixin, View):
    """API endpoint for feed records"""
    
    def get(self, request):
        records = FeedRecord.objects.select_related(
            'cycle__pond', 'feed_type'
        ).only(
            'date', 'cycle__pond__name', 'feed_type__name', 'quantity_kg', 'cost'
        ).order_by('-date')[:50]
        
        data = [{
            'id': r.id,
            'date': r.date,
            'pond': r.cycle.pond.name,
            'feed_type': r.feed_type.name,
            'quantity_kg': float(r.quantity_kg),
            'cost': float(r.cost),
        } for r in records]
        
        return JsonResponse({'success': True, 'data': data})


class FeedTypeListAPIView(LoginRequiredMixin, View):
    """API endpoint for feed types"""
    
    def get(self, request):
        cache_key = 'feed_types_list'
        cached = cache.get(cache_key)
        if cached:
            return JsonResponse({'success': True, 'data': cached})
        
        feed_types = FeedType.objects.all().only(
            'id', 'name', 'brand', 'category', 'current_stock',
            'reorder_level', 'current_price'
        ).values()
        
        data = list(feed_types)
        cache.set(cache_key, data, 3600)
        
        return JsonResponse({'success': True, 'data': data})


class LowStockFeedAPIView(LoginRequiredMixin, View):
    """API endpoint for low stock feed alerts"""
    
    def get(self, request):
        low_stock = FeedType.objects.filter(
            current_stock__lte=F('reorder_level')
        ).only('id', 'name', 'current_stock', 'reorder_level').values()
        
        return JsonResponse({'success': True, 'data': list(low_stock)})


class RecentWaterQualityAPIView(LoginRequiredMixin, View):
    """API endpoint for recent water quality readings"""
    
    def get(self, request):
        pond_id = request.GET.get('pond_id')
        queryset = WaterQuality.objects.select_related('pond').only(
            'id', 'pond__name', 'reading_date', 'temperature',
            'ph_level', 'dissolved_oxygen', 'alert_generated'
        )
        
        if pond_id:
            queryset = queryset.filter(pond_id=pond_id)
        
        readings = queryset.order_by('-reading_date')[:20].values(
            'id', 'pond__name', 'reading_date', 'temperature',
            'ph_level', 'dissolved_oxygen', 'alert_generated'
        )
        
        return JsonResponse({'success': True, 'data': list(readings)})


class WaterAlertsAPIView(LoginRequiredMixin, View):
    """API endpoint for water quality alerts"""
    
    def get(self, request):
        alerts = WaterQuality.objects.filter(
            alert_generated=True
        ).select_related('pond').only(
            'id', 'pond__name', 'reading_date', 'alert_message'
        ).order_by('-reading_date')[:20].values(
            'id', 'pond__name', 'reading_date', 'alert_message'
        )
        
        return JsonResponse({'success': True, 'data': list(alerts)})


class DiseaseRecordListAPIView(LoginRequiredMixin, View):
    """API endpoint for disease records"""
    
    def get(self, request):
        diseases = DiseaseRecord.objects.filter(
            is_resolved=False
        ).select_related('cycle__pond').only(
            'id', 'cycle__pond__name', 'disease_name', 'severity',
            'detection_date', 'estimated_affected'
        ).order_by('-detection_date')[:20].values(
            'id', 'cycle__pond__name', 'disease_name', 'severity',
            'detection_date', 'estimated_affected'
        )
        
        return JsonResponse({'success': True, 'data': list(diseases)})


class MortalityRecordListAPIView(LoginRequiredMixin, View):
    """API endpoint for mortality records"""
    
    def get(self, request):
        mortalities = MortalityRecord.objects.select_related(
            'cycle__pond'
        ).only(
            'id', 'cycle__pond__name', 'date', 'quantity_dead', 'reason'
        ).order_by('-date')[:20].values(
            'id', 'cycle__pond__name', 'date', 'quantity_dead', 'reason'
        )
        
        return JsonResponse({'success': True, 'data': list(mortalities)})


class HarvestListAPIView(LoginRequiredMixin, View):
    """API endpoint for harvest records"""
    
    def get(self, request):
        harvests = Harvest.objects.select_related(
            'cycle__pond'
        ).only(
            'id', 'cycle__pond__name', 'harvest_date', 'quantity_kg', 'grade'
        ).order_by('-harvest_date')[:20].values(
            'id', 'cycle__pond__name', 'harvest_date', 'quantity_kg', 'grade'
        )
        
        return JsonResponse({'success': True, 'data': list(harvests)})


class RecentHarvestsAPIView(LoginRequiredMixin, View):
    """API endpoint for recent harvests"""
    
    def get(self, request):
        recent = Harvest.objects.filter(
            harvest_date__gte=timezone.now().date() - timedelta(days=7)
        ).select_related('cycle__pond').only(
            'id', 'cycle__pond__name', 'harvest_date', 'quantity_kg'
        ).order_by('-harvest_date').values(
            'id', 'cycle__pond__name', 'harvest_date', 'quantity_kg'
        )
        
        return JsonResponse({'success': True, 'data': list(recent)})


class FishSaleListAPIView(LoginRequiredMixin, View):
    """API endpoint for fish sales"""
    
    def get(self, request):
        sales = FishSale.objects.select_related(
            'harvest__cycle__pond', 'customer'
        ).only(
            'id', 'sale_number', 'harvest__cycle__pond__name', 'customer_name',
            'quantity_kg', 'price_per_kg', 'sale_date', 'payment_status'
        ).order_by('-sale_date')[:20]
        
        data = [{
            'id': s.id,
            'sale_number': s.sale_number,
            'harvest__cycle__pond__name': s.harvest.cycle.pond.name if s.harvest else None,
            'customer_name': s.customer_name,
            'quantity_kg': float(s.quantity_kg),
            'price_per_kg': float(s.price_per_kg),
            'total': float(s.quantity_kg * s.price_per_kg),
            'sale_date': s.sale_date,
            'payment_status': s.payment_status,
        } for s in sales]
        
        return JsonResponse({'success': True, 'data': data})


class TodaySalesAPIView(LoginRequiredMixin, View):
    """API endpoint for today's sales"""
    
    def get(self, request):
        today = timezone.now().date()
        sales = FishSale.objects.filter(sale_date=today).only('quantity_kg', 'price_per_kg')
        
        total_quantity = sales.aggregate(total=Sum('quantity_kg'))['total'] or 0
        total_revenue = sum(s.quantity_kg * s.price_per_kg for s in sales)
        
        data = {
            'quantity': float(total_quantity),
            'revenue': float(total_revenue),
            'count': sales.count(),
        }
        
        return JsonResponse({'success': True, 'data': data})


class MonthlySalesAPIView(LoginRequiredMixin, View):
    """API endpoint for monthly sales data"""
    
    def get(self, request):
        year = int(request.GET.get('year', timezone.now().year))
        cache_key = f'monthly_sales_{year}'
        cached = cache.get(cache_key)
        
        if cached:
            return JsonResponse({'success': True, 'data': cached})
        
        from django.db import connection
        
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT 
                    strftime('%m', sale_date) as month,
                    COALESCE(SUM(quantity_kg * price_per_kg), 0) as total
                FROM fishery_fishsale
                WHERE strftime('%Y', sale_date) = %s
                GROUP BY month
                ORDER BY month
            """, [str(year)])
            rows = cursor.fetchall()
        
        monthly_data = [0] * 12
        for row in rows:
            month_idx = int(row[0]) - 1
            if 0 <= month_idx < 12:
                monthly_data[month_idx] = float(row[1])
        
        cache.set(cache_key, monthly_data, 3600)
        
        return JsonResponse({'success': True, 'data': monthly_data})


# class ExpenseListAPIView(LoginRequiredMixin, View):
#     """API endpoint for expenses"""
    
#     def get(self, request):
#         expenses = Expense.objects.select_related(
#             'cycle__pond'
#         ).only(
#             'id', 'cycle__pond__name', 'expense_date', 'expense_type',
#             'description', 'amount'
#         ).order_by('-expense_date')[:20].values(
#             'id', 'cycle__pond__name', 'expense_date', 'expense_type',
#             'description', 'amount'
#         )
        
#         return JsonResponse({'success': True, 'data': list(expenses)})


class MonthlyExpensesAPIView(LoginRequiredMixin, View):
    """API endpoint for monthly expenses"""
    
    def get(self, request):
        year = int(request.GET.get('year', timezone.now().year))
        cache_key = f'monthly_expenses_{year}'
        cached = cache.get(cache_key)
        
        if cached:
            return JsonResponse({'success': True, 'data': cached})
        
        from django.db import connection
        
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT 
                    strftime('%m', expense_date) as month,
                    COALESCE(SUM(amount), 0) as total
                FROM fishery_expense
                WHERE strftime('%Y', expense_date) = %s
                GROUP BY month
                ORDER BY month
            """, [str(year)])
            rows = cursor.fetchall()
        
        monthly_data = [0] * 12
        for row in rows:
            month_idx = int(row[0]) - 1
            if 0 <= month_idx < 12:
                monthly_data[month_idx] = float(row[1])
        
        cache.set(cache_key, monthly_data, 3600)
        
        return JsonResponse({'success': True, 'data': monthly_data})


class FinancialChartDataAPIView(LoginRequiredMixin, View):
    """API endpoint for financial chart data"""
    
    def get(self, request):
        year = int(request.GET.get('year', timezone.now().year))
        cache_key = f'financial_chart_{year}'
        cached = cache.get(cache_key)
        
        if cached:
            return JsonResponse({'success': True, 'data': cached})
        
        from django.db import connection
        
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT 
                    strftime('%m', sale_date) as month,
                    COALESCE(SUM(quantity_kg * price_per_kg), 0) as revenue
                FROM fishery_fishsale
                WHERE strftime('%Y', sale_date) = %s
                GROUP BY month
                ORDER BY month
            """, [str(year)])
            revenue_rows = cursor.fetchall()
            
            cursor.execute("""
                SELECT 
                    strftime('%m', expense_date) as month,
                    COALESCE(SUM(amount), 0) as expense
                FROM fishery_expense
                WHERE strftime('%Y', expense_date) = %s
                GROUP BY month
                ORDER BY month
            """, [str(year)])
            expense_rows = cursor.fetchall()
        
        revenue_data = [0] * 12
        expense_data = [0] * 12
        
        for row in revenue_rows:
            month_idx = int(row[0]) - 1
            if 0 <= month_idx < 12:
                revenue_data[month_idx] = float(row[1])
        
        for row in expense_rows:
            month_idx = int(row[0]) - 1
            if 0 <= month_idx < 12:
                expense_data[month_idx] = float(row[1])
        
        months = [datetime(year, m, 1).strftime('%b') for m in range(1, 13)]
        
        data = {
            'months': months,
            'revenue': revenue_data,
            'expenses': expense_data,
        }
        
        cache.set(cache_key, data, 3600)
        
        return JsonResponse({'success': True, 'data': data})


# ==================== BULK OPERATIONS API VIEWS ====================

class BulkPondDeleteAPIView(LoginRequiredMixin, View):
    """Bulk delete ponds"""
    
    def post(self, request):
        try:
            data = json.loads(request.body)
            ids = data.get('ids', [])
            
            if not ids:
                return JsonResponse({'success': False, 'error': 'No IDs provided'})
            
            count, _ = Pond.objects.filter(id__in=ids).delete()
            
            # Clear cache
            cache.delete(DASHBOARD_STATS_CACHE_KEY)
            cache.delete(POND_LIST_CACHE_KEY)
            
            return JsonResponse({'success': True, 'message': f'Deleted {count} ponds'})
            
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})


class BulkCycleDeleteAPIView(LoginRequiredMixin, View):
    """Bulk delete production cycles"""
    
    def post(self, request):
        try:
            data = json.loads(request.body)
            ids = data.get('ids', [])
            
            if not ids:
                return JsonResponse({'success': False, 'error': 'No IDs provided'})
            
            count, _ = ProductionCycle.objects.filter(id__in=ids).delete()
            
            # Clear cache
            cache.delete(DASHBOARD_STATS_CACHE_KEY)
            
            return JsonResponse({'success': True, 'message': f'Deleted {count} cycles'})
            
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})


class BulkSaleDeleteAPIView(LoginRequiredMixin, View):
    """Bulk delete sales"""
    
    def post(self, request):
        try:
            data = json.loads(request.body)
            ids = data.get('ids', [])
            
            if not ids:
                return JsonResponse({'success': False, 'error': 'No IDs provided'})
            
            count, _ = FishSale.objects.filter(id__in=ids).delete()
            
            # Clear cache
            cache.delete(DASHBOARD_STATS_CACHE_KEY)
            
            return JsonResponse({'success': True, 'message': f'Deleted {count} sales'})
            
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})


# ==================== POND VIEWS ====================

class PondListView(LoginRequiredMixin, ListView):
    """List all ponds - optimized with select_related and only()"""
    model = Pond
    template_name = 'fishery/pond/list.html'
    context_object_name = 'ponds'
    paginate_by = 20
    
    def get_queryset(self):
        # Check cache
        cache_key = f'pond_list_{self.request.GET.urlencode()}'
        cached = cache.get(cache_key)
        if cached:
            return cached
        
        queryset = Pond.objects.select_related('farm').only(
            'id', 'pond_id', 'name', 'farm__name', 'pond_type', 'size_in_acres',
            'status', 'is_active', 'location'
        )
        
        # Apply filters
        farm_id = self.request.GET.get('farm')
        if farm_id:
            queryset = queryset.filter(farm_id=farm_id)
        
        status = self.request.GET.get('status')
        if status:
            queryset = queryset.filter(status=status)
        
        pond_type = self.request.GET.get('type')
        if pond_type:
            queryset = queryset.filter(pond_type=pond_type)
        
        search = self.request.GET.get('search')
        if search:
            queryset = queryset.filter(
                Q(name__icontains=search) |
                Q(pond_id__icontains=search)
            )
        
        # Cache for 5 minutes
        cache.set(cache_key, queryset, 300)
        
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Cache farms list
        farms = cache.get('farms_list')
        if not farms:
            farms = Farm.objects.only('id', 'name').all()
            cache.set('farms_list', farms, 3600)
        
        context['farms'] = farms
        context['current_farm'] = self.request.GET.get('farm', '')
        context['current_status'] = self.request.GET.get('status', '')
        context['current_type'] = self.request.GET.get('type', '')
        context['search_query'] = self.request.GET.get('search', '')
        
        return context


class PondDetailView(LoginRequiredMixin, DetailView):
    """View pond details - optimized with prefetch_related"""
    model = Pond
    template_name = 'fishery/pond/detail.html'
    context_object_name = 'pond'
    
    def get_queryset(self):
        return Pond.objects.select_related('farm').prefetch_related(
            Prefetch('production_cycles', queryset=ProductionCycle.objects.select_related('species').only(
                'id', 'species__name', 'stocking_date', 'status'
            )[:5]),
            Prefetch('water_quality', queryset=WaterQuality.objects.only(
                'reading_date', 'temperature', 'ph_level', 'dissolved_oxygen', 'alert_generated'
            ).order_by('-reading_date')[:10])
        )


class PondCreateView(LoginRequiredMixin, CreateView):
    """Create new pond"""
    model = Pond
    form_class = PondForm
    template_name = 'fishery/pond/form.html'
    success_url = reverse_lazy('fishery:pond_list')
    
    def form_valid(self, form):
        form.instance.created_by = self.request.user
        response = super().form_valid(form)
        messages.success(self.request, f'Pond {form.instance.name} added successfully!')
        
        # Clear cache
        cache.delete(DASHBOARD_STATS_CACHE_KEY)
        cache.delete(POND_LIST_CACHE_KEY)
        
        return response


class PondUpdateView(LoginRequiredMixin, UpdateView):
    """Update pond"""
    model = Pond
    form_class = PondForm
    template_name = 'fishery/pond/form.html'
    success_url = reverse_lazy('fishery:pond_list')
    
    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, f'Pond {form.instance.name} updated successfully!')
        
        # Clear cache
        cache.delete(DASHBOARD_STATS_CACHE_KEY)
        cache.delete(POND_LIST_CACHE_KEY)
        
        return response


class PondDeleteView(LoginRequiredMixin, DeleteView):
    """Delete pond"""
    model = Pond
    template_name = 'fishery/pond/delete.html'
    success_url = reverse_lazy('fishery:pond_list')
    
    def delete(self, request, *args, **kwargs):
        pond = self.get_object()
        messages.success(request, f'Pond {pond.name} deleted successfully!')
        
        # Clear cache
        cache.delete(DASHBOARD_STATS_CACHE_KEY)
        cache.delete(POND_LIST_CACHE_KEY)
        
        return super().delete(request, *args, **kwargs)


# ==================== FISH SPECIES VIEWS ====================

class FishSpeciesListView(LoginRequiredMixin, ListView):
    """List all fish species - optimized"""
    model = FishSpecies
    template_name = 'fishery/species/list.html'
    context_object_name = 'species_list'
    paginate_by = 20
    
    def get_queryset(self):
        cache_key = f'species_list_{self.request.GET.urlencode()}'
        cached = cache.get(cache_key)
        if cached:
            return cached
        
        queryset = FishSpecies.objects.only(
            'id', 'name', 'scientific_name', 'category', 'water_type',
            'average_growth_days', 'market_price'
        )
        
        category = self.request.GET.get('category')
        if category:
            queryset = queryset.filter(category=category)
        
        water_type = self.request.GET.get('water_type')
        if water_type:
            queryset = queryset.filter(water_type=water_type)
        
        search = self.request.GET.get('search')
        if search:
            queryset = queryset.filter(
                Q(name__icontains=search) |
                Q(scientific_name__icontains=search)
            )
        
        cache.set(cache_key, queryset, 3600)
        return queryset


class FishSpeciesCreateView(LoginRequiredMixin, CreateView):
    """Create new fish species"""
    model = FishSpecies
    form_class = FishSpeciesForm
    template_name = 'fishery/species/form.html'
    success_url = reverse_lazy('fishery:species_list')
    
    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, f'Fish species {form.instance.name} added successfully!')
        
        # Clear cache
        cache.delete(SPECIES_LIST_CACHE_KEY)
        
        return response


class FishSpeciesUpdateView(LoginRequiredMixin, UpdateView):
    """Update fish species"""
    model = FishSpecies
    form_class = FishSpeciesForm
    template_name = 'fishery/species/form.html'
    success_url = reverse_lazy('fishery:species_list')


class FishSpeciesDeleteView(LoginRequiredMixin, DeleteView):
    """Delete fish species"""
    model = FishSpecies
    template_name = 'fishery/species/delete.html'
    success_url = reverse_lazy('fishery:species_list')


# ==================== PRODUCTION CYCLE VIEWS ====================

class ProductionCycleListView(LoginRequiredMixin, ListView):
    """List all production cycles - optimized"""
    model = ProductionCycle
    template_name = 'fishery/cycle/list.html'
    context_object_name = 'cycles'
    paginate_by = 20
    
    def get_queryset(self):
        queryset = ProductionCycle.objects.select_related('pond', 'species').only(
            'id', 'cycle_id', 'pond__name', 'species__name', 'stocking_date',
            'expected_harvest_date', 'status', 'survival_rate', 'fcr'
        )
        
        # Apply filters
        pond_id = self.request.GET.get('pond')
        if pond_id:
            queryset = queryset.filter(pond_id=pond_id)
        
        species_id = self.request.GET.get('species')
        if species_id:
            queryset = queryset.filter(species_id=species_id)
        
        status = self.request.GET.get('status')
        if status:
            queryset = queryset.filter(status=status)
        
        date_from = self.request.GET.get('date_from')
        if date_from:
            queryset = queryset.filter(stocking_date__gte=date_from)
        
        date_to = self.request.GET.get('date_to')
        if date_to:
            queryset = queryset.filter(stocking_date__lte=date_to)
        
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Cache filter options
        ponds = cache.get('ponds_for_filter')
        if not ponds:
            ponds = Pond.objects.filter(is_active=True).only('id', 'name')
            cache.set('ponds_for_filter', ponds, 3600)
        
        species = cache.get('species_for_filter')
        if not species:
            species = FishSpecies.objects.all().only('id', 'name')
            cache.set('species_for_filter', species, 3600)
        
        context['ponds'] = ponds
        context['species'] = species
        context['current_pond'] = self.request.GET.get('pond', '')
        context['current_species'] = self.request.GET.get('species', '')
        context['current_status'] = self.request.GET.get('status', '')
        
        return context


class ProductionCycleDetailView(LoginRequiredMixin, DetailView):
    """View production cycle details - optimized with prefetch_related"""
    model = ProductionCycle
    template_name = 'fishery/cycle/detail.html'
    context_object_name = 'cycle'
    
    def get_queryset(self):
        return ProductionCycle.objects.select_related('pond', 'species', 'batch').prefetch_related(
            Prefetch('feeds', queryset=FeedRecord.objects.select_related('feed_type').only(
                'date', 'feed_type__name', 'quantity_kg', 'cost'
            ).order_by('-date')[:10]),
            Prefetch('mortalities', queryset=MortalityRecord.objects.only(
                'date', 'quantity_dead', 'reason'
            ).order_by('-date')[:10]),
            Prefetch('harvests', queryset=Harvest.objects.only(
                'harvest_date', 'quantity_kg', 'piece_count', 'grade'
            ).order_by('-harvest_date')),
            Prefetch('expenses', queryset=Expense.objects.only(
                'expense_date', 'expense_type', 'description', 'amount'
            ).order_by('-expense_date')[:10]),
            Prefetch('diseases', queryset=DiseaseRecord.objects.only(
                'disease_name', 'detection_date', 'severity', 'is_resolved'
            ).order_by('-detection_date'))
        )


class ProductionCycleCreateView(LoginRequiredMixin, CreateView):
    """Create new production cycle"""
    model = ProductionCycle
    form_class = ProductionCycleForm
    template_name = 'fishery/cycle/form.html'
    success_url = reverse_lazy('fishery:cycle_list')
    
    def form_valid(self, form):
        form.instance.created_by = self.request.user
        response = super().form_valid(form)
        
        # Update pond status
        pond = form.instance.pond
        pond.status = 'STOCKED'
        pond.save()
        
        messages.success(self.request, f'Production cycle for {form.instance.pond.name} created successfully!')
        
        # Clear cache
        cache.delete(DASHBOARD_STATS_CACHE_KEY)
        
        return response


class ProductionCycleUpdateView(LoginRequiredMixin, UpdateView):
    """Update production cycle"""
    model = ProductionCycle
    form_class = ProductionCycleForm
    template_name = 'fishery/cycle/form.html'
    success_url = reverse_lazy('fishery:cycle_list')


class ProductionCycleCompleteView(LoginRequiredMixin, UpdateView):
    """Mark production cycle as completed"""
    model = ProductionCycle
    fields = ['actual_harvest_date', 'status']
    template_name = 'fishery/cycle/complete.html'
    success_url = reverse_lazy('fishery:cycle_list')
    
    def form_valid(self, form):
        form.instance.status = 'COMPLETED'
        if not form.instance.actual_harvest_date:
            form.instance.actual_harvest_date = timezone.now().date()
        
        # Update pond status
        pond = form.instance.pond
        pond.status = 'DRYING'
        pond.save()
        
        messages.success(self.request, f'Cycle for {form.instance.pond.name} marked as completed!')
        
        # Clear cache
        cache.delete(DASHBOARD_STATS_CACHE_KEY)
        
        return super().form_valid(form)


class ProductionCycleDeleteView(LoginRequiredMixin, DeleteView):
    """Delete production cycle"""
    model = ProductionCycle
    template_name = 'fishery/cycle/delete.html'
    success_url = reverse_lazy('fishery:cycle_list')
    
    def delete(self, request, *args, **kwargs):
        cycle = self.get_object()
        pond = cycle.pond
        pond.status = 'PREPARING'
        pond.save()
        messages.success(request, f'Production cycle deleted successfully!')
        
        # Clear cache
        cache.delete(DASHBOARD_STATS_CACHE_KEY)
        
        return super().delete(request, *args, **kwargs)


# ==================== FEED RECORD VIEWS ====================

class FeedRecordListView(LoginRequiredMixin, ListView):
    """List all feed records"""
    model = FeedRecord
    template_name = 'fishery/feed/record_list.html'
    context_object_name = 'records'
    paginate_by = 30
    
    def get_queryset(self):
        return FeedRecord.objects.select_related('cycle__pond', 'feed_type').only(
            'date', 'feed_time', 'cycle__pond__name', 'feed_type__name',
            'quantity_kg', 'cost', 'feed_consumption_rate'
        ).order_by('-date')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        today = timezone.now().date()
        
        # Aggregate today's totals
        today_stats = FeedRecord.objects.filter(date=today).aggregate(
            total_qty=Sum('quantity_kg'),
            total_cost=Sum('cost')
        )
        context['today_total'] = today_stats['total_qty'] or 0
        context['today_cost'] = today_stats['total_cost'] or 0
        
        # Monthly total
        context['monthly_total'] = FeedRecord.objects.filter(
            date__gte=today.replace(day=1)
        ).aggregate(total=Sum('quantity_kg'))['total'] or 0
        
        return context


class FeedRecordCreateView(LoginRequiredMixin, CreateView):
    """Create new feed record"""
    model = FeedRecord
    form_class = FeedRecordForm
    template_name = 'fishery/feed/record_form.html'
    success_url = reverse_lazy('fishery:feed_record_list')
    
    def form_valid(self, form):
        form.instance.recorded_by = self.request.user
        response = super().form_valid(form)
        
        # Update feed stock
        feed_type = form.instance.feed_type
        feed_type.current_stock -= form.instance.quantity_kg
        feed_type.save()
        
        messages.success(self.request, 'Feed record added successfully!')
        
        # Clear cache
        cache.delete(DASHBOARD_STATS_CACHE_KEY)
        
        return response


class FeedRecordUpdateView(LoginRequiredMixin, UpdateView):
    """Update feed record"""
    model = FeedRecord
    form_class = FeedRecordForm
    template_name = 'fishery/feed/record_form.html'
    success_url = reverse_lazy('fishery:feed_record_list')


class FeedRecordDeleteView(LoginRequiredMixin, DeleteView):
    """Delete feed record"""
    model = FeedRecord
    template_name = 'fishery/feed/delete.html'
    success_url = reverse_lazy('fishery:feed_record_list')


# ==================== FEED TYPE VIEWS ====================

class FeedTypeListView(LoginRequiredMixin, ListView):
    """List all feed types"""
    model = FeedType
    template_name = 'fishery/feed/type_list.html'
    context_object_name = 'feed_types'
    paginate_by = 20
    
    def get_queryset(self):
        return FeedType.objects.only(
            'id', 'name', 'brand', 'category', 'protein_percentage',
            'current_stock', 'reorder_level', 'current_price'
        )


class FeedTypeCreateView(LoginRequiredMixin, CreateView):
    """Create new feed type"""
    model = FeedType
    form_class = FeedTypeForm
    template_name = 'fishery/feed/type_form.html'
    success_url = reverse_lazy('fishery:feed_type_list')


class FeedTypeUpdateView(LoginRequiredMixin, UpdateView):
    """Update feed type"""
    model = FeedType
    form_class = FeedTypeForm
    template_name = 'fishery/feed/type_form.html'
    success_url = reverse_lazy('fishery:feed_type_list')


class FeedTypeDeleteView(LoginRequiredMixin, DeleteView):
    """Delete feed type"""
    model = FeedType
    template_name = 'fishery/feed/delete.html'
    success_url = reverse_lazy('fishery:feed_type_list')


# ==================== FEED PURCHASE VIEWS ====================

class FeedPurchaseListView(LoginRequiredMixin, ListView):
    """List all feed purchases"""
    model = FeedPurchase
    template_name = 'fishery/feed/purchase_list.html'
    context_object_name = 'purchases'
    paginate_by = 30
    
    def get_queryset(self):
        return FeedPurchase.objects.select_related('feed_type').only(
            'purchase_date', 'feed_type__name', 'quantity_kg',
            'price_per_kg', 'total_cost', 'batch_number', 'expiry_date'
        ).order_by('-purchase_date')


class FeedPurchaseCreateView(LoginRequiredMixin, CreateView):
    """Create new feed purchase"""
    model = FeedPurchase
    form_class = FeedPurchaseForm
    template_name = 'fishery/feed/purchase_form.html'
    success_url = reverse_lazy('fishery:feed_purchase_list')
    
    def form_valid(self, form):
        form.instance.created_by = self.request.user
        messages.success(self.request, 'Feed purchase recorded successfully!')
        
        # Clear cache
        cache.delete(DASHBOARD_STATS_CACHE_KEY)
        
        return super().form_valid(form)


# ==================== WATER QUALITY VIEWS ====================

class WaterQualityListView(LoginRequiredMixin, ListView):
    """List all water quality readings"""
    model = WaterQuality
    template_name = 'fishery/water/list.html'
    context_object_name = 'readings'
    paginate_by = 30
    
    def get_queryset(self):
        queryset = WaterQuality.objects.select_related('pond', 'recorded_by').only(
            'reading_date', 'pond__name', 'temperature', 'ph_level',
            'dissolved_oxygen', 'alert_generated', 'recorded_by__username'
        ).order_by('-reading_date')
        
        pond_id = self.request.GET.get('pond')
        if pond_id:
            queryset = queryset.filter(pond_id=pond_id)
        
        alert_only = self.request.GET.get('alert_only')
        if alert_only:
            queryset = queryset.filter(alert_generated=True)
        
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['ponds'] = Pond.objects.filter(is_active=True).only('id', 'name')
        context['current_pond'] = self.request.GET.get('pond', '')
        context['alert_only'] = self.request.GET.get('alert_only', False)
        return context


class WaterQualityCreateView(LoginRequiredMixin, CreateView):
    """Create new water quality reading"""
    model = WaterQuality
    form_class = WaterQualityForm
    template_name = 'fishery/water/form.html'
    success_url = reverse_lazy('fishery:water_list')
    
    def form_valid(self, form):
        form.instance.recorded_by = self.request.user
        response = super().form_valid(form)
        messages.success(self.request, 'Water quality reading recorded successfully!')
        
        # Clear cache
        cache.delete(DASHBOARD_STATS_CACHE_KEY)
        
        return response


class WaterQualityUpdateView(LoginRequiredMixin, UpdateView):
    """Update water quality reading"""
    model = WaterQuality
    form_class = WaterQualityForm
    template_name = 'fishery/water/form.html'
    success_url = reverse_lazy('fishery:water_list')


class WaterQualityDeleteView(LoginRequiredMixin, DeleteView):
    """Delete water quality reading"""
    model = WaterQuality
    template_name = 'fishery/water/delete.html'
    success_url = reverse_lazy('fishery:water_list')


# ==================== DISEASE RECORD VIEWS ====================

class DiseaseRecordListView(LoginRequiredMixin, ListView):
    """List all disease records"""
    model = DiseaseRecord
    template_name = 'fishery/health/disease_list.html'
    context_object_name = 'diseases'
    paginate_by = 30
    
    def get_queryset(self):
        return DiseaseRecord.objects.select_related('cycle__pond', 'diagnosed_by').only(
            'detection_date', 'cycle__pond__name', 'disease_name',
            'severity', 'estimated_affected', 'is_resolved', 'diagnosed_by__username'
        ).order_by('-detection_date')


class DiseaseRecordCreateView(LoginRequiredMixin, CreateView):
    """Create new disease record"""
    model = DiseaseRecord
    form_class = DiseaseRecordForm
    template_name = 'fishery/health/disease_form.html'
    success_url = reverse_lazy('fishery:disease_list')
    
    def form_valid(self, form):
        form.instance.diagnosed_by = self.request.user
        messages.success(self.request, 'Disease record added successfully!')
        
        # Clear cache
        cache.delete(DASHBOARD_STATS_CACHE_KEY)
        
        return super().form_valid(form)


class DiseaseRecordUpdateView(LoginRequiredMixin, UpdateView):
    """Update disease record"""
    model = DiseaseRecord
    form_class = DiseaseRecordForm
    template_name = 'fishery/health/disease_form.html'
    success_url = reverse_lazy('fishery:disease_list')


class DiseaseRecordDeleteView(LoginRequiredMixin, DeleteView):
    """Delete disease record"""
    model = DiseaseRecord
    template_name = 'fishery/health/delete.html'
    success_url = reverse_lazy('fishery:disease_list')


# ==================== MORTALITY RECORD VIEWS ====================

class MortalityRecordListView(LoginRequiredMixin, ListView):
    """List all mortality records"""
    model = MortalityRecord
    template_name = 'fishery/health/mortality_list.html'
    context_object_name = 'mortalities'
    paginate_by = 30
    
    def get_queryset(self):
        return MortalityRecord.objects.select_related('cycle__pond', 'disease').only(
            'date', 'cycle__pond__name', 'quantity_dead', 'reason', 'disease__disease_name'
        ).order_by('-date')


class MortalityRecordCreateView(LoginRequiredMixin, CreateView):
    """Create new mortality record"""
    model = MortalityRecord
    form_class = MortalityRecordForm
    template_name = 'fishery/health/mortality_form.html'
    success_url = reverse_lazy('fishery:mortality_list')
    
    def form_valid(self, form):
        form.instance.recorded_by = self.request.user
        messages.success(self.request, 'Mortality record added successfully!')
        
        # Clear cache
        cache.delete(DASHBOARD_STATS_CACHE_KEY)
        
        return super().form_valid(form)


class MortalityRecordUpdateView(LoginRequiredMixin, UpdateView):
    """Update mortality record"""
    model = MortalityRecord
    form_class = MortalityRecordForm
    template_name = 'fishery/health/mortality_form.html'
    success_url = reverse_lazy('fishery:mortality_list')


class MortalityRecordDeleteView(LoginRequiredMixin, DeleteView):
    """Delete mortality record"""
    model = MortalityRecord
    template_name = 'fishery/health/delete.html'
    success_url = reverse_lazy('fishery:mortality_list')


# ==================== HARVEST VIEWS ====================

class HarvestListView(LoginRequiredMixin, ListView):
    """List all harvests"""
    model = Harvest
    template_name = 'fishery/harvest/list.html'
    context_object_name = 'harvests'
    paginate_by = 30
    
    def get_queryset(self):
        return Harvest.objects.select_related('cycle__pond', 'harvested_by').only(
            'harvest_date', 'cycle__pond__name', 'quantity_kg',
            'piece_count', 'grade', 'harvested_by__username'
        ).order_by('-harvest_date')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        today = timezone.now().date()
        
        # Aggregate today's harvest
        context['today_total'] = Harvest.objects.filter(
            harvest_date=today
        ).aggregate(total=Sum('quantity_kg'))['total'] or 0
        
        # Monthly total
        context['monthly_total'] = Harvest.objects.filter(
            harvest_date__gte=today.replace(day=1)
        ).aggregate(total=Sum('quantity_kg'))['total'] or 0
        
        return context


class HarvestCreateView(LoginRequiredMixin, CreateView):
    """Create new harvest record"""
    model = Harvest
    form_class = HarvestForm
    template_name = 'fishery/harvest/form.html'
    success_url = reverse_lazy('fishery:harvest_list')
    
    def form_valid(self, form):
        form.instance.harvested_by = self.request.user
        response = super().form_valid(form)
        messages.success(self.request, 'Harvest recorded successfully!')
        
        # Clear cache
        cache.delete(DASHBOARD_STATS_CACHE_KEY)
        
        return response


class HarvestUpdateView(LoginRequiredMixin, UpdateView):
    """Update harvest record"""
    model = Harvest
    form_class = HarvestForm
    template_name = 'fishery/harvest/form.html'
    success_url = reverse_lazy('fishery:harvest_list')


class HarvestDeleteView(LoginRequiredMixin, DeleteView):
    """Delete harvest record"""
    model = Harvest
    template_name = 'fishery/harvest/delete.html'
    success_url = reverse_lazy('fishery:harvest_list')


# ==================== CUSTOMER VIEWS ====================

class CustomerListView(LoginRequiredMixin, ListView):
    """List all customers"""
    model = Customer
    template_name = 'fishery/sales/customer_list.html'
    context_object_name = 'customers'
    paginate_by = 30
    
    def get_queryset(self):
        return Customer.objects.only(
            'id', 'customer_id', 'name', 'customer_type',
            'phone', 'city', 'is_active', 'current_balance'
        ).order_by('name')


class CustomerCreateView(LoginRequiredMixin, CreateView):
    """Create new customer"""
    model = Customer
    form_class = CustomerForm
    template_name = 'fishery/sales/customer_form.html'
    success_url = reverse_lazy('fishery:customer_list')


class CustomerUpdateView(LoginRequiredMixin, UpdateView):
    """Update customer"""
    model = Customer
    form_class = CustomerForm
    template_name = 'fishery/sales/customer_form.html'
    success_url = reverse_lazy('fishery:customer_list')


class CustomerDeleteView(LoginRequiredMixin, DeleteView):
    """Delete customer"""
    model = Customer
    template_name = 'fishery/sales/delete.html'
    success_url = reverse_lazy('fishery:customer_list')


# ==================== FISH SALE VIEWS ====================

class FishSaleListView(LoginRequiredMixin, ListView):
    """List all fish sales"""
    model = FishSale
    template_name = 'fishery/sales/list.html'
    context_object_name = 'sales'
    paginate_by = 30
    
    def get_queryset(self):
        return FishSale.objects.select_related(
            'harvest__cycle__pond', 'harvest__cycle__species', 'customer'
        ).only(
            'sale_number', 'sale_date', 'customer_name', 'customer__name',
            'harvest__cycle__pond__name', 'harvest__cycle__species__name',
            'quantity_kg', 'price_per_kg', 'payment_status'
        ).order_by('-sale_date')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        today = timezone.now().date()
        first_day_month = today.replace(day=1)
        
        # Today's sales
        today_sales = FishSale.objects.filter(sale_date=today)
        context['today_quantity'] = today_sales.aggregate(total=Sum('quantity_kg'))['total'] or 0
        context['today_revenue'] = sum(s.quantity_kg * s.price_per_kg for s in today_sales)
        
        # Monthly sales
        monthly_sales = FishSale.objects.filter(sale_date__gte=first_day_month)
        context['monthly_revenue'] = sum(s.quantity_kg * s.price_per_kg for s in monthly_sales)
        
        return context


class FishSaleCreateView(LoginRequiredMixin, CreateView):
    """Create new fish sale"""
    model = FishSale
    form_class = FishSaleForm
    template_name = 'fishery/sales/form.html'
    success_url = reverse_lazy('fishery:sale_list')
    
    def form_valid(self, form):
        form.instance.created_by = self.request.user
        response = super().form_valid(form)
        messages.success(self.request, f'Sale recorded successfully! Total: ৳{form.instance.total_amount}')
        
        # Clear cache
        cache.delete(DASHBOARD_STATS_CACHE_KEY)
        
        return response


class FishSaleUpdateView(LoginRequiredMixin, UpdateView):
    """Update fish sale"""
    model = FishSale
    form_class = FishSaleForm
    template_name = 'fishery/sales/form.html'
    success_url = reverse_lazy('fishery:sale_list')


class FishSaleDeleteView(LoginRequiredMixin, DeleteView):
    """Delete fish sale"""
    model = FishSale
    template_name = 'fishery/sales/delete.html'
    success_url = reverse_lazy('fishery:sale_list')


# ==================== EXPENSE VIEWS ====================

class ExpenseListView(LoginRequiredMixin, ListView):
    """List all expenses"""
    model = Expense
    template_name = 'fishery/expense/list.html'
    context_object_name = 'expenses'
    paginate_by = 30
    
    def get_queryset(self):
        # Optimized queryset with select_related and only()
        return Expense.objects.select_related(
            'cycle__pond', 'feed_purchase', 'created_by'
        ).only(
            'id', 'expense_date', 'cycle__pond__name', 'expense_type',
            'description', 'amount', 'payment_method', 'paid_to',
            'receipt_number', 'notes', 'created_by__username',
            'feed_purchase__id', 'feed_purchase__feed_type__name'
        ).order_by('-expense_date')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        today = timezone.now().date()
        first_day_month = today.replace(day=1)
        
        # Monthly total
        context['monthly_total'] = Expense.objects.filter(
            expense_date__gte=first_day_month
        ).aggregate(total=Sum('amount'))['total'] or 0
        
        # Statistics by expense type
        expense_stats = Expense.objects.values('expense_type').annotate(
            total=Sum('amount'),
            count=Count('id')
        ).order_by('-total')
        
        context['expense_stats'] = expense_stats
        context['total_expenses'] = Expense.objects.count()
        context['total_amount'] = Expense.objects.aggregate(
            total=Sum('amount')
        )['total'] or 0
        
        # High value expenses ( > 50,000 )
        context['high_value_count'] = Expense.objects.filter(
            amount__gt=50000
        ).count()
        context['high_value_total'] = Expense.objects.filter(
            amount__gt=50000
        ).aggregate(total=Sum('amount'))['total'] or 0
        
        # This month's expenses by type for charts
        monthly_by_type = Expense.objects.filter(
            expense_date__gte=first_day_month
        ).values('expense_type').annotate(
            total=Sum('amount')
        ).order_by('-total')
        
        context['monthly_by_type'] = monthly_by_type
        
        # Recent feed purchases (last 5)
        context['recent_feed_purchases'] = FeedPurchase.objects.select_related(
            'feed_type'
        ).order_by('-purchase_date')[:5]
        
        return context


class ExpenseCreateView(LoginRequiredMixin, CreateView):
    """Create new expense"""
    model = Expense
    form_class = ExpenseForm
    template_name = 'fishery/expense/form.html'
    success_url = reverse_lazy('fishery:expense_list')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['action'] = 'add'
        context['title'] = 'Add New Expense'
        context['submit_text'] = 'Add Expense'
        
        # Pass cycles for the form
        context['cycles'] = ProductionCycle.objects.filter(
            status='RUNNING'
        ).select_related('pond', 'species')
        
        # Pass feed purchases for the form
        context['feed_purchases'] = FeedPurchase.objects.select_related(
            'feed_type'
        ).order_by('-purchase_date')[:20]
        
        return context
    
    def form_valid(self, form):
        # Set the created_by user
        form.instance.created_by = self.request.user
        
        # Handle VAT if checkbox was checked (if you're using the VAT version)
        if 'apply_vat' in form.cleaned_data and form.cleaned_data['apply_vat']:
            original_amount = form.instance.amount
            form.instance.amount = original_amount * Decimal('1.15')
            if form.instance.notes:
                form.instance.notes += f"\n(15% VAT applied. Original: ৳{original_amount})"
            else:
                form.instance.notes = f"15% VAT applied. Original amount: ৳{original_amount}"
        
        response = super().form_valid(form)
        
        # Success message
        messages.success(
            self.request, 
            f'✅ Expense added successfully! ৳{form.instance.amount:,.2f} for {form.instance.description}'
        )
        
        # Clear cache
        cache.delete(DASHBOARD_STATS_CACHE_KEY)
        cache.delete('expense_list_stats')
        
        return response
    
    def get_success_url(self):
        """Return to the expense list with a success message"""
        if '_addanother' in self.request.POST:
            return reverse_lazy('fishery:expense_add')
        return reverse_lazy('fishery:expense_list')


class ExpenseUpdateView(LoginRequiredMixin, UpdateView):
    """Update expense"""
    model = Expense
    form_class = ExpenseForm
    template_name = 'fishery/expense/form.html'
    success_url = reverse_lazy('fishery:expense_list')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['action'] = 'edit'
        context['title'] = f'Edit Expense: {self.object.description}'
        context['submit_text'] = 'Update Expense'
        
        # Pass cycles for the form
        context['cycles'] = ProductionCycle.objects.filter(
            status='RUNNING'
        ).select_related('pond', 'species')
        
        # Pass feed purchases for the form
        context['feed_purchases'] = FeedPurchase.objects.select_related(
            'feed_type'
        ).order_by('-purchase_date')[:20]
        
        # Check if expense is linked to feed purchase
        if self.object.feed_purchase:
            context['linked_feed'] = self.object.feed_purchase
        
        return context
    
    def form_valid(self, form):
        response = super().form_valid(form)
        
        # Success message
        messages.success(
            self.request, 
            f'✅ Expense updated successfully! ৳{form.instance.amount:,.2f}'
        )
        
        # Clear cache
        cache.delete(DASHBOARD_STATS_CACHE_KEY)
        cache.delete('expense_list_stats')
        
        return response
    
    def get_success_url(self):
        """Return to the expense list"""
        return reverse_lazy('fishery:expense_list')


class ExpenseDeleteView(LoginRequiredMixin, DeleteView):
    """Delete expense"""
    model = Expense
    template_name = 'fishery/expense/delete.html'
    success_url = reverse_lazy('fishery:expense_list')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        expense = self.get_object()
        
        # Calculate additional context for delete template
        context['cycle_total'] = expense.cycle.total_expense if expense.cycle else 0
        context['monthly_total'] = Expense.objects.filter(
            expense_date__year=expense.expense_date.year,
            expense_date__month=expense.expense_date.month
        ).aggregate(total=Sum('amount'))['total'] or 0
        
        context['is_high_value'] = expense.amount > 50000
        context['days_ago'] = (timezone.now().date() - expense.expense_date).days
        
        # Check if linked to feed purchase
        if expense.feed_purchase:
            context['linked_feed'] = expense.feed_purchase
        
        return context
    
    def delete(self, request, *args, **kwargs):
        expense = self.get_object()
        amount = expense.amount
        description = expense.description
        
        response = super().delete(request, *args, **kwargs)
        
        # Success message
        messages.warning(
            request, 
            f'🗑️ Expense deleted: ৳{amount:,.2f} for {description}'
        )
        
        # Clear cache
        cache.delete(DASHBOARD_STATS_CACHE_KEY)
        cache.delete('expense_list_stats')
        
        return response


# ==================== EXPENSE API VIEWS ====================

class ExpenseListAPIView(LoginRequiredMixin, View):
    """API endpoint for expenses"""
    
    def get(self, request):
        expenses = Expense.objects.select_related(
            'cycle__pond'
        ).order_by('-expense_date')[:50].values(
            'id', 'expense_date', 'cycle__pond__name', 'expense_type',
            'description', 'amount', 'payment_method'
        )
        
        return JsonResponse({
            'success': True,
            'data': list(expenses)
        })


class ExpenseStatsAPIView(LoginRequiredMixin, View):
    """API endpoint for expense statistics"""
    
    def get(self, request):
        today = timezone.now().date()
        this_month = today.replace(day=1)
        
        # Total expenses
        total = Expense.objects.aggregate(total=Sum('amount'))['total'] or 0
        
        # This month
        monthly = Expense.objects.filter(
            expense_date__gte=this_month
        ).aggregate(total=Sum('amount'))['total'] or 0
        
        # By type
        by_type = Expense.objects.values('expense_type').annotate(
            total=Sum('amount')
        ).order_by('-total')
        
        # Format by_type with display names
        type_data = []
        for item in by_type:
            type_data.append({
                'type': item['expense_type'],
                'type_display': dict(Expense.EXPENSE_TYPES).get(item['expense_type'], item['expense_type']),
                'total': float(item['total'])
            })
        
        return JsonResponse({
            'success': True,
            'data': {
                'total': float(total),
                'monthly': float(monthly),
                'by_type': type_data
            }
        })


class ExpenseByCycleAPIView(LoginRequiredMixin, View):
    """API endpoint for expenses by cycle"""
    
    def get(self, request, cycle_id):
        expenses = Expense.objects.filter(
            cycle_id=cycle_id
        ).order_by('-expense_date').values(
            'id', 'expense_date', 'expense_type', 'description', 'amount'
        )
        
        total = expenses.aggregate(total=Sum('amount'))['total'] or 0
        
        return JsonResponse({
            'success': True,
            'data': {
                'expenses': list(expenses),
                'total': float(total)
            }
        })


class BulkExpenseDeleteAPIView(LoginRequiredMixin, View):
    """Bulk delete expenses"""
    
    def post(self, request):
        try:
            data = json.loads(request.body)
            ids = data.get('ids', [])
            
            if not ids:
                return JsonResponse({'success': False, 'error': 'No IDs provided'})
            
            # Get expenses before deletion for count
            expenses = Expense.objects.filter(id__in=ids)
            count = expenses.count()
            
            # Delete them
            expenses.delete()
            
            # Clear cache
            cache.delete(DASHBOARD_STATS_CACHE_KEY)
            cache.delete('expense_list_stats')
            
            return JsonResponse({
                'success': True,
                'message': f'Deleted {count} expenses',
                'count': count
            })
            
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})

# ==================== REPORT VIEWS ====================

class FisheryReportDashboardView(LoginRequiredMixin, TemplateView):
    """Reports dashboard"""
    template_name = 'fishery/reports/index.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        today = timezone.now().date()
        
        context['current_year'] = today.year
        context['years'] = range(2020, today.year + 2)
        
        # Quick stats - optimized
        context['total_cycles'] = ProductionCycle.objects.only('id').count()
        context['total_harvest'] = Harvest.objects.aggregate(
            total=Sum('quantity_kg')
        )['total'] or 0
        
        return context


class ProductionReportView(LoginRequiredMixin, TemplateView):
    """Production report"""
    template_name = 'fishery/reports/production.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        year = int(self.request.GET.get('year', timezone.now().year))
        
        cache_key = f'production_report_{year}'
        cached = cache.get(cache_key)
        
        if cached:
            context.update(cached)
            return context
        
        monthly_data = []
        for month in range(1, 13):
            month_start = datetime(year, month, 1).date()
            if month == 12:
                month_end = datetime(year+1, 1, 1).date() - timedelta(days=1)
            else:
                month_end = datetime(year, month+1, 1).date() - timedelta(days=1)
            
            # Single query per month - can be optimized further with raw SQL
            harvest = Harvest.objects.filter(
                harvest_date__range=[month_start, month_end]
            ).aggregate(total=Sum('quantity_kg'))['total'] or 0
            
            feed = FeedRecord.objects.filter(
                date__range=[month_start, month_end]
            ).aggregate(total=Sum('quantity_kg'))['total'] or 0
            
            monthly_data.append({
                'month': month_start.strftime('%B'),
                'harvest': harvest,
                'feed': feed,
            })
        
        context['monthly_data'] = monthly_data
        context['year'] = year
        context['years'] = range(2020, timezone.now().year + 2)
        
        cache.set(cache_key, context, 3600)
        
        return context


class FinancialReportView(LoginRequiredMixin, TemplateView):
    """Financial report"""
    template_name = 'fishery/reports/financial.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        year = int(self.request.GET.get('year', timezone.now().year))
        
        # Get or create report
        report, created = FisheryFinancialReport.objects.get_or_create(year=year)
        if created or self.request.GET.get('refresh'):
            report.calculate_totals()
        
        context['report'] = report
        
        return context


# ==================== FISH BATCH VIEWS ====================

class FishBatchListView(LoginRequiredMixin, ListView):
    """List all fish batches"""
    model = FishBatch
    template_name = 'fishery/batch/list.html'
    context_object_name = 'batches'
    paginate_by = 20
    
    def get_queryset(self):
        queryset = FishBatch.objects.select_related('species').only(
            'batch_number', 'species__name', 'source', 'supplier', 'grade', 'is_certified'
        )
        
        species_id = self.request.GET.get('species')
        if species_id:
            queryset = queryset.filter(species_id=species_id)
        
        grade = self.request.GET.get('grade')
        if grade:
            queryset = queryset.filter(grade=grade)
        
        search = self.request.GET.get('search')
        if search:
            queryset = queryset.filter(
                Q(batch_number__icontains=search) |
                Q(supplier__icontains=search)
            )
        
        return queryset


class FishBatchCreateView(LoginRequiredMixin, CreateView):
    """Create new fish batch"""
    model = FishBatch
    form_class = FishBatchForm
    template_name = 'fishery/batch/form.html'
    success_url = reverse_lazy('fishery:batch_list')


class FishBatchUpdateView(LoginRequiredMixin, UpdateView):
    """Update fish batch"""
    model = FishBatch
    form_class = FishBatchForm
    template_name = 'fishery/batch/form.html'
    success_url = reverse_lazy('fishery:batch_list')


class FishBatchDeleteView(LoginRequiredMixin, DeleteView):
    """Delete fish batch"""
    model = FishBatch
    template_name = 'fishery/batch/delete.html'
    success_url = reverse_lazy('fishery:batch_list')


# ==================== FEED PURCHASE UPDATE/DELETE VIEWS ====================

class FeedPurchaseUpdateView(LoginRequiredMixin, UpdateView):
    """Update feed purchase"""
    model = FeedPurchase
    form_class = FeedPurchaseForm
    template_name = 'fishery/feed/purchase_form.html'
    success_url = reverse_lazy('fishery:feed_purchase_list')


class FeedPurchaseDeleteView(LoginRequiredMixin, DeleteView):
    """Delete feed purchase"""
    model = FeedPurchase
    template_name = 'fishery/feed/delete.html'
    success_url = reverse_lazy('fishery:feed_purchase_list')
    
    def delete(self, request, *args, **kwargs):
        purchase = self.get_object()
        # Revert stock
        feed_type = purchase.feed_type
        feed_type.current_stock -= purchase.quantity_kg
        feed_type.save()
        messages.success(request, 'Feed purchase deleted successfully!')
        
        # Clear cache
        cache.delete(DASHBOARD_STATS_CACHE_KEY)
        
        return super().delete(request, *args, **kwargs)


# ==================== TREATMENT RECORD VIEWS ====================

class TreatmentRecordListView(LoginRequiredMixin, ListView):
    """List all treatment records"""
    model = TreatmentRecord
    template_name = 'fishery/health/treatment_list.html'
    context_object_name = 'treatments'
    paginate_by = 30
    
    def get_queryset(self):
        return TreatmentRecord.objects.select_related(
            'cycle__pond', 'disease', 'applied_by'
        ).only(
            'application_date', 'cycle__pond__name', 'treatment_type',
            'medication_name', 'dosage', 'cost', 'applied_by__username'
        ).order_by('-application_date')


class TreatmentRecordCreateView(LoginRequiredMixin, CreateView):
    """Create new treatment record"""
    model = TreatmentRecord
    form_class = TreatmentRecordForm
    template_name = 'fishery/health/treatment_form.html'
    success_url = reverse_lazy('fishery:treatment_list')
    
    def form_valid(self, form):
        form.instance.applied_by = self.request.user
        messages.success(self.request, 'Treatment record added successfully!')
        
        # Clear cache
        cache.delete(DASHBOARD_STATS_CACHE_KEY)
        
        return super().form_valid(form)


class TreatmentRecordUpdateView(LoginRequiredMixin, UpdateView):
    """Update treatment record"""
    model = TreatmentRecord
    form_class = TreatmentRecordForm
    template_name = 'fishery/health/treatment_form.html'
    success_url = reverse_lazy('fishery:treatment_list')


class TreatmentRecordDeleteView(LoginRequiredMixin, DeleteView):
    """Delete treatment record"""
    model = TreatmentRecord
    template_name = 'fishery/health/delete.html'
    success_url = reverse_lazy('fishery:treatment_list')


# ==================== BUDGET VIEWS ====================

class BudgetListView(LoginRequiredMixin, ListView):
    """List all budgets"""
    model = Budget
    template_name = 'fishery/budget/list.html'
    context_object_name = 'budgets'
    paginate_by = 20
    
    def get_queryset(self):
        return Budget.objects.select_related('cycle__pond').only(
            'cycle__pond__name', 'planned_fingerling_cost', 'planned_feed_cost',
            'planned_revenue', 'planned_profit', 'planned_roi'
        ).order_by('-cycle__stocking_date')


class BudgetCreateView(LoginRequiredMixin, CreateView):
    """Create new budget"""
    model = Budget
    form_class = BudgetForm
    template_name = 'fishery/budget/form.html'
    success_url = reverse_lazy('fishery:budget_list')
    
    def get_initial(self):
        initial = super().get_initial()
        cycle_id = self.request.GET.get('cycle')
        if cycle_id:
            try:
                cycle = ProductionCycle.objects.only(
                    'fingerling_cost', 'expected_yield_kg'
                ).get(id=cycle_id)
                initial['cycle'] = cycle
                initial['planned_fingerling_cost'] = cycle.fingerling_cost
                initial['planned_harvest_kg'] = cycle.expected_yield_kg
            except ProductionCycle.DoesNotExist:
                pass
        return initial


class BudgetUpdateView(LoginRequiredMixin, UpdateView):
    """Update budget"""
    model = Budget
    form_class = BudgetForm
    template_name = 'fishery/budget/form.html'
    success_url = reverse_lazy('fishery:budget_list')


class BudgetDeleteView(LoginRequiredMixin, DeleteView):
    """Delete budget"""
    model = Budget
    template_name = 'fishery/budget/delete.html'
    success_url = reverse_lazy('fishery:budget_list')


class BudgetForCycleView(LoginRequiredMixin, TemplateView):
    """View budget for specific cycle"""
    template_name = 'fishery/budget/cycle_budget.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        cycle_id = self.kwargs.get('cycle_id')
        cycle = get_object_or_404(ProductionCycle.objects.select_related('pond', 'species'), id=cycle_id)
        
        budget, created = Budget.objects.get_or_create(cycle=cycle)
        if created:
            budget.planned_fingerling_cost = cycle.fingerling_cost
            budget.planned_harvest_kg = cycle.expected_yield_kg or 0
            budget.save()
        
        context['cycle'] = cycle
        context['budget'] = budget
        return context


# ==================== POND API VIEWS ====================

class PondListAPIView(LoginRequiredMixin, View):
    """API endpoint for pond list"""
    
    def get(self, request):
        cache_key = 'pond_api_list'
        cached = cache.get(cache_key)
        if cached:
            return JsonResponse({'success': True, 'data': cached})
        
        ponds = Pond.objects.filter(is_active=True).only(
            'id', 'name', 'pond_id', 'size_in_acres', 'status'
        ).values()
        
        data = list(ponds)
        cache.set(cache_key, data, 3600)
        
        return JsonResponse({'success': True, 'data': data})


class PondDetailAPIView(LoginRequiredMixin, View):
    """API endpoint for pond details"""
    
    def get(self, request, pk):
        try:
            pond = Pond.objects.select_related('farm').only(
                'name', 'pond_id', 'farm__name', 'size_in_acres', 'status'
            ).get(id=pk)
            
            current_cycle = pond.current_cycle()
            
            data = {
                'id': pond.id,
                'name': pond.name,
                'pond_id': pond.pond_id,
                'farm': pond.farm.name if pond.farm else None,
                'size_in_acres': pond.size_in_acres,
                'status': pond.get_status_display(),
                'current_cycle': current_cycle.id if current_cycle else None,
            }
            return JsonResponse({'success': True, 'data': data})
        except Pond.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Pond not found'})


class PondSearchAPIView(LoginRequiredMixin, View):
    """API endpoint for searching ponds"""
    
    def get(self, request):
        query = request.GET.get('q', '')
        if len(query) < 2:
            return JsonResponse({'success': True, 'data': []})
        
        ponds = Pond.objects.filter(
            Q(name__icontains=query) |
            Q(pond_id__icontains=query)
        ).only('id', 'name', 'pond_id', 'status').values()[:20]
        
        return JsonResponse({'success': True, 'data': list(ponds)})


# ==================== PRODUCTION CYCLE API VIEWS ====================

class ProductionCycleListAPIView(LoginRequiredMixin, View):
    """API endpoint for production cycle list"""
    
    def get(self, request):
        cache_key = 'running_cycles_api'
        cached = cache.get(cache_key)
        if cached:
            return JsonResponse({'success': True, 'data': cached})
        
        cycles = ProductionCycle.objects.filter(
            status='RUNNING'
        ).select_related('pond', 'species').only(
            'id', 'pond__name', 'species__name', 'stocking_date',
            'expected_harvest_date', 'survival_rate', 'fcr'
        ).values()[:50]
        
        data = list(cycles)
        cache.set(cache_key, data, 300)
        
        return JsonResponse({'success': True, 'data': data})


class ProductionCycleDetailAPIView(LoginRequiredMixin, View):
    """API endpoint for production cycle details"""
    
    def get(self, request, pk):
        try:
            cycle = ProductionCycle.objects.select_related(
                'pond', 'species'
            ).only(
                'pond__name', 'species__name', 'stocking_date', 'initial_quantity',
                'survival_rate', 'fcr', 'total_feed', 'total_harvest'
            ).get(id=pk)
            
            data = {
                'id': cycle.id,
                'pond': cycle.pond.name,
                'species': cycle.species.name,
                'stocking_date': cycle.stocking_date,
                'initial_quantity': cycle.initial_quantity,
                'survival_rate': float(cycle.survival_rate),
                'fcr': float(cycle.fcr),
                'total_feed': float(cycle.total_feed),
                'total_harvest': float(cycle.total_harvest),
                'total_sales': float(cycle.total_sales),
                'total_investment': float(cycle.total_investment),
                'net_profit': float(cycle.net_profit),
                'roi': float(cycle.roi_percentage),
            }
            return JsonResponse({'success': True, 'data': data})
        except ProductionCycle.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Cycle not found'})


class CompletedCyclesAPIView(LoginRequiredMixin, View):
    """API endpoint for completed cycles"""
    
    def get(self, request):
        cycles = ProductionCycle.objects.filter(
            status='COMPLETED'
        ).select_related('pond', 'species').only(
            'id', 'pond__name', 'species__name', 'actual_harvest_date',
            'total_harvest', 'net_profit', 'roi_percentage'
        ).order_by('-actual_harvest_date')[:20].values()
        
        return JsonResponse({'success': True, 'data': list(cycles)})


class CyclesByPondAPIView(LoginRequiredMixin, View):
    """API endpoint for cycles by pond"""
    
    def get(self, request, pond_id):
        cycles = ProductionCycle.objects.filter(
            pond_id=pond_id
        ).select_related('species').only(
            'id', 'species__name', 'stocking_date', 'status',
            'survival_rate', 'fcr', 'total_harvest'
        ).order_by('-stocking_date')[:10].values()
        
        return JsonResponse({'success': True, 'data': list(cycles)})


# ==================== FEED API VIEWS ====================

class FeedRecordDetailAPIView(LoginRequiredMixin, View):
    """API endpoint for feed record details"""
    
    def get(self, request, pk):
        try:
            record = FeedRecord.objects.select_related(
                'cycle__pond', 'feed_type'
            ).only(
                'date', 'cycle__pond__name', 'feed_type__name',
                'quantity_kg', 'cost', 'feed_consumption_rate'
            ).get(id=pk)
            
            data = {
                'id': record.id,
                'date': record.date,
                'pond': record.cycle.pond.name,
                'feed_type': record.feed_type.name,
                'quantity_kg': float(record.quantity_kg),
                'cost': float(record.cost),
                'cost_per_kg': float(record.cost_per_kg),
                'consumption_rate': record.get_feed_consumption_rate_display(),
            }
            return JsonResponse({'success': True, 'data': data})
        except FeedRecord.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Record not found'})


class DailyFeedAPIView(LoginRequiredMixin, View):
    """API endpoint for today's feed records"""
    
    def get(self, request):
        today = timezone.now().date()
        records = FeedRecord.objects.filter(
            date=today
        ).select_related('cycle__pond', 'feed_type').only(
            'cycle__pond__name', 'feed_type__name', 'quantity_kg', 'feed_time'
        ).values()
        
        total = FeedRecord.objects.filter(date=today).aggregate(
            total=Sum('quantity_kg')
        )['total'] or 0
        
        return JsonResponse({
            'success': True,
            'data': {
                'records': list(records),
                'total': float(total)
            }
        })


class FeedByCycleAPIView(LoginRequiredMixin, View):
    """API endpoint for feed records by cycle"""
    
    def get(self, request, cycle_id):
        records = FeedRecord.objects.filter(
            cycle_id=cycle_id
        ).select_related('feed_type').only(
            'date', 'feed_type__name', 'quantity_kg', 'cost'
        ).order_by('-date')[:30].values()
        
        total = FeedRecord.objects.filter(cycle_id=cycle_id).aggregate(
            total=Sum('quantity_kg')
        )['total'] or 0
        
        return JsonResponse({
            'success': True,
            'data': {
                'records': list(records),
                'total': float(total)
            }
        })


# ==================== WATER QUALITY API VIEWS ====================

class WaterQualityByPondAPIView(LoginRequiredMixin, View):
    """API endpoint for water quality by pond"""
    
    def get(self, request, pond_id):
        readings = WaterQuality.objects.filter(
            pond_id=pond_id
        ).only(
            'reading_date', 'temperature', 'ph_level', 'dissolved_oxygen',
            'ammonia', 'alert_generated'
        ).order_by('-reading_date')[:20].values()
        
        return JsonResponse({'success': True, 'data': list(readings)})


class WaterQualityChartAPIView(LoginRequiredMixin, View):
    """API endpoint for water quality chart data"""
    
    def get(self, request, pond_id):
        days = int(request.GET.get('days', 7))
        start_date = timezone.now().date() - timedelta(days=days)
        
        readings = WaterQuality.objects.filter(
            pond_id=pond_id,
            reading_date__gte=start_date
        ).only(
            'reading_date', 'temperature', 'ph_level', 'dissolved_oxygen'
        ).order_by('reading_date')
        
        data = {
            'labels': [r.reading_date.strftime('%Y-%m-%d') for r in readings],
            'temperature': [float(r.temperature) for r in readings],
            'ph': [float(r.ph_level) for r in readings],
            'oxygen': [float(r.dissolved_oxygen) for r in readings],
        }
        
        return JsonResponse({'success': True, 'data': data})


# ==================== HEALTH API VIEWS ====================

class ActiveDiseasesAPIView(LoginRequiredMixin, View):
    """API endpoint for active diseases"""
    
    def get(self, request):
        diseases = DiseaseRecord.objects.filter(
            is_resolved=False
        ).select_related('cycle__pond').only(
            'cycle__pond__name', 'disease_name', 'severity',
            'detection_date', 'estimated_affected'
        ).order_by('-detection_date')[:20].values()
        
        return JsonResponse({'success': True, 'data': list(diseases)})


class TodayMortalityAPIView(LoginRequiredMixin, View):
    """API endpoint for today's mortality"""
    
    def get(self, request):
        today = timezone.now().date()
        mortalities = MortalityRecord.objects.filter(
            date=today
        ).select_related('cycle__pond').only(
            'cycle__pond__name', 'quantity_dead', 'reason'
        ).values()
        
        total = mortalities.aggregate(total=Sum('quantity_dead'))['total'] or 0
        
        return JsonResponse({
            'success': True,
            'data': {
                'records': list(mortalities),
                'total': total
            }
        })


class MortalityByCycleAPIView(LoginRequiredMixin, View):
    """API endpoint for mortality by cycle"""
    
    def get(self, request, cycle_id):
        mortalities = MortalityRecord.objects.filter(
            cycle_id=cycle_id
        ).only(
            'date', 'quantity_dead', 'reason'
        ).order_by('-date')[:30].values()
        
        total = MortalityRecord.objects.filter(cycle_id=cycle_id).aggregate(
            total=Sum('quantity_dead')
        )['total'] or 0
        
        return JsonResponse({
            'success': True,
            'data': {
                'records': list(mortalities),
                'total': total
            }
        })


# ==================== HARVEST API VIEWS ====================

class HarvestByCycleAPIView(LoginRequiredMixin, View):
    """API endpoint for harvest by cycle"""
    
    def get(self, request, cycle_id):
        harvests = Harvest.objects.filter(
            cycle_id=cycle_id
        ).only(
            'harvest_date', 'quantity_kg', 'piece_count', 'avg_weight', 'grade'
        ).order_by('-harvest_date').values()
        
        total = harvests.aggregate(total=Sum('quantity_kg'))['total'] or 0
        
        return JsonResponse({
            'success': True,
            'data': {
                'records': list(harvests),
                'total': float(total)
            }
        })


class HarvestStatsAPIView(LoginRequiredMixin, View):
    """API endpoint for harvest statistics"""
    
    def get(self, request):
        today = timezone.now().date()
        this_month = today.replace(day=1)
        
        data = {
            'today': float(Harvest.objects.filter(harvest_date=today).aggregate(
                total=Sum('quantity_kg')
            )['total'] or 0),
            'this_month': float(Harvest.objects.filter(harvest_date__gte=this_month).aggregate(
                total=Sum('quantity_kg')
            )['total'] or 0),
            'this_year': float(Harvest.objects.filter(harvest_date__year=today.year).aggregate(
                total=Sum('quantity_kg')
            )['total'] or 0),
        }
        
        return JsonResponse({'success': True, 'data': data})


# ==================== SALES API VIEWS ====================

class FishSaleDetailAPIView(LoginRequiredMixin, View):
    """API endpoint for sale details"""
    
    def get(self, request, pk):
        try:
            sale = FishSale.objects.select_related(
                'harvest__cycle__pond', 'customer'
            ).only(
                'sale_number', 'sale_date', 'harvest__cycle__pond__name',
                'harvest__cycle__species__name', 'customer__name',
                'customer_name', 'quantity_kg', 'price_per_kg', 'payment_status'
            ).get(id=pk)
            
            data = {
                'id': sale.id,
                'sale_number': sale.sale_number,
                'date': sale.sale_date,
                'pond': sale.harvest.cycle.pond.name if sale.harvest else None,
                'species': sale.harvest.cycle.species.name if sale.harvest else None,
                'customer': sale.customer.name if sale.customer else sale.customer_name,
                'quantity_kg': float(sale.quantity_kg),
                'price_per_kg': float(sale.price_per_kg),
                'total_amount': float(sale.quantity_kg * sale.price_per_kg),
                'payment_status': sale.get_payment_status_display(),
            }
            return JsonResponse({'success': True, 'data': data})
        except FishSale.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Sale not found'})


class SalesByCustomerAPIView(LoginRequiredMixin, View):
    """API endpoint for sales by customer"""
    
    def get(self, request, customer_id):
        sales = FishSale.objects.filter(
            customer_id=customer_id
        ).select_related('harvest__cycle__pond').only(
            'sale_date', 'harvest__cycle__pond__name', 'quantity_kg',
            'price_per_kg', 'total_amount'
        ).order_by('-sale_date')[:20].values()
        
        total = sum(s['total_amount'] for s in sales)
        
        return JsonResponse({
            'success': True,
            'data': {
                'records': list(sales),
                'total': float(total)
            }
        })


class SalesStatsAPIView(LoginRequiredMixin, View):
    """API endpoint for sales statistics"""
    
    def get(self, request):
        today = timezone.now().date()
        this_month = today.replace(day=1)
        
        today_sales = FishSale.objects.filter(sale_date=today)
        today_qty = today_sales.aggregate(total=Sum('quantity_kg'))['total'] or 0
        today_rev = sum(s.quantity_kg * s.price_per_kg for s in today_sales)
        
        month_sales = FishSale.objects.filter(sale_date__gte=this_month)
        month_qty = month_sales.aggregate(total=Sum('quantity_kg'))['total'] or 0
        month_rev = sum(s.quantity_kg * s.price_per_kg for s in month_sales)
        
        # Top customers
        top_customers = FishSale.objects.values(
            'customer__name'
        ).annotate(
            total=Sum(F('quantity_kg') * F('price_per_kg'))
        ).order_by('-total')[:5]
        
        data = {
            'today': {
                'quantity': float(today_qty),
                'revenue': float(today_rev),
            },
            'this_month': {
                'quantity': float(month_qty),
                'revenue': float(month_rev),
            },
            'top_customers': list(top_customers),
        }
        
        return JsonResponse({'success': True, 'data': data})


# ==================== CUSTOMER API VIEWS ====================

class CustomerListAPIView(LoginRequiredMixin, View):
    """API endpoint for customer list"""
    
    def get(self, request):
        cache_key = 'customer_api_list'
        cached = cache.get(cache_key)
        if cached:
            return JsonResponse({'success': True, 'data': cached})
        
        customers = Customer.objects.filter(is_active=True).only(
            'id', 'name', 'customer_type', 'phone', 'city'
        ).values()[:50]
        
        data = list(customers)
        cache.set(cache_key, data, 3600)
        
        return JsonResponse({'success': True, 'data': data})


class CustomerDetailAPIView(LoginRequiredMixin, View):
    """API endpoint for customer details"""
    
    def get(self, request, pk):
        try:
            customer = Customer.objects.only(
                'name', 'customer_type', 'phone', 'email',
                'city', 'credit_limit', 'current_balance'
            ).get(id=pk)
            
            data = {
                'id': customer.id,
                'name': customer.name,
                'customer_type': customer.get_customer_type_display(),
                'phone': customer.phone,
                'email': customer.email,
                'city': customer.city,
                'credit_limit': float(customer.credit_limit),
                'current_balance': float(customer.current_balance),
            }
            return JsonResponse({'success': True, 'data': data})
        except Customer.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Customer not found'})


class CustomerSearchAPIView(LoginRequiredMixin, View):
    """API endpoint for searching customers"""
    
    def get(self, request):
        query = request.GET.get('q', '')
        if len(query) < 2:
            return JsonResponse({'success': True, 'data': []})
        
        customers = Customer.objects.filter(
            Q(name__icontains=query) |
            Q(phone__icontains=query) |
            Q(email__icontains=query)
        ).only('id', 'name', 'phone', 'city').values()[:20]
        
        return JsonResponse({'success': True, 'data': list(customers)})


# ==================== EXPENSE API VIEWS ====================

class ExpensesByCycleAPIView(LoginRequiredMixin, View):
    """API endpoint for expenses by cycle"""
    
    def get(self, request, cycle_id):
        expenses = Expense.objects.filter(
            cycle_id=cycle_id
        ).only(
            'expense_date', 'expense_type', 'description', 'amount'
        ).order_by('-expense_date')[:30].values()
        
        total = expenses.aggregate(total=Sum('amount'))['total'] or 0
        
        return JsonResponse({
            'success': True,
            'data': {
                'records': list(expenses),
                'total': float(total)
            }
        })


class ExpensesByTypeAPIView(LoginRequiredMixin, View):
    """API endpoint for expenses grouped by type"""
    
    def get(self, request):
        year = int(request.GET.get('year', timezone.now().year))
        
        from django.db import connection
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT expense_type, COALESCE(SUM(amount), 0) as total
                FROM fishery_expense
                WHERE strftime('%Y', expense_date) = %s
                GROUP BY expense_type
                ORDER BY total DESC
            """, [str(year)])
            rows = cursor.fetchall()
        
        data = [{
            'type': dict(Expense.EXPENSE_TYPES).get(r[0], r[0]),
            'total': float(r[1])
        } for r in rows]
        
        return JsonResponse({'success': True, 'data': data})


# ==================== FINANCIAL API VIEWS ====================

class FinancialSummaryAPIView(LoginRequiredMixin, View):
    """API endpoint for financial summary"""
    
    def get(self, request):
        today = timezone.now().date()
        this_month = today.replace(day=1)
        this_year = today.replace(month=1, day=1)
        
        # Revenue
        revenue = sum(
            s.quantity_kg * s.price_per_kg 
            for s in FishSale.objects.filter(sale_date__gte=this_month)
        )
        
        # Expenses
        expenses = Expense.objects.filter(
            expense_date__gte=this_month
        ).aggregate(total=Sum('amount'))['total'] or 0
        
        # YTD figures
        ytd_revenue = sum(
            s.quantity_kg * s.price_per_kg 
            for s in FishSale.objects.filter(sale_date__gte=this_year)
        )
        
        ytd_expenses = Expense.objects.filter(
            expense_date__gte=this_year
        ).aggregate(total=Sum('amount'))['total'] or 0
        
        data = {
            'monthly': {
                'revenue': float(revenue),
                'expenses': float(expenses),
                'profit': float(revenue - expenses)
            },
            'yearly': {
                'revenue': float(ytd_revenue),
                'expenses': float(ytd_expenses),
                'profit': float(ytd_revenue - ytd_expenses)
            }
        }
        
        return JsonResponse({'success': True, 'data': data})


class ProfitLossAPIView(LoginRequiredMixin, View):
    """API endpoint for profit/loss analysis"""
    
    def get(self, request):
        period = request.GET.get('period', 'month')
        today = timezone.now().date()
        
        if period == 'month':
            start_date = today.replace(day=1)
            end_date = today
        elif period == 'quarter':
            quarter = (today.month - 1) // 3 + 1
            start_date = datetime(today.year, quarter*3 - 2, 1).date()
            end_date = today
        elif period == 'year':
            start_date = datetime(today.year, 1, 1).date()
            end_date = today
        else:
            start_date = today - timedelta(days=30)
            end_date = today
        
        # Revenue
        revenue = sum(
            s.quantity_kg * s.price_per_kg 
            for s in FishSale.objects.filter(sale_date__range=[start_date, end_date])
        )
        
        # Expenses
        expenses = Expense.objects.filter(
            expense_date__range=[start_date, end_date]
        ).aggregate(total=Sum('amount'))['total'] or 0
        
        # Feed cost
        feed_cost = FeedRecord.objects.filter(
            date__range=[start_date, end_date]
        ).aggregate(total=Sum('cost'))['total'] or 0
        
        data = {
            'period': period,
            'start_date': start_date,
            'end_date': end_date,
            'revenue': float(revenue),
            'expenses': float(expenses),
            'feed_cost': float(feed_cost),
            'other_expenses': float(expenses - feed_cost),
            'net_profit': float(revenue - expenses),
            'profit_margin': round(((revenue - expenses) / revenue * 100) if revenue > 0 else 0, 2),
        }
        
        return JsonResponse({'success': True, 'data': data})


class ROIAnalysisAPIView(LoginRequiredMixin, View):
    """API endpoint for ROI analysis"""
    
    def get(self, request):
        completed_cycles = ProductionCycle.objects.filter(
            status='COMPLETED'
        ).select_related('pond', 'species').only(
            'pond__name', 'species__name', 'actual_harvest_date',
            'total_investment', 'total_sales', 'net_profit', 'roi_percentage'
        ).order_by('-actual_harvest_date')[:10]
        
        data = [{
            'cycle_id': c.id,
            'pond': c.pond.name,
            'species': c.species.name,
            'harvest_date': c.actual_harvest_date,
            'investment': float(c.total_investment),
            'revenue': float(c.total_sales),
            'profit': float(c.net_profit),
            'roi': float(c.roi_percentage),
        } for c in completed_cycles]
        
        return JsonResponse({'success': True, 'data': data})


# ==================== CHART API VIEWS ====================

class GrowthChartDataAPIView(LoginRequiredMixin, View):
    """API endpoint for growth chart data"""
    
    def get(self, request, cycle_id):
        try:
            cycle = ProductionCycle.objects.get(id=cycle_id)
            
            # Get feed records over time
            feed_data = FeedRecord.objects.filter(
                cycle=cycle
            ).values('date').annotate(
                total_feed=Sum('quantity_kg')
            ).order_by('date')
            
            # Get harvest data
            harvest_data = Harvest.objects.filter(
                cycle=cycle
            ).order_by('harvest_date')
            
            # Get mortality data
            mortality_data = cycle.mortalities.order_by('date')
            
            data = {
                'labels': [f['date'].strftime('%Y-%m-%d') for f in feed_data],
                'feed': [float(f['total_feed']) for f in feed_data],
                'harvest': [float(h.quantity_kg) for h in harvest_data],
                'mortality': [float(m.quantity_dead) for m in mortality_data],
            }
            
            return JsonResponse({'success': True, 'data': data})
        except ProductionCycle.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Cycle not found'})


# ==================== BULK OPERATIONS API VIEWS ====================

class BulkExpenseDeleteAPIView(LoginRequiredMixin, View):
    """Bulk delete expenses"""
    
    def post(self, request):
        try:
            data = json.loads(request.body)
            ids = data.get('ids', [])
            
            if not ids:
                return JsonResponse({'success': False, 'error': 'No IDs provided'})
            
            count, _ = Expense.objects.filter(id__in=ids).delete()
            
            # Clear cache
            cache.delete(DASHBOARD_STATS_CACHE_KEY)
            
            return JsonResponse({'success': True, 'message': f'Deleted {count} expenses'})
            
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})


class BulkFeedDeleteAPIView(LoginRequiredMixin, View):
    """Bulk delete feed records"""
    
    def post(self, request):
        try:
            data = json.loads(request.body)
            ids = data.get('ids', [])
            
            if not ids:
                return JsonResponse({'success': False, 'error': 'No IDs provided'})
            
            # Update stock before deleting
            records = FeedRecord.objects.filter(id__in=ids).select_related('feed_type')
            for record in records:
                feed_type = record.feed_type
                feed_type.current_stock += record.quantity_kg
                feed_type.save()
            
            count, _ = records.delete()
            
            # Clear cache
            cache.delete(DASHBOARD_STATS_CACHE_KEY)
            
            return JsonResponse({'success': True, 'message': f'Deleted {count} feed records'})
            
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})


class BulkHarvestDeleteAPIView(LoginRequiredMixin, View):
    """Bulk delete harvest records"""
    
    def post(self, request):
        try:
            data = json.loads(request.body)
            ids = data.get('ids', [])
            
            if not ids:
                return JsonResponse({'success': False, 'error': 'No IDs provided'})
            
            # Check if harvests have sales
            harvests = Harvest.objects.filter(id__in=ids).prefetch_related('sales')
            for harvest in harvests:
                if harvest.sales.exists():
                    return JsonResponse({
                        'success': False, 
                        'error': f'Cannot delete harvest with existing sales'
                    })
            
            count, _ = harvests.delete()
            
            # Clear cache
            cache.delete(DASHBOARD_STATS_CACHE_KEY)
            
            return JsonResponse({'success': True, 'message': f'Deleted {count} harvest records'})
            
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})


# ==================== SEARCH API VIEWS ====================

class SearchPondsAPIView(LoginRequiredMixin, View):
    """API endpoint for searching ponds"""
    
    def get(self, request):
        query = request.GET.get('q', '')
        if len(query) < 2:
            return JsonResponse({'success': True, 'data': []})
        
        ponds = Pond.objects.filter(
            Q(name__icontains=query) |
            Q(pond_id__icontains=query)
        ).only('id', 'name', 'pond_id', 'status').values()[:20]
        
        return JsonResponse({'success': True, 'data': list(ponds)})


class SearchCyclesAPIView(LoginRequiredMixin, View):
    """API endpoint for searching cycles"""
    
    def get(self, request):
        query = request.GET.get('q', '')
        if len(query) < 2:
            return JsonResponse({'success': True, 'data': []})
        
        cycles = ProductionCycle.objects.filter(
            Q(pond__name__icontains=query) |
            Q(species__name__icontains=query) |
            Q(cycle_id__icontains=query)
        ).select_related('pond', 'species').only(
            'id', 'cycle_id', 'pond__name', 'species__name', 'status'
        ).values()[:20]
        
        return JsonResponse({'success': True, 'data': list(cycles)})


class SearchSalesAPIView(LoginRequiredMixin, View):
    """API endpoint for searching sales"""
    
    def get(self, request):
        query = request.GET.get('q', '')
        if len(query) < 2:
            return JsonResponse({'success': True, 'data': []})
        
        sales = FishSale.objects.filter(
            Q(sale_number__icontains=query) |
            Q(customer_name__icontains=query) |
            Q(customer__name__icontains=query)
        ).select_related('harvest__cycle__pond').only(
            'id', 'sale_number', 'customer_name', 'harvest__cycle__pond__name',
            'quantity_kg', 'sale_date'
        ).values()[:20]
        
        return JsonResponse({'success': True, 'data': list(sales)})


class SearchCustomersAPIView(LoginRequiredMixin, View):
    """API endpoint for searching customers"""
    
    def get(self, request):
        query = request.GET.get('q', '')
        if len(query) < 2:
            return JsonResponse({'success': True, 'data': []})
        
        customers = Customer.objects.filter(
            Q(name__icontains=query) |
            Q(phone__icontains=query) |
            Q(email__icontains=query)
        ).only('id', 'name', 'phone', 'customer_type').values()[:20]
        
        return JsonResponse({'success': True, 'data': list(customers)})


# ==================== REPORT API VIEWS ====================

class ProductionReportAPIView(LoginRequiredMixin, View):
    """API endpoint for production report"""
    
    def get(self, request):
        year = int(request.GET.get('year', timezone.now().year))
        cache_key = f'api_production_report_{year}'
        cached = cache.get(cache_key)
        
        if cached:
            return JsonResponse({'success': True, 'data': cached})
        
        from django.db import connection
        
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT 
                    strftime('%m', harvest_date) as month,
                    COALESCE(SUM(quantity_kg), 0) as harvest,
                    COALESCE((SELECT SUM(quantity_kg) FROM fishery_feedrecord WHERE strftime('%m', date) = month), 0) as feed,
                    COALESCE((SELECT SUM(quantity_dead) FROM fishery_mortalityrecord WHERE strftime('%m', date) = month), 0) as mortality
                FROM fishery_harvest
                WHERE strftime('%Y', harvest_date) = %s
                GROUP BY month
                ORDER BY month
            """, [str(year)])
            rows = cursor.fetchall()
        
        monthly_data = []
        total_harvest = 0
        total_feed = 0
        
        for i, row in enumerate(rows, 1):
            month_name = datetime(year, int(row[0]), 1).strftime('%B')
            harvest = float(row[1])
            feed = float(row[2])
            mortality = float(row[3])
            
            monthly_data.append({
                'month': month_name,
                'harvest': harvest,
                'feed': feed,
                'mortality': mortality,
            })
            total_harvest += harvest
            total_feed += feed
        
        data = {
            'year': year,
            'monthly_data': monthly_data,
            'total_harvest': total_harvest,
            'total_feed': total_feed,
            'avg_fcr': round(total_feed / total_harvest, 2) if total_harvest > 0 else 0,
        }
        
        cache.set(cache_key, data, 3600)
        
        return JsonResponse({'success': True, 'data': data})


class FinancialReportAPIView(LoginRequiredMixin, View):
    """API endpoint for financial report"""
    
    def get(self, request):
        year = int(request.GET.get('year', timezone.now().year))
        cache_key = f'api_financial_report_{year}'
        cached = cache.get(cache_key)
        
        if cached:
            return JsonResponse({'success': True, 'data': cached})
        
        from django.db import connection
        
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT 
                    strftime('%m', sale_date) as month,
                    COALESCE(SUM(quantity_kg * price_per_kg), 0) as revenue,
                    COALESCE((SELECT SUM(amount) FROM fishery_expense WHERE strftime('%m', expense_date) = month), 0) as expenses,
                    COALESCE((SELECT SUM(cost) FROM fishery_feedrecord WHERE strftime('%m', date) = month), 0) as feed_cost
                FROM fishery_fishsale
                WHERE strftime('%Y', sale_date) = %s
                GROUP BY month
                ORDER BY month
            """, [str(year)])
            rows = cursor.fetchall()
        
        monthly_data = []
        total_revenue = 0
        total_expenses = 0
        
        for row in rows:
            month_name = datetime(year, int(row[0]), 1).strftime('%B')
            revenue = float(row[1])
            expenses = float(row[2])
            feed_cost = float(row[3])
            
            monthly_data.append({
                'month': month_name,
                'revenue': revenue,
                'expenses': expenses,
                'feed_cost': feed_cost,
                'other_expenses': expenses - feed_cost,
                'profit': revenue - expenses,
            })
            total_revenue += revenue
            total_expenses += expenses
        
        total_profit = total_revenue - total_expenses
        profit_margin = (total_profit / total_revenue * 100) if total_revenue > 0 else 0
        
        data = {
            'year': year,
            'monthly_data': monthly_data,
            'total_revenue': total_revenue,
            'total_expenses': total_expenses,
            'total_profit': total_profit,
            'profit_margin': round(profit_margin, 2),
        }
        
        cache.set(cache_key, data, 3600)
        
        return JsonResponse({'success': True, 'data': data})


class SalesReportAPIView(LoginRequiredMixin, View):
    """API endpoint for sales report"""
    
    def get(self, request):
        year = int(request.GET.get('year', timezone.now().year))
        
        from django.db import connection
        
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT 
                    strftime('%m', sale_date) as month,
                    COALESCE(SUM(quantity_kg * price_per_kg), 0) as total
                FROM fishery_fishsale
                WHERE strftime('%Y', sale_date) = %s
                GROUP BY month
                ORDER BY month
            """, [str(year)])
            rows = cursor.fetchall()
        
        monthly_sales = [0] * 12
        for row in rows:
            month_idx = int(row[0]) - 1
            if 0 <= month_idx < 12:
                monthly_sales[month_idx] = float(row[1])
        
        # Top species
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT 
                    fs.name,
                    COALESCE(SUM(fsale.quantity_kg * fsale.price_per_kg), 0) as total
                FROM fishery_fishsale fsale
                JOIN fishery_harvest h ON fsale.harvest_id = h.id
                JOIN fishery_productioncycle pc ON h.cycle_id = pc.id
                JOIN fishery_fishspecies fs ON pc.species_id = fs.id
                WHERE strftime('%Y', fsale.sale_date) = %s
                GROUP BY fs.name
                ORDER BY total DESC
                LIMIT 5
            """, [str(year)])
            species_rows = cursor.fetchall()
        
        top_species = [{'name': r[0], 'total': float(r[1])} for r in species_rows]
        
        data = {
            'year': year,
            'monthly_sales': monthly_sales,
            'total_sales': sum(monthly_sales),
            'top_species': top_species,
        }
        
        return JsonResponse({'success': True, 'data': data})


class ExpensesReportAPIView(LoginRequiredMixin, View):
    """API endpoint for expenses report"""
    
    def get(self, request):
        year = int(request.GET.get('year', timezone.now().year))
        
        from django.db import connection
        
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT 
                    strftime('%m', expense_date) as month,
                    COALESCE(SUM(amount), 0) as total
                FROM fishery_expense
                WHERE strftime('%Y', expense_date) = %s
                GROUP BY month
                ORDER BY month
            """, [str(year)])
            rows = cursor.fetchall()
        
        monthly_expenses = [0] * 12
        for row in rows:
            month_idx = int(row[0]) - 1
            if 0 <= month_idx < 12:
                monthly_expenses[month_idx] = float(row[1])
        
        # Expenses by type
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT 
                    expense_type,
                    COALESCE(SUM(amount), 0) as total
                FROM fishery_expense
                WHERE strftime('%Y', expense_date) = %s
                GROUP BY expense_type
                ORDER BY total DESC
            """, [str(year)])
            type_rows = cursor.fetchall()
        
        by_type = [{'type': dict(Expense.EXPENSE_TYPES).get(r[0], r[0]), 'total': float(r[1])} for r in type_rows]
        
        data = {
            'year': year,
            'monthly_expenses': monthly_expenses,
            'total_expenses': sum(monthly_expenses),
            'by_type': by_type,
        }
        
        return JsonResponse({'success': True, 'data': data})


# ==================== REPORT GENERATION VIEW ====================

class GenerateFinancialReportView(LoginRequiredMixin, View):
    """Generate financial report for a year"""
    
    def post(self, request):
        year = int(request.POST.get('year', timezone.now().year))
        
        # Get or create report
        report, created = FisheryFinancialReport.objects.get_or_create(year=year)
        report.calculate_totals()
        
        messages.success(request, f'Financial report for {year} generated successfully!')
        
        # Clear cache
        cache.delete(DASHBOARD_STATS_CACHE_KEY)
        
        return redirect(f"{reverse_lazy('fishery:financial_report')}?year={year}")


# ==================== REMAINING EXPORT VIEWS ====================

class ExportExpensesCSVView(LoginRequiredMixin, View):
    """Export expenses data to CSV"""
    
    def get(self, request):
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="expenses_export.csv"'
        
        writer = csv.writer(response)
        writer.writerow(['Date', 'Pond/Cycle', 'Expense Type', 'Description', 'Amount', 'Payment Method', 'Paid To', 'Receipt Number'])
        
        # Get filter parameters
        year = request.GET.get('year')
        expense_type = request.GET.get('type')
        pond_id = request.GET.get('pond')
        
        queryset = Expense.objects.select_related('cycle__pond').order_by('-expense_date')
        
        if year:
            queryset = queryset.filter(expense_date__year=year)
        if expense_type:
            queryset = queryset.filter(expense_type=expense_type)
        if pond_id:
            queryset = queryset.filter(cycle__pond_id=pond_id)
        
        for expense in queryset.iterator(chunk_size=100):
            writer.writerow([
                expense.expense_date.strftime('%Y-%m-%d'),
                expense.cycle.pond.name if expense.cycle else '-',
                expense.get_expense_type_display(),
                expense.description,
                f'৳{expense.amount}',
                expense.get_payment_method_display(),
                expense.paid_to or '',
                expense.receipt_number or ''
            ])
        
        return response


class ExportFeedCSVView(LoginRequiredMixin, View):
    """Export feed records to CSV"""
    
    def get(self, request):
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="feed_records_export.csv"'
        
        writer = csv.writer(response)
        writer.writerow(['Date', 'Pond', 'Cycle ID', 'Feed Type', 'Brand', 'Quantity (kg)', 'Cost (৳)', 'Cost per kg (৳)', 'Feed Time', 'Consumption Rate', 'Recorded By'])
        
        # Get filter parameters
        year = request.GET.get('year')
        month = request.GET.get('month')
        pond_id = request.GET.get('pond')
        feed_type_id = request.GET.get('feed_type')
        
        queryset = FeedRecord.objects.select_related(
            'cycle__pond', 'feed_type', 'recorded_by'
        ).order_by('-date', '-feed_time')
        
        if year:
            queryset = queryset.filter(date__year=year)
        if month:
            queryset = queryset.filter(date__month=month)
        if pond_id:
            queryset = queryset.filter(cycle__pond_id=pond_id)
        if feed_type_id:
            queryset = queryset.filter(feed_type_id=feed_type_id)
        
        for record in queryset.iterator(chunk_size=100):
            writer.writerow([
                record.date.strftime('%Y-%m-%d'),
                record.cycle.pond.name,
                record.cycle.cycle_id[:8] if record.cycle else '-',
                record.feed_type.name,
                record.feed_type.brand,
                f'{record.quantity_kg:.2f}',
                f'৳{record.cost:.2f}',
                f'৳{record.cost_per_kg:.2f}' if record.cost_per_kg else '৳0.00',
                record.get_feed_time_display() if record.feed_time else '-',
                record.get_feed_consumption_rate_display(),
                record.recorded_by.get_full_name() or record.recorded_by.username if record.recorded_by else ''
            ])
        
        return response


class ExportHarvestsCSVView(LoginRequiredMixin, View):
    """Export harvest records to CSV"""
    
    def get(self, request):
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="harvests_export.csv"'
        
        writer = csv.writer(response)
        writer.writerow(['Date', 'Pond', 'Species', 'Cycle ID', 'Quantity (kg)', 'Piece Count', 'Avg Weight (g)', 'Grade', 'Harvest Method', 'Harvested By', 'Total Sales (৳)', 'Notes'])
        
        # Get filter parameters
        year = request.GET.get('year')
        month = request.GET.get('month')
        pond_id = request.GET.get('pond')
        species_id = request.GET.get('species')
        grade = request.GET.get('grade')
        
        queryset = Harvest.objects.select_related(
            'cycle__pond', 'cycle__species', 'harvested_by'
        ).order_by('-harvest_date')
        
        if year:
            queryset = queryset.filter(harvest_date__year=year)
        if month:
            queryset = queryset.filter(harvest_date__month=month)
        if pond_id:
            queryset = queryset.filter(cycle__pond_id=pond_id)
        if species_id:
            queryset = queryset.filter(cycle__species_id=species_id)
        if grade:
            queryset = queryset.filter(grade=grade)
        
        for harvest in queryset.iterator(chunk_size=100):
            writer.writerow([
                harvest.harvest_date.strftime('%Y-%m-%d'),
                harvest.cycle.pond.name,
                harvest.cycle.species.name,
                harvest.cycle.cycle_id[:8] if harvest.cycle else '-',
                f'{harvest.quantity_kg:.2f}',
                harvest.piece_count or '-',
                f'{harvest.avg_weight:.0f}' if harvest.avg_weight else '-',
                harvest.get_grade_display(),
                harvest.get_harvest_method_display(),
                harvest.harvested_by.get_full_name() or harvest.harvested_by.username if harvest.harvested_by else '',
                f'৳{harvest.total_sales:.2f}' if harvest.total_sales else '৳0.00',
                harvest.notes or ''
            ])
        
        return response


class ExportPondsCSVView(LoginRequiredMixin, View):
    """Export ponds data to CSV"""
    
    def get(self, request):
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="ponds_export.csv"'
        
        writer = csv.writer(response)
        writer.writerow(['Pond ID', 'Name', 'Farm', 'Type', 'Size (acres)', 'Depth (ft)', 'Water Source', 'Bottom Type', 'Status', 'Location', 'Current Cycle'])
        
        queryset = Pond.objects.select_related('farm').order_by('name')
        
        for pond in queryset.iterator(chunk_size=100):
            writer.writerow([
                pond.pond_id,
                pond.name,
                pond.farm.name if pond.farm else '-',
                pond.get_pond_type_display(),
                pond.size_in_acres,
                pond.average_depth or '-',
                pond.get_water_source_display() if hasattr(pond, 'get_water_source_display') else pond.water_source,
                pond.get_bottom_type_display() if hasattr(pond, 'get_bottom_type_display') else pond.bottom_type,
                pond.get_status_display(),
                pond.location or '-',
                pond.current_cycle().cycle_id[:8] if pond.current_cycle() else 'None'
            ])
        
        return response


class ExportCyclesCSVView(LoginRequiredMixin, View):
    """Export production cycles to CSV"""
    
    def get(self, request):
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="cycles_export.csv"'
        
        writer = csv.writer(response)
        writer.writerow(['Cycle ID', 'Pond', 'Species', 'Stocking Date', 'Harvest Date', 'Initial Qty', 'Harvest (kg)', 'Survival %', 'FCR', 'Feed Used (kg)', 'Investment (৳)', 'Revenue (৳)', 'Profit (৳)', 'ROI %', 'Status'])
        
        queryset = ProductionCycle.objects.select_related('pond', 'species').order_by('-stocking_date')
        
        for cycle in queryset.iterator(chunk_size=100):
            writer.writerow([
                cycle.cycle_id[:8],
                cycle.pond.name,
                cycle.species.name,
                cycle.stocking_date.strftime('%Y-%m-%d'),
                cycle.actual_harvest_date.strftime('%Y-%m-%d') if cycle.actual_harvest_date else '-',
                cycle.initial_quantity,
                f'{cycle.total_harvest:.2f}',
                f'{cycle.survival_rate:.1f}',
                f'{cycle.fcr:.2f}',
                f'{cycle.total_feed:.2f}',
                f'৳{cycle.total_investment:.2f}',
                f'৳{cycle.total_sales:.2f}',
                f'৳{cycle.net_profit:.2f}',
                f'{cycle.roi_percentage:.1f}',
                cycle.get_status_display()
            ])
        
        return response


class ExportSalesCSVView(LoginRequiredMixin, View):
    """Export sales data to CSV"""
    
    def get(self, request):
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="sales_export.csv"'
        
        writer = csv.writer(response)
        writer.writerow(['Sale ID', 'Date', 'Customer', 'Pond', 'Species', 'Quantity (kg)', 'Price/kg (৳)', 'Total (৳)', 'Payment Status', 'Payment Method', 'Created By'])
        
        # Get filter parameters
        year = request.GET.get('year')
        month = request.GET.get('month')
        customer_id = request.GET.get('customer')
        payment_status = request.GET.get('payment_status')
        
        queryset = FishSale.objects.select_related(
            'harvest__cycle__pond', 'harvest__cycle__species', 'customer', 'created_by'
        ).order_by('-sale_date')
        
        if year:
            queryset = queryset.filter(sale_date__year=year)
        if month:
            queryset = queryset.filter(sale_date__month=month)
        if customer_id:
            queryset = queryset.filter(customer_id=customer_id)
        if payment_status:
            queryset = queryset.filter(payment_status=payment_status)
        
        for sale in queryset.iterator(chunk_size=100):
            writer.writerow([
                sale.sale_number[:8],
                sale.sale_date.strftime('%Y-%m-%d'),
                sale.customer.name if sale.customer else (sale.customer_name or 'Walk-in'),
                sale.harvest.cycle.pond.name if sale.harvest and sale.harvest.cycle else '-',
                sale.harvest.cycle.species.name if sale.harvest and sale.harvest.cycle else '-',
                f'{sale.quantity_kg:.2f}',
                f'৳{sale.price_per_kg:.2f}',
                f'৳{sale.total_amount:.2f}',
                sale.get_payment_status_display(),
                sale.get_payment_method_display(),
                sale.created_by.get_full_name() or sale.created_by.username if sale.created_by else ''
            ])
        
        return response