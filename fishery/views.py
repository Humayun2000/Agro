from django.urls import reverse_lazy
from django.views.generic import (
    ListView, CreateView, DetailView,
    UpdateView, DeleteView, TemplateView, 
)
from .services import (
    total_stock_investment,
    total_feed_expense,
    total_revenue,
    net_profit,
    mortality_percentage,
    harvest_yield_percentage,
    roi_percentage,
    total_capital
)

from django.contrib.auth.mixins import LoginRequiredMixin
from .models import Pond, FishSpecies, Stock, FeedRecord, MortalityRecord, Harvest, FishSale, ProductionCycle, FisheryFinancialReport, Expense
from .forms import PondForm, FishSpeciesForm, StockForm, FeedRecordForm, MortalityRecordForm, HarvestForm, FishSaleForm, ProductionCycleForm, ExpenseForm
from django.contrib import messages 
from django.db.models import Sum, F, DecimalField, ExpressionWrapper 
from decimal import Decimal
from django.utils import timezone
from django.shortcuts import get_object_or_404, redirect

# base fishery views  

class FisheryDashboardView(TemplateView):
    template_name = "fishery/dashboard.html"


# LIST
class PondListView(LoginRequiredMixin, ListView):
    model = Pond
    template_name = 'fishery/pond/pond_list.html'
    context_object_name = 'ponds'


# DETAIL
class PondDetailView(LoginRequiredMixin, DetailView):
    model = Pond
    template_name = 'fishery/pond/pond_detail.html'


# CREATE
class PondCreateView(LoginRequiredMixin, CreateView):
    model = Pond
    form_class = PondForm
    template_name = 'fishery/pond/pond_form.html'
    success_url = reverse_lazy('pond_list')


# UPDATE
class PondUpdateView(LoginRequiredMixin, UpdateView):
    model = Pond
    form_class = PondForm
    template_name = 'fishery/pond/pond_form.html'
    success_url = reverse_lazy('pond_list')


# DELETE
class PondDeleteView(LoginRequiredMixin, DeleteView):
    model = Pond
    template_name = 'fishery/pond/pond_confirm_delete.html'
    success_url = reverse_lazy('pond_list')


# Fishspecies all views           

class FishSpeciesListView(ListView):
    model = FishSpecies
    template_name = 'fishery/fishspecies/list.html'
    context_object_name = 'species'


class FishSpeciesDetailView(DetailView):
    model = FishSpecies
    template_name = 'fishery/fishspecies/detail.html'
    context_object_name = 'species'


class FishSpeciesCreateView(CreateView):
    model = FishSpecies
    form_class = FishSpeciesForm
    template_name = 'fishery/fishspecies/create.html'
    success_url = reverse_lazy('fishspecies_list')

    def form_valid(self, form):
        messages.success(self.request, "Fish Species created successfully.")
        return super().form_valid(form)


class FishSpeciesUpdateView(UpdateView):
    model = FishSpecies
    form_class = FishSpeciesForm
    template_name = 'fishery/fishspecies/update.html'
    success_url = reverse_lazy('fishspecies_list')

    def form_valid(self, form):
        messages.success(self.request, "Fish Species updated successfully.")
        return super().form_valid(form)


class FishSpeciesDeleteView(DeleteView):
    model = FishSpecies
    template_name = 'fishery/fishspecies/delete.html'
    success_url = reverse_lazy('fishspecies_list')

    def delete(self, request, *args, **kwargs):
        messages.success(self.request, "Fish Species deleted successfully.")
        return super().delete(request, *args, **kwargs)
    

# stock views  

class StockListView(ListView):
    model = Stock
    template_name = "fishery/stock/list.html"
    context_object_name = "stocks"


class StockDetailView(DetailView):
    model = Stock
    template_name = "fishery/stock/detail.html"
    context_object_name = "stock"


class StockCreateView(CreateView):
    model = Stock
    form_class = StockForm
    template_name = "fishery/stock/create.html"
    success_url = reverse_lazy('stock_list')

    def form_valid(self, form):
        messages.success(self.request, "Stock created successfully.")
        return super().form_valid(form)


class StockUpdateView(UpdateView):
    model = Stock
    form_class = StockForm
    template_name = "fishery/stock/update.html"
    success_url = reverse_lazy('stock_list')

    def form_valid(self, form):
        messages.success(self.request, "Stock updated successfully.")
        return super().form_valid(form)


class StockDeleteView(DeleteView):
    model = Stock
    template_name = "fishery/stock/delete.html"
    success_url = reverse_lazy('stock_list')

    def delete(self, request, *args, **kwargs):
        messages.success(self.request, "Stock deleted successfully.")
        return super().delete(request, *args, **kwargs)
    

# Feed record views 

