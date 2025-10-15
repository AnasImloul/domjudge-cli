"""Declarative problem service."""

from concurrent.futures import ThreadPoolExecutor, as_completed

from dom.constants import MAX_CONCURRENT_PROBLEM_OPERATIONS
from dom.core.services.base import BulkOperationMixin, Service, ServiceContext, ServiceResult
from dom.exceptions import APIError, ProblemError
from dom.logging_config import get_logger
from dom.types.problem import ProblemPackage

logger = get_logger(__name__)


class ProblemService(Service[ProblemPackage], BulkOperationMixin[ProblemPackage]):
    """
    Declarative service for managing problems.

    Provides clean methods for adding problems to contests with
    proper error handling and concurrency control.
    """

    def entity_name(self) -> str:
        """Return entity name."""
        return "Problem"

    def create(
        self, entity: ProblemPackage, context: ServiceContext
    ) -> ServiceResult[ProblemPackage]:
        """
        Add a problem to a contest.

        Args:
            entity: Problem package to add
            context: Service context with contest_id

        Returns:
            Service result with problem
        """
        if not context.contest_id:
            return ServiceResult.fail(
                ValueError("Contest ID required to add problem"), "Contest ID missing"
            )

        try:
            problem_id = self.client.problems.add_to_contest(context.contest_id, entity)
            entity.id = problem_id

            logger.info(
                "Successfully added problem to contest",
                extra={
                    "problem_name": entity.yaml.name,
                    "problem_id": problem_id,
                    "contest_id": context.contest_id,
                },
            )

            return ServiceResult.ok(
                entity, f"Problem '{entity.yaml.name}' added successfully", created=True
            )

        except APIError as e:
            logger.error(
                f"Failed to add problem '{entity.yaml.name}' to contest {context.contest_id}",
                exc_info=True,
                extra={
                    "problem_name": entity.yaml.name,
                    "contest_id": context.contest_id,
                    "error_type": type(e).__name__,
                },
            )
            return ServiceResult.fail(
                ProblemError(f"Failed to add problem '{entity.yaml.name}': {e}"),
                f"Problem '{entity.yaml.name}' failed",
            )

        except Exception as e:
            logger.error(
                f"Unexpected error adding problem '{entity.yaml.name}' to contest {context.contest_id}",
                exc_info=True,
                extra={
                    "problem_name": entity.yaml.name,
                    "contest_id": context.contest_id,
                    "error_type": type(e).__name__,
                },
            )
            return ServiceResult.fail(
                ProblemError(f"Unexpected error adding problem '{entity.yaml.name}': {e}"),
                f"Unexpected error for '{entity.yaml.name}'",
            )

    def create_many(
        self,
        entities: list[ProblemPackage],
        context: ServiceContext,
        stop_on_error: bool = False,
    ) -> list[ServiceResult[ProblemPackage]]:
        """
        Add multiple problems concurrently.

        Args:
            entities: List of problem packages
            context: Service context
            stop_on_error: Stop on first error if True

        Returns:
            List of service results
        """
        results: list[ServiceResult[ProblemPackage]] = []

        with ThreadPoolExecutor(max_workers=MAX_CONCURRENT_PROBLEM_OPERATIONS) as executor:
            # Submit all tasks
            future_to_problem = {
                executor.submit(self.create, problem, context): problem for problem in entities
            }

            # Collect results
            for future in as_completed(future_to_problem.keys()):
                try:
                    result = future.result()
                    results.append(result)

                    if stop_on_error and not result.success:
                        logger.warning("Stopping bulk problem creation due to error")
                        break

                except Exception as e:
                    logger.error(
                        f"Unexpected exception in problem creation task: {e}", exc_info=True
                    )
                    results.append(ServiceResult.fail(e, f"Task failed: {e}"))

                    if stop_on_error:
                        break

        return results
