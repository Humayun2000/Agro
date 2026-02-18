from django.urls import reverse_lazy
from django.views.generic import (
    ListView, CreateView, DetailView,
    UpdateView, DeleteView, TemplateView
)
from django.contrib.auth.mixins import LoginRequiredMixin
from .models import Pond, FishSpecies, Stock, FeedRecord
from .forms import PondForm, FishSpeciesForm, StockForm, FeedRecordForm
from django.contrib import messages


# base fishery views  

class FisheryDashboardView(TemplateView):
    template_name = "fishery/dashboard.html"


# LIST
class PondListView(LoginRequiredMixin, ListView):
    model = Pond
    template_name = 'fishery/pond_list.html'
    context_object_name = 'ponds'


# DETAIL
class PondDetailView(LoginRequiredMixin, DetailView):
    model = Pond
    template_name = 'fishery/pond_detail.html'


# CREATE
class PondCreateView(LoginRequiredMixin, CreateView):
    model = Pond
    form_class = PondForm
    template_name = 'fishery/pond_form.html'
    success_url = reverse_lazy('pond_list')


# UPDATE
class PondUpdateView(LoginRequiredMixin, UpdateView):
    model = Pond
    form_class = PondForm
    template_name = 'fishery/pond_form.html'
    success_url = reverse_lazy('pond_list')


# DELETE
class PondDeleteView(LoginRequiredMixin, DeleteView):
    model = Pond
    template_name = 'fishery/pond_confirm_delete.html'
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