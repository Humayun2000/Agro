from django.urls import reverse_lazy
from django.views.generic import (
    ListView, CreateView, DetailView,
    UpdateView, DeleteView, TemplateView
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
from .models import Pond, FishSpecies, Stock, FeedRecord, MortalityRecord, Harvest, FishSale
from .forms import PondForm, FishSpeciesForm, StockForm, FeedRecordForm, MortalityRecordForm, HarvestForm, FishSaleForm
from django.contrib import messages


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

class FishSaleListView(LoginRequiredMixin, ListView):
    model = FishSale
    template_name = 'fishery/sale/sale_list.html'
    context_object_name = 'sales'
    ordering = ['-sale_date']


class FishSaleCreateView(LoginRequiredMixin, CreateView):
    model = FishSale
    form_class = FishSaleForm
    template_name = 'fishery/sale/sale_form.html'
    success_url = reverse_lazy('sale_list')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Add Fish Sale'
        return context


class FishSaleUpdateView(LoginRequiredMixin, UpdateView):
    model = FishSale
    form_class = FishSaleForm
    template_name = 'fishery/sale/sale_form.html'
    success_url = reverse_lazy('sale_list')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Edit Fish Sale'
        return context


class FishSaleDeleteView(LoginRequiredMixin, DeleteView):
    model = FishSale
    template_name = 'fishery/sale/sale_confirm_delete.html'
    success_url = reverse_lazy('sale_list')
