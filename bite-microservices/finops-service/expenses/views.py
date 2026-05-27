"""
FinOps Views (ASR 1 - Performance)

GET /finops/expenses/by-area/?start_date=YYYY-MM-DD&end_date=YYYY-MM-DD&company_id=X

Target: p95 < 150ms under 100 concurrent users.

Strategy:
1. Redis cache layer (cache hit → ~2-5ms)
2. PostgreSQL query with composite index on (company_id, expense_date, area)
3. Single DB query using aggregation — no MongoDB access needed
4. SELECT only required columns
"""
import hashlib
import time
import logging

from django.db.models import Sum
from django.core.cache import cache
from django.http import JsonResponse
from django.views import View
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt

from .models import CloudExpense

logger = logging.getLogger('audit')


@method_decorator(csrf_exempt, name='dispatch')
class ExpensesByAreaView(View):
    """
    ASR 1: Aggregate cloud expenses by area/department for a given date range.
    Returns data directly from PostgreSQL with Redis caching.
    No MongoDB access required.
    """

    def get(self, request):
        start_ts = time.time()

        # --- Input validation ---
        start_date = request.GET.get('start_date')
        end_date = request.GET.get('end_date')
        company_id = request.GET.get('company_id')

        if not all([start_date, end_date, company_id]):
            return JsonResponse(
                {'error': 'Missing required params: start_date, end_date, company_id'},
                status=400,
            )

        try:
            company_id = int(company_id)
        except ValueError:
            return JsonResponse({'error': 'company_id must be an integer'}, status=400)

        # --- Cache key ---
        cache_key = self._build_cache_key(company_id, start_date, end_date)

        # --- Cache lookup ---
        cached_result = cache.get(cache_key)
        if cached_result is not None:
            elapsed_ms = (time.time() - start_ts) * 1000
            return JsonResponse({
                'data': cached_result,
                'source': 'cache',
                'latency_ms': round(elapsed_ms, 2),
                'period': {'start_date': start_date, 'end_date': end_date},
                'company_id': company_id,
            })

        # --- DB Query (uses composite index idx_expense_company_date_area) ---
        # Single aggregation query — no cross-service calls, no MongoDB access
        queryset = (
            CloudExpense.objects
            .filter(
                company_id=company_id,
                expense_date__gte=start_date,
                expense_date__lte=end_date,
            )
            .values('area', 'provider')
            .annotate(total_usd=Sum('amount_usd'))
            .order_by('area', 'provider')
        )

        results = [
            {
                'area': row['area'],
                'provider': row['provider'],
                'total_usd': float(row['total_usd']),
            }
            for row in queryset
        ]

        # Group by area (sum across providers)
        area_totals = {}
        for row in results:
            area = row['area']
            if area not in area_totals:
                area_totals[area] = {'area': area, 'total_usd': 0.0, 'breakdown': []}
            area_totals[area]['total_usd'] += row['total_usd']
            area_totals[area]['breakdown'].append({
                'provider': row['provider'],
                'total_usd': row['total_usd'],
            })

        final_data = list(area_totals.values())

        # --- Store in cache ---
        from django.conf import settings
        cache.set(cache_key, final_data, timeout=settings.EXPENSES_CACHE_TIMEOUT)

        elapsed_ms = (time.time() - start_ts) * 1000
        return JsonResponse({
            'data': final_data,
            'source': 'database',
            'latency_ms': round(elapsed_ms, 2),
            'period': {'start_date': start_date, 'end_date': end_date},
            'company_id': company_id,
        })

    def _build_cache_key(self, company_id, start_date, end_date):
        raw = f"expenses_area:{company_id}:{start_date}:{end_date}"
        return hashlib.md5(raw.encode()).hexdigest()


@method_decorator(csrf_exempt, name='dispatch')
class HealthCheckView(View):
    """Health endpoint — excluded from auth middleware."""
    def get(self, request):
        return JsonResponse({'status': 'ok', 'service': 'finops'})


@method_decorator(csrf_exempt, name='dispatch')
class SeedDataView(View):
    """
    Seed test data for the experiment.
    POST /finops/expenses/seed/?company_id=1&records=500
    """
    def post(self, request):
        import random
        from datetime import date, timedelta

        company_id = int(request.GET.get('company_id', 1))
        records = int(request.GET.get('records', 500))
        records = min(records, 5000)  # safety cap

        areas = ['Engineering', 'Marketing', 'Sales', 'Finance', 'Operations', 'HR', 'Data']
        providers = ['aws', 'azure', 'gcp']
        services = ['EC2', 'S3', 'RDS', 'Lambda', 'CloudFront', 'ElastiCache']

        base_date = date.today()
        expenses = []
        for _ in range(records):
            expense_date = base_date - timedelta(days=random.randint(0, 90))
            expenses.append(CloudExpense(
                area=random.choice(areas),
                department=random.choice(areas),
                provider=random.choice(providers),
                service_name=random.choice(services),
                amount_usd=round(random.uniform(10.0, 5000.0), 4),
                expense_date=expense_date,
                company_id=company_id,
            ))

        CloudExpense.objects.bulk_create(expenses)
        return JsonResponse({
            'message': f'Seeded {records} expense records for company_id={company_id}',
            'total_in_db': CloudExpense.objects.filter(company_id=company_id).count(),
        })
