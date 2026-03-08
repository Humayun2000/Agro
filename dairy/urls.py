from django.urls import path, include
from . import views

app_name = 'dairy'

urlpatterns = [
    # ==================== DASHBOARD ====================
    path('', views.DairyDashboardView.as_view(), name='dairy_dashboard'),
    
    # ==================== API ENDPOINTS ====================
    path('api/', include('dairy.api_urls')),
    
    # ==================== CATTLE MANAGEMENT ====================
    path('cattle/', views.CattleListView.as_view(), name='cattle_list'),
    path('cattle/<int:pk>/', views.CattleDetailView.as_view(), name='cattle_detail'),
    path('cattle/add/', views.CattleCreateView.as_view(), name='cattle_add'),
    path('cattle/<int:pk>/edit/', views.CattleUpdateView.as_view(), name='cattle_edit'),
    path('cattle/<int:pk>/delete/', views.CattleDeleteView.as_view(), name='cattle_delete'),
    
    # ==================== MILK RECORDS ====================
    path('milk/', views.MilkRecordListView.as_view(), name='milk_list'),
    path('milk/add/', views.MilkRecordCreateView.as_view(), name='milk_add'),
    path('milk/<int:pk>/edit/', views.MilkRecordUpdateView.as_view(), name='milk_edit'),
    path('milk/<int:pk>/delete/', views.MilkRecordDeleteView.as_view(), name='milk_delete'),
    
    # ==================== MILK SALES ====================
    path('milk-sales/', views.MilkSaleListView.as_view(), name='milk_sale_list'),
    path('milk-sales/add/', views.MilkSaleCreateView.as_view(), name='milk_sale_add'),
    path('milk-sales/<int:pk>/edit/', views.MilkSaleUpdateView.as_view(), name='milk_sale_edit'),
    path('milk-sales/<int:pk>/delete/', views.MilkSaleDeleteView.as_view(), name='milk_sale_delete'),
    
    # ==================== CATTLE SALES ====================
    path('cattle-sales/', views.CattleSaleListView.as_view(), name='cattle_sale_list'),
    path('cattle-sales/add/', views.CattleSaleCreateView.as_view(), name='cattle_sale_add'),
    path('cattle-sales/<int:pk>/edit/', views.CattleSaleUpdateView.as_view(), name='cattle_sale_edit'),
    path('cattle-sales/<int:pk>/delete/', views.CattleSaleDeleteView.as_view(), name='cattle_sale_delete'),
    
    # ==================== HEALTH RECORDS ====================
    path('health/', views.HealthRecordListView.as_view(), name='health_list'),
    path('health/add/', views.HealthRecordCreateView.as_view(), name='health_add'),
    path('health/<int:pk>/edit/', views.HealthRecordUpdateView.as_view(), name='health_edit'),
    path('health/<int:pk>/delete/', views.HealthRecordDeleteView.as_view(), name='health_delete'),
    
    # ==================== WEIGHT RECORDS ====================
    path('weight/', views.WeightRecordListView.as_view(), name='weight_list'),
    path('weight/add/', views.WeightRecordCreateView.as_view(), name='weight_add'),
    path('weight/<int:pk>/edit/', views.WeightRecordUpdateView.as_view(), name='weight_edit'),
    path('weight/<int:pk>/delete/', views.WeightRecordDeleteView.as_view(), name='weight_delete'),
    
        # ==================== FEEDING RECORDS ====================
    path('feeding/', views.FeedingRecordListView.as_view(), name='feeding_list'),
    path('feeding/add/', views.FeedingRecordCreateView.as_view(), name='feeding_add'),
    path('feeding/<int:pk>/edit/', views.FeedingRecordUpdateView.as_view(), name='feeding_edit'),
    path('feeding/<int:pk>/delete/', views.FeedingRecordDeleteView.as_view(), name='feeding_delete'),

    
    # ==================== BREEDING RECORDS ====================
    path('breeding/', views.BreedingRecordListView.as_view(), name='breeding_list'),
    path('breeding/add/', views.BreedingRecordCreateView.as_view(), name='breeding_add'),
    path('breeding/<int:pk>/edit/', views.BreedingRecordUpdateView.as_view(), name='breeding_edit'),
    path('breeding/<int:pk>/delete/', views.BreedingRecordDeleteView.as_view(), name='breeding_delete'),
    
    # ==================== VACCINATION RECORDS ====================
    path('vaccination/', views.VaccinationListView.as_view(), name='vaccination_list'),
    path('vaccination/add/', views.VaccinationCreateView.as_view(), name='vaccination_add'),
    path('vaccination/<int:pk>/edit/', views.VaccinationUpdateView.as_view(), name='vaccination_edit'),
    path('vaccination/<int:pk>/delete/', views.VaccinationDeleteView.as_view(), name='vaccination_delete'),
    
    # ==================== EXPENSES ====================
    path('expenses/', views.ExpenseListView.as_view(), name='expense_list'),
    path('expenses/add/', views.ExpenseCreateView.as_view(), name='expense_add'),
    path('expenses/<int:pk>/edit/', views.ExpenseUpdateView.as_view(), name='expense_edit'),
    path('expenses/<int:pk>/delete/', views.ExpenseDeleteView.as_view(), name='expense_delete'),
    
    # ==================== INVESTMENTS ====================
    path('investments/', views.InvestmentListView.as_view(), name='investment_list'),
    path('investments/add/', views.InvestmentCreateView.as_view(), name='investment_add'),
    path('investments/<int:pk>/edit/', views.InvestmentUpdateView.as_view(), name='investment_edit'),
    path('investments/<int:pk>/delete/', views.InvestmentDeleteView.as_view(), name='investment_delete'),
    
    # ==================== REPORTS ====================
    path('reports/', views.ReportDashboardView.as_view(), name='report_dashboard'),
    path('reports/monthly/', views.MonthlyReportView.as_view(), name='monthly_report'),
    path('reports/yearly/', views.YearlyReportView.as_view(), name='yearly_report'),
    path('reports/milk-production/', views.MilkProductionReportView.as_view(), name='milk_production_report'),
    path('reports/health-summary/', views.HealthSummaryReportView.as_view(), name='health_summary_report'),
    path('reports/breeding-performance/', views.BreedingPerformanceReportView.as_view(), name='breeding_performance_report'),
    
    # ==================== EXPORTS ====================
    # Detailed export URLs with format
    path('export/cattle/csv/', views.ExportCattleCSVAPIView.as_view(), name='export_cattle_csv'),
    path('export/cattle/pdf/', views.ExportCattlePDFView.as_view(), name='export_cattle_pdf'),
    path('export/milk/csv/', views.ExportMilkCSVAPIView.as_view(), name='export_milk_csv'),
    path('export/milk/pdf/', views.ExportMilkPDFView.as_view(), name='export_milk_pdf'),
    path('export/health/csv/', views.ExportHealthCSVView.as_view(), name='export_health_csv'),
    path('export/health/pdf/', views.ExportHealthPDFView.as_view(), name='export_health_pdf'),
    path('export/feeding/csv/', views.ExportFeedingCSVView.as_view(), name='export_feeding_csv'),
    path('export/feeding/pdf/', views.ExportFeedingPDFView.as_view(), name='export_feeding_pdf'),
    path('export/weight/csv/', views.ExportWeightCSVView.as_view(), name='export_weight_csv'),
    path('export/weight/pdf/', views.ExportWeightPDFView.as_view(), name='export_weight_pdf'),
    path('export/breeding/csv/', views.ExportBreedingCSVView.as_view(), name='export_breeding_csv'),
    path('export/breeding/pdf/', views.ExportBreedingPDFView.as_view(), name='export_breeding_pdf'),
    path('export/vaccination/csv/', views.ExportVaccinationCSVView.as_view(), name='export_vaccination_csv'),
    path('export/vaccination/pdf/', views.ExportVaccinationPDFView.as_view(), name='export_vaccination_pdf'),
    path('export/sales/csv/', views.ExportSalesCSVAPIView.as_view(), name='export_sales_csv'),
    path('export/sales/pdf/', views.ExportSalesPDFView.as_view(), name='export_sales_pdf'),
    path('export/financial/csv/', views.ExportFinancialCSVAPIView.as_view(), name='export_financial_csv'),
    path('export/financial/pdf/', views.ExportFinancialPDFView.as_view(), name='export_financial_pdf'),
    
    # ==================== BACKWARD COMPATIBILITY EXPORT URLS ====================
    # Simple URLs that templates expect - ADD THESE!
    path('export/cattle/', views.ExportCattleCSVAPIView.as_view(), name='export_cattle'),
    path('export/milk/', views.ExportMilkCSVAPIView.as_view(), name='export_milk'),
    path('export/health/', views.ExportHealthCSVView.as_view(), name='export_health'),
    path('export/feeding/', views.ExportFeedingCSVView.as_view(), name='export_feeding'),
    path('export/weight/', views.ExportWeightCSVView.as_view(), name='export_weight'),
    path('export/breeding/', views.ExportBreedingCSVView.as_view(), name='export_breeding'),
    path('export/vaccination/', views.ExportVaccinationCSVView.as_view(), name='export_vaccination'),
    path('export/sales/', views.ExportSalesCSVAPIView.as_view(), name='export_sales'),
    path('export/financial/', views.ExportFinancialCSVAPIView.as_view(), name='export_financial'),
]