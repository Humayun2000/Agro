from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView, TemplateView, View
from django.urls import reverse_lazy
from django.contrib import messages
from django.db.models import Sum, Avg, Count, Q, Min, Max
from django.utils import timezone
from django.http import JsonResponse, HttpResponse
from datetime import datetime, timedelta
from decimal import Decimal
import csv
import json

# PDF generation imports
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter, landscape
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph
from reportlab.lib.styles import getSampleStyleSheet

from .models import *
from .forms import *






# ==================== DASHBOARD VIEW ====================

class DairyDashboardView(LoginRequiredMixin, TemplateView):
    """Main Dairy Dashboard"""
    template_name = 'dairy/dashboard.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        today = timezone.now().date()
        first_day_month = today.replace(day=1)
        
        # Cattle Statistics
        context['total_cattle'] = Cattle.objects.count()
        context['active_cattle'] = Cattle.objects.filter(status='ACTIVE').count()
        context['dairy_cattle'] = Cattle.objects.filter(cattle_type__in=['DAIRY', 'DUAL'], status='ACTIVE').count()
        context['beef_cattle'] = Cattle.objects.filter(cattle_type__in=['BEEF', 'DUAL'], status='ACTIVE').count()
        
        # Milk Statistics
        context['today_milk'] = MilkRecord.objects.filter(date=today).aggregate(total=Sum('quantity'))['total'] or 0
        context['monthly_milk'] = MilkRecord.objects.filter(date__gte=first_day_month).aggregate(total=Sum('quantity'))['total'] or 0
        context['avg_fat'] = MilkRecord.objects.filter(date=today).aggregate(avg=Avg('fat_percentage'))['avg'] or 0
        
        # Health Statistics
        context['health_alerts'] = HealthRecord.objects.filter(is_emergency=True, date__gte=today - timedelta(days=7)).count()
        context['emergency_count'] = HealthRecord.objects.filter(is_emergency=True).count()
        context['upcoming_vaccinations'] = VaccinationSchedule.objects.filter(
            scheduled_date__gte=today, is_completed=False
        ).count()
        context['overdue_vaccinations'] = VaccinationSchedule.objects.filter(
            scheduled_date__lt=today, is_completed=False
        ).count()
        
        # Breeding Statistics
        context['in_heat'] = Cattle.objects.filter(
            gender='F', status='ACTIVE',
            breeding_records__status='BRED',
            breeding_records__breeding_date__gte=today - timedelta(days=21)
        ).distinct().count()
        
        context['pregnant'] = BreedingRecord.objects.filter(is_pregnant=True, status='CONFIRMED').count()
        context['due_to_calve'] = BreedingRecord.objects.filter(
            expected_calving_date__range=[today, today + timedelta(days=30)],
            is_pregnant=True
        ).count()
        
        # Weight Statistics
        context['weight_records'] = WeightRecord.objects.count()
        context['avg_gain'] = WeightRecord.objects.filter(
            daily_gain__isnull=False
        ).aggregate(avg=Avg('daily_gain'))['avg'] or 0
        
        # Feeding Statistics
        context['today_feedings'] = FeedingRecord.objects.filter(date=today).count()
        context['total_feed'] = FeedingRecord.objects.aggregate(total=Sum('quantity'))['total'] or 0
        
        # Sales Statistics
        context['today_milk_sales'] = MilkSale.objects.filter(date=today).aggregate(
            total_qty=Sum('quantity'),
            total_amount=Sum('total_amount')
        )
        context['monthly_revenue'] = MilkSale.objects.filter(
            date__gte=first_day_month
        ).aggregate(total=Sum('total_amount'))['total'] or 0
        
        return context


# ==================== API VIEWS FOR DASHBOARD ====================

class DashboardStatsAPIView(LoginRequiredMixin, View):
    """API endpoint for dashboard statistics"""
    
    def get(self, request):
        today = timezone.now().date()
        week_ago = today - timedelta(days=7)
        month_ago = today - timedelta(days=30)
        first_day_month = today.replace(day=1)
        
        data = {
            'cattle': {
                'total': Cattle.objects.count(),
                'active': Cattle.objects.filter(status='ACTIVE').count(),
                'dairy': Cattle.objects.filter(cattle_type__in=['DAIRY', 'DUAL'], status='ACTIVE').count(),
                'beef': Cattle.objects.filter(cattle_type__in=['BEEF', 'DUAL'], status='ACTIVE').count(),
            },
            'milk': {
                'today': float(MilkRecord.objects.filter(date=today).aggregate(total=Sum('quantity'))['total'] or 0),
                'week': float(MilkRecord.objects.filter(date__gte=week_ago).aggregate(total=Sum('quantity'))['total'] or 0),
                'month': float(MilkRecord.objects.filter(date__gte=month_ago).aggregate(total=Sum('quantity'))['total'] or 0),
                'avg_fat': float(MilkRecord.objects.filter(date=today).aggregate(avg=Avg('fat_percentage'))['avg'] or 0),
            },
            'health': {
                'alerts': HealthRecord.objects.filter(is_emergency=True, date__gte=week_ago).count(),
                'emergencies': HealthRecord.objects.filter(is_emergency=True).count(),
                'upcoming_vaccinations': VaccinationSchedule.objects.filter(
                    scheduled_date__gte=today, is_completed=False
                ).count(),
                'overdue_vaccinations': VaccinationSchedule.objects.filter(
                    scheduled_date__lt=today, is_completed=False
                ).count(),
            },
            'breeding': {
                'in_heat': Cattle.objects.filter(
                    gender='F', status='ACTIVE',
                    breeding_records__status='BRED',
                    breeding_records__breeding_date__gte=today - timedelta(days=21)
                ).distinct().count(),
                'pregnant': BreedingRecord.objects.filter(is_pregnant=True, status='CONFIRMED').count(),
                'due_to_calve': BreedingRecord.objects.filter(
                    expected_calving_date__range=[today, today + timedelta(days=30)],
                    is_pregnant=True
                ).count(),
                'due_this_month': BreedingRecord.objects.filter(
                    expected_calving_date__year=today.year,
                    expected_calving_date__month=today.month,
                    is_pregnant=True
                ).count(),
            },
            'weight': {
                'records': WeightRecord.objects.count(),
                'avg_gain': float(WeightRecord.objects.filter(
                    daily_gain__isnull=False
                ).aggregate(avg=Avg('daily_gain'))['avg'] or 0),
            },
            'feeding': {
                'today': FeedingRecord.objects.filter(date=today).count(),
                'total': float(FeedingRecord.objects.aggregate(total=Sum('quantity'))['total'] or 0),
            },
            'sales': {
                'today_quantity': float(MilkSale.objects.filter(date=today).aggregate(total=Sum('quantity'))['total'] or 0),
                'today_revenue': float(MilkSale.objects.filter(date=today).aggregate(total=Sum('total_amount'))['total'] or 0),
            },
            'finance': {
                'monthly_revenue': float(MilkSale.objects.filter(
                    date__gte=first_day_month
                ).aggregate(total=Sum('total_amount'))['total'] or 0),
                'revenue_trend': 12.5,  # This would be calculated from actual data
            },
            'trends': {
                'cattle': 5,
                'milk': 8,
            }
        }
        
        return JsonResponse({'success': True, 'data': data})


class MilkChartDataAPIView(LoginRequiredMixin, View):
    """API endpoint for milk production chart data"""
    
    def get(self, request):
        period = request.GET.get('period', 'week')
        today = timezone.now().date()
        
        if period == 'week':
            labels = []
            values = []
            for i in range(6, -1, -1):
                date = today - timedelta(days=i)
                labels.append(date.strftime('%a'))
                total = MilkRecord.objects.filter(date=date).aggregate(total=Sum('quantity'))['total'] or 0
                values.append(float(total))
        elif period == 'month':
            labels = []
            values = []
            for i in range(3, -1, -1):
                week_start = today - timedelta(days=(i+1)*7)
                week_end = today - timedelta(days=i*7)
                labels.append(f'Week {4-i}')
                total = MilkRecord.objects.filter(date__range=[week_start, week_end]).aggregate(total=Sum('quantity'))['total'] or 0
                values.append(float(total))
        else:  # year
            labels = []
            values = []
            for i in range(11, -1, -1):
                month = today - timedelta(days=30*i)
                labels.append(month.strftime('%b'))
                month_start = month.replace(day=1)
                if month.month == 12:
                    month_end = month.replace(day=31)
                else:
                    month_end = month.replace(month=month.month+1, day=1) - timedelta(days=1)
                total = MilkRecord.objects.filter(date__range=[month_start, month_end]).aggregate(total=Sum('quantity'))['total'] or 0
                values.append(float(total))
        
        return JsonResponse({
            'success': True,
            'labels': labels,
            'values': values
        })


class RecentActivityAPIView(LoginRequiredMixin, View):
    """API endpoint for recent activities"""
    
    def get(self, request):
        activities = []
        
        # Recent milk records
        for record in MilkRecord.objects.select_related('cattle').order_by('-created_at')[:3]:
            activities.append({
                'icon': 'droplet',
                'color': 'warning',
                'description': f"Milk recorded: {record.cattle.tag_number} - {record.quantity}L",
                'time': record.created_at.strftime('%H:%M %p'),
            })
        
        # Recent health records
        for record in HealthRecord.objects.select_related('cattle').order_by('-created_at')[:3]:
            activities.append({
                'icon': 'heart-pulse',
                'color': 'danger',
                'description': f"{record.get_health_type_display()}: {record.cattle.tag_number}",
                'time': record.created_at.strftime('%H:%M %p'),
            })
        
        # Recent cattle additions
        for cattle in Cattle.objects.order_by('-created_at')[:3]:
            activities.append({
                'icon': 'shield',
                'color': 'primary',
                'description': f"New cattle added: {cattle.tag_number}",
                'time': cattle.created_at.strftime('%H:%M %p'),
            })
        
        # Sort by time (most recent first)
        activities.sort(key=lambda x: x['time'], reverse=True)
        
        return JsonResponse({'success': True, 'activities': activities[:10]})


class NotificationsAPIView(LoginRequiredMixin, View):
    """API endpoint for notifications"""
    
    def get(self, request):
        today = timezone.now().date()
        notifications = []
        
        # Overdue vaccinations
        overdue_vax = VaccinationSchedule.objects.filter(
            scheduled_date__lt=today, is_completed=False
        ).select_related('cattle')[:5]
        
        for vax in overdue_vax:
            notifications.append({
                'type': 'danger',
                'icon': 'exclamation-triangle',
                'title': 'Overdue Vaccination',
                'message': f"{vax.cattle.tag_number} - {vax.get_vaccine_type_display()} overdue",
                'action_url': f"/dairy/vaccination/{vax.id}/"
            })
        
        # Due soon vaccinations
        due_vax = VaccinationSchedule.objects.filter(
            scheduled_date__range=[today, today + timedelta(days=7)],
            is_completed=False
        ).select_related('cattle')[:5]
        
        for vax in due_vax:
            notifications.append({
                'type': 'warning',
                'icon': 'clock',
                'title': 'Vaccination Due Soon',
                'message': f"{vax.cattle.tag_number} - {vax.get_vaccine_type_display()} in { (vax.scheduled_date - today).days } days",
                'action_url': f"/dairy/vaccination/{vax.id}/"
            })
        
        # Emergency health cases
        emergencies = HealthRecord.objects.filter(
            is_emergency=True, date__gte=today - timedelta(days=7)
        ).select_related('cattle')[:5]
        
        for emergency in emergencies:
            notifications.append({
                'type': 'danger',
                'icon': 'heart-pulse',
                'title': 'Emergency Case',
                'message': f"{emergency.cattle.tag_number} - {emergency.diagnosis}",
                'action_url': f"/dairy/health/{emergency.id}/"
            })
        
        # Due to calve
        due_calve = BreedingRecord.objects.filter(
            expected_calving_date__range=[today, today + timedelta(days=7)],
            is_pregnant=True
        ).select_related('cattle')[:5]
        
        for calving in due_calve:
            notifications.append({
                'type': 'success',
                'icon': 'egg',
                'title': 'Due to Calve',
                'message': f"{calving.cattle.tag_number} due in { (calving.expected_calving_date - today).days } days",
                'action_url': f"/dairy/breeding/{calving.id}/"
            })
        
        return JsonResponse({
            'success': True,
            'notifications': notifications[:10],
            'total': len(notifications)
        })


# ==================== CATTLE VIEWS ====================

class CattleListView(LoginRequiredMixin, ListView):
    """List all cattle"""
    model = Cattle
    template_name = 'dairy/cattle/list.html'
    context_object_name = 'cattle'
    paginate_by = 20
    
    def get_queryset(self):
        queryset = super().get_queryset().select_related('sire', 'dam', 'created_by')
        
        # Filter by type
        cattle_type = self.request.GET.get('type')
        if cattle_type:
            queryset = queryset.filter(cattle_type=cattle_type)
        
        # Filter by status
        status = self.request.GET.get('status')
        if status:
            queryset = queryset.filter(status=status)
        
        # Filter by gender
        gender = self.request.GET.get('gender')
        if gender:
            queryset = queryset.filter(gender=gender)
        
        # Search
        search = self.request.GET.get('search')
        if search:
            queryset = queryset.filter(
                Q(tag_number__icontains=search) |
                Q(name__icontains=search) |
                Q(breed__icontains=search) |
                Q(location__icontains=search)
            )
        
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['total_count'] = self.get_queryset().count()
        context['dairy_count'] = self.get_queryset().filter(cattle_type__in=['DAIRY', 'DUAL']).count()
        context['beef_count'] = self.get_queryset().filter(cattle_type__in=['BEEF', 'DUAL']).count()
        context['active_count'] = self.get_queryset().filter(status='ACTIVE').count()
        
        # Filter badges
        context['current_type'] = self.request.GET.get('type', '')
        context['current_status'] = self.request.GET.get('status', '')
        context['current_gender'] = self.request.GET.get('gender', '')
        context['search_query'] = self.request.GET.get('search', '')
        
        return context


class CattleDetailView(LoginRequiredMixin, DetailView):
    model = Cattle
    template_name = 'dairy/cattle/detail.html'
    context_object_name = 'cattle'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        cattle = self.get_object()
        today = timezone.now().date()
        
        # Related records
        context['milk_records'] = MilkRecord.objects.filter(cattle=cattle).order_by('-date', '-session')[:10]
        context['health_records'] = HealthRecord.objects.filter(cattle=cattle).order_by('-date')[:5]
        context['weight_records'] = WeightRecord.objects.filter(cattle=cattle).order_by('-date')[:5]
        context['feeding_records'] = FeedingRecord.objects.filter(cattle=cattle).order_by('-date', '-feed_time')[:5]
        context['breeding_records'] = BreedingRecord.objects.filter(cattle=cattle).order_by('-breeding_date')[:5]
        context['vaccinations'] = VaccinationSchedule.objects.filter(cattle=cattle).order_by('-scheduled_date')[:5]
        context['today'] = today
        
        # Statistics
        context['total_milk'] = MilkRecord.objects.filter(cattle=cattle).aggregate(total=Sum('quantity'))['total'] or 0
        context['avg_fat'] = MilkRecord.objects.filter(cattle=cattle).aggregate(avg=Avg('fat_percentage'))['avg'] or 0
        context['total_expenses'] = cattle.total_expenses()
        context['total_revenue'] = 0  # Changed: milk sales are global, not per cattle
        context['net_profit'] = cattle.net_profit()
        
        # Weight gain calculation
        if context['weight_records'] and len(context['weight_records']) >= 2:
            first_weight = context['weight_records'].last()
            last_weight = context['weight_records'].first()
            days_diff = (last_weight.date - first_weight.date).days
            if days_diff > 0:
                daily_gain = (last_weight.weight - first_weight.weight) / days_diff
            else:
                daily_gain = 0
        else:
            daily_gain = 0
        
        context['daily_gain'] = round(daily_gain, 2)
        context['age_in_months'] = cattle.age_in_months()
        
        return context

class CattleCreateView(LoginRequiredMixin, CreateView):
    """Create new cattle"""
    model = Cattle
    form_class = CattleForm
    template_name = 'dairy/cattle/form.html'
    success_url = reverse_lazy('dairy:cattle_list')
    
    def form_valid(self, form):
        form.instance.created_by = self.request.user
        response = super().form_valid(form)
        messages.success(self.request, f'Cattle {form.instance.tag_number} added successfully!')
        return response
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Add New Cattle'
        context['submit_text'] = 'Add Cattle'
        context['action'] = 'add'
        return context