# List all feed records
class FeedListView(LoginRequiredMixin, ListView):
    model = FeedRecord
    template_name = 'fishery/feed/feed_list.html'
    context_object_name = 'feeds'
    ordering = ['-date']

# Create new feed record
class FeedCreateView(LoginRequiredMixin, CreateView):
    model = FeedRecord
    form_class = FeedRecordForm
    template_name = 'fishery/feed/feed_form.html'
    success_url = reverse_lazy('feed_list')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Add Feed Record'
        return context

# Update existing feed record
class FeedUpdateView(LoginRequiredMixin, UpdateView):
    model = FeedRecord
    form_class = FeedRecordForm
    template_name = 'fishery/feed/feed_form.html'
    success_url = reverse_lazy('feed_list')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Edit Feed Record'
        return context

# Delete a feed record
class FeedDeleteView(LoginRequiredMixin, DeleteView):
    model = FeedRecord
    template_name = 'fishery/feed/feed_confirm_delete.html'
    success_url = reverse_lazy('feed_list')


# Mortality record views 

class MortalityListView(LoginRequiredMixin, ListView):
    model = MortalityRecord
    template_name = 'fishery/mortality/mortality_list.html'
    context_object_name = 'records'
    ordering = ['-date']


class MortalityCreateView(LoginRequiredMixin, CreateView):
    model = MortalityRecord
    form_class = MortalityRecordForm
    template_name = 'fishery/mortality/mortality_form.html'
    success_url = reverse_lazy('mortality_list')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Add Mortality Record'
        return context


class MortalityUpdateView(LoginRequiredMixin, UpdateView):
    model = MortalityRecord
    form_class = MortalityRecordForm
    template_name = 'fishery/mortality/mortality_form.html'
    success_url = reverse_lazy('mortality_list')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Edit Mortality Record'
        return context


class MortalityDeleteView(LoginRequiredMixin, DeleteView):
    model = MortalityRecord
    template_name = 'fishery/mortality/mortality_confirm_delete.html'
    success_url = reverse_lazy('mortality_list')

# Harvest views will be implemented in the next phase of development.

class HarvestListView(LoginRequiredMixin, ListView):
    model = Harvest
    template_name = 'fishery/harvest/harvest_list.html'
    context_object_name = 'harvests'
    ordering = ['-harvest_date']


class HarvestCreateView(LoginRequiredMixin, CreateView):
    model = Harvest
    form_class = HarvestForm
    template_name = 'fishery/harvest/harvest_form.html'
    success_url = reverse_lazy('harvest_list')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Add Harvest Record'
        return context


class HarvestUpdateView(LoginRequiredMixin, UpdateView):
    model = Harvest
    form_class = HarvestForm
    template_name = 'fishery/harvest/harvest_form.html'
    success_url = reverse_lazy('harvest_list')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Edit Harvest Record'
        return context


class HarvestDeleteView(LoginRequiredMixin, DeleteView):
    model = Harvest
    template_name = 'fishery/harvest/harvest_confirm_delete.html'
    success_url = reverse_lazy('harvest_list')



# fishery analytics view

class FisheryFinancialDashboardView(LoginRequiredMixin, TemplateView):
    template_name = 'fishery/financialy_dashboard.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context['stock_investment'] = total_stock_investment()
        context['feed_expense'] = total_feed_expense()
        context['revenue'] = total_revenue()
        context['capital'] = total_capital()
        context['profit'] = net_profit()

        context['mortality_percent'] = mortality_percentage()
        context['harvest_percent'] = harvest_yield_percentage()
        context['roi'] = roi_percentage()

        return context
    

# fish sales views 

# ---------------------------
# List View
# ---------------------------
class FishSaleListView(LoginRequiredMixin, ListView):
    model = FishSale
    template_name = "fishery/sale/sale_list.html"
    context_object_name = "sales"
    paginate_by = 15

    def get_queryset(self):
        # Select related harvest → stock → pond & cycle → species
        return FishSale.objects.select_related(
            "harvest__stock__pond",
            "harvest__cycle__species"
        ).annotate(
            pond_name=F("harvest__stock__pond__name"),
            species_name=F("harvest__cycle__species__name")
        ).order_by("-sale_date")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        qs = self.get_queryset()

        context["total_quantity"] = qs.aggregate(total=Sum("quantity_kg"))["total"] or 0
        context["total_sales_amount"] = qs.aggregate(
            total=Sum(
                ExpressionWrapper(
                    F("quantity_kg") * F("price_per_kg"),
                    output_field=DecimalField(max_digits=14, decimal_places=2)
                )
            )
        )["total"] or 0
        return context

# ---------------------------
# Create View
# ---------------------------
class FishSaleCreateView(LoginRequiredMixin, CreateView):
    model = FishSale
    form_class = FishSaleForm
    template_name = "fishery/sale/sale_form.html"
    success_url = reverse_lazy("sale_list")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["title"] = "Add Fish Sale"
        return context

