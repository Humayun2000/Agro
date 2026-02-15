from django.urls import reverse_lazy
from django.views.generic import (
    ListView, CreateView, DetailView,
    UpdateView, DeleteView
)
from django.contrib.auth.mixins import LoginRequiredMixin
from .models import Pond
from .forms import PondForm


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
