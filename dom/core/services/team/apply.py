"""Declarative team service."""

from concurrent.futures import ThreadPoolExecutor, as_completed

from dom.constants import (
    DEFAULT_COUNTRY_CODE,
    DEFAULT_TEAM_GROUP_ID,
    HASH_MODULUS,
    MAX_CONCURRENT_TEAM_OPERATIONS,
)
from dom.core.services.base import BulkOperationMixin, Service, ServiceContext, ServiceResult
from dom.exceptions import APIError, TeamError
from dom.logging_config import get_logger
from dom.types.api.models import AddOrganization, AddTeam, AddUser
from dom.types.secrets import SecretsProvider
from dom.types.team import Team
from dom.utils.hashing import deterministic_hash

logger = get_logger(__name__)


class TeamService(Service[Team], BulkOperationMixin[Team]):
    """
    Declarative service for managing teams.

    Provides clean methods for adding teams to contests with
    proper error handling, concurrency control, and idempotency.

    This service is idempotent - running multiple times with the same teams
    will not create duplicates.
    """

    def __init__(self, client, secrets: SecretsProvider):
        super().__init__(client)
        self.secrets = secrets

    def create(self, entity: Team, context: ServiceContext) -> ServiceResult[Team]:
        """
        Add a single team to a contest.

        Args:
            entity: Team to add
            context: Service context with contest_id

        Returns:
            Service result with team
        """
        if not context.contest_id:
            return ServiceResult.fail(
                ValueError("Contest ID required to add team"), "Contest ID missing"
            )

        try:
            # Create organization if team has affiliation
            organization_id = None
            if entity.affiliation is not None:
                organization_id = self._create_organization(
                    entity.affiliation, entity.country, context
                )

            # Teams are uniquely identified across (name, affiliation, country)
            # so different organizations can have teams with the same display name.
            composite_key = entity.composite_key

            # Stable team_id across runs (uses the persisted hash seed). DOMjudge
            # still dedupes by composite ``name`` below; making team_id stable
            # makes log/debug correlation easier and the request payload
            # reproducible.
            team_id = str(deterministic_hash(self.secrets, composite_key, modulo=HASH_MODULUS))

            # The composite team name IS the join key. ``entity.username`` is
            # ``team{deterministic_hash}`` set by the config loader, so this
            # form is stable across runs.
            team_name = f"{entity.username}|{composite_key}"

            # Use original team name as display_name for clean scoreboard
            display_name = entity.name

            logger.debug(
                f"Creating team: name={display_name}, username={entity.username}, "
                f"team_id={team_id}, affiliation={entity.affiliation}, country={entity.country}"
            )

            # Use contest-specific group if available, otherwise fall back to default
            group_ids = (
                [context.team_group_id] if context.team_group_id else [DEFAULT_TEAM_GROUP_ID]
            )

            team_result = self.client.teams.add_to_contest(
                contest_id=context.contest_id,
                team_data=AddTeam(
                    id=team_id,
                    name=team_name,
                    display_name=display_name,
                    group_ids=group_ids,
                    organization_id=organization_id,
                ),
            )
            entity.id = team_result.id

            # Create user only if team was newly created (idempotency)
            if team_result.created:
                self._create_user_for_team(entity, context)
                logger.info(
                    "Successfully added team",
                    extra={
                        "team_name": entity.name,
                        "team_id": entity.id,
                        "contest_id": context.contest_id,
                    },
                )
                return ServiceResult.ok(
                    entity, f"Team '{entity.name}' created successfully", created=True
                )
            else:
                logger.info(
                    "Team already exists, skipped user creation",
                    extra={
                        "team_name": entity.name,
                        "team_id": entity.id,
                        "contest_id": context.contest_id,
                    },
                )
                return ServiceResult.ok(
                    entity, f"Team '{entity.name}' already exists", created=False
                )

        except APIError as e:
            error_msg = f"Failed to add team '{entity.name}' to contest {context.contest_id}: {e}"
            logger.error(
                error_msg,
                exc_info=True,
                extra={
                    "team_name": entity.name,
                    "contest_id": context.contest_id,
                    "error_type": type(e).__name__,
                },
            )
            return ServiceResult.fail(TeamError(error_msg), f"Team '{entity.name}' failed")

    def _create_organization(
        self, affiliation: str, country: str | None, context: ServiceContext
    ) -> str:
        """
        Create organization for team affiliation.

        Organizations are uniquely identified by (affiliation, country).
        This allows different institutions in different countries to have the same name.

        Args:
            affiliation: Organization name
            country: ISO 3166-1 alpha-3 country code (e.g., "MAR", "USA")
            context: Service context

        Returns:
            Organization ID
        """
        org_country = country or DEFAULT_COUNTRY_CODE
        # ``MIT|USA`` and ``MIT|GBR`` are different organizations.
        # Stable across runs via the persisted hash seed; DOMjudge dedupes by
        # name + country regardless.
        org_composite_key = f"{affiliation}|{org_country}"
        org_id = str(deterministic_hash(self.secrets, org_composite_key, modulo=HASH_MODULUS))

        org_result = self.client.organizations.add_to_contest(
            contest_id=context.contest_id,  # type: ignore[arg-type]
            organization=AddOrganization(
                id=org_id,
                shortname=affiliation,
                name=affiliation,
                formal_name=affiliation,
                country=org_country,
            ),
        )
        return org_result.id

    def _create_user_for_team(self, team: Team, context: ServiceContext) -> None:  # noqa: ARG002
        """
        Create user account for team.

        Args:
            team: Team entity
            context: Service context
        """
        self.client.users.add(
            user_data=AddUser(
                username=team.username,  # type: ignore[arg-type]
                name=team.name,
                password=team.password.get_secret_value(),  # type: ignore[arg-type]
                team_id=team.id,
                roles=["team"],
            )
        )

    def create_many(
        self,
        entities: list[Team],
        context: ServiceContext,
        stop_on_error: bool = False,
    ) -> list[ServiceResult[Team]]:
        """
        Add multiple teams concurrently.

        Args:
            entities: List of teams
            context: Service context
            stop_on_error: Stop on first error if True

        Returns:
            List of service results
        """
        results: list[ServiceResult[Team]] = []

        with ThreadPoolExecutor(max_workers=MAX_CONCURRENT_TEAM_OPERATIONS) as executor:
            # Submit all tasks
            future_to_team = {
                executor.submit(self.create, team, context): team for team in entities
            }

            # Collect results
            for future in as_completed(future_to_team.keys()):
                team = future_to_team[future]
                try:
                    result = future.result()
                    results.append(result)

                    if stop_on_error and not result.success:
                        logger.warning(
                            f"Stopping bulk team creation due to error with '{team.name}'"
                        )
                        break

                except Exception as e:
                    logger.error(
                        f"Unexpected exception in team creation task for '{team.name}'",
                        exc_info=True,
                        extra={"team_name": team.name},
                    )
                    results.append(ServiceResult.fail(e, f"Task failed: {e}"))

                    if stop_on_error:
                        break

        return results
