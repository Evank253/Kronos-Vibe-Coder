"""Provider registry and contract-level execution dispatch."""
from typing import Dict
from .providers.local import LocalExecutionProvider


class ProviderRegistry:
    def __init__(self):
        self._providers: Dict[str, object] = {"local": LocalExecutionProvider()}

    def register(self, provider):
        self._providers[provider.name] = provider

    def get(self, name):
        provider = self._providers.get(name)
        if provider is None:
            raise KeyError(f"execution provider unavailable: {name}")
        return provider

    def health(self):
        return {name: provider.health() for name, provider in self._providers.items()}
