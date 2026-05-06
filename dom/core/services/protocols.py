"""Structural interfaces for the service layer.

Services depend on these protocols rather than concrete infrastructure classes,
so tests and alternate implementations can satisfy the contract by shape alone.
"""

from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from dom.infrastructure.api.client import DomJudgeClient
    from dom.infrastructure.api.services import (
        ContestService,
        GroupService,
        OrganizationService,
        ProblemService,
        SubmissionService,
        TeamService,
        UserService,
    )


class DomJudgeAPIProtocol(Protocol):
    """Structural type matching the public surface of DomJudgeAPI.

    Any object exposing these attributes satisfies the protocol — concrete
    `DomJudgeAPI` instances do, and so do test doubles built with
    `Mock(spec=DomJudgeAPIProtocol)` or fakes.
    """

    client: "DomJudgeClient"
    contests: "ContestService"
    problems: "ProblemService"
    teams: "TeamService"
    groups: "GroupService"
    users: "UserService"
    organizations: "OrganizationService"
    submissions: "SubmissionService"
