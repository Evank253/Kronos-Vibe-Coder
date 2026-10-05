"""Provider interface. Providers report execution facts; they do not qualify them."""
from abc import ABC, abstractmethod
from .local import LocalExecutionProvider


class ExecutionProvider(ABC):
    name = "abstract"

    @abstractmethod
    def execute(self, request):
        raise NotImplementedError

    @abstractmethod
    def health(self):
        raise NotImplementedError
