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

    # stock all urls 

    path('stock/', StockListView.as_view(), name='stock_list'),
    path('stock/create/', StockCreateView.as_view(), name='stock_create'),
    path('stock/<int:pk>/', StockDetailView.as_view(), name='stock_detail'),
    path('stock/<int:pk>/update/', StockUpdateView.as_view(), name='stock_update'),
    path('stock/<int:pk>/delete/', StockDeleteView.as_view(), name='stock_delete'),

    # feed record all urls
    path('feed/', FeedListView.as_view(), name='feed_list'),
    path('feed/add/', FeedCreateView.as_view(), name='feed_create'),
    path('feed/<int:pk>/edit/', FeedUpdateView.as_view(), name='feed_update'),
    path('feed/<int:pk>/delete/', FeedDeleteView.as_view(), name='feed_delete'),

    # mortality record all urls
    path('mortality/', MortalityListView.as_view(), name='mortality_list'),
    path('mortality/add/', MortalityCreateView.as_view(), name='mortality_create'),
    path('mortality/<int:pk>/edit/', MortalityUpdateView.as_view(), name='mortality_update'),
    path('mortality/<int:pk>/delete/', MortalityDeleteView.as_view(), name='mortality_delete'),

    # harvest all urls
    path('harvest/', HarvestListView.as_view(), name='harvest_list'),
    path('harvest/add/', HarvestCreateView.as_view(), name='harvest_create'),
    path('harvest/<int:pk>/edit/', HarvestUpdateView.as_view(), name='harvest_update'),
    path('harvest/<int:pk>/delete/', HarvestDeleteView.as_view(), name='harvest_delete'),


    # financial overview url
    path('financial-dashboard/', FisheryFinancialDashboardView.as_view(), name='financialy_dashboard'),

    # fish sale urls 

    path('sale/', FishSaleListView.as_view(), name='sale_list'),
    path('sale/add/', FishSaleCreateView.as_view(), name='sale_create'),
    path('sale/<int:pk>/edit/', FishSaleUpdateView.as_view(), name='sale_update'),
    path('sale/<int:pk>/delete/', FishSaleDeleteView.as_view(), name='sale_delete'),

]
