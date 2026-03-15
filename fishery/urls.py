# fishery/urls.py

from django.urls import path, include
from . import views

app_name = 'fishery'

urlpatterns = [
    # ==================== DASHBOARD ====================
    path('', views.FisheryDashboardView.as_view(), name='dashboard'),
    path('dashboard/', views.FisheryDashboardView.as_view(), name='dashboard_alt'),
    
    # ==================== API ENDPOINTS ====================
    path('api/', include('fishery.api_urls')),
    
    # ==================== FARM MANAGEMENT ====================
    path('farms/', views.FarmListView.as_view(), name='farm_list'),
    path('farms/<int:pk>/', views.FarmDetailView.as_view(), name='farm_detail'),
    path('farms/add/', views.FarmCreateView.as_view(), name='farm_add'),
    path('farms/<int:pk>/edit/', views.FarmUpdateView.as_view(), name='farm_edit'),
    path('farms/<int:pk>/delete/', views.FarmDeleteView.as_view(), name='farm_delete'),



    # ==================== POND MANAGEMENT ====================
    # List and Detail
    path('ponds/', views.PondListView.as_view(), name='pond_list'),
    path('ponds/<int:pk>/', views.PondDetailView.as_view(), name='pond_detail'),
    
    # Create, Update, Delete
    path('ponds/add/', views.PondCreateView.as_view(), name='pond_add'),
    path('ponds/<int:pk>/edit/', views.PondUpdateView.as_view(), name='pond_edit'),
    path('ponds/<int:pk>/delete/', views.PondDeleteView.as_view(), name='pond_delete'),
    
    # ==================== FISH SPECIES ====================
    path('species/', views.FishSpeciesListView.as_view(), name='species_list'),
    path('species/add/', views.FishSpeciesCreateView.as_view(), name='species_add'),
    path('species/<int:pk>/edit/', views.FishSpeciesUpdateView.as_view(), name='species_edit'),
    path('species/<int:pk>/delete/', views.FishSpeciesDeleteView.as_view(), name='species_delete'),
    
    # ==================== FISH BATCH ====================
    path('batches/', views.FishBatchListView.as_view(), name='batch_list'),
    path('batches/add/', views.FishBatchCreateView.as_view(), name='batch_add'),
    path('batches/<int:pk>/edit/', views.FishBatchUpdateView.as_view(), name='batch_edit'),
    path('batches/<int:pk>/delete/', views.FishBatchDeleteView.as_view(), name='batch_delete'),
    
    # ==================== PRODUCTION CYCLES ====================
    # List and Detail
    path('cycles/', views.ProductionCycleListView.as_view(), name='cycle_list'),
    path('cycles/<int:pk>/', views.ProductionCycleDetailView.as_view(), name='cycle_detail'),
    
    # Create, Update, Delete
    path('cycles/add/', views.ProductionCycleCreateView.as_view(), name='cycle_add'),
    path('cycles/<int:pk>/edit/', views.ProductionCycleUpdateView.as_view(), name='cycle_edit'),
    path('cycles/<int:pk>/complete/', views.ProductionCycleCompleteView.as_view(), name='cycle_complete'),
    path('cycles/<int:pk>/delete/', views.ProductionCycleDeleteView.as_view(), name='cycle_delete'),
    
    # ==================== FEED MANAGEMENT ====================
    # Feed Types
    path('feed/types/', views.FeedTypeListView.as_view(), name='feed_type_list'),
    path('feed/types/add/', views.FeedTypeCreateView.as_view(), name='feed_type_add'),
    path('feed/types/<int:pk>/edit/', views.FeedTypeUpdateView.as_view(), name='feed_type_edit'),
    path('feed/types/<int:pk>/delete/', views.FeedTypeDeleteView.as_view(), name='feed_type_delete'),
    
    # Feed Purchases
    path('feed/purchases/', views.FeedPurchaseListView.as_view(), name='feed_purchase_list'),
    path('feed/purchases/add/', views.FeedPurchaseCreateView.as_view(), name='feed_purchase_add'),
    path('feed/purchases/<int:pk>/edit/', views.FeedPurchaseUpdateView.as_view(), name='feed_purchase_edit'),
    path('feed/purchases/<int:pk>/delete/', views.FeedPurchaseDeleteView.as_view(), name='feed_purchase_delete'),
    
    # Feed Records (Daily Feeding)
    path('feed/records/', views.FeedRecordListView.as_view(), name='feed_record_list'),
    path('feed/records/add/', views.FeedRecordCreateView.as_view(), name='feed_record_add'),
    path('feed/records/<int:pk>/edit/', views.FeedRecordUpdateView.as_view(), name='feed_record_edit'),
    path('feed/records/<int:pk>/delete/', views.FeedRecordDeleteView.as_view(), name='feed_record_delete'),
    
    # ==================== WATER QUALITY ====================
    path('water/', views.WaterQualityListView.as_view(), name='water_list'),
    path('water/add/', views.WaterQualityCreateView.as_view(), name='water_add'),
    path('water/<int:pk>/edit/', views.WaterQualityUpdateView.as_view(), name='water_edit'),
    path('water/<int:pk>/delete/', views.WaterQualityDeleteView.as_view(), name='water_delete'),
    
    # ==================== HEALTH MANAGEMENT ====================
    # Disease Records
    path('health/diseases/', views.DiseaseRecordListView.as_view(), name='disease_list'),
    path('health/diseases/add/', views.DiseaseRecordCreateView.as_view(), name='disease_add'),
    path('health/diseases/<int:pk>/edit/', views.DiseaseRecordUpdateView.as_view(), name='disease_edit'),
    path('health/diseases/<int:pk>/delete/', views.DiseaseRecordDeleteView.as_view(), name='disease_delete'),
    
    # Mortality Records
    path('health/mortality/', views.MortalityRecordListView.as_view(), name='mortality_list'),
    path('health/mortality/add/', views.MortalityRecordCreateView.as_view(), name='mortality_add'),
    path('health/mortality/<int:pk>/edit/', views.MortalityRecordUpdateView.as_view(), name='mortality_edit'),
    path('health/mortality/<int:pk>/delete/', views.MortalityRecordDeleteView.as_view(), name='mortality_delete'),
    
    # Treatment Records
    path('health/treatments/', views.TreatmentRecordListView.as_view(), name='treatment_list'),
    path('health/treatments/add/', views.TreatmentRecordCreateView.as_view(), name='treatment_add'),
    path('health/treatments/<int:pk>/edit/', views.TreatmentRecordUpdateView.as_view(), name='treatment_edit'),
    path('health/treatments/<int:pk>/delete/', views.TreatmentRecordDeleteView.as_view(), name='treatment_delete'),
    
    # ==================== HARVEST MANAGEMENT ====================
    path('harvests/', views.HarvestListView.as_view(), name='harvest_list'),
    path('harvests/add/', views.HarvestCreateView.as_view(), name='harvest_add'),
    path('harvests/<int:pk>/edit/', views.HarvestUpdateView.as_view(), name='harvest_edit'),
    path('harvests/<int:pk>/delete/', views.HarvestDeleteView.as_view(), name='harvest_delete'),
    
    # ==================== CUSTOMER MANAGEMENT ====================
    path('customers/', views.CustomerListView.as_view(), name='customer_list'),
    path('customers/add/', views.CustomerCreateView.as_view(), name='customer_add'),
    path('customers/<int:pk>/edit/', views.CustomerUpdateView.as_view(), name='customer_edit'),
    path('customers/<int:pk>/delete/', views.CustomerDeleteView.as_view(), name='customer_delete'),
    
    # ==================== SALES MANAGEMENT ====================
    path('sales/', views.FishSaleListView.as_view(), name='sale_list'),
    path('sales/add/', views.FishSaleCreateView.as_view(), name='sale_add'),
    path('sales/<int:pk>/edit/', views.FishSaleUpdateView.as_view(), name='sale_edit'),
    path('sales/<int:pk>/delete/', views.FishSaleDeleteView.as_view(), name='sale_delete'),
    
    # ==================== EXPENSES ====================
    path('expenses/', views.ExpenseListView.as_view(), name='expense_list'),
    path('expenses/add/', views.ExpenseCreateView.as_view(), name='expense_add'),
    path('expenses/<int:pk>/edit/', views.ExpenseUpdateView.as_view(), name='expense_edit'),
    path('expenses/<int:pk>/delete/', views.ExpenseDeleteView.as_view(), name='expense_delete'),
    
    # ==================== BUDGET ====================
    path('budgets/', views.BudgetListView.as_view(), name='budget_list'),
    path('budgets/add/', views.BudgetCreateView.as_view(), name='budget_add'),
    path('budgets/<int:pk>/edit/', views.BudgetUpdateView.as_view(), name='budget_edit'),
    path('budgets/<int:pk>/delete/', views.BudgetDeleteView.as_view(), name='budget_delete'),
    path('budgets/cycle/<int:cycle_id>/', views.BudgetForCycleView.as_view(), name='budget_for_cycle'),
    
    # ==================== REPORTS ====================
    path('reports/', views.FisheryReportDashboardView.as_view(), name='report_dashboard'),
    path('reports/production/', views.ProductionReportView.as_view(), name='production_report'),
    path('reports/financial/', views.FinancialReportView.as_view(), name='financial_report'),
    path('reports/financial/generate/', views.GenerateFinancialReportView.as_view(), name='generate_financial_report'),
    
    # ==================== EXPORTS ====================
    # Detailed export URLs with format
    path('export/ponds/csv/', views.ExportPondsCSVView.as_view(), name='export_ponds_csv'),
    path('export/cycles/csv/', views.ExportCyclesCSVView.as_view(), name='export_cycles_csv'),
    path('export/sales/csv/', views.ExportSalesCSVView.as_view(), name='export_sales_csv'),
    path('export/expenses/csv/', views.ExportExpensesCSVView.as_view(), name='export_expenses_csv'),
    path('export/feed/csv/', views.ExportFeedCSVView.as_view(), name='export_feed_csv'),
    path('export/harvests/csv/', views.ExportHarvestsCSVView.as_view(), name='export_harvests_csv'),
    
    # Simple export URLs (backward compatibility)
    path('export/ponds/', views.ExportPondsCSVView.as_view(), name='export_ponds'),
    path('export/cycles/', views.ExportCyclesCSVView.as_view(), name='export_cycles'),
    path('export/sales/', views.ExportSalesCSVView.as_view(), name='export_sales'),
    path('export/expenses/', views.ExportExpensesCSVView.as_view(), name='export_expenses'),
    path('export/feed/', views.ExportFeedCSVView.as_view(), name='export_feed'),
    path('export/harvests/', views.ExportHarvestsCSVView.as_view(), name='export_harvests'),
]