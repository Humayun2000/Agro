from django.urls import path
from . import views

app_name = 'dairy_api'

urlpatterns = [
    # ==================== DASHBOARD APIS ====================
    path('dashboard/stats/', views.DashboardStatsAPIView.as_view(), name='api_dashboard_stats'),
    path('dashboard/milk-chart/', views.MilkChartDataAPIView.as_view(), name='api_milk_chart'),
    path('dashboard/recent-activity/', views.RecentActivityAPIView.as_view(), name='api_recent_activity'),
    path('dashboard/notifications/', views.NotificationsAPIView.as_view(), name='api_notifications'),
    
    # ==================== CATTLE APIS ====================
    # Cattle data endpoints
    path('cattle/', views.CattleListAPIView.as_view(), name='api_cattle_list'),
    path('cattle/<int:cattle_id>/', views.CattleDetailAPIView.as_view(), name='api_cattle_detail'),
    path('cattle/search/', views.CattleSearchAPIView.as_view(), name='api_cattle_search'),
    path('cattle/stats/', views.CattleStatsAPIView.as_view(), name='api_cattle_stats'),
    
    # Cattle financial endpoints
    path('cattle/<int:cattle_id>/financial/', views.CattleFinancialAPIView.as_view(), name='api_cattle_financial'),
    path('cattle/<int:cattle_id>/growth/', views.CattleGrowthAPIView.as_view(), name='api_cattle_growth'),
    
    # ==================== MILK RECORD APIS ====================
    path('milk/', views.MilkRecordListAPIView.as_view(), name='api_milk_list'),
    path('milk/<int:record_id>/', views.MilkRecordDetailAPIView.as_view(), name='api_milk_detail'),
    path('milk/stats/', views.MilkStatsAPIView.as_view(), name='api_milk_stats'),
    path('milk/today/', views.MilkTodayAPIView.as_view(), name='api_milk_today'),
    path('milk/by-cattle/<int:cattle_id>/', views.MilkByCattleAPIView.as_view(), name='api_milk_by_cattle'),
    
    # ==================== MILK SALE APIS ====================
    path('milk-sales/', views.MilkSaleListAPIView.as_view(), name='api_milk_sale_list'),
    path('milk-sales/<int:sale_id>/', views.MilkSaleDetailAPIView.as_view(), name='api_milk_sale_detail'),
    path('milk-sales/stats/', views.MilkSaleStatsAPIView.as_view(), name='api_milk_sale_stats'),
    path('milk-sales/monthly/', views.MilkSaleMonthlyAPIView.as_view(), name='api_milk_sale_monthly'),
    
    # ==================== CATTLE SALE APIS ====================
    path('cattle-sales/', views.CattleSaleListAPIView.as_view(), name='api_cattle_sale_list'),
    path('cattle-sales/<int:sale_id>/', views.CattleSaleDetailAPIView.as_view(), name='api_cattle_sale_detail'),
    path('cattle-sales/stats/', views.CattleSaleStatsAPIView.as_view(), name='api_cattle_sale_stats'),
    
    # ==================== HEALTH RECORD APIS ====================
    path('health/', views.HealthRecordListAPIView.as_view(), name='api_health_list'),
    path('health/<int:record_id>/', views.HealthRecordDetailAPIView.as_view(), name='api_health_detail'),
    path('health/alerts/', views.HealthAlertsAPIView.as_view(), name='api_health_alerts'),
    path('health/emergencies/', views.HealthEmergenciesAPIView.as_view(), name='api_health_emergencies'),
    path('health/by-cattle/<int:cattle_id>/', views.HealthByCattleAPIView.as_view(), name='api_health_by_cattle'),
    
    # ==================== WEIGHT RECORD APIS ====================
    path('weight/', views.WeightRecordListAPIView.as_view(), name='api_weight_list'),
    path('weight/<int:record_id>/', views.WeightRecordDetailAPIView.as_view(), name='api_weight_detail'),
    path('weight/by-cattle/<int:cattle_id>/', views.WeightByCattleAPIView.as_view(), name='api_weight_by_cattle'),
    path('weight/chart/<int:cattle_id>/', views.WeightChartAPIView.as_view(), name='api_weight_chart'),
    
    # ==================== FEEDING RECORD APIS ====================
    path('feeding/', views.FeedingRecordListAPIView.as_view(), name='api_feeding_list'),
    path('feeding/<int:record_id>/', views.FeedingRecordDetailAPIView.as_view(), name='api_feeding_detail'),
    path('feeding/today/', views.FeedingTodayAPIView.as_view(), name='api_feeding_today'),
    path('feeding/stats/', views.FeedingStatsAPIView.as_view(), name='api_feeding_stats'),
    path('feeding/by-cattle/<int:cattle_id>/', views.FeedingByCattleAPIView.as_view(), name='api_feeding_by_cattle'),
    
    # ==================== BREEDING RECORD APIS ====================
    path('breeding/', views.BreedingRecordListAPIView.as_view(), name='api_breeding_list'),
    path('breeding/<int:record_id>/', views.BreedingRecordDetailAPIView.as_view(), name='api_breeding_detail'),
    path('breeding/calendar/', views.BreedingCalendarAPIView.as_view(), name='api_breeding_calendar'),
    path('breeding/due-calving/', views.DueCalvingAPIView.as_view(), name='api_due_calving'),
    path('breeding/in-heat/', views.InHeatAPIView.as_view(), name='api_in_heat'),
    path('breeding/stats/', views.BreedingStatsAPIView.as_view(), name='api_breeding_stats'),
    
    # ==================== VACCINATION APIS ====================
    path('vaccination/', views.VaccinationListAPIView.as_view(), name='api_vaccination_list'),
    path('vaccination/<int:vax_id>/', views.VaccinationDetailAPIView.as_view(), name='api_vaccination_detail'),
    path('vaccination/upcoming/', views.UpcomingVaccinationsAPIView.as_view(), name='api_upcoming_vaccinations'),
    path('vaccination/overdue/', views.OverdueVaccinationsAPIView.as_view(), name='api_overdue_vaccinations'),
    path('vaccination/by-cattle/<int:cattle_id>/', views.VaccinationByCattleAPIView.as_view(), name='api_vaccination_by_cattle'),
    path('vaccination/complete/<int:vax_id>/', views.CompleteVaccinationAPIView.as_view(), name='api_complete_vaccination'),
    
    # ==================== EXPENSE APIS ====================
    path('expenses/', views.ExpenseListAPIView.as_view(), name='api_expense_list'),
    path('expenses/<int:expense_id>/', views.ExpenseDetailAPIView.as_view(), name='api_expense_detail'),
    path('expenses/stats/', views.ExpenseStatsAPIView.as_view(), name='api_expense_stats'),
    path('expenses/monthly/', views.ExpenseMonthlyAPIView.as_view(), name='api_expense_monthly'),
    path('expenses/by-category/', views.ExpenseByCategoryAPIView.as_view(), name='api_expense_by_category'),
    
    # ==================== INVESTMENT APIS ====================
    path('investments/', views.InvestmentListAPIView.as_view(), name='api_investment_list'),
    path('investments/<int:investment_id>/', views.InvestmentDetailAPIView.as_view(), name='api_investment_detail'),
    path('investments/stats/', views.InvestmentStatsAPIView.as_view(), name='api_investment_stats'),
    path('investments/by-type/', views.InvestmentByTypeAPIView.as_view(), name='api_investment_by_type'),
    
    # ==================== FINANCIAL APIS ====================
    path('financial/summary/', views.FinancialSummaryAPIView.as_view(), name='api_financial_summary'),
    path('financial/monthly/<int:year>/<int:month>/', views.FinancialMonthlyAPIView.as_view(), name='api_financial_monthly'),
    path('financial/yearly/<int:year>/', views.FinancialYearlyAPIView.as_view(), name='api_financial_yearly'),
    path('financial/profit-loss/', views.ProfitLossAPIView.as_view(), name='api_profit_loss'),
    
    # ==================== REPORT APIS ====================
    path('reports/milk-production/', views.MilkProductionReportAPIView.as_view(), name='api_milk_production_report'),
    path('reports/health-summary/', views.HealthSummaryReportAPIView.as_view(), name='api_health_summary_report'),
    path('reports/breeding-performance/', views.BreedingPerformanceReportAPIView.as_view(), name='api_breeding_performance_report'),
    path('reports/financial/', views.FinancialReportAPIView.as_view(), name='api_financial_report'),
    
    # ==================== CHART DATA APIS ====================
    path('charts/milk-trends/', views.MilkTrendsChartAPIView.as_view(), name='api_milk_trends_chart'),
    path('charts/weight-gain/<int:cattle_id>/', views.WeightGainChartAPIView.as_view(), name='api_weight_gain_chart'),
    path('charts/breeding-success/', views.BreedingSuccessChartAPIView.as_view(), name='api_breeding_success_chart'),
    path('charts/financial-overview/', views.FinancialOverviewChartAPIView.as_view(), name='api_financial_overview_chart'),
    
    # ==================== BULK OPERATIONS APIS ====================
    path('bulk/cattle/delete/', views.BulkCattleDeleteAPIView.as_view(), name='api_bulk_cattle_delete'),
    path('bulk/milk/delete/', views.BulkMilkDeleteAPIView.as_view(), name='api_bulk_milk_delete'),
    path('bulk/health/delete/', views.BulkHealthDeleteAPIView.as_view(), name='api_bulk_health_delete'),
    path('bulk/weight/delete/', views.BulkWeightDeleteAPIView.as_view(), name='api_bulk_weight_delete'),  # ADD THIS LINE
    path('bulk/vaccination/complete/', views.BulkVaccinationCompleteAPIView.as_view(), name='api_bulk_vaccination_complete'),
    # ==================== SEARCH APIS ====================
    path('search/cattle/', views.SearchCattleAPIView.as_view(), name='api_search_cattle'),
    path('search/records/', views.SearchRecordsAPIView.as_view(), name='api_search_records'),
    
    # ==================== EXPORT APIS ====================
    path('export/cattle/csv/', views.ExportCattleCSVAPIView.as_view(), name='api_export_cattle_csv'),
    path('export/milk/csv/', views.ExportMilkCSVAPIView.as_view(), name='api_export_milk_csv'),
    path('export/sales/csv/', views.ExportSalesCSVAPIView.as_view(), name='api_export_sales_csv'),
    path('export/financial/csv/', views.ExportFinancialCSVAPIView.as_view(), name='api_export_financial_csv'),
]