class CattleUpdateView(LoginRequiredMixin, UpdateView):
    """Update cattle"""
    model = Cattle
    form_class = CattleForm
    template_name = 'dairy/cattle/form.html'
    success_url = reverse_lazy('dairy:cattle_list')
    
    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, f'Cattle {form.instance.tag_number} updated successfully!')
        return response
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Edit Cattle'
        context['submit_text'] = 'Update Cattle'
        context['action'] = 'edit'
        return context


class CattleDeleteView(LoginRequiredMixin, DeleteView):
    """Delete cattle"""
    model = Cattle
    template_name = 'dairy/cattle/delete.html'
    success_url = reverse_lazy('dairy:cattle_list')
    
    def delete(self, request, *args, **kwargs):
        cattle = self.get_object()
        messages.success(request, f'Cattle {cattle.tag_number} deleted successfully!')
        return super().delete(request, *args, **kwargs)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        cattle = self.get_object()
        context['milk_count'] = MilkRecord.objects.filter(cattle=cattle).count()
        context['health_count'] = HealthRecord.objects.filter(cattle=cattle).count()
        context['weight_count'] = WeightRecord.objects.filter(cattle=cattle).count()
        context['breeding_count'] = BreedingRecord.objects.filter(cattle=cattle).count()
        context['total_records'] = context['milk_count'] + context['health_count'] + context['weight_count'] + context['breeding_count']
        return context


# ==================== MILK RECORD VIEWS ====================

class MilkRecordListView(LoginRequiredMixin, ListView):
    """List all milk records"""
    model = MilkRecord
    template_name = 'dairy/milk/list.html'
    context_object_name = 'records'
    paginate_by = 30
    
    def get_queryset(self):
        return MilkRecord.objects.select_related('cattle', 'recorded_by').order_by('-date', '-session')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        today = timezone.now().date()
        
        context['today_total'] = MilkRecord.objects.filter(date=today).aggregate(total=Sum('quantity'))['total'] or 0
        context['weekly_total'] = MilkRecord.objects.filter(date__gte=today - timedelta(days=7)).aggregate(total=Sum('quantity'))['total'] or 0
        context['monthly_total'] = MilkRecord.objects.filter(date__gte=today - timedelta(days=30)).aggregate(total=Sum('quantity'))['total'] or 0
        context['avg_fat'] = MilkRecord.objects.filter(date=today).aggregate(avg=Avg('fat_percentage'))['avg'] or 0
        
        return context


class MilkRecordCreateView(LoginRequiredMixin, CreateView):
    """Create new milk record"""
    model = MilkRecord
    form_class = MilkRecordForm
    template_name = 'dairy/milk/form.html'
    success_url = reverse_lazy('dairy:milk_list')
    
    def form_valid(self, form):
        form.instance.recorded_by = self.request.user
        response = super().form_valid(form)
        messages.success(self.request, 'Milk record added successfully!')
        return response
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Add Milk Record'
        context['submit_text'] = 'Add Record'
        context['action'] = 'add'
        return context


class MilkRecordUpdateView(LoginRequiredMixin, UpdateView):
    """Update milk record"""
    model = MilkRecord
    form_class = MilkRecordForm
    template_name = 'dairy/milk/form.html'
    success_url = reverse_lazy('dairy:milk_list')
    
    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, 'Milk record updated successfully!')
        return response
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Edit Milk Record'
        context['submit_text'] = 'Update Record'
        context['action'] = 'edit'
        return context


class MilkRecordDeleteView(LoginRequiredMixin, DeleteView):
    """Delete milk record"""
    model = MilkRecord
    template_name = 'dairy/milk/delete.html'
    success_url = reverse_lazy('dairy:milk_list')
    
    def delete(self, request, *args, **kwargs):
        record = self.get_object()
        messages.success(request, f'Milk record for {record.cattle.tag_number} on {record.date} deleted successfully!')
        return super().delete(request, *args, **kwargs)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        record = self.get_object()
        context['cattle_total_milk'] = MilkRecord.objects.filter(cattle=record.cattle).aggregate(total=Sum('quantity'))['total'] or 0
        context['cattle_daily_avg'] = MilkRecord.objects.filter(cattle=record.cattle).aggregate(avg=Avg('quantity'))['avg'] or 0
        return context


# ==================== MILK SALE VIEWS ====================

class MilkSaleListView(LoginRequiredMixin, ListView):
    """List all milk sales"""
    model = MilkSale
    template_name = 'dairy/milk_sale/list.html'
    context_object_name = 'sales'
    paginate_by = 30
    
    def get_queryset(self):
        return MilkSale.objects.all().order_by('-date')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        today = timezone.now().date()
        
        context['today_total'] = MilkSale.objects.filter(date=today).aggregate(total=Sum('total_amount'))['total'] or 0
        context['monthly_total'] = MilkSale.objects.filter(date__gte=today.replace(day=1)).aggregate(total=Sum('total_amount'))['total'] or 0
        context['yearly_total'] = MilkSale.objects.filter(date__year=today.year).aggregate(total=Sum('total_amount'))['total'] or 0
        
        return context


class MilkSaleCreateView(LoginRequiredMixin, CreateView):
    """Create new milk sale"""
    model = MilkSale
    form_class = MilkSaleForm
    template_name = 'dairy/milk_sale/form.html'
    success_url = reverse_lazy('dairy:milk_sale_list')
    
    def form_valid(self, form):
        form.instance.created_by = self.request.user
        response = super().form_valid(form)
        messages.success(self.request, f'Milk sale of ৳{form.instance.total_amount} added successfully!')
        return response
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Add Milk Sale'
        context['submit_text'] = 'Add Sale'
        return context


class MilkSaleUpdateView(LoginRequiredMixin, UpdateView):
    """Update milk sale"""
    model = MilkSale
    form_class = MilkSaleForm
    template_name = 'dairy/milk_sale/form.html'
    success_url = reverse_lazy('dairy:milk_sale_list')
    
    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, 'Milk sale updated successfully!')
        return response


class MilkSaleDeleteView(LoginRequiredMixin, DeleteView):
    """Delete milk sale"""
    model = MilkSale
    template_name = 'dairy/milk_sale/delete.html'
    success_url = reverse_lazy('dairy:milk_sale_list')
    
    def delete(self, request, *args, **kwargs):
        messages.success(request, 'Milk sale deleted successfully!')
        return super().delete(request, *args, **kwargs)


# ==================== CATTLE SALE VIEWS ====================

class CattleSaleListView(LoginRequiredMixin, ListView):
    """List all cattle sales"""
    model = CattleSale
    template_name = 'dairy/cattle_sale/list.html'
    context_object_name = 'sales'
    paginate_by = 30
    
    def get_queryset(self):
        return CattleSale.objects.select_related('cattle', 'created_by').order_by('-sale_date')


class CattleSaleCreateView(LoginRequiredMixin, CreateView):
    """Create new cattle sale"""
    model = CattleSale
    form_class = CattleSaleForm
    template_name = 'dairy/cattle_sale/form.html'
    success_url = reverse_lazy('dairy:cattle_sale_list')
    
    def form_valid(self, form):
        form.instance.created_by = self.request.user
        cattle = form.cleaned_data['cattle']
        cattle.status = 'SOLD'
        cattle.save()
        
        response = super().form_valid(form)
        messages.success(self.request, f'{cattle.tag_number} sold for ৳{form.instance.sale_price}!')
        return response

class CattleDetailView(LoginRequiredMixin, DetailView):
    model = Cattle
    template_name = 'dairy/cattle/detail.html'
    context_object_name = 'cattle'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        cattle = self.get_object()
        today = timezone.now().date()
        
        # Related records
        context['milk_records'] = MilkRecord.objects.filter(cattle=cattle).order_by('-date', '-session')[:10]
        context['health_records'] = HealthRecord.objects.filter(cattle=cattle).order_by('-date')[:5]
        context['weight_records'] = WeightRecord.objects.filter(cattle=cattle).order_by('-date')[:5]
        context['feeding_records'] = FeedingRecord.objects.filter(cattle=cattle).order_by('-date', '-feed_time')[:5]
        context['breeding_records'] = BreedingRecord.objects.filter(cattle=cattle).order_by('-breeding_date')[:5]
        context['vaccinations'] = VaccinationSchedule.objects.filter(cattle=cattle).order_by('-scheduled_date')[:5]
        context['today'] = today
        
        # Statistics
        context['total_milk'] = MilkRecord.objects.filter(cattle=cattle).aggregate(total=Sum('quantity'))['total'] or 0
        context['avg_fat'] = MilkRecord.objects.filter(cattle=cattle).aggregate(avg=Avg('fat_percentage'))['avg'] or 0
        context['total_expenses'] = cattle.total_expenses()
        context['total_revenue'] = cattle.total_milk_revenue()
        context['net_profit'] = cattle.net_profit()
        
        return context


class CattleSaleUpdateView(LoginRequiredMixin, UpdateView):
    """Update cattle sale"""
    model = CattleSale
    form_class = CattleSaleForm
    template_name = 'dairy/cattle_sale/form.html'
    success_url = reverse_lazy('dairy:cattle_sale_list')


class CattleSaleDeleteView(LoginRequiredMixin, DeleteView):
    model = CattleSale
    template_name = 'dairy/cattle_sale/delete.html'
    success_url = reverse_lazy('dairy:cattle_sale_list')
    
    def delete(self, request, *args, **kwargs):
        self.object = self.get_object()
        cattle = self.object.cattle
        cattle.status = 'ACTIVE'
        cattle.save()
        messages.success(request, f'Sale record deleted and {cattle.tag_number} marked as active.')
        return super().delete(request, *args, **kwargs)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['sale'] = self.get_object()
        return context


# ==================== HEALTH RECORD VIEWS ====================

class HealthRecordListView(LoginRequiredMixin, ListView):
    """List all health records"""
    model = HealthRecord
    template_name = 'dairy/health/list.html'
    context_object_name = 'records'
    paginate_by = 30
    
    def get_queryset(self):
        return HealthRecord.objects.select_related('cattle', 'created_by').order_by('-date')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        today = timezone.now().date()
        
        context['emergency_count'] = HealthRecord.objects.filter(is_emergency=True, date__gte=today - timedelta(days=7)).count()
        context['followup_count'] = HealthRecord.objects.filter(next_checkup_date__gte=today).count()
        context['overdue_followups'] = HealthRecord.objects.filter(next_checkup_date__lt=today, next_checkup_date__isnull=False).count()
        
        return context


class HealthRecordCreateView(LoginRequiredMixin, CreateView):
    """Create new health record"""
    model = HealthRecord
    form_class = HealthRecordForm
    template_name = 'dairy/health/form.html'
    success_url = reverse_lazy('dairy:health_list')
    
    def form_valid(self, form):
        form.instance.created_by = self.request.user
        response = super().form_valid(form)
        messages.success(self.request, 'Health record added successfully!')
        return response
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Add Health Record'
        context['submit_text'] = 'Add Record'
        return context


class HealthRecordUpdateView(LoginRequiredMixin, UpdateView):
    """Update health record"""
    model = HealthRecord
    form_class = HealthRecordForm
    template_name = 'dairy/health/form.html'
    success_url = reverse_lazy('dairy:health_list')


class HealthRecordDeleteView(LoginRequiredMixin, DeleteView):
    """Delete health record"""
    model = HealthRecord
    template_name = 'dairy/health/delete.html'
    success_url = reverse_lazy('dairy:health_list')


# ==================== WEIGHT RECORD VIEWS ====================

class WeightRecordListView(LoginRequiredMixin, ListView):
    """List all weight records"""
    model = WeightRecord
    template_name = 'dairy/weight/list.html'
    context_object_name = 'records'
    paginate_by = 30
    
    def get_queryset(self):
        return WeightRecord.objects.select_related('cattle', 'recorded_by').order_by('-date')


class WeightRecordCreateView(LoginRequiredMixin, CreateView):
    """Create new weight record"""
    model = WeightRecord
    form_class = WeightRecordForm
    template_name = 'dairy/weight/form.html'
    success_url = reverse_lazy('dairy:weight_list')
    
    def form_valid(self, form):
        form.instance.recorded_by = self.request.user
        response = super().form_valid(form)
        messages.success(self.request, 'Weight record added successfully!')
        return response
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Add Weight Record'
        context['submit_text'] = 'Add Record'
        return context


class WeightRecordUpdateView(LoginRequiredMixin, UpdateView):
    """Update weight record"""
    model = WeightRecord
    form_class = WeightRecordForm
    template_name = 'dairy/weight/form.html'
    success_url = reverse_lazy('dairy:weight_list')


class WeightRecordDeleteView(LoginRequiredMixin, DeleteView):
    """Delete weight record"""
    model = WeightRecord
    template_name = 'dairy/weight/delete.html'
    success_url = reverse_lazy('dairy:weight_list')


# ==================== FEEDING RECORD VIEWS ====================

class FeedingRecordListView(LoginRequiredMixin, ListView):
    """List all feeding records"""
    model = FeedingRecord
    template_name = 'dairy/feeding/list.html'
    context_object_name = 'records'
    paginate_by = 30
    
    def get_queryset(self):
        return FeedingRecord.objects.select_related('cattle', 'fed_by').order_by('-date', '-feed_time')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        today = timezone.now().date()
        
        context['today_total'] = FeedingRecord.objects.filter(date=today).aggregate(total=Sum('quantity'))['total'] or 0
        context['today_cost'] = FeedingRecord.objects.filter(date=today).aggregate(total=Sum('total_cost'))['total'] or 0
        
        return context


class FeedingRecordCreateView(LoginRequiredMixin, CreateView):
    """Create new feeding record"""
    model = FeedingRecord
    form_class = FeedingRecordForm
    template_name = 'dairy/feeding/form.html'
    success_url = reverse_lazy('dairy:feeding_list')
    
    def form_valid(self, form):
        form.instance.fed_by = self.request.user
        response = super().form_valid(form)
        messages.success(self.request, 'Feeding record added successfully!')
        return response
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Add Feeding Record'
        context['submit_text'] = 'Add Record'
        return context


class FeedingRecordUpdateView(LoginRequiredMixin, UpdateView):
    """Update feeding record"""
    model = FeedingRecord
    form_class = FeedingRecordForm
    template_name = 'dairy/feeding/form.html'
    success_url = reverse_lazy('dairy:feeding_list')


class FeedingRecordDeleteView(LoginRequiredMixin, DeleteView):
    """Delete feeding record"""
    model = FeedingRecord
    template_name = 'dairy/feeding/delete.html'
    success_url = reverse_lazy('dairy:feeding_list')


# ==================== BREEDING RECORD VIEWS ====================

class BreedingRecordListView(LoginRequiredMixin, ListView):
    """List all breeding records"""
    model = BreedingRecord
    template_name = 'dairy/breeding/list.html'
    context_object_name = 'records'
    paginate_by = 30
    
    def get_queryset(self):
        return BreedingRecord.objects.select_related('cattle', 'sire', 'offspring', 'created_by').order_by('-breeding_date')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        today = timezone.now().date()
        
        context['pregnant_count'] = BreedingRecord.objects.filter(is_pregnant=True, status='CONFIRMED').count()
        context['due_this_month'] = BreedingRecord.objects.filter(
            expected_calving_date__year=today.year,
            expected_calving_date__month=today.month,
            is_pregnant=True
        ).count()
        
        return context


class BreedingRecordCreateView(LoginRequiredMixin, CreateView):
    """Create new breeding record"""
    model = BreedingRecord
    form_class = BreedingRecordForm
    template_name = 'dairy/breeding/form.html'
    success_url = reverse_lazy('dairy:breeding_list')
    
    def form_valid(self, form):
        form.instance.created_by = self.request.user
        response = super().form_valid(form)
        messages.success(self.request, 'Breeding record added successfully!')
        return response
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Add Breeding Record'
        context['submit_text'] = 'Add Record'
        return context


class BreedingRecordUpdateView(LoginRequiredMixin, UpdateView):
    """Update breeding record"""
    model = BreedingRecord
    form_class = BreedingRecordForm
    template_name = 'dairy/breeding/form.html'
    success_url = reverse_lazy('dairy:breeding_list')


