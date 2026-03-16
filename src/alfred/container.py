"""Service Locator pattern for dependency injection.

Provides global access to registered services for cron jobs and other
components that need dependencies but can't receive them via constructors.
"""

from abc import ABC
from typing import TypeVar

T = TypeVar("T")


class ServiceLocator:
    """Global service registry for dependency access.

    Used by cron jobs and other components to access shared dependencies
    without explicit constructor injection. Registered at application startup.

    Example:
        # Register services in Alfred.__init__
        ServiceLocator.register(SessionSummarizer, self.summarizer)
        ServiceLocator.register(SessionManager, self.session_manager)

        # Access in cron job
        summarizer = ServiceLocator.resolve(SessionSummarizer)
    """

    _services: dict[type, object] = {}

    @classmethod
    def register(cls, service_type: type[T] | type[ABC], instance: T) -> None:
        """Register a service instance.

        Args:
            service_type: The type/interface to register under
            instance: The service instance
        """
        cls._services[service_type] = instance

    @classmethod
    def resolve(cls, service_type: type[T] | type[ABC]) -> T:
        """Resolve a service by type.

        Args:
            service_type: The type to look up

        Returns:
            The registered service instance

        Raises:
            KeyError: If service not registered
        """
        if service_type not in cls._services:
            raise KeyError(f"Service {service_type.__name__} not registered")
        return cls._services[service_type]  # type: ignore

    @classmethod
    def has(cls, service_type: type[T] | type[ABC]) -> bool:
        """Check if a service is registered."""
        return service_type in cls._services

    @classmethod
    def clear(cls) -> None:
        """Clear all registered services. Use for testing."""
        cls._services.clear()
