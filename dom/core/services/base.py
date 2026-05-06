"""Base service abstractions for declarative service layer.

This module provides declarative base classes for building services
that follow clean architecture principles.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Generic, TypeVar

from dom.core.services.protocols import DomJudgeAPIProtocol

TOutput = TypeVar("TOutput")
TEntity = TypeVar("TEntity")


@dataclass
class ServiceContext:
    """
    Context for service operations.

    Provides access to dependencies needed by services.
    """

    client: DomJudgeAPIProtocol
    contest_id: str | None = None
    contest_shortname: str | None = None
    team_group_id: str | None = None  # Contest-specific team group for scoreboard filtering

    def for_contest(
        self,
        contest_id: str,
        contest_shortname: str | None = None,
        team_group_id: str | None = None,
    ) -> "ServiceContext":
        """Create new context for a specific contest."""
        return ServiceContext(
            client=self.client,
            contest_id=contest_id,
            contest_shortname=contest_shortname,
            team_group_id=team_group_id,
        )


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

    def __init__(self, client: DomJudgeAPIProtocol):
        """
        Initialize service with API client.

        Args:
            client: DOMjudge API client
        """
        self.client = client

    @abstractmethod
    def entity_name(self) -> str:
        """Return the name of the entity this service manages."""


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