class BreedingRecordDeleteView(LoginRequiredMixin, DeleteView):
    """Delete breeding record"""
    model = BreedingRecord
    template_name = 'dairy/breeding/delete.html'
    success_url = reverse_lazy('dairy:breeding_list')


# ==================== VACCINATION VIEWS ====================

class VaccinationListView(LoginRequiredMixin, ListView):
    """List all vaccinations"""
    model = VaccinationSchedule
    template_name = 'dairy/vaccination/list.html'
    context_object_name = 'vaccinations'
    paginate_by = 30
    
    def get_queryset(self):
        return VaccinationSchedule.objects.select_related('cattle', 'administered_by').order_by('scheduled_date')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        today = timezone.now().date()
        
        context['upcoming'] = VaccinationSchedule.objects.filter(
            scheduled_date__gte=today, is_completed=False
        ).count()
        
        context['overdue'] = VaccinationSchedule.objects.filter(
            scheduled_date__lt=today, is_completed=False
        ).count()
        
        context['completed'] = VaccinationSchedule.objects.filter(is_completed=True).count()
        
        return context


class VaccinationCreateView(LoginRequiredMixin, CreateView):
    """Create new vaccination"""
    model = VaccinationSchedule
    form_class = VaccinationForm
    template_name = 'dairy/vaccination/form.html'
    success_url = reverse_lazy('dairy:vaccination_list')
    
    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, 'Vaccination scheduled successfully!')
        return response
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Schedule Vaccination'
        context['submit_text'] = 'Schedule'
        return context


class VaccinationUpdateView(LoginRequiredMixin, UpdateView):
    """Update vaccination"""
    model = VaccinationSchedule
    form_class = VaccinationForm
    template_name = 'dairy/vaccination/form.html'
    success_url = reverse_lazy('dairy:vaccination_list')
    
    def form_valid(self, form):
        if form.instance.is_completed and not form.instance.administered_date:
            form.instance.administered_date = timezone.now().date()
            form.instance.administered_by = self.request.user
        response = super().form_valid(form)
        messages.success(self.request, 'Vaccination updated successfully!')
        return response


class VaccinationDeleteView(LoginRequiredMixin, DeleteView):
    """Delete vaccination"""
    model = VaccinationSchedule
    template_name = 'dairy/vaccination/delete.html'
    success_url = reverse_lazy('dairy:vaccination_list')


# ==================== EXPENSE VIEWS ====================

class ExpenseListView(LoginRequiredMixin, ListView):
    """List all expenses"""
    model = Expense
    template_name = 'dairy/expense/list.html'
    context_object_name = 'expenses'
    paginate_by = 30
    
    def get_queryset(self):
        return Expense.objects.select_related('category', 'cattle', 'created_by').order_by('-date')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        today = timezone.now().date()
        
        context['monthly_total'] = Expense.objects.filter(date__gte=today.replace(day=1)).aggregate(total=Sum('amount'))['total'] or 0
        context['yearly_total'] = Expense.objects.filter(date__year=today.year).aggregate(total=Sum('amount'))['total'] or 0
        
        return context


class ExpenseCreateView(LoginRequiredMixin, CreateView):
    """Create new expense"""
    model = Expense
    form_class = ExpenseForm
    template_name = 'dairy/expense/form.html'
    success_url = reverse_lazy('dairy:expense_list')
    
    def form_valid(self, form):
        form.instance.created_by = self.request.user
        response = super().form_valid(form)
        messages.success(self.request, 'Expense added successfully!')
        return response


class ExpenseUpdateView(LoginRequiredMixin, UpdateView):
    """Update expense"""
    model = Expense
    form_class = ExpenseForm
    template_name = 'dairy/expense/form.html'
    success_url = reverse_lazy('dairy:expense_list')


class ExpenseDeleteView(LoginRequiredMixin, DeleteView):
    """Delete expense"""
    model = Expense
    template_name = 'dairy/expense/delete.html'
    success_url = reverse_lazy('dairy:expense_list')


# ==================== INVESTMENT VIEWS ====================

class InvestmentListView(LoginRequiredMixin, ListView):
    """List all investments"""
    model = Investment
    template_name = 'dairy/investment/list.html'
    context_object_name = 'investments'
    paginate_by = 30
    
    def get_queryset(self):
        return Investment.objects.select_related('cattle', 'created_by').order_by('-date')


class InvestmentCreateView(LoginRequiredMixin, CreateView):
    """Create new investment"""
    model = Investment
    form_class = InvestmentForm
    template_name = 'dairy/investment/form.html'
    success_url = reverse_lazy('dairy:investment_list')
    
    def form_valid(self, form):
        form.instance.created_by = self.request.user
        response = super().form_valid(form)
        messages.success(self.request, 'Investment added successfully!')
        return response


class InvestmentUpdateView(LoginRequiredMixin, UpdateView):
    """Update investment"""
    model = Investment
    form_class = InvestmentForm
    template_name = 'dairy/investment/form.html'
    success_url = reverse_lazy('dairy:investment_list')


class InvestmentDeleteView(LoginRequiredMixin, DeleteView):
    """Delete investment"""
    model = Investment
    template_name = 'dairy/investment/delete.html'
    success_url = reverse_lazy('dairy:investment_list')


# ==================== REPORT VIEWS ====================

class MonthlyReportView(LoginRequiredMixin, TemplateView):
    """Monthly financial report"""
    template_name = 'dairy/reports/monthly.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        year = int(self.request.GET.get('year', timezone.now().year))
        month = int(self.request.GET.get('month', timezone.now().month))
        
        start_date = datetime(year, month, 1).date()
        if month == 12:
            end_date = datetime(year + 1, 1, 1).date() - timedelta(days=1)
        else:
            end_date = datetime(year, month + 1, 1).date() - timedelta(days=1)
        
        # Milk Sales
        milk_sales = MilkSale.objects.filter(date__range=[start_date, end_date])
        context['milk_sales'] = milk_sales
        context['total_milk_sales'] = milk_sales.aggregate(total=Sum('total_amount'))['total'] or 0
        context['total_milk_quantity'] = milk_sales.aggregate(total=Sum('quantity'))['total'] or 0
        
        # Cattle Sales
        cattle_sales = CattleSale.objects.filter(sale_date__range=[start_date, end_date])
        context['cattle_sales'] = cattle_sales
        context['total_cattle_sales'] = cattle_sales.aggregate(total=Sum('sale_price'))['total'] or 0
        
        # Expenses
        expenses = Expense.objects.filter(date__range=[start_date, end_date])
        context['expenses'] = expenses
        context['total_expenses'] = expenses.aggregate(total=Sum('amount'))['total'] or 0
        
        # Investments
        investments = Investment.objects.filter(date__range=[start_date, end_date])
        context['investments'] = investments
        context['total_investments'] = investments.aggregate(total=Sum('amount'))['total'] or 0
        
        # Summary
        context['total_income'] = context['total_milk_sales'] + context['total_cattle_sales']
        context['net_profit'] = context['total_income'] - context['total_expenses']
        context['year'] = year
        context['month'] = month
        context['month_name'] = start_date.strftime('%B')
        
        return context


class YearlyReportView(LoginRequiredMixin, TemplateView):
    """Yearly financial report"""
    template_name = 'dairy/reports/yearly.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        year = int(self.request.GET.get('year', timezone.now().year))
        
        start_date = datetime(year, 1, 1).date()
        end_date = datetime(year, 12, 31).date()
        
        # Monthly breakdown
        monthly_data = []
        for month in range(1, 13):
            month_start = datetime(year, month, 1).date()
            if month == 12:
                month_end = datetime(year, 12, 31).date()
            else:
                month_end = datetime(year, month + 1, 1).date() - timedelta(days=1)
            
            milk_sales = MilkSale.objects.filter(date__range=[month_start, month_end]).aggregate(total=Sum('total_amount'))['total'] or 0
            expenses = Expense.objects.filter(date__range=[month_start, month_end]).aggregate(total=Sum('amount'))['total'] or 0
            
            monthly_data.append({
                'month': month_start.strftime('%B'),
                'milk_sales': milk_sales,
                'expenses': expenses,
                'profit': milk_sales - expenses
            })
        
        context['monthly_data'] = monthly_data
        
        # Yearly totals
        context['total_milk_sales'] = sum(m['milk_sales'] for m in monthly_data)
        context['total_expenses'] = sum(m['expenses'] for m in monthly_data)
        context['total_profit'] = context['total_milk_sales'] - context['total_expenses']
        context['year'] = year
        
        return context


# ==================== EXPORT VIEWS ====================

class ExportCattleCSVView(LoginRequiredMixin, View):
    """Export cattle data to CSV"""
    
    def get(self, request):
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="cattle_export.csv"'
        
        writer = csv.writer(response)
        writer.writerow(['Tag Number', 'Name', 'Type', 'Breed', 'Gender', 'Birth Date', 'Age', 'Weight', 'Status', 'Location'])
        
        for cattle in Cattle.objects.all():
            writer.writerow([
                cattle.tag_number,
                cattle.name or '',
                cattle.get_cattle_type_display(),
                cattle.get_breed_display(),
                cattle.get_gender_display(),
                cattle.birth_date,
                cattle.age_in_months(),
                cattle.weight,
                cattle.status,
                cattle.location or ''
            ])
        
        return response 
    





# ==================== API VIEWS FOR EACH ENDPOINT ====================

# Cattle API Views
class CattleListAPIView(LoginRequiredMixin, View):
    def get(self, request):
        cattle = Cattle.objects.all().values('id', 'tag_number', 'name', 'cattle_type', 'breed', 'gender', 'status')
        return JsonResponse({'success': True, 'data': list(cattle)})

class CattleDetailAPIView(LoginRequiredMixin, View):
    def get(self, request, cattle_id):
        try:
            cattle = Cattle.objects.get(id=cattle_id)
            data = {
                'id': cattle.id,
                'tag_number': cattle.tag_number,
                'name': cattle.name,
                'cattle_type': cattle.get_cattle_type_display(),
                'breed': cattle.get_breed_display(),
                'gender': cattle.get_gender_display(),
                'birth_date': cattle.birth_date,
                'age_months': cattle.age_in_months(),
                'weight': float(cattle.weight) if cattle.weight else None,
                'status': cattle.status,
                'purchase_price': float(cattle.purchase_price) if cattle.purchase_price else None,
                'current_value': float(cattle.current_value) if cattle.current_value else None,
            }
            return JsonResponse({'success': True, 'data': data})
        except Cattle.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Cattle not found'})

class CattleSearchAPIView(LoginRequiredMixin, View):
    def get(self, request):
        query = request.GET.get('q', '')
        if len(query) < 2:
            return JsonResponse({'success': True, 'data': []})
        
        cattle = Cattle.objects.filter(
            Q(tag_number__icontains=query) |
            Q(name__icontains=query)
        ).values('id', 'tag_number', 'name', 'breed', 'status')[:20]
        
        return JsonResponse({'success': True, 'data': list(cattle)})

class CattleStatsAPIView(LoginRequiredMixin, View):
    def get(self, request):
        total = Cattle.objects.count()
        active = Cattle.objects.filter(status='ACTIVE').count()
        dairy = Cattle.objects.filter(cattle_type__in=['DAIRY', 'DUAL']).count()
        beef = Cattle.objects.filter(cattle_type__in=['BEEF', 'DUAL']).count()
        
        return JsonResponse({
            'success': True,
            'data': {
                'total': total,
                'active': active,
                'dairy': dairy,
                'beef': beef
            }
        })

class CattleFinancialAPIView(LoginRequiredMixin, View):
    def get(self, request, cattle_id):
        try:
            cattle = Cattle.objects.get(id=cattle_id)
            data = {
                'purchase_price': float(cattle.purchase_price) if cattle.purchase_price else 0,
                'current_value': float(cattle.current_value) if cattle.current_value else 0,
                'total_milk_revenue': float(cattle.total_milk_revenue()),
                'total_expenses': float(cattle.total_expenses()),
                'net_profit': float(cattle.net_profit()),
            }
            return JsonResponse({'success': True, 'data': data})
        except Cattle.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Cattle not found'})

class CattleGrowthAPIView(LoginRequiredMixin, View):
    def get(self, request, cattle_id):
        weights = WeightRecord.objects.filter(cattle_id=cattle_id).order_by('date')
        data = {
            'labels': [w.date.strftime('%Y-%m-%d') for w in weights],
            'values': [float(w.weight) for w in weights]
        }
        return JsonResponse({'success': True, 'data': data})

# Milk Record API Views
class MilkRecordListAPIView(LoginRequiredMixin, View):
    def get(self, request):
        records = MilkRecord.objects.select_related('cattle').all().order_by('-date')[:100]
        data = [{
            'id': r.id,
            'date': r.date,
            'cattle_tag': r.cattle.tag_number,
            'session': r.get_session_display(),
            'quantity': float(r.quantity),
            'fat_percentage': float(r.fat_percentage) if r.fat_percentage else None,
        } for r in records]
        return JsonResponse({'success': True, 'data': data})

class MilkRecordDetailAPIView(LoginRequiredMixin, View):
    def get(self, request, record_id):
        try:
            record = MilkRecord.objects.select_related('cattle').get(id=record_id)
            data = {
                'id': record.id,
                'date': record.date,
                'cattle_id': record.cattle.id,
                'cattle_tag': record.cattle.tag_number,
                'session': record.session,
                'session_display': record.get_session_display(),
                'quantity': float(record.quantity),
                'fat_percentage': float(record.fat_percentage) if record.fat_percentage else None,
                'temperature': float(record.temperature) if record.temperature else None,
                'quality_notes': record.quality_notes,
            }
            return JsonResponse({'success': True, 'data': data})
        except MilkRecord.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Record not found'})

class MilkStatsAPIView(LoginRequiredMixin, View):
    def get(self, request):
        today = timezone.now().date()
        week_ago = today - timedelta(days=7)
        month_ago = today - timedelta(days=30)
        
        data = {
            'today': float(MilkRecord.objects.filter(date=today).aggregate(total=Sum('quantity'))['total'] or 0),
            'this_week': float(MilkRecord.objects.filter(date__gte=week_ago).aggregate(total=Sum('quantity'))['total'] or 0),
            'this_month': float(MilkRecord.objects.filter(date__gte=month_ago).aggregate(total=Sum('quantity'))['total'] or 0),
            'avg_fat': float(MilkRecord.objects.filter(date=today).aggregate(avg=Avg('fat_percentage'))['avg'] or 0),
        }
        return JsonResponse({'success': True, 'data': data})

class MilkTodayAPIView(LoginRequiredMixin, View):
    def get(self, request):
        today = timezone.now().date()
        records = MilkRecord.objects.filter(date=today).select_related('cattle')
        data = [{
            'id': r.id,
            'cattle_tag': r.cattle.tag_number,
            'session': r.get_session_display(),
            'quantity': float(r.quantity),
            'fat': float(r.fat_percentage) if r.fat_percentage else None,
        } for r in records]
        return JsonResponse({'success': True, 'data': data})

class MilkByCattleAPIView(LoginRequiredMixin, View):
    def get(self, request, cattle_id):
        records = MilkRecord.objects.filter(cattle_id=cattle_id).order_by('-date')[:30]
        data = [{
            'id': r.id,
            'date': r.date,
            'session': r.get_session_display(),
            'quantity': float(r.quantity),
        } for r in records]
        return JsonResponse({'success': True, 'data': data})

# Milk Sale API Views
class MilkSaleListAPIView(LoginRequiredMixin, View):
    def get(self, request):
        sales = MilkSale.objects.all().order_by('-date')[:100]
        data = [{
            'id': s.id,
            'date': s.date,
            'quantity': float(s.quantity),
            'price_per_liter': float(s.price_per_liter),
            'total_amount': float(s.total_amount),
            'sale_type': s.get_sale_type_display(),
            'customer_name': s.customer_name,
        } for s in sales]
        return JsonResponse({'success': True, 'data': data})

class MilkSaleDetailAPIView(LoginRequiredMixin, View):
    def get(self, request, sale_id):
        try:
            sale = MilkSale.objects.get(id=sale_id)
            data = {
                'id': sale.id,
                'date': sale.date,
                'quantity': float(sale.quantity),
                'price_per_liter': float(sale.price_per_liter),
                'total_amount': float(sale.total_amount),
                'sale_type': sale.sale_type,
                'sale_type_display': sale.get_sale_type_display(),
                'customer_name': sale.customer_name,
                'payment_received': sale.payment_received,
                'notes': sale.notes,
            }
            return JsonResponse({'success': True, 'data': data})
        except MilkSale.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Sale not found'})

