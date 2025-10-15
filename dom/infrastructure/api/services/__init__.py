"""API service modules for DOMjudge resources.

This module provides focused service classes for different DOMjudge resources:
- ContestService: Contest operations
- ProblemService: Problem operations
- TeamService: Team operations
- UserService: User operations
- OrganizationService: Organization operations
- SubmissionService: Submission operations

Each service is focused on a single resource type and follows Single Responsibility Principle.
"""

from .contests import ContestService
from .organizations import OrganizationService
from .problems import ProblemService
from .submissions import SubmissionService
from .teams import TeamService
from .users import UserService

__all__ = [
    "ContestService",
    "OrganizationService",
    "ProblemService",
    "SubmissionService",
    "TeamService",
    "UserService",
]
