# fishery/api_urls.py

from django.urls import path
from . import views

urlpatterns = [
    # ==================== DASHBOARD APIS ====================
    path('dashboard/stats/', views.FisheryDashboardStatsAPIView.as_view(), name='api_dashboard_stats'),
    path('dashboard/production-chart/', views.ProductionChartDataAPIView.as_view(), name='api_production_chart'),
    path('dashboard/recent-activity/', views.FisheryRecentActivityAPIView.as_view(), name='api_recent_activity'),
    path('dashboard/notifications/', views.FisheryNotificationsAPIView.as_view(), name='api_notifications'),
    
    # Farm API endpoints
    path('api/farms/', views.FarmListAPIView.as_view(), name='farm_api_list'),
    path('api/farms/<int:pk>/', views.FarmDetailAPIView.as_view(), name='farm_api_detail'),
    path('api/farms/<int:pk>/stats/', views.FarmStatsAPIView.as_view(), name='farm_api_stats'),

    # ==================== POND APIS ====================
    path('ponds/', views.PondListAPIView.as_view(), name='api_pond_list'),
    path('ponds/<int:pk>/', views.PondDetailAPIView.as_view(), name='api_pond_detail'),
    path('ponds/stats/', views.PondStatsAPIView.as_view(), name='api_pond_stats'),
    path('ponds/search/', views.PondSearchAPIView.as_view(), name='api_pond_search'),
    
    # ==================== PRODUCTION CYCLE APIS ====================
    path('cycles/', views.ProductionCycleListAPIView.as_view(), name='api_cycle_list'),
    path('cycles/<int:pk>/', views.ProductionCycleDetailAPIView.as_view(), name='api_cycle_detail'),
    path('cycles/stats/', views.CycleStatsAPIView.as_view(), name='api_cycle_stats'),
    path('cycles/running/', views.RunningCyclesAPIView.as_view(), name='api_running_cycles'),
    path('cycles/completed/', views.CompletedCyclesAPIView.as_view(), name='api_completed_cycles'),
    path('cycles/by-pond/<int:pond_id>/', views.CyclesByPondAPIView.as_view(), name='api_cycles_by_pond'),
    
    # ==================== FEED APIS ====================
    path('feed/records/', views.FeedRecordListAPIView.as_view(), name='api_feed_list'),
    path('feed/records/<int:pk>/', views.FeedRecordDetailAPIView.as_view(), name='api_feed_detail'),
    path('feed/types/', views.FeedTypeListAPIView.as_view(), name='api_feed_type_list'),
    path('feed/low-stock/', views.LowStockFeedAPIView.as_view(), name='api_low_stock_feed'),
    path('feed/daily/', views.DailyFeedAPIView.as_view(), name='api_daily_feed'),
    path('feed/by-cycle/<int:cycle_id>/', views.FeedByCycleAPIView.as_view(), name='api_feed_by_cycle'),
    
    # ==================== WATER QUALITY APIS ====================
    path('water/recent/', views.RecentWaterQualityAPIView.as_view(), name='api_recent_water'),
    path('water/alerts/', views.WaterAlertsAPIView.as_view(), name='api_water_alerts'),
    path('water/by-pond/<int:pond_id>/', views.WaterQualityByPondAPIView.as_view(), name='api_water_by_pond'),
    path('water/chart/<int:pond_id>/', views.WaterQualityChartAPIView.as_view(), name='api_water_chart'),
    
    # ==================== HEALTH APIS ====================
    path('health/diseases/', views.DiseaseRecordListAPIView.as_view(), name='api_disease_list'),
    path('health/diseases/active/', views.ActiveDiseasesAPIView.as_view(), name='api_active_diseases'),
    path('health/mortality/', views.MortalityRecordListAPIView.as_view(), name='api_mortality_list'),
    path('health/mortality/today/', views.TodayMortalityAPIView.as_view(), name='api_today_mortality'),
    path('health/mortality/by-cycle/<int:cycle_id>/', views.MortalityByCycleAPIView.as_view(), name='api_mortality_by_cycle'),
    
    # ==================== HARVEST APIS ====================
    path('harvests/', views.HarvestListAPIView.as_view(), name='api_harvest_list'),
    path('harvests/recent/', views.RecentHarvestsAPIView.as_view(), name='api_recent_harvests'),
    path('harvests/by-cycle/<int:cycle_id>/', views.HarvestByCycleAPIView.as_view(), name='api_harvest_by_cycle'),
    path('harvests/stats/', views.HarvestStatsAPIView.as_view(), name='api_harvest_stats'),
    
    # ==================== SALES APIS ====================
    path('sales/', views.FishSaleListAPIView.as_view(), name='api_sale_list'),
    path('sales/<int:pk>/', views.FishSaleDetailAPIView.as_view(), name='api_sale_detail'),
    path('sales/today/', views.TodaySalesAPIView.as_view(), name='api_today_sales'),
    path('sales/monthly/', views.MonthlySalesAPIView.as_view(), name='api_monthly_sales'),
    path('sales/by-customer/<int:customer_id>/', views.SalesByCustomerAPIView.as_view(), name='api_sales_by_customer'),
    path('sales/stats/', views.SalesStatsAPIView.as_view(), name='api_sales_stats'),
    
    # ==================== CUSTOMER APIS ====================
    path('customers/', views.CustomerListAPIView.as_view(), name='api_customer_list'),
    path('customers/<int:pk>/', views.CustomerDetailAPIView.as_view(), name='api_customer_detail'),
    path('customers/search/', views.CustomerSearchAPIView.as_view(), name='api_customer_search'),
    
    # ==================== EXPENSE APIS ====================
    path('expenses/', views.ExpenseListAPIView.as_view(), name='api_expense_list'),
    path('expenses/monthly/', views.MonthlyExpensesAPIView.as_view(), name='api_monthly_expenses'),
    path('expenses/by-cycle/<int:cycle_id>/', views.ExpensesByCycleAPIView.as_view(), name='api_expenses_by_cycle'),
    path('expenses/by-type/', views.ExpensesByTypeAPIView.as_view(), name='api_expenses_by_type'),
    
    # ==================== FINANCIAL APIS ====================
    path('financial/summary/', views.FinancialSummaryAPIView.as_view(), name='api_financial_summary'),
    path('financial/profit-loss/', views.ProfitLossAPIView.as_view(), name='api_profit_loss'),
    path('financial/roi/', views.ROIAnalysisAPIView.as_view(), name='api_roi_analysis'),
    
    # ==================== CHART DATA APIS ====================
    path('charts/production/', views.ProductionChartDataAPIView.as_view(), name='api_production_chart'),
    path('charts/financial/', views.FinancialChartDataAPIView.as_view(), name='api_financial_chart'),
    path('charts/growth/<int:cycle_id>/', views.GrowthChartDataAPIView.as_view(), name='api_growth_chart'),
    path('charts/water-quality/<int:pond_id>/', views.WaterQualityChartAPIView.as_view(), name='api_water_quality_chart'),
    
    # ==================== BULK OPERATIONS APIS ====================
    path('bulk/ponds/delete/', views.BulkPondDeleteAPIView.as_view(), name='api_bulk_pond_delete'),
    path('bulk/cycles/delete/', views.BulkCycleDeleteAPIView.as_view(), name='api_bulk_cycle_delete'),
    path('bulk/sales/delete/', views.BulkSaleDeleteAPIView.as_view(), name='api_bulk_sale_delete'),
    path('bulk/expenses/delete/', views.BulkExpenseDeleteAPIView.as_view(), name='api_bulk_expense_delete'),
    path('bulk/feed/delete/', views.BulkFeedDeleteAPIView.as_view(), name='api_bulk_feed_delete'),
    path('bulk/harvests/delete/', views.BulkHarvestDeleteAPIView.as_view(), name='api_bulk_harvest_delete'),
    
    # ==================== SEARCH APIS ====================
    path('search/ponds/', views.SearchPondsAPIView.as_view(), name='api_search_ponds'),
    path('search/cycles/', views.SearchCyclesAPIView.as_view(), name='api_search_cycles'),
    path('search/sales/', views.SearchSalesAPIView.as_view(), name='api_search_sales'),
    path('search/customers/', views.SearchCustomersAPIView.as_view(), name='api_search_customers'),
    
    # ==================== REPORT APIS ====================
    path('reports/production/', views.ProductionReportAPIView.as_view(), name='api_production_report'),
    path('reports/financial/', views.FinancialReportAPIView.as_view(), name='api_financial_report'),
    path('reports/sales/', views.SalesReportAPIView.as_view(), name='api_sales_report'),
    path('reports/expenses/', views.ExpensesReportAPIView.as_view(), name='api_expenses_report'),
]