class MilkSaleStatsAPIView(LoginRequiredMixin, View):
    def get(self, request):
        today = timezone.now().date()
        first_day_month = today.replace(day=1)
        
        data = {
            'today': float(MilkSale.objects.filter(date=today).aggregate(total=Sum('total_amount'))['total'] or 0),
            'this_month': float(MilkSale.objects.filter(date__gte=first_day_month).aggregate(total=Sum('total_amount'))['total'] or 0),
            'total_quantity': float(MilkSale.objects.aggregate(total=Sum('quantity'))['total'] or 0),
            'total_revenue': float(MilkSale.objects.aggregate(total=Sum('total_amount'))['total'] or 0),
        }
        return JsonResponse({'success': True, 'data': data})

class MilkSaleMonthlyAPIView(LoginRequiredMixin, View):
    def get(self, request):
        year = int(request.GET.get('year', timezone.now().year))
        monthly_data = []
        
        for month in range(1, 13):
            total = MilkSale.objects.filter(
                date__year=year,
                date__month=month
            ).aggregate(total=Sum('total_amount'))['total'] or 0
            monthly_data.append(float(total))
        
        return JsonResponse({'success': True, 'data': monthly_data})

# Cattle Sale API Views
class CattleSaleListAPIView(LoginRequiredMixin, View):
    def get(self, request):
        sales = CattleSale.objects.select_related('cattle').all().order_by('-sale_date')[:100]
        data = [{
            'id': s.id,
            'sale_date': s.sale_date,
            'cattle_tag': s.cattle.tag_number,
            'sale_price': float(s.sale_price),
            'buyer_name': s.buyer_name,
            'profit_loss': float(s.profit_loss()),
        } for s in sales]
        return JsonResponse({'success': True, 'data': data})

class CattleSaleDetailAPIView(LoginRequiredMixin, View):
    def get(self, request, sale_id):
        try:
            sale = CattleSale.objects.select_related('cattle').get(id=sale_id)
            data = {
                'id': sale.id,
                'sale_date': sale.sale_date,
                'cattle_id': sale.cattle.id,
                'cattle_tag': sale.cattle.tag_number,
                'sale_price': float(sale.sale_price),
                'buyer_name': sale.buyer_name,
                'buyer_contact': sale.buyer_contact,
                'payment_received': sale.payment_received,
                'profit_loss': float(sale.profit_loss()),
                'notes': sale.notes,
            }
            return JsonResponse({'success': True, 'data': data})
        except CattleSale.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Sale not found'})

class CattleSaleStatsAPIView(LoginRequiredMixin, View):
    def get(self, request):
        year = timezone.now().year
        data = {
            'total_sales': CattleSale.objects.count(),
            'total_revenue': float(CattleSale.objects.aggregate(total=Sum('sale_price'))['total'] or 0),
            'this_year': float(CattleSale.objects.filter(sale_date__year=year).aggregate(total=Sum('sale_price'))['total'] or 0),
            'avg_price': float(CattleSale.objects.aggregate(avg=Avg('sale_price'))['avg'] or 0),
        }
        return JsonResponse({'success': True, 'data': data})

# Health Record API Views
class HealthRecordListAPIView(LoginRequiredMixin, View):
    def get(self, request):
        records = HealthRecord.objects.select_related('cattle').all().order_by('-date')[:100]
        data = [{
            'id': r.id,
            'date': r.date,
            'cattle_tag': r.cattle.tag_number,
            'health_type': r.get_health_type_display(),
            'diagnosis': r.diagnosis,
            'veterinarian': r.veterinarian,
            'is_emergency': r.is_emergency,
        } for r in records]
        return JsonResponse({'success': True, 'data': data})

class HealthRecordDetailAPIView(LoginRequiredMixin, View):
    def get(self, request, record_id):
        try:
            record = HealthRecord.objects.select_related('cattle').get(id=record_id)
            data = {
                'id': record.id,
                'date': record.date,
                'cattle_id': record.cattle.id,
                'cattle_tag': record.cattle.tag_number,
                'health_type': record.health_type,
                'health_type_display': record.get_health_type_display(),
                'diagnosis': record.diagnosis,
                'treatment': record.treatment,
                'medications': record.medications,
                'veterinarian': record.veterinarian,
                'next_checkup_date': record.next_checkup_date,
                'is_emergency': record.is_emergency,
                'treatment_cost': float(record.treatment_cost) if record.treatment_cost else None,
                'notes': record.notes,
            }
            return JsonResponse({'success': True, 'data': data})
        except HealthRecord.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Record not found'})

class HealthAlertsAPIView(LoginRequiredMixin, View):
    def get(self, request):
        today = timezone.now().date()
        
        emergencies = HealthRecord.objects.filter(
            is_emergency=True,
            date__gte=today - timedelta(days=7)
        ).select_related('cattle')[:10]
        
        overdue = HealthRecord.objects.filter(
            next_checkup_date__lt=today,
            next_checkup_date__isnull=False
        ).select_related('cattle')[:10]
        
        data = {
            'emergencies': [{
                'id': e.id,
                'cattle_tag': e.cattle.tag_number,
                'diagnosis': e.diagnosis,
                'date': e.date,
            } for e in emergencies],
            'overdue_followups': [{
                'id': o.id,
                'cattle_tag': o.cattle.tag_number,
                'checkup_date': o.next_checkup_date,
                'health_type': o.get_health_type_display(),
            } for o in overdue],
        }
        return JsonResponse({'success': True, 'data': data})

class HealthEmergenciesAPIView(LoginRequiredMixin, View):
    def get(self, request):
        emergencies = HealthRecord.objects.filter(
            is_emergency=True
        ).select_related('cattle').order_by('-date')[:20]
        
        data = [{
            'id': e.id,
            'date': e.date,
            'cattle_tag': e.cattle.tag_number,
            'diagnosis': e.diagnosis,
            'veterinarian': e.veterinarian,
        } for e in emergencies]
        return JsonResponse({'success': True, 'data': data})

class HealthByCattleAPIView(LoginRequiredMixin, View):
    def get(self, request, cattle_id):
        records = HealthRecord.objects.filter(cattle_id=cattle_id).order_by('-date')[:20]
        data = [{
            'id': r.id,
            'date': r.date,
            'health_type': r.get_health_type_display(),
            'diagnosis': r.diagnosis,
            'veterinarian': r.veterinarian,
        } for r in records]
        return JsonResponse({'success': True, 'data': data})

# Weight Record API Views
class WeightRecordListAPIView(LoginRequiredMixin, View):
    def get(self, request):
        records = WeightRecord.objects.select_related('cattle').all().order_by('-date')[:100]
        data = [{
            'id': r.id,
            'date': r.date,
            'cattle_tag': r.cattle.tag_number,
            'weight': float(r.weight),
            'daily_gain': float(r.daily_gain) if r.daily_gain else None,
        } for r in records]
        return JsonResponse({'success': True, 'data': data})

class WeightRecordDetailAPIView(LoginRequiredMixin, View):
    def get(self, request, record_id):
        try:
            record = WeightRecord.objects.select_related('cattle').get(id=record_id)
            data = {
                'id': record.id,
                'date': record.date,
                'cattle_id': record.cattle.id,
                'cattle_tag': record.cattle.tag_number,
                'weight': float(record.weight),
                'daily_gain': float(record.daily_gain) if record.daily_gain else None,
                'age_in_days': record.age_in_days,
                'notes': record.notes,
            }
            return JsonResponse({'success': True, 'data': data})
        except WeightRecord.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Record not found'})

class WeightByCattleAPIView(LoginRequiredMixin, View):
    def get(self, request, cattle_id):
        records = WeightRecord.objects.filter(cattle_id=cattle_id).order_by('-date')[:30]
        data = [{
            'id': r.id,
            'date': r.date,
            'weight': float(r.weight),
            'daily_gain': float(r.daily_gain) if r.daily_gain else None,
        } for r in records]
        return JsonResponse({'success': True, 'data': data})
    
class BulkWeightDeleteAPIView(LoginRequiredMixin, View):
    """Bulk delete weight records"""
    
    def post(self, request):
        try:
            data = json.loads(request.body)
            ids = data.get('ids', [])
            
            if not ids:
                return JsonResponse({'success': False, 'error': 'No IDs provided'})
            
            # Get all weight records
            records = WeightRecord.objects.filter(id__in=ids)
            
            # Store count for response
            count = records.count()
            
            # Delete all records
            records.delete()
            
            return JsonResponse({
                'success': True, 
                'message': f'Successfully deleted {count} weight records',
                'count': count
            })
            
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})


class WeightChartAPIView(LoginRequiredMixin, View):
    def get(self, request, cattle_id):
        records = WeightRecord.objects.filter(cattle_id=cattle_id).order_by('date')
        data = {
            'labels': [r.date.strftime('%Y-%m-%d') for r in records],
            'values': [float(r.weight) for r in records],
        }
        return JsonResponse({'success': True, 'data': data})

# Feeding Record API Views
class FeedingRecordListAPIView(LoginRequiredMixin, View):
    def get(self, request):
        records = FeedingRecord.objects.select_related('cattle').all().order_by('-date', '-feed_time')[:100]
        data = [{
            'id': r.id,
            'date': r.date,
            'feed_time': r.feed_time.strftime('%H:%M'),
            'cattle_tag': r.cattle.tag_number,
            'feed_type': r.get_feed_type_display(),
            'quantity': float(r.quantity),
            'total_cost': float(r.total_cost),
        } for r in records]
        return JsonResponse({'success': True, 'data': data})

class FeedingRecordDetailAPIView(LoginRequiredMixin, View):
    def get(self, request, record_id):
        try:
            record = FeedingRecord.objects.select_related('cattle').get(id=record_id)
            data = {
                'id': record.id,
                'date': record.date,
                'feed_time': record.feed_time.strftime('%H:%M'),
                'cattle_id': record.cattle.id,
                'cattle_tag': record.cattle.tag_number,
                'feed_type': record.feed_type,
                'feed_type_display': record.get_feed_type_display(),
                'quantity': float(record.quantity),
                'cost_per_kg': float(record.cost_per_kg),
                'total_cost': float(record.total_cost),
                'feed_quality': record.feed_quality,
                'feed_quality_display': record.get_feed_quality_display(),
                'notes': record.notes,
            }
            return JsonResponse({'success': True, 'data': data})
        except FeedingRecord.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Record not found'})

class FeedingTodayAPIView(LoginRequiredMixin, View):
    def get(self, request):
        today = timezone.now().date()
        records = FeedingRecord.objects.filter(date=today).select_related('cattle')
        data = [{
            'id': r.id,
            'feed_time': r.feed_time.strftime('%H:%M'),
            'cattle_tag': r.cattle.tag_number,
            'feed_type': r.get_feed_type_display(),
            'quantity': float(r.quantity),
        } for r in records]
        return JsonResponse({'success': True, 'data': data})

class FeedingStatsAPIView(LoginRequiredMixin, View):
    def get(self, request):
        today = timezone.now().date()
        month_ago = today - timedelta(days=30)
        
        data = {
            'today_count': FeedingRecord.objects.filter(date=today).count(),
            'today_quantity': float(FeedingRecord.objects.filter(date=today).aggregate(total=Sum('quantity'))['total'] or 0),
            'today_cost': float(FeedingRecord.objects.filter(date=today).aggregate(total=Sum('total_cost'))['total'] or 0),
            'month_quantity': float(FeedingRecord.objects.filter(date__gte=month_ago).aggregate(total=Sum('quantity'))['total'] or 0),
            'month_cost': float(FeedingRecord.objects.filter(date__gte=month_ago).aggregate(total=Sum('total_cost'))['total'] or 0),
        }
        return JsonResponse({'success': True, 'data': data})

class FeedingByCattleAPIView(LoginRequiredMixin, View):
    def get(self, request, cattle_id):
        records = FeedingRecord.objects.filter(cattle_id=cattle_id).order_by('-date', '-feed_time')[:30]
        data = [{
            'id': r.id,
            'date': r.date,
            'feed_time': r.feed_time.strftime('%H:%M'),
            'feed_type': r.get_feed_type_display(),
            'quantity': float(r.quantity),
            'total_cost': float(r.total_cost),
        } for r in records]
        return JsonResponse({'success': True, 'data': data})

# Breeding Record API Views
class BreedingRecordListAPIView(LoginRequiredMixin, View):
    def get(self, request):
        records = BreedingRecord.objects.select_related('cattle', 'sire', 'offspring').all().order_by('-breeding_date')[:100]
        data = [{
            'id': r.id,
            'breeding_date': r.breeding_date,
            'cattle_tag': r.cattle.tag_number,
            'sire_tag': r.sire.tag_number if r.sire else None,
            'breeding_method': r.breeding_method,
            'is_pregnant': r.is_pregnant,
            'status': r.get_status_display(),
            'expected_calving_date': r.expected_calving_date,
        } for r in records]
        return JsonResponse({'success': True, 'data': data})

class BreedingRecordDetailAPIView(LoginRequiredMixin, View):
    def get(self, request, record_id):
        try:
            record = BreedingRecord.objects.select_related('cattle', 'sire', 'offspring').get(id=record_id)
            data = {
                'id': record.id,
                'breeding_date': record.breeding_date,
                'cattle_id': record.cattle.id,
                'cattle_tag': record.cattle.tag_number,
                'sire_id': record.sire.id if record.sire else None,
                'sire_tag': record.sire.tag_number if record.sire else None,
                'breeding_method': record.breeding_method,
                'pregnancy_check_date': record.pregnancy_check_date,
                'is_pregnant': record.is_pregnant,
                'expected_calving_date': record.expected_calving_date,
                'actual_calving_date': record.actual_calving_date,
                'status': record.status,
                'status_display': record.get_status_display(),
                'offspring_id': record.offspring.id if record.offspring else None,
                'offspring_tag': record.offspring.tag_number if record.offspring else None,
                'notes': record.notes,
            }
            return JsonResponse({'success': True, 'data': data})
        except BreedingRecord.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Record not found'})

class BreedingCalendarAPIView(LoginRequiredMixin, View):
    def get(self, request):
        month = int(request.GET.get('month', timezone.now().month))
        year = int(request.GET.get('year', timezone.now().year))
        
        breedings = BreedingRecord.objects.filter(
            breeding_date__year=year,
            breeding_date__month=month
        ).select_related('cattle')
        
        calvings = BreedingRecord.objects.filter(
            expected_calving_date__year=year,
            expected_calving_date__month=month,
            is_pregnant=True
        ).select_related('cattle')
        
        data = {
            'breedings': [{
                'id': b.id,
                'date': b.breeding_date,
                'cattle_tag': b.cattle.tag_number,
                'method': b.breeding_method,
            } for b in breedings],
            'calvings': [{
                'id': c.id,
                'date': c.expected_calving_date,
                'cattle_tag': c.cattle.tag_number,
            } for c in calvings],
        }
        return JsonResponse({'success': True, 'data': data})

class DueCalvingAPIView(LoginRequiredMixin, View):
    def get(self, request):
        today = timezone.now().date()
        due = BreedingRecord.objects.filter(
            expected_calving_date__range=[today, today + timedelta(days=30)],
            is_pregnant=True
        ).select_related('cattle')[:20]
        
        data = [{
            'id': d.id,
            'cattle_tag': d.cattle.tag_number,
            'expected_date': d.expected_calving_date,
            'days_left': (d.expected_calving_date - today).days,
        } for d in due]
        return JsonResponse({'success': True, 'data': data})

class InHeatAPIView(LoginRequiredMixin, View):
    def get(self, request):
        today = timezone.now().date()
        in_heat = Cattle.objects.filter(
            gender='F',
            status='ACTIVE',
            breeding_records__status='BRED',
            breeding_records__breeding_date__gte=today - timedelta(days=21)
        ).distinct()[:20]
        
        data = [{
            'id': c.id,
            'tag_number': c.tag_number,
            'name': c.name,
            'last_breeding': c.breeding_records.filter(status='BRED').first().breeding_date if c.breeding_records.exists() else None,
        } for c in in_heat]
        return JsonResponse({'success': True, 'data': data})

