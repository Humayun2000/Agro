from django.urls import path
from .views import *

urlpatterns = [
    
    # Dashboard
    path('', DairyDashboardView.as_view(), name='dairy_dashboard'),

    # Breed
    path('breed/', BreedListView.as_view(), name='breed_list'),
    path('breed/create/', BreedCreateView.as_view(), name='breed_create'),
    path('breed/<int:pk>/update/', BreedUpdateView.as_view(), name='breed_update'),
    path('breed/<int:pk>/delete/', BreedDeleteView.as_view(), name='breed_delete'),

    # Cow
    path('cow/', CowListView.as_view(), name='cow_list'),
    path('cow/create/', CowCreateView.as_view(), name='cow_create'),
    path('cow/<int:pk>/update/', CowUpdateView.as_view(), name='cow_update'),
    path('cow/<int:pk>/delete/', CowDeleteView.as_view(), name='cow_delete'),

    # Milk Production
    path('milk/', MilkProductionListView.as_view(), name='milk_list'),
    path('milk/create/', MilkProductionCreateView.as_view(), name='milk_create'),
    path('milk/<int:pk>/update/', MilkProductionUpdateView.as_view(), name='milk_update'),
    path('milk/<int:pk>/delete/', MilkProductionDeleteView.as_view(), name='milk_delete'),
]