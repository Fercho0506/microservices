"""
AWS Cloud Provider Adapter

Fetches cost and usage data from AWS Cost Explorer API.
"""
import os
import random
from datetime import date, timedelta
from typing import List, Optional

from .base import CloudProviderInterface, RawUsageRecord


class AWSProvider(CloudProviderInterface):
    """
    AWS implementation of CloudProviderInterface.
    Uses boto3 (AWS SDK) to fetch Cost Explorer data.
    In AWS Academy environments, uses instance profile credentials (no IAM keys needed).
    """

    def __init__(self):
        self.region = os.environ.get('AWS_REGION', 'us-east-1')
        # Note: In AWS Academy, credentials come from the instance profile automatically.
        # boto3 picks them up from the environment without explicit keys.

    def get_provider_name(self) -> str:
        return 'aws'

    def validate_credentials(self) -> bool:
        try:
            import boto3
            sts = boto3.client('sts', region_name=self.region)
            sts.get_caller_identity()
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
        Fetch AWS cost data via Cost Explorer.
        Falls back to simulated data if boto3 is unavailable (for local dev/testing).
        """
        try:
            return self._fetch_from_cost_explorer(start_date, end_date)
        except ImportError:
            # boto3 not installed — return simulated data for experiment
            return self._simulate_data(start_date, end_date)
        except Exception as e:
            print(f"[AWSProvider] Cost Explorer error: {e}. Using simulated data.")
            return self._simulate_data(start_date, end_date)

    def _fetch_from_cost_explorer(self, start_date: date, end_date: date) -> List[RawUsageRecord]:
        import boto3
        client = boto3.client('ce', region_name='us-east-1')

        response = client.get_cost_and_usage(
            TimePeriod={
                'Start': start_date.isoformat(),
                'End': end_date.isoformat(),
            },
            Granularity='DAILY',
            Metrics=['UnblendedCost'],
            GroupBy=[
                {'Type': 'DIMENSION', 'Key': 'SERVICE'},
                {'Type': 'TAG', 'Key': 'Area'},
            ],
        )

        records = []
        for result in response.get('ResultsByTime', []):
            usage_date = date.fromisoformat(result['TimePeriod']['Start'])
            for group in result.get('Groups', []):
                service = group['Keys'][0] if group['Keys'] else 'unknown'
                area_tag = group['Keys'][1] if len(group['Keys']) > 1 else 'Untagged'
                amount = float(group['Metrics']['UnblendedCost']['Amount'])
                if amount == 0:
                    continue
                records.append(RawUsageRecord(
                    provider='aws',
                    account_id=account_id or 'aws-account',
                    service_name=service,
                    region=self.region,
                    area=area_tag,
                    department=area_tag,
                    amount_usd=amount,
                    usage_date=usage_date,
                ))
        return records

    def _simulate_data(self, start_date: date, end_date: date) -> List[RawUsageRecord]:
        """Generate realistic simulated AWS cost data for experiment purposes."""
        areas = ['Engineering', 'Marketing', 'Sales', 'Finance', 'Operations']
        services = ['Amazon EC2', 'Amazon S3', 'Amazon RDS', 'AWS Lambda', 'Amazon CloudFront']
        records = []
        current = start_date
        while current <= end_date:
            for area in areas:
                for service in services:
                    if random.random() < 0.7:
                        records.append(RawUsageRecord(
                            provider='aws',
                            account_id='123456789012',
                            service_name=service,
                            region=self.region,
                            area=area,
                            department=area,
                            amount_usd=round(random.uniform(5.0, 500.0), 4),
                            usage_date=current,
                            tags={'environment': 'production', 'area': area},
                        ))
            current += timedelta(days=1)
        return records

    def get_supported_services(self):
        return ['EC2', 'S3', 'RDS', 'Lambda', 'CloudFront', 'ElastiCache', 'ECS']