class BreedingStatsAPIView(LoginRequiredMixin, View):
    def get(self, request):
        total = BreedingRecord.objects.count()
        pregnant = BreedingRecord.objects.filter(is_pregnant=True).count()
        calved = BreedingRecord.objects.filter(status='CALVED').count()
        failed = BreedingRecord.objects.filter(status='FAILED').count()
        
        data = {
            'total': total,
            'pregnant': pregnant,
            'calved': calved,
            'failed': failed,
            'success_rate': round((calved / total * 100) if total > 0 else 0, 1),
        }
        return JsonResponse({'success': True, 'data': data})

# Vaccination API Views
class VaccinationListAPIView(LoginRequiredMixin, View):
    def get(self, request):
        vaccinations = VaccinationSchedule.objects.select_related('cattle').all().order_by('scheduled_date')[:100]
        data = [{
            'id': v.id,
            'scheduled_date': v.scheduled_date,
            'cattle_tag': v.cattle.tag_number,
            'vaccine_type': v.get_vaccine_type_display(),
            'is_completed': v.is_completed,
            'administered_date': v.administered_date,
        } for v in vaccinations]
        return JsonResponse({'success': True, 'data': data})

class VaccinationDetailAPIView(LoginRequiredMixin, View):
    def get(self, request, vax_id):
        try:
            vax = VaccinationSchedule.objects.select_related('cattle', 'administered_by').get(id=vax_id)
            data = {
                'id': vax.id,
                'scheduled_date': vax.scheduled_date,
                'cattle_id': vax.cattle.id,
                'cattle_tag': vax.cattle.tag_number,
                'vaccine_type': vax.vaccine_type,
                'vaccine_type_display': vax.get_vaccine_type_display(),
                'is_completed': vax.is_completed,
                'administered_date': vax.administered_date,
                'dosage': vax.dosage,
                'batch_number': vax.batch_number,
                'cost': float(vax.cost) if vax.cost else None,
                'notes': vax.notes,
            }
            return JsonResponse({'success': True, 'data': data})
        except VaccinationSchedule.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Vaccination not found'})

class UpcomingVaccinationsAPIView(LoginRequiredMixin, View):
    def get(self, request):
        today = timezone.now().date()
        upcoming = VaccinationSchedule.objects.filter(
            scheduled_date__gte=today,
            is_completed=False
        ).select_related('cattle').order_by('scheduled_date')[:20]
        
        data = [{
            'id': v.id,
            'scheduled_date': v.scheduled_date,
            'cattle_tag': v.cattle.tag_number,
            'vaccine_type': v.get_vaccine_type_display(),
            'days_left': (v.scheduled_date - today).days,
        } for v in upcoming]
        return JsonResponse({'success': True, 'data': data})

class OverdueVaccinationsAPIView(LoginRequiredMixin, View):
    def get(self, request):
        today = timezone.now().date()
        overdue = VaccinationSchedule.objects.filter(
            scheduled_date__lt=today,
            is_completed=False
        ).select_related('cattle').order_by('scheduled_date')[:20]
        
        data = [{
            'id': v.id,
            'scheduled_date': v.scheduled_date,
            'cattle_tag': v.cattle.tag_number,
            'vaccine_type': v.get_vaccine_type_display(),
            'days_overdue': (today - v.scheduled_date).days,
        } for v in overdue]
        return JsonResponse({'success': True, 'data': data})

class VaccinationByCattleAPIView(LoginRequiredMixin, View):
    def get(self, request, cattle_id):
        vaccinations = VaccinationSchedule.objects.filter(cattle_id=cattle_id).order_by('-scheduled_date')[:20]
        data = [{
            'id': v.id,
            'scheduled_date': v.scheduled_date,
            'vaccine_type': v.get_vaccine_type_display(),
            'is_completed': v.is_completed,
            'administered_date': v.administered_date,
        } for v in vaccinations]
        return JsonResponse({'success': True, 'data': data})

class CompleteVaccinationAPIView(LoginRequiredMixin, View):
    def post(self, request, vax_id):
        try:
            vax = VaccinationSchedule.objects.get(id=vax_id)
            data = json.loads(request.body)
            
            vax.is_completed = True
            vax.administered_date = data.get('administered_date', timezone.now().date())
            vax.batch_number = data.get('batch_number', vax.batch_number)
            vax.dosage = data.get('dosage', vax.dosage)
            vax.administered_by = request.user
            vax.save()
            
            return JsonResponse({'success': True, 'message': 'Vaccination marked as completed'})
        except VaccinationSchedule.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Vaccination not found'})

# Expense API Views
class ExpenseListAPIView(LoginRequiredMixin, View):
    def get(self, request):
        expenses = Expense.objects.select_related('category', 'cattle').all().order_by('-date')[:100]
        data = [{
            'id': e.id,
            'date': e.date,
            'category': e.category.name if e.category else None,
            'description': e.description,
            'amount': float(e.amount),
            'cattle_tag': e.cattle.tag_number if e.cattle else None,
        } for e in expenses]
        return JsonResponse({'success': True, 'data': data})

class ExpenseDetailAPIView(LoginRequiredMixin, View):
    def get(self, request, expense_id):
        try:
            expense = Expense.objects.select_related('category', 'cattle').get(id=expense_id)
            data = {
                'id': expense.id,
                'date': expense.date,
                'category_id': expense.category.id if expense.category else None,
                'category_name': expense.category.name if expense.category else None,
                'description': expense.description,
                'amount': float(expense.amount),
                'payment_method': expense.payment_method,
                'payment_method_display': expense.get_payment_method_display(),
                'receipt_number': expense.receipt_number,
                'cattle_id': expense.cattle.id if expense.cattle else None,
                'cattle_tag': expense.cattle.tag_number if expense.cattle else None,
                'notes': expense.notes,
            }
            return JsonResponse({'success': True, 'data': data})
        except Expense.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Expense not found'})

class ExpenseStatsAPIView(LoginRequiredMixin, View):
    def get(self, request):
        today = timezone.now().date()
        month_ago = today - timedelta(days=30)
        year_ago = today - timedelta(days=365)
        
        data = {
            'total': float(Expense.objects.aggregate(total=Sum('amount'))['total'] or 0),
            'this_month': float(Expense.objects.filter(date__gte=month_ago).aggregate(total=Sum('amount'))['total'] or 0),
            'this_year': float(Expense.objects.filter(date__gte=year_ago).aggregate(total=Sum('amount'))['total'] or 0),
            'avg_monthly': float(Expense.objects.filter(date__gte=year_ago).aggregate(avg=Avg('amount'))['avg'] or 0),
        }
        return JsonResponse({'success': True, 'data': data})

class ExpenseMonthlyAPIView(LoginRequiredMixin, View):
    def get(self, request):
        year = int(request.GET.get('year', timezone.now().year))
        monthly_data = []
        
        for month in range(1, 13):
            total = Expense.objects.filter(
                date__year=year,
                date__month=month
            ).aggregate(total=Sum('amount'))['total'] or 0
            monthly_data.append(float(total))
        
        return JsonResponse({'success': True, 'data': monthly_data})

class ExpenseByCategoryAPIView(LoginRequiredMixin, View):
    def get(self, request):
        categories = ExpenseCategory.objects.all()
        data = []
        
        for category in categories:
            total = Expense.objects.filter(category=category).aggregate(total=Sum('amount'))['total'] or 0
            if total > 0:
                data.append({
                    'category': category.name,
                    'total': float(total),
                    'count': Expense.objects.filter(category=category).count(),
                })
        
        return JsonResponse({'success': True, 'data': data})

# Investment API Views
class InvestmentListAPIView(LoginRequiredMixin, View):
    def get(self, request):
        investments = Investment.objects.select_related('cattle').all().order_by('-date')[:100]
        data = [{
            'id': i.id,
            'date': i.date,
            'investment_type': i.get_investment_type_display(),
            'description': i.description,
            'amount': float(i.amount),
            'cattle_tag': i.cattle.tag_number if i.cattle else None,
        } for i in investments]
        return JsonResponse({'success': True, 'data': data})

class InvestmentDetailAPIView(LoginRequiredMixin, View):
    def get(self, request, investment_id):
        try:
            investment = Investment.objects.select_related('cattle').get(id=investment_id)
            data = {
                'id': investment.id,
                'date': investment.date,
                'investment_type': investment.investment_type,
                'investment_type_display': investment.get_investment_type_display(),
                'description': investment.description,
                'amount': float(investment.amount),
                'cattle_id': investment.cattle.id if investment.cattle else None,
                'cattle_tag': investment.cattle.tag_number if investment.cattle else None,
                'notes': investment.notes,
            }
            return JsonResponse({'success': True, 'data': data})
        except Investment.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Investment not found'})

class InvestmentStatsAPIView(LoginRequiredMixin, View):
    def get(self, request):
        data = {
            'total': float(Investment.objects.aggregate(total=Sum('amount'))['total'] or 0),
            'count': Investment.objects.count(),
            'avg_amount': float(Investment.objects.aggregate(avg=Avg('amount'))['avg'] or 0),
        }
        return JsonResponse({'success': True, 'data': data})

class InvestmentByTypeAPIView(LoginRequiredMixin, View):
    def get(self, request):
        investment_types = [choice[0] for choice in Investment.INVESTMENT_TYPES]
        data = []
        
        for inv_type in investment_types:
            total = Investment.objects.filter(investment_type=inv_type).aggregate(total=Sum('amount'))['total'] or 0
            if total > 0:
                data.append({
                    'type': inv_type,
                    'type_display': dict(Investment.INVESTMENT_TYPES)[inv_type],
                    'total': float(total),
                    'count': Investment.objects.filter(investment_type=inv_type).count(),
                })
        
        return JsonResponse({'success': True, 'data': data})

# Financial API Views
class FinancialSummaryAPIView(LoginRequiredMixin, View):
    def get(self, request):
        today = timezone.now().date()
        month_ago = today - timedelta(days=30)
        
        milk_sales = MilkSale.objects.filter(date__gte=month_ago).aggregate(total=Sum('total_amount'))['total'] or 0
        cattle_sales = CattleSale.objects.filter(sale_date__gte=month_ago).aggregate(total=Sum('sale_price'))['total'] or 0
        expenses = Expense.objects.filter(date__gte=month_ago).aggregate(total=Sum('amount'))['total'] or 0
        investments = Investment.objects.filter(date__gte=month_ago).aggregate(total=Sum('amount'))['total'] or 0
        
        data = {
            'period': {
                'start': month_ago,
                'end': today,
            },
            'income': {
                'milk_sales': float(milk_sales),
                'cattle_sales': float(cattle_sales),
                'total': float(milk_sales + cattle_sales),
            },
            'expenses': {
                'total': float(expenses),
            },
            'investments': {
                'total': float(investments),
            },
            'net_profit': float(milk_sales + cattle_sales - expenses),
        }
        return JsonResponse({'success': True, 'data': data})

class FinancialMonthlyAPIView(LoginRequiredMixin, View):
    def get(self, request, year, month):
        start_date = datetime(year, month, 1).date()
        if month == 12:
            end_date = datetime(year + 1, 1, 1).date() - timedelta(days=1)
        else:
            end_date = datetime(year, month + 1, 1).date() - timedelta(days=1)
        
        milk_sales = MilkSale.objects.filter(date__range=[start_date, end_date]).aggregate(total=Sum('total_amount'))['total'] or 0
        cattle_sales = CattleSale.objects.filter(sale_date__range=[start_date, end_date]).aggregate(total=Sum('sale_price'))['total'] or 0
        expenses = Expense.objects.filter(date__range=[start_date, end_date]).aggregate(total=Sum('amount'))['total'] or 0
        
        data = {
            'year': year,
            'month': month,
            'month_name': start_date.strftime('%B'),
            'income': {
                'milk_sales': float(milk_sales),
                'cattle_sales': float(cattle_sales),
                'total': float(milk_sales + cattle_sales),
            },
            'expenses': float(expenses),
            'net_profit': float(milk_sales + cattle_sales - expenses),
        }
        return JsonResponse({'success': True, 'data': data})

class FinancialYearlyAPIView(LoginRequiredMixin, View):
    def get(self, request, year):
        start_date = datetime(year, 1, 1).date()
        end_date = datetime(year, 12, 31).date()
        
        milk_sales = MilkSale.objects.filter(date__range=[start_date, end_date]).aggregate(total=Sum('total_amount'))['total'] or 0
        cattle_sales = CattleSale.objects.filter(sale_date__range=[start_date, end_date]).aggregate(total=Sum('sale_price'))['total'] or 0
        expenses = Expense.objects.filter(date__range=[start_date, end_date]).aggregate(total=Sum('amount'))['total'] or 0
        
        monthly_breakdown = []
        for month in range(1, 13):
            month_start = datetime(year, month, 1).date()
            if month == 12:
                month_end = datetime(year, 12, 31).date()
            else:
                month_end = datetime(year, month + 1, 1).date() - timedelta(days=1)
            
            month_milk = MilkSale.objects.filter(date__range=[month_start, month_end]).aggregate(total=Sum('total_amount'))['total'] or 0
            month_expenses = Expense.objects.filter(date__range=[month_start, month_end]).aggregate(total=Sum('amount'))['total'] or 0
            
            monthly_breakdown.append({
                'month': month_start.strftime('%B'),
                'milk_sales': float(month_milk),
                'expenses': float(month_expenses),
                'profit': float(month_milk - month_expenses),
            })
        
        data = {
            'year': year,
            'total_income': float(milk_sales + cattle_sales),
            'total_expenses': float(expenses),
            'net_profit': float(milk_sales + cattle_sales - expenses),
            'monthly_breakdown': monthly_breakdown,
        }
        return JsonResponse({'success': True, 'data': data})

class ProfitLossAPIView(LoginRequiredMixin, View):
    def get(self, request):
        period = request.GET.get('period', 'month')
        today = timezone.now().date()
        
        if period == 'month':
            start_date = today.replace(day=1)
            end_date = today
        elif period == 'quarter':
            quarter = (today.month - 1) // 3 + 1
            start_date = datetime(today.year, 3*quarter - 2, 1).date()
            end_date = today
        elif period == 'year':
            start_date = datetime(today.year, 1, 1).date()
            end_date = today
        else:
            start_date = today - timedelta(days=30)
            end_date = today
        
        milk_sales = MilkSale.objects.filter(date__range=[start_date, end_date]).aggregate(total=Sum('total_amount'))['total'] or 0
        cattle_sales = CattleSale.objects.filter(sale_date__range=[start_date, end_date]).aggregate(total=Sum('sale_price'))['total'] or 0
        expenses = Expense.objects.filter(date__range=[start_date, end_date]).aggregate(total=Sum('amount'))['total'] or 0
        
        data = {
            'period': period,
            'start_date': start_date,
            'end_date': end_date,
            'revenue': {
                'milk_sales': float(milk_sales),
                'cattle_sales': float(cattle_sales),
                'total': float(milk_sales + cattle_sales),
            },
            'expenses': float(expenses),
            'net_profit': float(milk_sales + cattle_sales - expenses),
            'profit_margin': round(((milk_sales + cattle_sales - expenses) / (milk_sales + cattle_sales) * 100) if (milk_sales + cattle_sales) > 0 else 0, 2),
        }
        return JsonResponse({'success': True, 'data': data})

# Report API Views
class MilkProductionReportAPIView(LoginRequiredMixin, View):
    def get(self, request):
        year = int(request.GET.get('year', timezone.now().year))
        data = []
        
        for month in range(1, 13):
            month_start = datetime(year, month, 1).date()
            if month == 12:
                month_end = datetime(year, 12, 31).date()
            else:
                month_end = datetime(year, month + 1, 1).date() - timedelta(days=1)
            
            total = MilkRecord.objects.filter(date__range=[month_start, month_end]).aggregate(total=Sum('quantity'))['total'] or 0
            count = MilkRecord.objects.filter(date__range=[month_start, month_end]).count()
            avg_fat = MilkRecord.objects.filter(date__range=[month_start, month_end]).aggregate(avg=Avg('fat_percentage'))['avg'] or 0
            
            data.append({
                'month': month_start.strftime('%B'),
                'total_milk': float(total),
                'record_count': count,
                'avg_fat': float(avg_fat),
            })
        
        return JsonResponse({'success': True, 'data': data})

