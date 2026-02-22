from django.db.models import Sum, F, DecimalField
from .models import Stock, FeedRecord, FishSale, MortalityRecord, Harvest


# =============================
# FINANCIAL METRICS
# =============================

def total_stock_investment():
    return Stock.objects.aggregate(total=Sum('cost'))['total'] or 0


def total_feed_expense():
    return FeedRecord.objects.aggregate(total=Sum('cost'))['total'] or 0


def total_revenue():
    return FishSale.objects.aggregate(
        total=Sum(
            F('quantity_kg') * F('price_per_kg'),
            output_field=DecimalField()
        )
    )['total'] or 0


def total_capital():
    return total_stock_investment() + total_feed_expense()


def net_profit():
    return total_revenue() - total_capital()


# =============================
# PRODUCTION METRICS
# =============================

def total_stock_quantity():
    return Stock.objects.aggregate(total=Sum('quantity'))['total'] or 0


def total_mortality_quantity():
    return MortalityRecord.objects.aggregate(total=Sum('quantity_dead'))['total'] or 0


def total_harvest_quantity():
    return Harvest.objects.aggregate(total=Sum('quantity_kg'))['total'] or 0


def mortality_percentage():
    stock_qty = total_stock_quantity()
    if stock_qty == 0:
        return 0
    return round((total_mortality_quantity() / stock_qty) * 100, 2)


def harvest_yield_percentage():
    stock_qty = total_stock_quantity()
    if stock_qty == 0:
        return 0
    return round((total_harvest_quantity() / stock_qty) * 100, 2)


def roi_percentage():
    capital = total_capital()
    if capital == 0:
        return 0
    return round((net_profit() / capital) * 100, 2)