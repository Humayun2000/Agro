from django.urls import path
from . import views 
from .views import *

urlpatterns = [
    # base fishery urls
    path('dashboard/', FisheryDashboardView.as_view(), name='fishery_dashboard'),

    path('ponds/', views.PondListView.as_view(), name='pond_list'),
    path('ponds/create/', views.PondCreateView.as_view(), name='pond_create'),
    path('ponds/<int:pk>/', views.PondDetailView.as_view(), name='pond_detail'),
    path('ponds/<int:pk>/update/', views.PondUpdateView.as_view(), name='pond_update'),
    path('ponds/<int:pk>/delete/', views.PondDeleteView.as_view(), name='pond_delete'),


    # fishspecies all urls
    path('species/', FishSpeciesListView.as_view(), name='fishspecies_list'),
    path('species/create/', FishSpeciesCreateView.as_view(), name='fishspecies_create'),
    path('species/<int:pk>/', FishSpeciesDetailView.as_view(), name='fishspecies_detail'),
    path('species/<int:pk>/update/', FishSpeciesUpdateView.as_view(), name='fishspecies_update'),
    path('species/<int:pk>/delete/', FishSpeciesDeleteView.as_view(), name='fishspecies_delete'),
]
