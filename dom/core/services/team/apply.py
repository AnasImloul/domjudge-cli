from concurrent.futures import ThreadPoolExecutor, as_completed

from dom.constants import (
    DEFAULT_COUNTRY_CODE,
    DEFAULT_TEAM_GROUP_ID,
    HASH_MODULUS,
    MAX_CONCURRENT_TEAM_OPERATIONS,
)
from dom.exceptions import APIError, TeamError
from dom.infrastructure.api.domjudge import DomJudgeAPI
from dom.logging_config import get_logger
from dom.types.api.models import AddOrganization, AddTeam, AddUser
from dom.types.team import Team

logger = get_logger(__name__)


def apply_teams_to_contest(client: DomJudgeAPI, contest_id: str, teams: list[Team]) -> list[Team]:
    """
    Apply teams to a contest with proper error handling.

    This operation is idempotent - running multiple times with the same teams
    will not create duplicates.

    Args:
        client: DOMjudge API client
        contest_id: Contest identifier
        teams: List of teams to add

    Returns:
        List of successfully added teams

    Raises:
        TeamError: If one or more teams fail to add, with details about which
                   teams failed and why.

    Example:
        >>> client = DomJudgeAPI(...)
        >>> teams = [Team(name="Alpha", ...), Team(name="Beta", ...)]
        >>> added_teams = apply_teams_to_contest(client, "contest123", teams)
        >>> len(added_teams)  # All teams successfully added
        2
    """

    def add_team(team: Team) -> Team:
        """
        Add a single team to the contest.

        Raises:
            TeamError: If team addition fails
        """
        try:
            organization_id = None
            if team.affiliation is not None:
                org_result = client.organizations.add_to_contest(
                    contest_id=contest_id,
                    organization=AddOrganization(
                        id=str(hash(team.affiliation) % HASH_MODULUS),
                        shortname=team.affiliation,
                        name=team.affiliation,
                        formal_name=team.affiliation,
                        country=DEFAULT_COUNTRY_CODE,
                    ),
                )
                organization_id = org_result.id

            team_result = client.teams.add_to_contest(
                contest_id=contest_id,
                team_data=AddTeam(
                    id=str(hash(team.name) % HASH_MODULUS),
                    name=f"{team.username}({team.name})",
                    display_name=team.name,
                    group_ids=[DEFAULT_TEAM_GROUP_ID],
                    organization_id=organization_id,
                ),
            )
            team.id = team_result.id

            # Only create user if team was newly created
            if team_result.created:
                client.users.add(
                    user_data=AddUser(
                        username=team.username,  # type: ignore[arg-type]
                        name=team.name,
                        password=team.password.get_secret_value(),  # type: ignore[arg-type]
                        team_id=team.id,
                        roles=["team"],
                    )
                )
                logger.info(
                    "Successfully added team",
                    extra={"team_name": team.name, "team_id": team.id, "contest_id": contest_id},
                )
            else:
                logger.info(
                    "Team already exists, skipped user creation",
                    extra={"team_name": team.name, "team_id": team.id, "contest_id": contest_id},
                )

            return team

        except APIError as e:
            error_msg = f"Failed to add team '{team.name}' to contest {contest_id}: {e}"
            logger.error(
                error_msg,
                exc_info=True,
                extra={
                    "team_name": team.name,
                    "contest_id": contest_id,
                    "error_type": type(e).__name__,
                },
            )
            raise TeamError(error_msg) from e
        except Exception as e:
            error_msg = f"Unexpected error adding team '{team.name}' to contest {contest_id}: {e}"
            logger.error(
                error_msg,
                exc_info=True,
                extra={
                    "team_name": team.name,
                    "contest_id": contest_id,
                    "error_type": type(e).__name__,
                },
            )
            raise TeamError(error_msg) from e

    # Track successes and failures
    results: list[Team] = []
    failures: list[tuple[Team, Exception]] = []

    # Use bounded thread pool to respect rate limiting
    with ThreadPoolExecutor(max_workers=MAX_CONCURRENT_TEAM_OPERATIONS) as executor:
        # Map futures to teams for better error reporting
        future_to_team: dict[object, Team] = {
            executor.submit(add_team, team): team for team in teams
        }

        for future in as_completed(future_to_team.keys()):  # type: ignore[var-annotated, arg-type]
            team = future_to_team[future]
            try:
                result = future.result()
                results.append(result)
            except TeamError as e:
                # Already logged in add_team()
                failures.append((team, e))
            except Exception as e:
                # Unexpected exception not caught by add_team()
                logger.error(
                    f"Unexpected exception in team addition task for '{team.name}'",
                    exc_info=True,
                    extra={"team_name": team.name},
                )
                failures.append((team, e))

    # Report results
    if failures:
        failed_teams = ", ".join([f"'{team.name}'" for team, _ in failures])
        error_summary = f"{len(failures)}/{len(teams)} team(s) failed to add: {failed_teams}"
        logger.error(
            error_summary,
            extra={
                "total_teams": len(teams),
                "successful": len(results),
                "failed": len(failures),
                "contest_id": contest_id,
            },
        )
        raise TeamError(error_summary)

    logger.info(
        f"Successfully added all {len(results)} teams to contest",
        extra={"teams_count": len(results), "contest_id": contest_id},
    )

    return results