class HealthSummaryReportAPIView(LoginRequiredMixin, View):
    def get(self, request):
        year = int(request.GET.get('year', timezone.now().year))
        
        health_types = [choice[0] for choice in HealthRecord.HEALTH_TYPES]
        data = []
        
        for health_type in health_types:
            count = HealthRecord.objects.filter(
                health_type=health_type,
                date__year=year
            ).count()
            
            cost = HealthRecord.objects.filter(
                health_type=health_type,
                date__year=year
            ).aggregate(total=Sum('treatment_cost'))['total'] or 0
            
            if count > 0:
                data.append({
                    'type': health_type,
                    'type_display': dict(HealthRecord.HEALTH_TYPES)[health_type],
                    'count': count,
                    'total_cost': float(cost),
                })
        
        emergencies = HealthRecord.objects.filter(
            is_emergency=True,
            date__year=year
        ).count()
        
        return JsonResponse({
            'success': True,
            'data': {
                'by_type': data,
                'total_emergencies': emergencies,
                'total_cases': HealthRecord.objects.filter(date__year=year).count(),
            }
        })

class BreedingPerformanceReportAPIView(LoginRequiredMixin, View):
    def get(self, request):
        year = int(request.GET.get('year', timezone.now().year))
        
        total = BreedingRecord.objects.filter(breeding_date__year=year).count()
        successful = BreedingRecord.objects.filter(
            breeding_date__year=year,
            status='CALVED'
        ).count()
        failed = BreedingRecord.objects.filter(
            breeding_date__year=year,
            status='FAILED'
        ).count()
        ongoing = BreedingRecord.objects.filter(
            breeding_date__year=year,
            status='CONFIRMED'
        ).count()
        
        data = {
            'year': year,
            'total_breedings': total,
            'successful': successful,
            'failed': failed,
            'ongoing': ongoing,
            'success_rate': round((successful / total * 100) if total > 0 else 0, 2),
        }
        return JsonResponse({'success': True, 'data': data})

class FinancialReportAPIView(LoginRequiredMixin, View):
    def get(self, request):
        year = int(request.GET.get('year', timezone.now().year))
        
        monthly_data = []
        for month in range(1, 13):
            month_start = datetime(year, month, 1).date()
            if month == 12:
                month_end = datetime(year, 12, 31).date()
            else:
                month_end = datetime(year, month + 1, 1).date() - timedelta(days=1)
            
            milk_sales = MilkSale.objects.filter(date__range=[month_start, month_end]).aggregate(total=Sum('total_amount'))['total'] or 0
            cattle_sales = CattleSale.objects.filter(sale_date__range=[month_start, month_end]).aggregate(total=Sum('sale_price'))['total'] or 0
            expenses = Expense.objects.filter(date__range=[month_start, month_end]).aggregate(total=Sum('amount'))['total'] or 0
            
            monthly_data.append({
                'month': month_start.strftime('%B'),
                'revenue': float(milk_sales + cattle_sales),
                'expenses': float(expenses),
                'profit': float(milk_sales + cattle_sales - expenses),
            })
        
        total_revenue = sum(m['revenue'] for m in monthly_data)
        total_expenses = sum(m['expenses'] for m in monthly_data)
        
        data = {
            'year': year,
            'monthly_data': monthly_data,
            'total_revenue': total_revenue,
            'total_expenses': total_expenses,
            'net_profit': total_revenue - total_expenses,
            'profit_margin': round(((total_revenue - total_expenses) / total_revenue * 100) if total_revenue > 0 else 0, 2),
        }
        return JsonResponse({'success': True, 'data': data})

# Chart Data API Views
class MilkTrendsChartAPIView(LoginRequiredMixin, View):
    def get(self, request):
        period = request.GET.get('period', 'year')
        today = timezone.now().date()
        
        if period == 'year':
            labels = []
            values = []
            for month in range(1, 13):
                labels.append(datetime(today.year, month, 1).strftime('%b'))
                total = MilkRecord.objects.filter(
                    date__year=today.year,
                    date__month=month
                ).aggregate(total=Sum('quantity'))['total'] or 0
                values.append(float(total))
        elif period == 'quarter':
            labels = ['Week 1', 'Week 2', 'Week 3', 'Week 4', 'Week 5', 'Week 6', 'Week 7', 'Week 8', 'Week 9', 'Week 10', 'Week 11', 'Week 12']
            values = []
            for i in range(12):
                week_start = today - timedelta(days=(11-i)*7)
                week_end = week_start + timedelta(days=6)
                total = MilkRecord.objects.filter(date__range=[week_start, week_end]).aggregate(total=Sum('quantity'))['total'] or 0
                values.append(float(total))
        else:  # month
            labels = []
            values = []
            days_in_month = (today.replace(month=today.month+1, day=1) - timedelta(days=1)).day if today.month < 12 else 31
            for day in range(1, days_in_month + 1):
                date = datetime(today.year, today.month, day).date()
                labels.append(str(day))
                total = MilkRecord.objects.filter(date=date).aggregate(total=Sum('quantity'))['total'] or 0
                values.append(float(total))
        
        return JsonResponse({
            'success': True,
            'data': {
                'labels': labels,
                'values': values,
            }
        })

class WeightGainChartAPIView(LoginRequiredMixin, View):
    def get(self, request, cattle_id):
        records = WeightRecord.objects.filter(cattle_id=cattle_id).order_by('date')
        
        data = {
            'labels': [r.date.strftime('%Y-%m-%d') for r in records],
            'weights': [float(r.weight) for r in records],
            'gains': [float(r.daily_gain) if r.daily_gain else 0 for r in records],
        }
        return JsonResponse({'success': True, 'data': data})

class BreedingSuccessChartAPIView(LoginRequiredMixin, View):
    def get(self, request):
        years = []
        success_rates = []
        
        current_year = timezone.now().year
        for year in range(current_year - 4, current_year + 1):
            total = BreedingRecord.objects.filter(breeding_date__year=year).count()
            successful = BreedingRecord.objects.filter(
                breeding_date__year=year,
                status='CALVED'
            ).count()
            
            years.append(str(year))
            success_rates.append(round((successful / total * 100) if total > 0 else 0, 2))
        
        return JsonResponse({
            'success': True,
            'data': {
                'years': years,
                'rates': success_rates,
            }
        })

class FinancialOverviewChartAPIView(LoginRequiredMixin, View):
    def get(self, request):
        year = int(request.GET.get('year', timezone.now().year))
        
        revenue_data = []
        expense_data = []
        
        for month in range(1, 13):
            month_start = datetime(year, month, 1).date()
            if month == 12:
                month_end = datetime(year, 12, 31).date()
            else:
                month_end = datetime(year, month + 1, 1).date() - timedelta(days=1)
            
            revenue = MilkSale.objects.filter(date__range=[month_start, month_end]).aggregate(total=Sum('total_amount'))['total'] or 0
            expenses = Expense.objects.filter(date__range=[month_start, month_end]).aggregate(total=Sum('amount'))['total'] or 0
            
            revenue_data.append(float(revenue))
            expense_data.append(float(expenses))
        
        return JsonResponse({
            'success': True,
            'data': {
                'months': [datetime(year, m, 1).strftime('%b') for m in range(1, 13)],
                'revenue': revenue_data,
                'expenses': expense_data,
            }
        })

# Bulk Operations API Views
class BulkCattleDeleteAPIView(LoginRequiredMixin, View):
    def post(self, request):
        try:
            data = json.loads(request.body)
            ids = data.get('ids', [])
            
            if not ids:
                return JsonResponse({'success': False, 'error': 'No IDs provided'})
            
            count, _ = Cattle.objects.filter(id__in=ids).delete()
            return JsonResponse({'success': True, 'message': f'Deleted {count} cattle records'})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})

class BulkMilkDeleteAPIView(LoginRequiredMixin, View):
    def post(self, request):
        try:
            data = json.loads(request.body)
            ids = data.get('ids', [])
            
            if not ids:
                return JsonResponse({'success': False, 'error': 'No IDs provided'})
            
            count, _ = MilkRecord.objects.filter(id__in=ids).delete()
            return JsonResponse({'success': True, 'message': f'Deleted {count} milk records'})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})

class BulkHealthDeleteAPIView(LoginRequiredMixin, View):
    def post(self, request):
        try:
            data = json.loads(request.body)
            ids = data.get('ids', [])
            
            if not ids:
                return JsonResponse({'success': False, 'error': 'No IDs provided'})
            
            count, _ = HealthRecord.objects.filter(id__in=ids).delete()
            return JsonResponse({'success': True, 'message': f'Deleted {count} health records'})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})

class BulkVaccinationCompleteAPIView(LoginRequiredMixin, View):
    def post(self, request):
        try:
            data = json.loads(request.body)
            ids = data.get('ids', [])
            admin_date = data.get('admin_date', timezone.now().date())
            
            if not ids:
                return JsonResponse({'success': False, 'error': 'No IDs provided'})
            
            count = VaccinationSchedule.objects.filter(id__in=ids).update(
                is_completed=True,
                administered_date=admin_date,
                administered_by=request.user
            )
            
            return JsonResponse({'success': True, 'message': f'Completed {count} vaccinations'})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})

# Search API Views
class SearchCattleAPIView(LoginRequiredMixin, View):
    def get(self, request):
        query = request.GET.get('q', '')
        if len(query) < 2:
            return JsonResponse({'success': True, 'data': []})
        
        cattle = Cattle.objects.filter(
            Q(tag_number__icontains=query) |
            Q(name__icontains=query)
        ).values('id', 'tag_number', 'name', 'breed', 'status')[:20]
        
        return JsonResponse({'success': True, 'data': list(cattle)})

class SearchRecordsAPIView(LoginRequiredMixin, View):
    def get(self, request):
        query = request.GET.get('q', '')
        record_type = request.GET.get('type', 'all')
        
        results = []
        
        if record_type in ['all', 'cattle']:
            cattle = Cattle.objects.filter(
                Q(tag_number__icontains=query) |
                Q(name__icontains=query)
            )[:5]
            for c in cattle:
                results.append({
                    'type': 'cattle',
                    'id': c.id,
                    'tag': c.tag_number,
                    'name': c.name,
                    'url': f'/dairy/cattle/{c.id}/'
                })
        
        if record_type in ['all', 'milk']:
            milk = MilkRecord.objects.filter(
                Q(cattle__tag_number__icontains=query)
            ).select_related('cattle')[:5]
            for m in milk:
                results.append({
                    'type': 'milk',
                    'id': m.id,
                    'cattle': m.cattle.tag_number,
                    'date': m.date,
                    'url': f'/dairy/milk/{m.id}/'
                })
        
        return JsonResponse({'success': True, 'data': results})

# Export API Views
class ExportCattleCSVAPIView(LoginRequiredMixin, View):
    def get(self, request):
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="cattle_export.csv"'
        
        writer = csv.writer(response)
        writer.writerow(['Tag Number', 'Name', 'Type', 'Breed', 'Gender', 'Birth Date', 'Age', 'Weight', 'Status', 'Location'])
        
        for cattle in Cattle.objects.all():
            writer.writerow([
                cattle.tag_number,
                cattle.name or '',
                cattle.get_cattle_type_display(),
                cattle.get_breed_display(),
                cattle.get_gender_display(),
                cattle.birth_date,
                cattle.age_in_months(),
                cattle.weight,
                cattle.status,
                cattle.location or ''
            ])
        
        return response

class ExportMilkCSVAPIView(LoginRequiredMixin, View):
    def get(self, request):
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="milk_records_export.csv"'
        
        writer = csv.writer(response)
        writer.writerow(['Date', 'Cattle Tag', 'Session', 'Quantity (L)', 'Fat %', 'Temperature'])
        
        for record in MilkRecord.objects.select_related('cattle').all():
            writer.writerow([
                record.date,
                record.cattle.tag_number,
                record.get_session_display(),
                record.quantity,
                record.fat_percentage or '',
                record.temperature or ''
            ])
        
        return response

class ExportSalesCSVAPIView(LoginRequiredMixin, View):
    def get(self, request):
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="sales_export.csv"'
        
        writer = csv.writer(response)
        writer.writerow(['Date', 'Type', 'Cattle/Customer', 'Quantity', 'Price', 'Total', 'Payment Status'])
        
        # Milk Sales
        for sale in MilkSale.objects.all():
            writer.writerow([
                sale.date,
                'Milk Sale',
                sale.customer_name or 'Retail',
                f"{sale.quantity} L",
                sale.price_per_liter,
                sale.total_amount,
                'Paid' if sale.payment_received else 'Pending'
            ])
        
        # Cattle Sales
        for sale in CattleSale.objects.select_related('cattle').all():
            writer.writerow([
                sale.sale_date,
                'Cattle Sale',
                sale.cattle.tag_number,
                '1 head',
                sale.sale_price,
                sale.sale_price,
                'Paid' if sale.payment_received else 'Pending'
            ])
        
        return response

class ExportFinancialCSVAPIView(LoginRequiredMixin, View):
    def get(self, request):
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="financial_export.csv"'
        
        writer = csv.writer(response)
        writer.writerow(['Date', 'Type', 'Description', 'Category', 'Amount'])
        
        # Expenses
        for expense in Expense.objects.select_related('category').all():
            writer.writerow([
                expense.date,
                'Expense',
                expense.description,
                expense.category.name if expense.category else 'Other',
                expense.amount
            ])
        
        # Milk Sales (Income)
        for sale in MilkSale.objects.all():
            writer.writerow([
                sale.date,
                'Income - Milk',
                f"Milk Sale - {sale.quantity}L",
                'Milk Sales',
                sale.total_amount
            ])
        
        # Cattle Sales (Income)
        for sale in CattleSale.objects.select_related('cattle').all():
            writer.writerow([
                sale.sale_date,
                'Income - Cattle',
                f"Cattle Sale - {sale.cattle.tag_number}",
                'Cattle Sales',
                sale.sale_price
            ])
        
        # Investments
        for investment in Investment.objects.all():
            writer.writerow([
                investment.date,
                'Investment',
                investment.description,
                investment.get_investment_type_display(),
                investment.amount
            ])
        
        return response


# ==================== EXPORT VIEWS (Non-API) ====================

class ExportCattleCSVView(LoginRequiredMixin, View):
    """Export cattle data to CSV"""
    def get(self, request):
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="cattle_export.csv"'
        
        writer = csv.writer(response)
        writer.writerow(['Tag Number', 'Name', 'Type', 'Breed', 'Gender', 'Birth Date', 'Age', 'Weight', 'Status', 'Location'])
        
        for cattle in Cattle.objects.all():
            writer.writerow([
                cattle.tag_number,
                cattle.name or '',
                cattle.get_cattle_type_display(),
                cattle.get_breed_display(),
                cattle.get_gender_display(),
                cattle.birth_date,
                cattle.age_in_months(),
                cattle.weight,
                cattle.status,
                cattle.location or ''
            ])
        
        return response


class ExportMilkCSVView(LoginRequiredMixin, View):
    """Export milk records to CSV"""
    def get(self, request):
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="milk_records_export.csv"'
        
        writer = csv.writer(response)
        writer.writerow(['Date', 'Cattle Tag', 'Session', 'Quantity (L)', 'Fat %', 'Temperature'])
        
        for record in MilkRecord.objects.select_related('cattle').all():
            writer.writerow([
                record.date,
                record.cattle.tag_number,
                record.get_session_display(),
                record.quantity,
                record.fat_percentage or '',
                record.temperature or ''
            ])
        
        return response


class ExportSalesCSVView(LoginRequiredMixin, View):
    """Export sales data to CSV"""
    def get(self, request):
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="sales_export.csv"'
        
        writer = csv.writer(response)
        writer.writerow(['Date', 'Type', 'Cattle/Customer', 'Quantity', 'Price', 'Total', 'Payment Status'])
        
        # Milk Sales
        for sale in MilkSale.objects.all():
            writer.writerow([
                sale.date,
                'Milk Sale',
                sale.customer_name or 'Retail',
                f"{sale.quantity} L",
                sale.price_per_liter,
                sale.total_amount,
                'Paid' if sale.payment_received else 'Pending'
            ])
        
        # Cattle Sales
        for sale in CattleSale.objects.select_related('cattle').all():
            writer.writerow([
                sale.sale_date,
                'Cattle Sale',
                sale.cattle.tag_number,
                '1 head',
                sale.sale_price,
                sale.sale_price,
                'Paid' if sale.payment_received else 'Pending'
            ])
        
        return response


