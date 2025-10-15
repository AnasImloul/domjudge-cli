"""Declarative request builders for DomJudge API.

This module provides a fluent, declarative interface for building API requests
that makes the intent clear and improves maintainability.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Generic, TypeVar

from dom.logging_config import get_logger

logger = get_logger(__name__)

T = TypeVar("T")


class HTTPMethod(str, Enum):
    """HTTP methods."""

    GET = "GET"
    POST = "POST"
    PUT = "PUT"
    DELETE = "DELETE"
    PATCH = "PATCH"


@dataclass
class APIRequest:
    """
    Declarative API request specification.

    This class describes what request should be made, not how to make it.
    The actual execution is delegated to the client.
    """

    method: HTTPMethod
    path: str
    query_params: dict[str, Any] = field(default_factory=dict)
    headers: dict[str, str] = field(default_factory=dict)
    body: Any | None = None
    cache_key: str | None = None
    cache_ttl: int | None = None
    invalidate_cache: str | None = None

    def describe(self) -> str:
        """Human-readable description of the request."""
        return f"{self.method.value} {self.path}"

    def with_query_param(self, key: str, value: Any) -> "APIRequest":
        """Add a query parameter (returns new instance)."""
        new_params = {**self.query_params, key: value}
        return APIRequest(
            method=self.method,
            path=self.path,
            query_params=new_params,
            headers=self.headers,
            body=self.body,
            cache_key=self.cache_key,
            cache_ttl=self.cache_ttl,
            invalidate_cache=self.invalidate_cache,
        )

    def with_header(self, key: str, value: str) -> "APIRequest":
        """Add a header (returns new instance)."""
        new_headers = {**self.headers, key: value}
        return APIRequest(
            method=self.method,
            path=self.path,
            query_params=self.query_params,
            headers=new_headers,
            body=self.body,
            cache_key=self.cache_key,
            cache_ttl=self.cache_ttl,
            invalidate_cache=self.invalidate_cache,
        )

    def with_cache(self, key: str, ttl: int | None = None) -> "APIRequest":
        """Enable caching for this request (returns new instance)."""
        return APIRequest(
            method=self.method,
            path=self.path,
            query_params=self.query_params,
            headers=self.headers,
            body=self.body,
            cache_key=key,
            cache_ttl=ttl,
            invalidate_cache=self.invalidate_cache,
        )

    def invalidating_cache(self, key: str) -> "APIRequest":
        """Mark cache key to invalidate after request (returns new instance)."""
        return APIRequest(
            method=self.method,
            path=self.path,
            query_params=self.query_params,
            headers=self.headers,
            body=self.body,
            cache_key=self.cache_key,
            cache_ttl=self.cache_ttl,
            invalidate_cache=key,
        )


class RequestBuilder(Generic[T]):
    """
    Fluent builder for API requests with type-safe response handling.

    This provides a declarative interface for building API requests
    that makes the intent clear and improves maintainability.

    Example:
        >>> request = (
        ...     RequestBuilder.get("/api/v4/contests")
        ...     .with_query_param("public", "true")
        ...     .with_cache("contests_public", ttl=300)
        ...     .build()
        ... )
        >>> # Request describes what we want, not how to get it
    """

    def __init__(self, request: APIRequest):
        """
        Initialize builder with request.

        Args:
            request: API request specification
        """
        self._request = request

    @classmethod
    def get(cls, path: str) -> "RequestBuilder[Any]":
        """
        Create a GET request builder.

        Args:
            path: API endpoint path

        Returns:
            Request builder
        """
        return cls(APIRequest(method=HTTPMethod.GET, path=path))

    @classmethod
    def post(cls, path: str, body: Any | None = None) -> "RequestBuilder[Any]":
        """
        Create a POST request builder.

        Args:
            path: API endpoint path
            body: Request body

        Returns:
            Request builder
        """
        return cls(APIRequest(method=HTTPMethod.POST, path=path, body=body))

    @classmethod
    def put(cls, path: str, body: Any | None = None) -> "RequestBuilder[Any]":
        """
        Create a PUT request builder.

        Args:
            path: API endpoint path
            body: Request body

        Returns:
            Request builder
        """
        return cls(APIRequest(method=HTTPMethod.PUT, path=path, body=body))

    @classmethod
    def delete(cls, path: str) -> "RequestBuilder[Any]":
        """
        Create a DELETE request builder.

        Args:
            path: API endpoint path

        Returns:
            Request builder
        """
        return cls(APIRequest(method=HTTPMethod.DELETE, path=path))

    def with_query_param(self, key: str, value: Any) -> "RequestBuilder[T]":
        """
        Add a query parameter.

        Args:
            key: Parameter name
            value: Parameter value

        Returns:
            Builder with parameter added
        """
        self._request = self._request.with_query_param(key, value)
        return self

    def with_header(self, key: str, value: str) -> "RequestBuilder[T]":
        """
        Add a header.

        Args:
            key: Header name
            value: Header value

        Returns:
            Builder with header added
        """
        self._request = self._request.with_header(key, value)
        return self

    def with_cache(self, key: str, ttl: int | None = None) -> "RequestBuilder[T]":
        """
        Enable caching for this request.

        Args:
            key: Cache key
            ttl: Optional cache TTL override

        Returns:
            Builder with caching enabled
        """
        self._request = self._request.with_cache(key, ttl)
        return self

    def invalidating_cache(self, key: str) -> "RequestBuilder[T]":
        """
        Mark cache key to invalidate after request.

        Args:
            key: Cache key to invalidate

        Returns:
            Builder with cache invalidation
        """
        self._request = self._request.invalidating_cache(key)
        return self

    def build(self) -> APIRequest:
        """
        Build the final request specification.

        Returns:
            API request specification
        """
        return self._request


# Declarative request specifications for common operations


def list_contests_request(public_only: bool = False) -> APIRequest:
    """
    Create request to list contests.

    Args:
        public_only: Only return public contests

    Returns:
        API request specification
    """
    builder = RequestBuilder.get("/api/v4/contests")

    if public_only:
        builder = builder.with_query_param("public", "true")

    return builder.with_cache("contests_list", ttl=300).build()


def get_contest_request(contest_id: str) -> APIRequest:
    """
    Create request to get a specific contest.

    Args:
        contest_id: Contest identifier

    Returns:
        API request specification
    """
    return (
        RequestBuilder.get(f"/api/v4/contests/{contest_id}")
        .with_cache(f"contest_{contest_id}", ttl=300)
        .build()
    )


def create_contest_request(contest_data: dict[str, Any]) -> APIRequest:
    """
    Create request to create a contest.

    Args:
        contest_data: Contest data

    Returns:
        API request specification
    """
    return (
        RequestBuilder.post("/api/v4/contests", body=contest_data)
        .invalidating_cache("contests_list")
        .build()
    )


def list_problems_request(contest_id: str) -> APIRequest:
    """
    Create request to list problems for a contest.

    Args:
        contest_id: Contest identifier

    Returns:
        API request specification
    """
    return (
        RequestBuilder.get(f"/api/v4/contests/{contest_id}/problems")
        .with_cache(f"contest_{contest_id}_problems", ttl=300)
        .build()
    )


def add_problem_request(contest_id: str, problem_data: Any) -> APIRequest:
    """
    Create request to add a problem to a contest.

    Args:
        contest_id: Contest identifier
        problem_data: Problem data

    Returns:
        API request specification
    """
    return (
        RequestBuilder.post(f"/api/v4/contests/{contest_id}/problems", body=problem_data)
        .invalidating_cache(f"contest_{contest_id}_problems")
        .build()
    )


def list_teams_request(contest_id: str) -> APIRequest:
    """
    Create request to list teams for a contest.

    Args:
        contest_id: Contest identifier

    Returns:
        API request specification
    """
    return (
        RequestBuilder.get(f"/api/v4/contests/{contest_id}/teams")
        .with_cache(f"contest_{contest_id}_teams", ttl=300)
        .build()
    )


def add_team_request(contest_id: str, team_data: dict[str, Any]) -> APIRequest:
    """
    Create request to add a team to a contest.

    Args:
        contest_id: Contest identifier
        team_data: Team data

    Returns:
        API request specification
    """
    return (
        RequestBuilder.post(f"/api/v4/contests/{contest_id}/teams", body=team_data)
        .invalidating_cache(f"contest_{contest_id}_teams")
        .build()
    )
