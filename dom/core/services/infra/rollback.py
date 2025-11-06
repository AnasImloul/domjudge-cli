"""Rollback orchestration for infrastructure deployment failures.

This module provides transaction-like semantics for infrastructure deployment,
allowing automatic rollback of partially deployed resources on failure.
"""

from collections.abc import Callable
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path

from dom.exceptions import InfrastructureError
from dom.infrastructure.docker.containers import DockerClient
from dom.logging_config import console, get_logger
from dom.shared.filesystem import ensure_dom_directory

logger = get_logger(__name__)


class DeploymentStep(str, Enum):
    """Deployment steps that can be rolled back."""

    GENERATE_COMPOSE = "generate_compose"
    START_DATABASE = "start_database"
    START_DOMSERVER = "start_domserver"
    START_MYSQL_CLIENT = "start_mysql_client"
    START_JUDGEHOSTS = "start_judgehosts"
    UPDATE_ADMIN_PASSWORD = "update_admin_password"  # nosec B105
    REGENERATE_COMPOSE = "regenerate_compose"


@dataclass
class DeploymentTransaction:
    """
    Tracks deployment progress for rollback support.

    Maintains a stack of completed steps and their rollback handlers.
    """

    completed_steps: list[DeploymentStep] = field(default_factory=list)
    rollback_handlers: dict[DeploymentStep, Callable[[], None]] = field(default_factory=dict)
    docker_client: DockerClient | None = None
    compose_file: Path | None = None

    def record_step(
        self, step: DeploymentStep, rollback_handler: Callable[[], None] | None = None
    ) -> None:
        """
        Record a completed deployment step.

        Args:
            step: Deployment step that was completed
            rollback_handler: Optional custom rollback handler for this step
        """
        self.completed_steps.append(step)
        if rollback_handler:
            self.rollback_handlers[step] = rollback_handler

        logger.debug(
            f"Deployment step completed: {step.value}",
            extra={"step": step.value, "total_steps": len(self.completed_steps)},
        )

    def rollback(self) -> None:
        """
        Roll back all completed deployment steps in reverse order.

        This provides best-effort cleanup of partially deployed infrastructure.
        """
        if not self.completed_steps:
            logger.info("No deployment steps to rollback")
            return

        console.print("\n[yellow]** Deployment failed - initiating rollback...[/yellow]")
        logger.warning(
            f"Rolling back {len(self.completed_steps)} deployment steps",
            extra={"steps_count": len(self.completed_steps)},
        )

        failures = []

        # Rollback in reverse order
        for step in reversed(self.completed_steps):
            try:
                console.print(f"[dim]Rolling back: {step.value}[/dim]")
                logger.info(f"Rolling back step: {step.value}")

                # Use custom handler if registered
                if step in self.rollback_handlers:
                    self.rollback_handlers[step]()
                else:
                    # Default rollback behavior
                    self._default_rollback(step)

                logger.info(f"Successfully rolled back: {step.value}")

            except Exception as e:
                error_msg = f"Failed to rollback step '{step.value}': {e}"
                logger.error(error_msg, exc_info=True)
                failures.append(error_msg)
                # Continue rolling back other steps

        if failures:
            console.print(
                f"\n[red]x Rollback completed with {len(failures)} failures[/red]",
            )
            console.print("[yellow]Manual cleanup may be required:[/yellow]")
            for failure in failures:
                console.print(f"  - {failure}")
            logger.warning(
                f"Rollback completed with failures: {failures}",
                extra={"failure_count": len(failures)},
            )
        else:
            console.print("\n[green]+ Rollback completed successfully[/green]")
            logger.info("Rollback completed successfully")

    def _default_rollback(self, step: DeploymentStep) -> None:
        """
        Default rollback behavior for each step type.

        Args:
            step: Deployment step to rollback
        """
        if not self.docker_client:
            self.docker_client = DockerClient()

        if not self.compose_file:
            self.compose_file = ensure_dom_directory() / "docker-compose.yml"

        # container_prefix = get_container_prefix()  # TODO: Use for container naming

        if step == DeploymentStep.GENERATE_COMPOSE:
            # Remove generated compose file
            if self.compose_file and self.compose_file.exists():
                self.compose_file.unlink()
                logger.info(f"Removed generated compose file: {self.compose_file}")

        elif step == DeploymentStep.START_DATABASE:
            # Stop MariaDB container
            try:
                self.docker_client.stop_all_services(self.compose_file, remove_volumes=True)
            except Exception as e:
                logger.warning(f"Could not stop database during rollback: {e}")

        elif step == DeploymentStep.START_DOMSERVER:
            # Stop Domserver (stop_all_services will handle this)
            pass

        elif step == DeploymentStep.START_MYSQL_CLIENT:
            # MySQL client is a sidecar, will be stopped with other services
            pass

        elif step == DeploymentStep.START_JUDGEHOSTS:
            # Stop all judgehosts (stop_all_services will handle this)
            pass

        elif step == DeploymentStep.REGENERATE_COMPOSE:
            # Nothing special to rollback
            pass

        elif step == DeploymentStep.UPDATE_ADMIN_PASSWORD:
            # Can't easily rollback password update without knowing previous password
            # But since we're rolling back entire deployment, database will be removed
            logger.info("Admin password change will be reverted with database removal")

        # For safety, always try to stop all services at the end
        if step in [
            DeploymentStep.START_DATABASE,
            DeploymentStep.START_DOMSERVER,
            DeploymentStep.START_JUDGEHOSTS,
        ]:
            try:
                self.docker_client.stop_all_services(self.compose_file, remove_volumes=True)
            except Exception as e:
                # Non-critical, services might already be stopped
                logger.debug(f"Stop services during rollback (non-critical): {e}")


def with_rollback(transaction: DeploymentTransaction) -> Callable:
    """
    Decorator to add automatic rollback to a function.

    If the decorated function raises an exception, automatically triggers
    rollback of all recorded deployment steps.

    Args:
        transaction: Deployment transaction to rollback on failure

    Returns:
        Decorated function with rollback support

    Example:
        >>> transaction = DeploymentTransaction()
        >>> @with_rollback(transaction)
        ... def deploy_infrastructure():
        ...     # deployment steps
        ...     transaction.record_step(DeploymentStep.START_DATABASE)
    """

    def decorator(func: Callable) -> Callable:
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                logger.error(f"Deployment failed: {e}", exc_info=True)
                transaction.rollback()
                raise InfrastructureError(f"Deployment failed and rolled back: {e}") from e

        return wrapper

    return decorator
