"""Type definitions for structured logging contexts.

This module provides TypedDict classes for consistent structured logging
across the application. Using these types ensures log fields are consistent
and makes log analysis easier.

Usage:
    >>> from dom.types.logging import ProblemLogContext
    >>> logger.info(
    ...     "Added problem",
    ...     extra=ProblemLogContext(
    ...         problem_name="A",
    ...         contest_id="123"
    ...     )
    ... )
"""

from typing import TypedDict


class ProblemLogContext(TypedDict, total=False):
    """
    Structured log context for problem-related operations.

    Fields:
        problem_name: Name/letter of the problem (A, B, C, etc.)
        problem_id: DOMjudge problem ID
        contest_id: Associated contest ID
        problem_index: Index in problem list
        problem_letter: Assigned letter
        original_name: Original problem name before assignment
        error_type: Type of exception if error occurred
    """

    problem_name: str
    problem_id: str | None
    contest_id: str
    problem_index: int
    problem_letter: str
    original_name: str
    error_type: str


class TeamLogContext(TypedDict, total=False):
    """
    Structured log context for team-related operations.

    Fields:
        team_name: Display name of the team
        team_id: DOMjudge team ID
        team_username: Team login username
        contest_id: Associated contest ID
        organization_id: Team's organization ID
        error_type: Type of exception if error occurred
    """

    team_name: str
    team_id: str
    team_username: str
    contest_id: str
    organization_id: str
    error_type: str


class ContestLogContext(TypedDict, total=False):
    """
    Structured log context for contest-related operations.

    Fields:
        contest_name: Full name of the contest
        contest_id: DOMjudge contest ID
        contest_shortname: Short name/identifier
        created: Whether contest was newly created
        problems_count: Number of problems in contest
        teams_count: Number of teams in contest
        error_type: Type of exception if error occurred
    """

    contest_name: str
    contest_id: str
    contest_shortname: str
    created: bool
    problems_count: int
    teams_count: int
    error_type: str


class APILogContext(TypedDict, total=False):
    """
    Structured log context for API-related operations.

    Fields:
        endpoint: API endpoint path
        method: HTTP method (GET, POST, etc.)
        status_code: HTTP response status code
        cache_hit: Whether response was served from cache
        rate_limited: Whether request was rate limited
        response_time: Response time in milliseconds
        error_type: Type of exception if error occurred
    """

    endpoint: str
    method: str
    status_code: int
    cache_hit: bool
    rate_limited: bool
    response_time: float
    error_type: str


class InfrastructureLogContext(TypedDict, total=False):
    """
    Structured log context for infrastructure operations.

    Fields:
        container_name: Docker container name
        container_id: Docker container ID
        port: Port number
        judges_count: Number of judgehosts
        operation: Type of operation (start, stop, destroy, etc.)
        error_type: Type of exception if error occurred
    """

    container_name: str
    container_id: str
    port: int
    judges_count: int
    operation: str
    error_type: str


class ValidationLogContext(TypedDict, total=False):
    """
    Structured log context for validation operations.

    Fields:
        field_name: Name of field being validated
        field_value: Value being validated (sanitized)
        validation_rule: Name of validation rule applied
        error_message: Validation error message if failed
    """

    field_name: str
    field_value: str
    validation_rule: str
    error_message: str


class ServiceLogContext(TypedDict, total=False):
    """
    Structured log context for service layer operations.

    Fields:
        service_name: Name of the service
        operation: Operation being performed
        total_items: Total number of items to process
        successful: Number of successful operations
        failed: Number of failed operations
        duration: Operation duration in seconds
        error_type: Type of exception if error occurred
    """

    service_name: str
    operation: str
    total_items: int
    successful: int
    failed: int
    duration: float
    error_type: str
