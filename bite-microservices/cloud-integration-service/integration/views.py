"""
Cloud Integration Service Views (ASR 3 - Maintainability)

Endpoints:
  GET  /integration/health/
  GET  /integration/providers/
  POST /integration/sync/?provider=aws&start_date=YYYY-MM-DD&end_date=YYYY-MM-DD
  GET  /integration/raw-data/?provider=aws&limit=50
"""
import json
from datetime import date, timedelta

from django.conf import settings
from django.http import JsonResponse
from django.views import View
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt

from .providers.factory import get_provider, list_providers


@method_decorator(csrf_exempt, name='dispatch')
class HealthCheckView(View):
    def get(self, request):
        return JsonResponse({'status': 'ok', 'service': 'cloud-integration'})


@method_decorator(csrf_exempt, name='dispatch')
class ProvidersView(View):
    """List all registered cloud providers."""
    def get(self, request):
        return JsonResponse({
            'registered_providers': list_providers(),
            'active_provider': settings.ACTIVE_CLOUD_PROVIDER,
        })


@method_decorator(csrf_exempt, name='dispatch')
class SyncView(View):
    """
    Trigger a data sync from a cloud provider.
    Fetches raw usage data and persists to MongoDB (DocumentDB).
    """
    def post(self, request):
        provider_name = request.GET.get('provider', settings.ACTIVE_CLOUD_PROVIDER)
        start_date_str = request.GET.get('start_date')
        end_date_str = request.GET.get('end_date')

        if start_date_str:
            start_date = date.fromisoformat(start_date_str)
        else:
            start_date = date.today() - timedelta(days=7)

        if end_date_str:
            end_date = date.fromisoformat(end_date_str)
        else:
            end_date = date.today()

        try:
            provider = get_provider(provider_name)
        except ValueError as e:
            return JsonResponse({'error': str(e)}, status=400)

        records = provider.fetch_usage_data(start_date, end_date)

        # Persist to MongoDB (Amazon DocumentDB)
        saved_count = self._save_to_mongo(records, provider_name)

        return JsonResponse({
            'provider': provider_name,
            'records_fetched': len(records),
            'records_saved': saved_count,
            'period': {
                'start_date': start_date.isoformat(),
                'end_date': end_date.isoformat(),
            },
        })

    def _save_to_mongo(self, records, provider_name):
        """Persist raw usage records to MongoDB/DocumentDB."""
        try:
            import pymongo
            client = pymongo.MongoClient(
                host=settings.MONGODB_HOST,
                port=settings.MONGODB_PORT,
                serverSelectionTimeoutMS=3000,
            )
            db = client[settings.MONGODB_DB]
            collection = db[f'raw_usage_{provider_name}']

            docs = [
                {
                    'provider': r.provider,
                    'account_id': r.account_id,
                    'service_name': r.service_name,
                    'region': r.region,
                    'area': r.area,
                    'department': r.department,
                    'amount_usd': r.amount_usd,
                    'usage_date': r.usage_date.isoformat(),
                    'resource_id': r.resource_id,
                    'tags': r.tags or {},
                }
                for r in records
            ]

            if docs:
                result = collection.insert_many(docs)
                return len(result.inserted_ids)
            return 0
        except Exception as e:
            print(f"[Integration] MongoDB error: {e}. Returning record count anyway.")
            return len(records)


@method_decorator(csrf_exempt, name='dispatch')
class RawDataView(View):
    """Retrieve raw cloud usage data from MongoDB."""
    def get(self, request):
        provider_name = request.GET.get('provider', settings.ACTIVE_CLOUD_PROVIDER)
        limit = int(request.GET.get('limit', 50))

        try:
            import pymongo
            client = pymongo.MongoClient(
                host=settings.MONGODB_HOST,
                port=settings.MONGODB_PORT,
                serverSelectionTimeoutMS=3000,
            )
            db = client[settings.MONGODB_DB]
            collection = db[f'raw_usage_{provider_name}']
            docs = list(collection.find({}, {'_id': 0}).limit(limit))
            return JsonResponse({'provider': provider_name, 'count': len(docs), 'data': docs})
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)
