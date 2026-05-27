"""
Cloud Provider Abstraction Layer (ASR 3 - Maintainability)

Strategy Pattern: Each cloud provider implements CloudProviderInterface.
To add a new provider (e.g., GCP):
  1. Create providers/gcp_provider.py implementing CloudProviderInterface
  2. Register it in providers/factory.py

That's it — FinOps and CRON services are completely unaffected.
Maximum 2 files changed to integrate a new provider.
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import date
from typing import List, Optional


@dataclass
class RawUsageRecord:
    """Normalized usage record returned by any cloud provider."""
    provider: str
    account_id: str
    service_name: str
    region: str
    area: str
    department: str
    amount_usd: float
    usage_date: date
    resource_id: Optional[str] = None
    tags: Optional[dict] = None


class CloudProviderInterface(ABC):
    """
    Interface that all cloud provider adapters must implement.
    Adding a new provider = creating one new file implementing this interface.
    """

    @abstractmethod
    def get_provider_name(self) -> str:
        """Return the unique name of this provider (e.g., 'aws', 'gcp', 'azure')."""
        pass

    @abstractmethod
    def fetch_usage_data(
        self,
        start_date: date,
        end_date: date,
        account_id: Optional[str] = None,
    ) -> List[RawUsageRecord]:
        """
        Fetch raw usage/cost data from the cloud provider API.
        Returns a normalized list of RawUsageRecord.
        """
        pass

    @abstractmethod
    def validate_credentials(self) -> bool:
        """Validate that the provider credentials are working."""
        pass

    def get_supported_services(self) -> List[str]:
        """Optionally override to list supported services."""
        return []
