"""
Cloud Provider Factory (ASR 3 - Maintainability)

This is FILE 2 of 2 that needs modification when adding a new cloud provider.
Simply import the new provider class and add it to PROVIDER_REGISTRY.

Example — adding Azure:
  1. Create providers/azure_provider.py implementing CloudProviderInterface
  2. Add: from .azure_provider import AzureProvider
  3. Add: 'azure': AzureProvider to PROVIDER_REGISTRY

That's it. Maximum 2 files changed total.
"""
from .aws_provider import AWSProvider
from .gcp_provider import GCPProvider
# from .azure_provider import AzureProvider  # Uncomment when adding Azure

PROVIDER_REGISTRY = {
    'aws': AWSProvider,
    'gcp': GCPProvider,
    # 'azure': AzureProvider,  # Uncomment when adding Azure
}


def get_provider(provider_name: str):
    """
    Factory method: returns an initialized provider instance.
    Raises ValueError if provider is not registered.
    """
    provider_class = PROVIDER_REGISTRY.get(provider_name.lower())
    if not provider_class:
        available = list(PROVIDER_REGISTRY.keys())
        raise ValueError(
            f"Provider '{provider_name}' not found. Available: {available}"
        )
    return provider_class()


def get_all_providers():
    """Return instances of all registered providers."""
    return [cls() for cls in PROVIDER_REGISTRY.values()]


def list_providers():
    """Return names of all registered providers."""
    return list(PROVIDER_REGISTRY.keys())