# ---------------------------
# Update View
# ---------------------------
class FishSaleUpdateView(LoginRequiredMixin, UpdateView):
    model = FishSale
    form_class = FishSaleForm
    template_name = "fishery/sale/sale_form.html"
    success_url = reverse_lazy("sale_list")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["title"] = "Edit Fish Sale"
        return context

# ---------------------------
# Delete View
# ---------------------------
class FishSaleDeleteView(LoginRequiredMixin, DeleteView):
    model = FishSale
    template_name = "fishery/sale/sale_confirm_delete.html"
    success_url = reverse_lazy("sale_list")

# production cycle views will be implemented in the next phase of development.

class ProductionCycleListView(ListView):
    model = ProductionCycle
    template_name = 'fishery/cycle/cycle_list.html'
    context_object_name = 'cycles'
    ordering = ['-stocking_date']

class ProductionCycleDetailView(DetailView):
    model = ProductionCycle
    template_name = 'fishery/cycle/cycle_detail.html'
    context_object_name = 'cycle'

class ProductionCycleCreateView(CreateView):
    model = ProductionCycle
    form_class = ProductionCycleForm
    template_name = 'fishery/cycle/cycle_form.html'
    success_url = reverse_lazy('cycle_list')

class ProductionCycleUpdateView(UpdateView):
    model = ProductionCycle
    form_class = ProductionCycleForm
    template_name = 'fishery/cycle/cycle_form.html'
    success_url = reverse_lazy('cycle_list')

class ProductionCycleDeleteView(DeleteView):
    model = ProductionCycle
    template_name = 'fishery/cycle/cycle_confirm_delete.html'
    success_url = reverse_lazy('cycle_list')

class ExpenseCreateView(CreateView):
    model = Expense
    form_class = ExpenseForm
    template_name = 'fishery/cycle/expense_form.html'
    success_url = reverse_lazy('cycle_list')  # or redirect to cycle_detail

    def get_initial(self):
        initial = super().get_initial()
        cycle_id = self.request.GET.get('cycle')
        if cycle_id:
            initial['cycle'] = cycle_id
        return initial

    def form_valid(self, form):
        messages.success(self.request, "Expense added successfully.")
        return super().form_valid(form)


class ExpenseUpdateView(UpdateView):
    model = Expense
    form_class = ExpenseForm
    template_name = 'fishery/cycle/expense_form.html'
    success_url = reverse_lazy('cycle_list')


class ExpenseDeleteView(DeleteView):
    model = Expense
    template_name = 'fishery/cycle/expense_confirm_delete.html'
    success_url = reverse_lazy('cycle_list')

# Anual report view will be implemented in the next phase of development.


class FisheryAnnualReportView(TemplateView):
    template_name = 'fishery/report/annual_report.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        year = self.kwargs.get('year') or timezone.now().year

        # -------- INVESTMENTS -------- #

        total_fish_purchase = (
            Stock.objects.filter(stocking_date__year=year)
            .aggregate(total=Sum('cost'))['total'] or Decimal('0')
        )

        total_feed_purchase = (
            FeedRecord.objects.filter(date__year=year)
            .aggregate(total=Sum('cost'))['total'] or Decimal('0')
        )

        total_other_expenses = (
            Expense.objects.filter(cycle__stocking_date__year=year)
            .aggregate(total=Sum('amount'))['total'] or Decimal('0')
        )

        total_investment = (
            total_fish_purchase +
            total_feed_purchase +
            total_other_expenses
        )

        # -------- PRODUCTION -------- #

        total_harvest = (
            Harvest.objects.filter(harvest_date__year=year)
            .aggregate(total=Sum('quantity_kg'))['total'] or Decimal('0')
        )

        total_mortality = (
            MortalityRecord.objects.filter(date__year=year)
            .aggregate(total=Sum('quantity_dead'))['total'] or 0
        )

        # -------- SALES -------- #

        sales_expression = ExpressionWrapper(
            F('quantity_kg') * F('price_per_kg'),
            output_field=DecimalField(max_digits=15, decimal_places=2)
        )

        total_sales = (
            FishSale.objects.filter(sale_date__year=year)
            .aggregate(total=Sum(sales_expression))['total'] or Decimal('0')
        )

        # -------- PROFIT -------- #

        net_profit = total_sales - total_investment

        # -------- ROI -------- #

        roi = None
        if total_investment > 0:
            roi = (net_profit / total_investment) * Decimal('100')

        context.update({
            'year': year,
            'total_fish_purchase': total_fish_purchase,
            'total_feed_purchase': total_feed_purchase,
            'total_other_expenses': total_other_expenses,
            'total_investment': total_investment,
            'total_harvest': total_harvest,
            'total_sales': total_sales,
            'net_profit': net_profit,
            'total_mortality': total_mortality,
            'roi': roi,
        })

        return context