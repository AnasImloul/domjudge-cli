"""Infrastructure API service modules for DOMjudge resources.

This module provides thin HTTP wrappers for different DOMjudge resources.
These are infrastructure-layer services that handle direct API communication.

For business logic and orchestration, see dom.core.services.

Services:
- ContestAPIService: Contest HTTP operations
- ProblemAPIService: Problem HTTP operations
- TeamAPIService: Team HTTP operations
- GroupAPIService: Team group/category HTTP operations
- UserAPIService: User HTTP operations
- OrganizationAPIService: Organization HTTP operations
- SubmissionAPIService: Submission HTTP operations

Each service is focused on a single resource type and follows Single Responsibility Principle.
"""

from .contests import ContestAPIService
from .groups import GroupAPIService
from .organizations import OrganizationAPIService
from .problems import ProblemAPIService
from .submissions import SubmissionAPIService
from .teams import TeamAPIService
from .users import UserAPIService

__all__ = [
    "ContestAPIService",
    "GroupAPIService",
    "OrganizationAPIService",
    "ProblemAPIService",
    "SubmissionAPIService",
    "TeamAPIService",
    "UserAPIService",
]