class ExportFinancialCSVView(LoginRequiredMixin, View):
    """Export financial data to CSV"""
    def get(self, request):
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="financial_export.csv"'
        
        writer = csv.writer(response)
        writer.writerow(['Date', 'Type', 'Description', 'Category', 'Amount'])
        
        # Expenses
        for expense in Expense.objects.select_related('category').all():
            writer.writerow([
                expense.date,
                'Expense',
                expense.description,
                expense.category.name if expense.category else 'Other',
                expense.amount
            ])
        
        # Milk Sales (Income)
        for sale in MilkSale.objects.all():
            writer.writerow([
                sale.date,
                'Income - Milk',
                f"Milk Sale - {sale.quantity}L",
                'Milk Sales',
                sale.total_amount
            ])
        
        # Cattle Sales (Income)
        for sale in CattleSale.objects.select_related('cattle').all():
            writer.writerow([
                sale.sale_date,
                'Income - Cattle',
                f"Cattle Sale - {sale.cattle.tag_number}",
                'Cattle Sales',
                sale.sale_price
            ])
        
        # Investments
        for investment in Investment.objects.all():
            writer.writerow([
                investment.date,
                'Investment',
                investment.description,
                investment.get_investment_type_display(),
                investment.amount
            ])
        
        return response




# ==================== MISSING CSV EXPORT VIEWS ====================

class ExportHealthCSVView(LoginRequiredMixin, View):
    """Export health records to CSV"""
    
    def get(self, request):
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="health_records_export.csv"'
        
        writer = csv.writer(response)
        writer.writerow(['Date', 'Cattle Tag', 'Health Type', 'Diagnosis', 'Treatment', 
                        'Veterinarian', 'Cost', 'Emergency', 'Follow-up Date'])
        
        for record in HealthRecord.objects.select_related('cattle').all():
            writer.writerow([
                record.date.strftime('%Y-%m-%d'),
                record.cattle.tag_number,
                record.get_health_type_display(),
                record.diagnosis,
                record.treatment or '',
                record.veterinarian,
                record.treatment_cost or '',
                'Yes' if record.is_emergency else 'No',
                record.next_checkup_date.strftime('%Y-%m-%d') if record.next_checkup_date else ''
            ])
        
        return response


class ExportFeedingCSVView(LoginRequiredMixin, View):
    """Export feeding records to CSV"""
    
    def get(self, request):
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="feeding_records_export.csv"'
        
        writer = csv.writer(response)
        writer.writerow(['Date', 'Time', 'Cattle Tag', 'Feed Type', 'Quantity (kg)', 
                        'Cost/kg', 'Total Cost', 'Quality', 'Notes'])
        
        for record in FeedingRecord.objects.select_related('cattle').all():
            writer.writerow([
                record.date.strftime('%Y-%m-%d'),
                record.feed_time.strftime('%H:%M'),
                record.cattle.tag_number,
                record.get_feed_type_display(),
                record.quantity,
                record.cost_per_kg,
                record.total_cost,
                record.get_feed_quality_display(),
                record.notes or ''
            ])
        
        return response


class ExportWeightCSVView(LoginRequiredMixin, View):
    """Export weight records to CSV"""
    
    def get(self, request):
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="weight_records_export.csv"'
        
        writer = csv.writer(response)
        writer.writerow(['Date', 'Cattle Tag', 'Weight (kg)', 'Daily Gain (kg/day)', 'Age (days)', 'Notes'])
        
        for record in WeightRecord.objects.select_related('cattle').all():
            writer.writerow([
                record.date.strftime('%Y-%m-%d'),
                record.cattle.tag_number,
                record.weight,
                record.daily_gain or '',
                record.age_in_days or '',
                record.notes or ''
            ])
        
        return response


class ExportBreedingCSVView(LoginRequiredMixin, View):
    """Export breeding records to CSV"""
    
    def get(self, request):
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="breeding_records_export.csv"'
        
        writer = csv.writer(response)
        writer.writerow(['Breeding Date', 'Dam Tag', 'Sire Tag', 'Method', 'Status', 
                        'Pregnant', 'Pregnancy Check', 'Expected Calving', 'Actual Calving', 'Offspring', 'Notes'])
        
        for record in BreedingRecord.objects.select_related('cattle', 'sire', 'offspring').all():
            writer.writerow([
                record.breeding_date.strftime('%Y-%m-%d'),
                record.cattle.tag_number,
                record.sire.tag_number if record.sire else '',
                record.breeding_method,
                record.get_status_display(),
                'Yes' if record.is_pregnant else 'No',
                record.pregnancy_check_date.strftime('%Y-%m-%d') if record.pregnancy_check_date else '',
                record.expected_calving_date.strftime('%Y-%m-%d') if record.expected_calving_date else '',
                record.actual_calving_date.strftime('%Y-%m-%d') if record.actual_calving_date else '',
                record.offspring.tag_number if record.offspring else '',
                record.notes or ''
            ])
        
        return response


class ExportVaccinationCSVView(LoginRequiredMixin, View):
    """Export vaccination records to CSV"""
    
    def get(self, request):
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="vaccination_records_export.csv"'
        
        writer = csv.writer(response)
        writer.writerow(['Scheduled Date', 'Cattle Tag', 'Vaccine Type', 'Status', 
                        'Administered Date', 'Batch Number', 'Dosage', 'Cost', 'Notes'])
        
        for record in VaccinationSchedule.objects.select_related('cattle', 'administered_by').all():
            writer.writerow([
                record.scheduled_date.strftime('%Y-%m-%d'),
                record.cattle.tag_number,
                record.get_vaccine_type_display(),
                'Completed' if record.is_completed else 'Pending',
                record.administered_date.strftime('%Y-%m-%d') if record.administered_date else '',
                record.batch_number or '',
                record.dosage or '',
                record.cost or '',
                record.notes or ''
            ])
        
        return response

# ==================== REPORT DASHBOARD VIEW ====================

class ReportDashboardView(LoginRequiredMixin, TemplateView):
    """Reports dashboard/index page"""
    template_name = 'dairy/reports/index.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        today = timezone.now().date()
        
        context['current_year'] = today.year
        context['current_month'] = today.month
        context['current_month_name'] = today.strftime('%B')
        context['prev_month'] = today.month - 1 if today.month > 1 else 12
        context['prev_year'] = today.year - 1
        context['current_date'] = today.isoformat()
        context['prev_year'] = today.year - 1
        
        context['total_cattle'] = Cattle.objects.filter(status='ACTIVE').count()
        
        # YTD Revenue
        ytd_revenue = MilkSale.objects.filter(date__year=today.year).aggregate(total=Sum('total_amount'))['total'] or 0
        context['ytd_revenue'] = ytd_revenue
        
        # Recent reports (placeholder - you can implement based on your needs)
        context['recent_reports'] = []
        
        return context


# ==================== MILK PRODUCTION REPORT VIEW ====================

# class MilkProductionReportView(LoginRequiredMixin, TemplateView):
#     """Milk production report"""
#     template_name = 'dairy/reports/milk_production.html'
    
#     def get_context_data(self, **kwargs):
#         context = super().get_context_data(**kwargs)
#         year = int(self.request.GET.get('year', timezone.now().year))
        
#         monthly_data = []
#         for month in range(1, 13):
#             month_start = datetime(year, month, 1).date()
#             if month == 12:
#                 month_end = datetime(year, 12, 31).date()
#             else:
#                 month_end = datetime(year, month + 1, 1).date() - timedelta(days=1)
            
#             total = MilkRecord.objects.filter(date__range=[month_start, month_end]).aggregate(total=Sum('quantity'))['total'] or 0
#             count = MilkRecord.objects.filter(date__range=[month_start, month_end]).count()
#             avg_fat = MilkRecord.objects.filter(date__range=[month_start, month_end]).aggregate(avg=Avg('fat_percentage'))['avg'] or 0
            
#             monthly_data.append({
#                 'month': month_start.strftime('%B'),
#                 'total': total,
#                 'count': count,
#                 'avg_fat': avg_fat
#             })
        
#         context['monthly_data'] = monthly_data
#         context['year'] = year
#         context['years'] = range(2020, timezone.now().year + 1)
        
#         return context


# # ==================== HEALTH SUMMARY REPORT VIEW ====================

# class HealthSummaryReportView(LoginRequiredMixin, TemplateView):
#     """Health summary report"""
#     template_name = 'dairy/reports/health_summary.html'
    
#     def get_context_data(self, **kwargs):
#         context = super().get_context_data(**kwargs)
#         year = int(self.request.GET.get('year', timezone.now().year))
        
#         health_types = []
#         for health_type, label in HealthRecord.HEALTH_TYPES:
#             count = HealthRecord.objects.filter(health_type=health_type, date__year=year).count()
#             cost = HealthRecord.objects.filter(health_type=health_type, date__year=year).aggregate(total=Sum('treatment_cost'))['total'] or 0
            
#             if count > 0:
#                 health_types.append({
#                     'type': label,
#                     'count': count,
#                     'cost': cost
#                 })
        
#         emergencies = HealthRecord.objects.filter(is_emergency=True, date__year=year).count()
#         total_cases = HealthRecord.objects.filter(date__year=year).count()
#         total_cost = HealthRecord.objects.filter(date__year=year).aggregate(total=Sum('treatment_cost'))['total'] or 0
        
#         context['health_types'] = health_types
#         context['emergencies'] = emergencies
#         context['total_cases'] = total_cases
#         context['total_cost'] = total_cost
#         context['year'] = year
#         context['years'] = range(2020, timezone.now().year + 1)
        
#         return context


# # ==================== BREEDING PERFORMANCE REPORT VIEW ====================

# class BreedingPerformanceReportView(LoginRequiredMixin, TemplateView):
#     """Breeding performance report"""
#     template_name = 'dairy/reports/breeding_performance.html'
    
#     def get_context_data(self, **kwargs):
#         context = super().get_context_data(**kwargs)
#         year = int(self.request.GET.get('year', timezone.now().year))
        
#         total_breedings = BreedingRecord.objects.filter(breeding_date__year=year).count()
#         successful = BreedingRecord.objects.filter(breeding_date__year=year, status='CALVED').count()
#         failed = BreedingRecord.objects.filter(breeding_date__year=year, status='FAILED').count()
#         ongoing = BreedingRecord.objects.filter(breeding_date__year=year, status='CONFIRMED').count()
        
#         # Monthly breakdown
#         monthly_data = []
#         for month in range(1, 13):
#             month_breedings = BreedingRecord.objects.filter(
#                 breeding_date__year=year,
#                 breeding_date__month=month
#             ).count()
            
#             month_calvings = BreedingRecord.objects.filter(
#                 actual_calving_date__year=year,
#                 actual_calving_date__month=month
#             ).count()
            
#             monthly_data.append({
#                 'month': datetime(year, month, 1).strftime('%B'),
#                 'breedings': month_breedings,
#                 'calvings': month_calvings
#             })
        
#         context['total_breedings'] = total_breedings
#         context['successful'] = successful
#         context['failed'] = failed
#         context['ongoing'] = ongoing
#         context['success_rate'] = round((successful / total_breedings * 100) if total_breedings > 0 else 0, 1)
#         context['monthly_data'] = monthly_data
#         context['year'] = year
#         context['years'] = range(2020, timezone.now().year + 1)
        
#         return context


# views.py

