from django.urls import path, include
from . import views

app_name = 'dairy'

urlpatterns = [
    # ==================== DASHBOARD ====================
    path('', views.DairyDashboardView.as_view(), name='dairy_dashboard'),
    
    # ==================== API ENDPOINTS ====================
    # Include all API URLs from api_urls.py
    path('api/', include('dairy.api_urls')),
    
    # ==================== CATTLE MANAGEMENT ====================
    # List and Detail
    path('cattle/', views.CattleListView.as_view(), name='cattle_list'),
    path('cattle/<int:pk>/', views.CattleDetailView.as_view(), name='cattle_detail'),
    
    # Create/Update/Delete
    path('cattle/add/', views.CattleCreateView.as_view(), name='cattle_add'),
    path('cattle/<int:pk>/edit/', views.CattleUpdateView.as_view(), name='cattle_edit'),
    path('cattle/<int:pk>/delete/', views.CattleDeleteView.as_view(), name='cattle_delete'),
    
    # ==================== MILK RECORDS ====================
    # List
    path('milk/', views.MilkRecordListView.as_view(), name='milk_list'),
    
    # Create/Update/Delete
    path('milk/add/', views.MilkRecordCreateView.as_view(), name='milk_add'),
    path('milk/<int:pk>/edit/', views.MilkRecordUpdateView.as_view(), name='milk_edit'),
    path('milk/<int:pk>/delete/', views.MilkRecordDeleteView.as_view(), name='milk_delete'),
    
    # ==================== MILK SALES ====================
    # List
    path('milk-sales/', views.MilkSaleListView.as_view(), name='milk_sale_list'),
    
    # Create/Update/Delete
    path('milk-sales/add/', views.MilkSaleCreateView.as_view(), name='milk_sale_add'),
    path('milk-sales/<int:pk>/edit/', views.MilkSaleUpdateView.as_view(), name='milk_sale_edit'),
    path('milk-sales/<int:pk>/delete/', views.MilkSaleDeleteView.as_view(), name='milk_sale_delete'),
    
    # ==================== CATTLE SALES ====================
    # List
    path('cattle-sales/', views.CattleSaleListView.as_view(), name='cattle_sale_list'),
    
    # Create/Update/Delete
    path('cattle-sales/add/', views.CattleSaleCreateView.as_view(), name='cattle_sale_add'),
    path('cattle-sales/<int:pk>/edit/', views.CattleSaleUpdateView.as_view(), name='cattle_sale_edit'),
    path('cattle-sales/<int:pk>/delete/', views.CattleSaleDeleteView.as_view(), name='cattle_sale_delete'),
    
    # ==================== HEALTH RECORDS ====================
    # List
    path('health/', views.HealthRecordListView.as_view(), name='health_list'),
    
    # Create/Update/Delete
    path('health/add/', views.HealthRecordCreateView.as_view(), name='health_add'),
    path('health/<int:pk>/edit/', views.HealthRecordUpdateView.as_view(), name='health_edit'),
    path('health/<int:pk>/delete/', views.HealthRecordDeleteView.as_view(), name='health_delete'),
    
    # ==================== WEIGHT RECORDS ====================
    # List
    path('weight/', views.WeightRecordListView.as_view(), name='weight_list'),
    
    # Create/Update/Delete
    path('weight/add/', views.WeightRecordCreateView.as_view(), name='weight_add'),
    path('weight/<int:pk>/edit/', views.WeightRecordUpdateView.as_view(), name='weight_edit'),
    path('weight/<int:pk>/delete/', views.WeightRecordDeleteView.as_view(), name='weight_delete'),
    
    # ==================== FEEDING RECORDS ====================
    # List
    path('feeding/', views.FeedingRecordListView.as_view(), name='feeding_list'),
    
    # Create/Update/Delete
    path('feeding/add/', views.FeedingRecordCreateView.as_view(), name='feeding_add'),
    path('feeding/<int:pk>/edit/', views.FeedingRecordUpdateView.as_view(), name='feeding_edit'),
    path('feeding/<int:pk>/delete/', views.FeedingRecordDeleteView.as_view(), name='feeding_delete'),
    
    # ==================== BREEDING RECORDS ====================
    # List
    path('breeding/', views.BreedingRecordListView.as_view(), name='breeding_list'),
    
    # Create/Update/Delete
    path('breeding/add/', views.BreedingRecordCreateView.as_view(), name='breeding_add'),
    path('breeding/<int:pk>/edit/', views.BreedingRecordUpdateView.as_view(), name='breeding_edit'),
    path('breeding/<int:pk>/delete/', views.BreedingRecordDeleteView.as_view(), name='breeding_delete'),
    
    # ==================== VACCINATION RECORDS ====================
    # List
    path('vaccination/', views.VaccinationListView.as_view(), name='vaccination_list'),
    
    # Create/Update/Delete
    path('vaccination/add/', views.VaccinationCreateView.as_view(), name='vaccination_add'),
    path('vaccination/<int:pk>/edit/', views.VaccinationUpdateView.as_view(), name='vaccination_edit'),
    path('vaccination/<int:pk>/delete/', views.VaccinationDeleteView.as_view(), name='vaccination_delete'),
    
    # ==================== EXPENSES ====================
    # List
    path('expenses/', views.ExpenseListView.as_view(), name='expense_list'),
    
    # Create/Update/Delete
    path('expenses/add/', views.ExpenseCreateView.as_view(), name='expense_add'),
    path('expenses/<int:pk>/edit/', views.ExpenseUpdateView.as_view(), name='expense_edit'),
    path('expenses/<int:pk>/delete/', views.ExpenseDeleteView.as_view(), name='expense_delete'),
    
    # ==================== INVESTMENTS ====================
    # List
    path('investments/', views.InvestmentListView.as_view(), name='investment_list'),
    
    # Create/Update/Delete
    path('investments/add/', views.InvestmentCreateView.as_view(), name='investment_add'),
    path('investments/<int:pk>/edit/', views.InvestmentUpdateView.as_view(), name='investment_edit'),
    path('investments/<int:pk>/delete/', views.InvestmentDeleteView.as_view(), name='investment_delete'),
    
    # ==================== REPORTS ====================
    path('reports/monthly/', views.MonthlyReportView.as_view(), name='monthly_report'),
    path('reports/yearly/', views.YearlyReportView.as_view(), name='yearly_report'),
    
    # ==================== EXPORTS (Using API Views) ====================
    path('export/cattle/', views.ExportCattleCSVAPIView.as_view(), name='export_cattle'),
    path('export/milk/', views.ExportMilkCSVAPIView.as_view(), name='export_milk'),
    path('export/sales/', views.ExportSalesCSVAPIView.as_view(), name='export_sales'),
    path('export/financial/', views.ExportFinancialCSVAPIView.as_view(), name='export_financial'),
]