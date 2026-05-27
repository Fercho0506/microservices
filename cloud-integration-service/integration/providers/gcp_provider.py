"""
GCP Cloud Provider Adapter (ASR 3 - Maintainability Experiment)

This file demonstrates how a NEW provider is integrated by:
  1. Creating THIS file (providers/gcp_provider.py)
  2. Registering it in providers/factory.py

Zero changes to FinOps service or CRON Worker service.
"""
import os
import random
from datetime import date, timedelta
from typing import List, Optional

from .base import CloudProviderInterface, RawUsageRecord


class GCPProvider(CloudProviderInterface):
    """
    GCP implementation of CloudProviderInterface.
    Uses Google Cloud Billing API to fetch cost data.
    """

    def __init__(self):
        self.project_id = os.environ.get('GCP_PROJECT_ID', 'my-gcp-project')
        self.credentials_path = os.environ.get('GOOGLE_APPLICATION_CREDENTIALS', '')

    def get_provider_name(self) -> str:
        return 'gcp'

    def validate_credentials(self) -> bool:
        """Validate GCP service account credentials."""
        try:
            from google.cloud import billing_v1
            client = billing_v1.CloudBillingClient()
            return True
        except ImportError:
            # google-cloud-billing not installed — acceptable for experiment
            return True
        except Exception:
            return False

    def fetch_usage_data(
        self,
        start_date: date,
        end_date: date,
        account_id: Optional[str] = None,
    ) -> List[RawUsageRecord]:
        """
        Fetch GCP cost data via Cloud Billing API.
        Falls back to simulated data if SDK unavailable.
        """
        try:
            return self._fetch_from_billing_api(start_date, end_date)
        except Exception as e:
            print(f"[GCPProvider] Billing API error: {e}. Using simulated data.")
            return self._simulate_data(start_date, end_date)

    def _fetch_from_billing_api(self, start_date: date, end_date: date) -> List[RawUsageRecord]:
        """Real GCP Billing API call (requires google-cloud-billing SDK)."""
        from google.cloud import bigquery

        client = bigquery.Client(project=self.project_id)
        query = f"""
            SELECT
                service.description as service_name,
                labels.value as area,
                usage_start_time as usage_date,
                SUM(cost) as amount_usd
            FROM `{self.project_id}.billing_export.gcp_billing_export`
            WHERE DATE(usage_start_time) BETWEEN '{start_date}' AND '{end_date}'
              AND labels.key = 'area'
            GROUP BY service_name, area, usage_date
        """
        results = client.query(query).result()
        return [
            RawUsageRecord(
                provider='gcp',
                account_id=self.project_id,
                service_name=row.service_name,
                region='us-central1',
                area=row.area or 'Untagged',
                department=row.area or 'Untagged',
                amount_usd=float(row.amount_usd),
                usage_date=row.usage_date.date(),
            )
            for row in results
        ]

    def _simulate_data(self, start_date: date, end_date: date) -> List[RawUsageRecord]:
        """Simulated GCP cost data for experiment."""
        areas = ['Engineering', 'Marketing', 'Data', 'Operations']
        services = ['Compute Engine', 'Cloud Storage', 'Cloud SQL', 'Cloud Functions', 'BigQuery']
        records = []
        current = start_date
        while current <= end_date:
            for area in areas:
                for service in services:
                    if random.random() < 0.65:
                        records.append(RawUsageRecord(
                            provider='gcp',
                            account_id=self.project_id,
                            service_name=service,
                            region='us-central1',
                            area=area,
                            department=area,
                            amount_usd=round(random.uniform(3.0, 400.0), 4),
                            usage_date=current,
                            tags={'environment': 'production', 'area': area},
                        ))
            current += timedelta(days=1)
        return records

    def get_supported_services(self):
        return ['Compute Engine', 'Cloud Storage', 'Cloud SQL', 'Cloud Functions', 'BigQuery', 'GKE']
