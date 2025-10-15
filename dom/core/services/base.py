"""Base service abstractions for declarative service layer.

This module provides declarative base classes for building services
that follow clean architecture principles.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Generic, TypeVar

from dom.infrastructure.api.domjudge import DomJudgeAPI
from dom.logging_config import get_logger

logger = get_logger(__name__)

TInput = TypeVar("TInput")
TOutput = TypeVar("TOutput")
TEntity = TypeVar("TEntity")


@dataclass
class ServiceContext:
    """
    Context for service operations.

    Provides access to dependencies needed by services.
    """

    client: DomJudgeAPI
    contest_id: str | None = None

    def for_contest(self, contest_id: str) -> "ServiceContext":
        """Create new context for a specific contest."""
        return ServiceContext(client=self.client, contest_id=contest_id)


@dataclass
class ServiceResult(Generic[TOutput]):
    """
    Result of a service operation.

    Encapsulates success/failure state with data or error.
    """

    success: bool
    data: TOutput | None = None
    error: Exception | None = None
    message: str = ""
    created: bool = False

    @classmethod
    def ok(
        cls, data: TOutput, message: str = "", created: bool = False
    ) -> "ServiceResult[TOutput]":
        """Create a successful result."""
        return cls(success=True, data=data, message=message, created=created)

    @classmethod
    def fail(cls, error: Exception, message: str = "") -> "ServiceResult[TOutput]":
        """Create a failed result."""
        return cls(success=False, error=error, message=message)

    def unwrap(self) -> TOutput:
        """Get the data or raise the error."""
        if self.error:
            raise self.error
        if self.data is None:
            raise ValueError("Service result has no data")
        return self.data


class Service(ABC, Generic[TEntity]):
    """
    Base class for declarative services.

    Services encapsulate business logic for managing a specific type of entity.
    They provide high-level operations that declare intent clearly.

    Example:
        >>> class ProblemService(Service[Problem]):
        ...     def add_to_contest(self, contest_id: str, problem: Problem) -> ServiceResult[Problem]:
        ...         # Implementation
        ...         pass
    """

    def __init__(self, client: DomJudgeAPI):
        """
        Initialize service with API client.

        Args:
            client: DOMjudge API client
        """
        self.client = client

    @abstractmethod
    def entity_name(self) -> str:
        """Return the name of the entity this service manages."""


class CRUDService(Service[TEntity], ABC):
    """
    Service with CRUD operations.

    Provides declarative methods for Create, Read, Update, Delete operations.
    """

    def create(self, entity: TEntity, context: ServiceContext) -> ServiceResult[TEntity]:
        """
        Create a new entity.

        Args:
            entity: Entity to create
            context: Service context

        Returns:
            Service result with created entity
        """
        try:
            created = self._perform_create(entity, context)
            return ServiceResult.ok(
                created,
                f"{self.entity_name()} created successfully",
                created=True,
            )
        except Exception as e:
            logger.error(
                f"Failed to create {self.entity_name()}",
                exc_info=True,
            )
            return ServiceResult.fail(e, f"Failed to create {self.entity_name()}: {e}")

    def get(self, entity_id: str, context: ServiceContext) -> ServiceResult[TEntity]:
        """
        Get an entity by ID.

        Args:
            entity_id: Entity identifier
            context: Service context

        Returns:
            Service result with entity
        """
        try:
            entity = self._perform_get(entity_id, context)
            return ServiceResult.ok(entity, f"{self.entity_name()} retrieved")
        except Exception as e:
            logger.error(
                f"Failed to get {self.entity_name()} {entity_id}",
                exc_info=True,
            )
            return ServiceResult.fail(e, f"Failed to get {self.entity_name()}: {e}")

    def list_all(self, context: ServiceContext) -> ServiceResult[list[TEntity]]:
        """
        List all entities.

        Args:
            context: Service context

        Returns:
            Service result with list of entities
        """
        try:
            entities = self._perform_list(context)
            return ServiceResult.ok(
                entities,
                f"Retrieved {len(entities)} {self.entity_name()}(s)",
            )
        except Exception as e:
            logger.error(
                f"Failed to list {self.entity_name()}s",
                exc_info=True,
            )
            return ServiceResult.fail(e, f"Failed to list {self.entity_name()}s: {e}")

    def update(
        self, entity_id: str, entity: TEntity, context: ServiceContext
    ) -> ServiceResult[TEntity]:
        """
        Update an entity.

        Args:
            entity_id: Entity identifier
            entity: Updated entity data
            context: Service context

        Returns:
            Service result with updated entity
        """
        try:
            updated = self._perform_update(entity_id, entity, context)
            return ServiceResult.ok(updated, f"{self.entity_name()} updated")
        except Exception as e:
            logger.error(
                f"Failed to update {self.entity_name()} {entity_id}",
                exc_info=True,
            )
            return ServiceResult.fail(e, f"Failed to update {self.entity_name()}: {e}")

    def delete(self, entity_id: str, context: ServiceContext) -> ServiceResult[None]:
        """
        Delete an entity.

        Args:
            entity_id: Entity identifier
            context: Service context

        Returns:
            Service result
        """
        try:
            self._perform_delete(entity_id, context)
            return ServiceResult.ok(None, f"{self.entity_name()} deleted")
        except Exception as e:
            logger.error(
                f"Failed to delete {self.entity_name()} {entity_id}",
                exc_info=True,
            )
            return ServiceResult.fail(e, f"Failed to delete {self.entity_name()}: {e}")

    # Abstract methods that subclasses must implement

    @abstractmethod
    def _perform_create(self, entity: TEntity, context: ServiceContext) -> TEntity:
        """Perform the actual create operation."""

    @abstractmethod
    def _perform_get(self, entity_id: str, context: ServiceContext) -> TEntity:
        """Perform the actual get operation."""

    @abstractmethod
    def _perform_list(self, context: ServiceContext) -> list[TEntity]:
        """Perform the actual list operation."""

    @abstractmethod
    def _perform_update(self, entity_id: str, entity: TEntity, context: ServiceContext) -> TEntity:
        """Perform the actual update operation."""

    @abstractmethod
    def _perform_delete(self, entity_id: str, context: ServiceContext) -> None:
        """Perform the actual delete operation."""


class BulkOperationMixin(Generic[TEntity]):
    """
    Mixin for services that support bulk operations.

    Provides declarative methods for operating on multiple entities at once.
    """

    def create_many(
        self,
        entities: list[TEntity],
        context: ServiceContext,
        stop_on_error: bool = False,
    ) -> list[ServiceResult[TEntity]]:
        """
        Create multiple entities.

        Args:
            entities: List of entities to create
            context: Service context
            stop_on_error: Stop on first error if True

        Returns:
            List of service results
        """
        results: list[ServiceResult[TEntity]] = []

        for entity in entities:
            result = self.create(entity, context)  # type: ignore[attr-defined]
            results.append(result)

            if stop_on_error and not result.success:
                break

        return results

    def get_summary(self, results: list[ServiceResult[TEntity]]) -> dict[str, int]:
        """
        Get summary of operation results.

        Args:
            results: List of service results

        Returns:
            Summary with success/failure counts
        """
        return {
            "total": len(results),
            "successful": sum(1 for r in results if r.success),
            "failed": sum(1 for r in results if not r.success),
            "created": sum(1 for r in results if r.created),
        }


class AsyncOperationMixin:
    """
    Mixin for services that support async operations.

    Provides declarative methods for non-blocking operations.
    """

    async def create_async(
        self, entity: TEntity, context: ServiceContext
    ) -> ServiceResult[TEntity]:
        """
        Create entity asynchronously.

        Args:
            entity: Entity to create
            context: Service context

        Returns:
            Service result
        """
        # This would use async client if available
        # For now, just call sync version
        return self.create(entity, context)  # type: ignore[attr-defined,no-any-return]


# Declarative service specifications


@dataclass
class ServiceOperation(Generic[TInput, TOutput]):
    """
    Declarative specification of a service operation.

    Describes what operation should be performed, not how.
    """

    name: str
    description: str
    input_type: type[TInput]
    output_type: type[TOutput]
    idempotent: bool = False
    cacheable: bool = False

    def describe(self) -> str:
        """Get human-readable description."""
        return f"{self.name}: {self.description}"


# Example usage:
#
# create_problem = ServiceOperation(
#     name="create_problem",
#     description="Add a problem to a contest",
#     input_type=ProblemPackage,
#     output_type=Problem,
#     idempotent=True,
# )
