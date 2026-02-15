from django.urls import path
from . import views

urlpatterns = [
    path('ponds/', views.PondListView.as_view(), name='pond_list'),
    path('ponds/create/', views.PondCreateView.as_view(), name='pond_create'),
    path('ponds/<int:pk>/', views.PondDetailView.as_view(), name='pond_detail'),
    path('ponds/<int:pk>/update/', views.PondUpdateView.as_view(), name='pond_update'),
    path('ponds/<int:pk>/delete/', views.PondDeleteView.as_view(), name='pond_delete'),
]