class MilkProductionReportView(LoginRequiredMixin, TemplateView):
    template_name = 'dairy/reports/milk_production.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Get filter parameters
        period = self.request.GET.get('period', 'monthly')
        year = int(self.request.GET.get('year', timezone.now().year))
        month = self.request.GET.get('month')
        if month:
            month = int(month)
        start_date = self.request.GET.get('start_date')
        end_date = self.request.GET.get('end_date')
        cattle_id = self.request.GET.get('cattle')
        
        # Calculate date range based on period
        if period == 'daily':
            if start_date:
                start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
                end_date = start_date
            else:
                start_date = timezone.now().date()
                end_date = start_date
        elif period == 'weekly':
            if start_date:
                start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
                end_date = start_date + timedelta(days=6)
            else:
                end_date = timezone.now().date()
                start_date = end_date - timedelta(days=6)
        elif period == 'monthly':
            if month:
                start_date = datetime(year, month, 1).date()
                if month == 12:
                    end_date = datetime(year+1, 1, 1).date() - timedelta(days=1)
                else:
                    end_date = datetime(year, month+1, 1).date() - timedelta(days=1)
            else:
                today = timezone.now().date()
                start_date = datetime(today.year, today.month, 1).date()
                if today.month == 12:
                    end_date = datetime(today.year+1, 1, 1).date() - timedelta(days=1)
                else:
                    end_date = datetime(today.year, today.month+1, 1).date() - timedelta(days=1)
        elif period == 'quarterly':
            quarter = int(self.request.GET.get('quarter', (timezone.now().month-1)//3 + 1))
            start_month = quarter * 3 - 2
            end_month = quarter * 3
            start_date = datetime(year, start_month, 1).date()
            if end_month == 12:
                end_date = datetime(year+1, 1, 1).date() - timedelta(days=1)
            else:
                end_date = datetime(year, end_month+1, 1).date() - timedelta(days=1)
        elif period == 'yearly':
            start_date = datetime(year, 1, 1).date()
            end_date = datetime(year, 12, 31).date()
        elif period == 'custom':
            if start_date:
                start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
            if end_date:
                end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
            if not start_date:
                start_date = timezone.now().date() - timedelta(days=30)
            if not end_date:
                end_date = timezone.now().date()
        
        # Base queryset
        milk_records = MilkRecord.objects.filter(
            date__range=[start_date, end_date]
        ).select_related('cattle')
        
        # Filter by specific cattle if selected
        if cattle_id:
            milk_records = milk_records.filter(cattle_id=cattle_id)
        
        # Calculate summary statistics - using imported Sum, Avg, etc.
        total_milk = milk_records.aggregate(
            total=Sum('quantity')
        )['total'] or 0
        context['total_milk'] = total_milk
        
        days_diff = (end_date - start_date).days + 1
        context['avg_daily'] = total_milk / days_diff if days_diff > 0 else 0
        
        avg_fat = milk_records.aggregate(
            avg=Avg('fat_percentage')
        )['avg'] or 0
        context['avg_fat'] = avg_fat
        
        # Revenue calculation
        milk_sales = MilkSale.objects.filter(
            date__range=[start_date, end_date]
        )
        total_revenue = milk_sales.aggregate(
            total=Sum('total_amount')
        )['total'] or 0
        context['total_revenue'] = total_revenue
        
        context['avg_price'] = total_revenue / total_milk if total_milk > 0 else 0
        
        # Lactating cows
        lactating_cows = milk_records.values('cattle').distinct().count()
        context['total_lactating'] = lactating_cows
        context['avg_per_cow'] = total_milk / lactating_cows if lactating_cows > 0 else 0
        
        # Peak production day
        daily_totals = milk_records.values('date').annotate(
            daily_total=Sum('quantity')
        ).order_by('-daily_total')
        
        if daily_totals:
            peak_day = daily_totals.first()
            context['peak_day'] = peak_day['date']
            context['peak_amount'] = peak_day['daily_total']
        else:
            context['peak_day'] = None
            context['peak_amount'] = 0
        
        # Growth percentage compared to previous period
        prev_start = start_date - timedelta(days=days_diff)
        prev_end = start_date - timedelta(days=1)
        
        prev_total = MilkRecord.objects.filter(
            date__range=[prev_start, prev_end]
        ).aggregate(prev_total=Sum('quantity'))['prev_total'] or 0
        
        context['milk_growth'] = ((total_milk - prev_total) / prev_total * 100) if prev_total > 0 else 0
        
        # Top producers - Using Max (make sure Max is imported)
        from django.db.models import Max  # Import here if not at top
        
        top_producers_data = milk_records.values(
            'cattle', 'cattle__tag_number', 'cattle__name', 'cattle__breed'
        ).annotate(
            total=Sum('quantity'),
            avg=Avg('quantity'),
            max=Max('quantity')
        ).order_by('-total')[:10]
        
        context['top_producers'] = []
        for producer in top_producers_data:
            producer_dict = {
                'cattle': {
                    'id': producer['cattle'],
                    'tag_number': producer['cattle__tag_number'],
                    'name': producer['cattle__name'] or '',
                    'breed': producer['cattle__breed'],
                    'get_breed_display': lambda: producer['cattle__breed']
                },
                'total': producer['total'],
                'avg': producer['avg'],
                'max': producer['max'],
                'percentage': (producer['total'] / total_milk * 100) if total_milk > 0 else 0
            }
            context['top_producers'].append(producer_dict)
        
        # Daily breakdown
        daily_data = milk_records.values('date').annotate(
            morning=Sum('quantity', filter=Q(session='MORNING')),
            afternoon=Sum('quantity', filter=Q(session='AFTERNOON')),
            evening=Sum('quantity', filter=Q(session='EVENING')),
            total=Sum('quantity'),
            avg_fat=Avg('fat_percentage'),
            cow_count=Count('cattle', distinct=True)
        ).order_by('date')
        
        context['daily_breakdown'] = []
        context['chart_labels'] = []
        context['morning_data'] = []
        context['afternoon_data'] = []
        context['evening_data'] = []
        context['total_data'] = []
        
        for day in daily_data:
            # Calculate revenue for this day
            day_revenue = MilkSale.objects.filter(
                date=day['date']
            ).aggregate(day_total=Sum('total_amount'))['day_total'] or 0
            
            context['daily_breakdown'].append({
                'date': day['date'],
                'morning': float(day['morning'] or 0),
                'afternoon': float(day['afternoon'] or 0),
                'evening': float(day['evening'] or 0),
                'total': float(day['total'] or 0),
                'avg_fat': float(day['avg_fat'] or 0),
                'cow_count': day['cow_count'] or 0,
                'revenue': float(day_revenue)
            })
            
            context['chart_labels'].append(day['date'].strftime('%Y-%m-%d'))
            context['morning_data'].append(float(day['morning'] or 0))
            context['afternoon_data'].append(float(day['afternoon'] or 0))
            context['evening_data'].append(float(day['evening'] or 0))
            context['total_data'].append(float(day['total'] or 0))
        
        # Context for filters
        context['period'] = period
        context['year'] = year
        context['month'] = month
        context['start_date'] = start_date
        context['end_date'] = end_date
        context['selected_cattle'] = int(cattle_id) if cattle_id else None
        
        # Years for filter dropdown
        current_year = timezone.now().year
        context['years'] = range(current_year - 5, current_year + 1)
        
        # Months for filter dropdown
        context['months'] = [
            {'value': 1, 'name': 'January'},
            {'value': 2, 'name': 'February'},
            {'value': 3, 'name': 'March'},
            {'value': 4, 'name': 'April'},
            {'value': 5, 'name': 'May'},
            {'value': 6, 'name': 'June'},
            {'value': 7, 'name': 'July'},
            {'value': 8, 'name': 'August'},
            {'value': 9, 'name': 'September'},
            {'value': 10, 'name': 'October'},
            {'value': 11, 'name': 'November'},
            {'value': 12, 'name': 'December'},
        ]
        
        # Cattle list for filter
        context['cattle_list'] = Cattle.objects.filter(status='ACTIVE').values('id', 'tag_number', 'name')
        
        return context

class HealthSummaryReportView(LoginRequiredMixin, TemplateView):
    template_name = 'dairy/reports/health_summary.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        year = int(self.request.GET.get('year', timezone.now().year))
        quarter = int(self.request.GET.get('quarter', 
                     (timezone.now().month - 1) // 3 + 1))
        
        # Calculate quarter dates
        start_month = quarter * 3 - 2
        end_month = quarter * 3
        start_date = datetime(year, start_month, 1).date()
        
        if end_month == 12:
            end_date = datetime(year+1, 1, 1).date() - timedelta(days=1)
        else:
            end_date = datetime(year, end_month+1, 1).date() - timedelta(days=1)
        
        # Get health records
        health_records = HealthRecord.objects.filter(
            date__range=[start_date, end_date]
        ).select_related('cattle')
        
        # Cases by type
        context['cases_by_type'] = health_records.values(
            'health_type'
        ).annotate(
            count=Count('id'),
            total_cost=Sum('treatment_cost')
        )
        
        # Emergency cases
        context['emergencies'] = health_records.filter(
            is_emergency=True
        ).order_by('-date')[:10]
        
        # Vaccination status
        today = timezone.now().date()
        context['vaccination_status'] = {
            'upcoming': VaccinationSchedule.objects.filter(
                scheduled_date__gte=today,
                is_completed=False
            ).count(),
            'overdue': VaccinationSchedule.objects.filter(
                scheduled_date__lt=today,
                is_completed=False
            ).count(),
            'completed': VaccinationSchedule.objects.filter(
                administered_date__year=year
            ).count(),
        }
        
        context['year'] = year
        context['quarter'] = quarter
        
        return context


class BreedingPerformanceReportView(LoginRequiredMixin, TemplateView):
    template_name = 'dairy/reports/breeding_performance.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        year = int(self.request.GET.get('year', timezone.now().year))
        
        # Get breeding records for the year
        breedings = BreedingRecord.objects.filter(
            breeding_date__year=year
        ).select_related('cattle', 'sire')
        
        # Calculate statistics
        context['total_breedings'] = breedings.count()
        context['confirmed_pregnant'] = breedings.filter(
            is_pregnant=True
        ).count()
        context['calved'] = breedings.filter(
            status='CALVED'
        ).count()
        
        # Success rate
        if context['total_breedings'] > 0:
            context['success_rate'] = round(
                context['confirmed_pregnant'] / context['total_breedings'] * 100, 1
            )
        
        # Upcoming calving
        today = timezone.now().date()
        context['upcoming_calving'] = BreedingRecord.objects.filter(
            expected_calving_date__gte=today,
            is_pregnant=True,
            status='CONFIRMED'
        ).order_by('expected_calving_date')[:10]
        
        # Sire performance
        context['sire_performance'] = breedings.values(
            'sire__tag_number', 'sire__breed'
        ).annotate(
            total=Count('id'),
            successful=Count('id', filter=Q(is_pregnant=True))
        ).order_by('-successful')
        
        context['year'] = year
        
        return context


# ==================== PDF EXPORT VIEWS ====================

class ExportCattlePDFView(LoginRequiredMixin, View):
    """Export cattle data to PDF"""
    
    def get(self, request):
        response = HttpResponse(content_type='application/pdf')
        response['Content-Disposition'] = 'attachment; filename="cattle_export.pdf"'
        
        doc = SimpleDocTemplate(response, pagesize=landscape(letter))
        elements = []
        
        styles = getSampleStyleSheet()
        title = Paragraph("Cattle Export Report", styles['Title'])
        elements.append(title)
        
        data = [['Tag Number', 'Name', 'Type', 'Breed', 'Gender', 'Age', 'Weight', 'Status']]
        for cattle in Cattle.objects.all()[:50]:
            data.append([
                cattle.tag_number,
                cattle.name or '-',
                cattle.get_cattle_type_display(),
                cattle.get_breed_display(),
                cattle.get_gender_display(),
                str(cattle.age_in_months()) + 'mo',
                str(cattle.weight) + 'kg' if cattle.weight else '-',
                cattle.status
            ])
        
        table = Table(data)
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        
        elements.append(table)
        doc.build(elements)
        return response


class ExportMilkPDFView(LoginRequiredMixin, View):
    """Export milk records to PDF"""
    
    def get(self, request):
        response = HttpResponse(content_type='application/pdf')
        response['Content-Disposition'] = 'attachment; filename="milk_records_export.pdf"'
        
        doc = SimpleDocTemplate(response, pagesize=landscape(letter))
        elements = []
        
        styles = getSampleStyleSheet()
        title = Paragraph("Milk Records Export", styles['Title'])
        elements.append(title)
        
        data = [['Date', 'Cattle', 'Session', 'Quantity (L)', 'Fat %', 'Temperature']]
        for record in MilkRecord.objects.select_related('cattle').all()[:50]:
            data.append([
                record.date.strftime('%Y-%m-%d'),
                record.cattle.tag_number,
                record.get_session_display(),
                str(record.quantity),
                str(record.fat_percentage) if record.fat_percentage else '-',
                str(record.temperature) if record.temperature else '-'
            ])
        
        table = Table(data)
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        
        elements.append(table)
        doc.build(elements)
        return response


class ExportHealthPDFView(LoginRequiredMixin, View):
    """Export health records to PDF"""
    
    def get(self, request):
        response = HttpResponse(content_type='application/pdf')
        response['Content-Disposition'] = 'attachment; filename="health_records_export.pdf"'
        
        doc = SimpleDocTemplate(response, pagesize=landscape(letter))
        elements = []
        
        styles = getSampleStyleSheet()
        title = Paragraph("Health Records Export", styles['Title'])
        elements.append(title)
        
        data = [['Date', 'Cattle', 'Health Type', 'Diagnosis', 'Veterinarian', 'Cost']]
        for record in HealthRecord.objects.select_related('cattle').all()[:50]:
            data.append([
                record.date.strftime('%Y-%m-%d'),
                record.cattle.tag_number,
                record.get_health_type_display(),
                record.diagnosis[:30] + '...' if len(record.diagnosis) > 30 else record.diagnosis,
                record.veterinarian,
                str(record.treatment_cost) if record.treatment_cost else '-'
            ])
        
        table = Table(data)
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        
        elements.append(table)
        doc.build(elements)
        return response


class ExportFeedingPDFView(LoginRequiredMixin, View):
    """Export feeding records to PDF"""
    
    def get(self, request):
        response = HttpResponse(content_type='application/pdf')
        response['Content-Disposition'] = 'attachment; filename="feeding_records_export.pdf"'
        
        doc = SimpleDocTemplate(response, pagesize=landscape(letter))
        elements = []
        
        styles = getSampleStyleSheet()
        title = Paragraph("Feeding Records Export", styles['Title'])
        elements.append(title)
        
        data = [['Date', 'Time', 'Cattle', 'Feed Type', 'Quantity (kg)', 'Cost']]
        for record in FeedingRecord.objects.select_related('cattle').all()[:50]:
            data.append([
                record.date.strftime('%Y-%m-%d'),
                record.feed_time.strftime('%H:%M'),
                record.cattle.tag_number,
                record.get_feed_type_display(),
                str(record.quantity),
                str(record.total_cost)
            ])
        
        table = Table(data)
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        
        elements.append(table)
        doc.build(elements)
        return response


class ExportWeightPDFView(LoginRequiredMixin, View):
    """Export weight records to PDF"""
    
    def get(self, request):
        response = HttpResponse(content_type='application/pdf')
        response['Content-Disposition'] = 'attachment; filename="weight_records_export.pdf"'
        
        doc = SimpleDocTemplate(response, pagesize=landscape(letter))
        elements = []
        
        styles = getSampleStyleSheet()
        title = Paragraph("Weight Records Export", styles['Title'])
        elements.append(title)
        
        data = [['Date', 'Cattle', 'Weight (kg)', 'Daily Gain', 'Age (days)']]
        for record in WeightRecord.objects.select_related('cattle').all()[:50]:
            data.append([
                record.date.strftime('%Y-%m-%d'),
                record.cattle.tag_number,
                str(record.weight),
                str(record.daily_gain) if record.daily_gain else '-',
                str(record.age_in_days) if record.age_in_days else '-'
            ])
        
        table = Table(data)
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        
        elements.append(table)
        doc.build(elements)
        return response


class ExportBreedingPDFView(LoginRequiredMixin, View):
    """Export breeding records to PDF"""
    
    def get(self, request):
        response = HttpResponse(content_type='application/pdf')
        response['Content-Disposition'] = 'attachment; filename="breeding_records_export.pdf"'
        
        doc = SimpleDocTemplate(response, pagesize=landscape(letter))
        elements = []
        
        styles = getSampleStyleSheet()
        title = Paragraph("Breeding Records Export", styles['Title'])
        elements.append(title)
        
        data = [['Breeding Date', 'Dam', 'Sire', 'Method', 'Status', 'Expected Calving']]
        for record in BreedingRecord.objects.select_related('cattle', 'sire').all()[:50]:
            data.append([
                record.breeding_date.strftime('%Y-%m-%d'),
                record.cattle.tag_number,
                record.sire.tag_number if record.sire else '-',
                record.breeding_method,
                record.get_status_display(),
                record.expected_calving_date.strftime('%Y-%m-%d') if record.expected_calving_date else '-'
            ])
        
        table = Table(data)
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        
        elements.append(table)
        doc.build(elements)
        return response


class ExportVaccinationPDFView(LoginRequiredMixin, View):
    """Export vaccination records to PDF"""
    
    def get(self, request):
        response = HttpResponse(content_type='application/pdf')
        response['Content-Disposition'] = 'attachment; filename="vaccination_records_export.pdf"'
        
        doc = SimpleDocTemplate(response, pagesize=landscape(letter))
        elements = []
        
        styles = getSampleStyleSheet()
        title = Paragraph("Vaccination Records Export", styles['Title'])
        elements.append(title)
        
        data = [['Scheduled Date', 'Cattle', 'Vaccine', 'Status', 'Administered', 'Batch']]
        for record in VaccinationSchedule.objects.select_related('cattle').all()[:50]:
            data.append([
                record.scheduled_date.strftime('%Y-%m-%d'),
                record.cattle.tag_number,
                record.get_vaccine_type_display(),
                'Completed' if record.is_completed else 'Pending',
                record.administered_date.strftime('%Y-%m-%d') if record.administered_date else '-',
                record.batch_number or '-'
            ])
        
        table = Table(data)
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        
        elements.append(table)
        doc.build(elements)
        return response


class ExportSalesPDFView(LoginRequiredMixin, View):
    """Export sales records to PDF"""
    
    def get(self, request):
        response = HttpResponse(content_type='application/pdf')
        response['Content-Disposition'] = 'attachment; filename="sales_export.pdf"'
        
        doc = SimpleDocTemplate(response, pagesize=landscape(letter))
        elements = []
        
        styles = getSampleStyleSheet()
        title = Paragraph("Sales Export", styles['Title'])
        elements.append(title)
        
        data = [['Date', 'Type', 'Details', 'Quantity', 'Amount', 'Status']]
        
        # Milk Sales
        for sale in MilkSale.objects.all()[:25]:
            data.append([
                sale.date.strftime('%Y-%m-%d'),
                'Milk Sale',
                sale.customer_name or 'Retail',
                str(sale.quantity) + ' L',
                '৳' + str(sale.total_amount),
                'Paid' if sale.payment_received else 'Pending'
            ])
        
        # Cattle Sales
        for sale in CattleSale.objects.select_related('cattle').all()[:25]:
            data.append([
                sale.sale_date.strftime('%Y-%m-%d'),
                'Cattle Sale',
                sale.cattle.tag_number,
                '1 head',
                '৳' + str(sale.sale_price),
                'Paid' if sale.payment_received else 'Pending'
            ])
        
        table = Table(data)
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        
        elements.append(table)
        doc.build(elements)
        return response


class ExportFinancialPDFView(LoginRequiredMixin, View):
    """Export financial records to PDF"""
    
    def get(self, request):
        response = HttpResponse(content_type='application/pdf')
        response['Content-Disposition'] = 'attachment; filename="financial_export.pdf"'
        
        doc = SimpleDocTemplate(response, pagesize=landscape(letter))
        elements = []
        
        styles = getSampleStyleSheet()
        title = Paragraph("Financial Export", styles['Title'])
        elements.append(title)
        
        # Summary Section
        total_income = MilkSale.objects.aggregate(total=Sum('total_amount'))['total'] or 0
        total_expenses = Expense.objects.aggregate(total=Sum('amount'))['total'] or 0
        total_investments = Investment.objects.aggregate(total=Sum('amount'))['total'] or 0
        
        data = [
            ['Financial Summary', '', ''],
            ['Total Income', '৳' + str(total_income), ''],
            ['Total Expenses', '৳' + str(total_expenses), ''],
            ['Net Profit', '৳' + str(total_income - total_expenses), ''],
            ['', '', ''],
            ['Expenses by Category', '', ''],
        ]
        
        # Expenses by category
        for category in ExpenseCategory.objects.all():
            category_total = Expense.objects.filter(category=category).aggregate(total=Sum('amount'))['total'] or 0
            if category_total > 0:
                data.append([category.name, '৳' + str(category_total), ''])
        
        table = Table(data)
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        
        elements.append(table)
        doc.build(elements)
        return response