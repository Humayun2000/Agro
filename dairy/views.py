from django.urls import reverse_lazy
from django.db.models import Sum, F, ExpressionWrapper, DecimalField
from django.utils import timezone
from django.views.generic import TemplateView
from django.views.generic import (
    ListView, CreateView, UpdateView, DeleteView
)
from .models import Breed, Cow, MilkProduction
from .forms import BreedForm, CowForm, MilkProductionForm

class DairyDashboardView(TemplateView):
    template_name = "dairy/dashboard.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        today = timezone.now().date()
        current_month = today.month
        current_year = today.year

        context['total_cows'] = Cow.objects.count()
        context['active_cows'] = Cow.objects.filter(status='active').count()
        context['lactating_cows'] = Cow.objects.filter(
            lactating=True,
            status='active'
        ).count()

        today_milk = MilkProduction.objects.filter(date=today).aggregate(
            total=Sum(
                ExpressionWrapper(
                    F('morning_milk') + F('evening_milk'),
                    output_field=DecimalField()
                )
            )
        )

        context['today_milk'] = today_milk['total'] or 0

        monthly_milk = MilkProduction.objects.filter(
            date__year=current_year,
            date__month=current_month
        ).aggregate(
            total=Sum(
                ExpressionWrapper(
                    F('morning_milk') + F('evening_milk'),
                    output_field=DecimalField()
                )
            )
        )

        context['monthly_milk'] = monthly_milk['total'] or 0

        return context

# -------------------------
# Breed CRUD
# -------------------------

class BreedListView(ListView):
    model = Breed
    template_name = 'dairy/breed/list.html'


class BreedCreateView(CreateView):
    model = Breed
    form_class = BreedForm
    template_name = 'dairy/breed/form.html'
    success_url = reverse_lazy('breed_list')


class BreedUpdateView(UpdateView):
    model = Breed
    form_class = BreedForm
    template_name = 'dairy/breed/form.html'
    success_url = reverse_lazy('breed_list')


class BreedDeleteView(DeleteView):
    model = Breed
    template_name = 'dairy/breed/confirm_delete.html'
    success_url = reverse_lazy('breed_list')


# -------------------------
# Cow CRUD
# -------------------------

class CowListView(ListView):
    model = Cow
    template_name = 'dairy/cow/list.html'


class CowCreateView(CreateView):
    model = Cow
    form_class = CowForm
    template_name = 'dairy/cow/form.html'
    success_url = reverse_lazy('cow_list')


class CowUpdateView(UpdateView):
    model = Cow
    form_class = CowForm
    template_name = 'dairy/cow/form.html'
    success_url = reverse_lazy('cow_list')


class CowDeleteView(DeleteView):
    model = Cow
    template_name = 'dairy/cow/confirm_delete.html'
    success_url = reverse_lazy('cow_list')


# -------------------------
# Milk Production CRUD
# -------------------------

class MilkProductionListView(ListView):
    model = MilkProduction
    template_name = 'dairy/milk/list.html'


class MilkProductionCreateView(CreateView):
    model = MilkProduction
    form_class = MilkProductionForm
    template_name = 'dairy/milk/form.html'
    success_url = reverse_lazy('milk_list')


class MilkProductionUpdateView(UpdateView):
    model = MilkProduction
    form_class = MilkProductionForm
    template_name = 'dairy/milk/form.html'
    success_url = reverse_lazy('milk_list')


class MilkProductionDeleteView(DeleteView):
    model = MilkProduction
    template_name = 'dairy/milk/confirm_delete.html'
    success_url = reverse_lazy('milk_list')