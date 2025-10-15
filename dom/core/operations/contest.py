"""Declarative operations for contest management."""

from pathlib import Path

from dom.core.config.loaders import load_config, load_contest_config, load_infrastructure_config
from dom.core.services.contest.apply import apply_contests
from dom.core.services.contest.plan import plan_contest_changes
from dom.core.services.problem.verify import verify_problemset as verify_problemset_service
from dom.logging_config import get_logger
from dom.types.config.processed import ContestConfig, DomConfig

from .base import Operation, OperationContext, OperationResult

logger = get_logger(__name__)


class LoadConfigOperation(Operation[DomConfig]):
    """Load complete DomJudge configuration from file."""

    def __init__(self, config_path: Path | None = None):
        """
        Initialize config loading operation.

        Args:
            config_path: Optional path to configuration file
        """
        self.config_path = config_path

    def describe(self) -> str:
        """Describe what this operation does."""
        path_str = str(self.config_path) if self.config_path else "default location"
        return f"Load configuration from {path_str}"

    def validate(self, context: OperationContext) -> list[str]:  # noqa: ARG002
        """Validate that config file exists if path provided."""
        if self.config_path and not self.config_path.exists():
            return [f"Configuration file not found: {self.config_path}"]
        return []

    def execute(self, context: OperationContext) -> OperationResult[DomConfig]:
        """Execute configuration loading."""
        try:
            config = load_config(self.config_path, context.secrets)
            logger.info(f"Loaded configuration from {config.loaded_from}")
            return OperationResult.success(
                config, f"Configuration loaded from {config.loaded_from}"
            )
        except Exception as e:
            logger.error(f"Failed to load configuration: {e}", exc_info=True)
            return OperationResult.failure(e, f"Failed to load configuration: {e}")


class LoadContestConfigOperation(Operation[ContestConfig]):
    """Load specific contest configuration from file."""

    def __init__(self, config_path: Path | None, contest_name: str):
        """
        Initialize contest config loading operation.

        Args:
            config_path: Optional path to configuration file
            contest_name: Name of the contest to load
        """
        self.config_path = config_path
        self.contest_name = contest_name

    def describe(self) -> str:
        """Describe what this operation does."""
        return f"Load contest '{self.contest_name}' configuration"

    def validate(self, context: OperationContext) -> list[str]:  # noqa: ARG002
        """Validate that config file exists if path provided."""
        if self.config_path and not self.config_path.exists():
            return [f"Configuration file not found: {self.config_path}"]
        return []

    def execute(self, context: OperationContext) -> OperationResult[ContestConfig]:
        """Execute contest configuration loading."""
        try:
            contest_config = load_contest_config(
                self.config_path, self.contest_name, context.secrets
            )
            return OperationResult.success(
                contest_config, f"Contest '{self.contest_name}' configuration loaded"
            )
        except KeyError as e:
            return OperationResult.failure(e, str(e))
        except Exception as e:
            logger.error(
                f"Failed to load contest '{self.contest_name}' configuration: {e}", exc_info=True
            )
            return OperationResult.failure(e, f"Failed to load contest configuration: {e}")


class PlanContestChangesOperation(Operation[str]):
    """Plan what changes would be made to contests (for dry-run)."""

    def __init__(self, config: DomConfig):
        """
        Initialize contest planning operation.

        Args:
            config: Complete DomJudge configuration
        """
        self.config = config

    def describe(self) -> str:
        """Describe what this operation does."""
        return "Analyze planned changes for contests"

    def execute(self, context: OperationContext) -> OperationResult[str]:
        """Execute contest change planning."""
        try:
            # Use service to plan changes
            plan = plan_contest_changes(self.config, context.secrets)

            # Format plan as string for display
            summary = (
                f"Planned changes:\n"
                f"  - Contests: {plan.contest_count}\n"
                f"  - Problems: {plan.total_problems}\n"
                f"  - Teams: {plan.total_teams}\n"
                f"  - Total changes: {len(plan.changes)}"
            )

            return OperationResult.success(summary, "Contest changes planned")
        except Exception as e:
            logger.error(f"Failed to plan contest changes: {e}", exc_info=True)
            return OperationResult.failure(e, f"Failed to plan changes: {e}")


class ApplyContestsOperation(Operation[None]):
    """Apply contest configuration to the DomJudge platform."""

    def __init__(self, config: DomConfig):
        """
        Initialize contest application operation.

        Args:
            config: Complete DomJudge configuration
        """
        self.config = config

    def describe(self) -> str:
        """Describe what this operation does."""
        contest_count = len(self.config.contests)
        return f"Apply {contest_count} contest(s) to DomJudge platform"

    def execute(self, context: OperationContext) -> OperationResult[None]:
        """Execute contest application."""
        try:
            apply_contests(self.config, context.secrets)
            contest_count = len(self.config.contests)
            return OperationResult.success(None, f"Successfully applied {contest_count} contest(s)")
        except Exception as e:
            logger.error(f"Failed to apply contests: {e}", exc_info=True)
            return OperationResult.failure(e, f"Failed to apply contests: {e}")


class VerifyProblemsetOperation(Operation[None]):
    """Verify problemset for a contest."""

    def __init__(self, config_path: Path | None, contest_name: str):
        """
        Initialize problemset verification operation.

        Args:
            config_path: Path to configuration file
            contest_name: Name of the contest to verify
        """
        self.config_path = config_path
        self.contest_name = contest_name

    def describe(self) -> str:
        """Describe what this operation does."""
        return f"Verify problemset for contest '{self.contest_name}'"

    def execute(self, context: OperationContext) -> OperationResult[None]:
        """Execute problemset verification."""
        try:
            # Load contest and infrastructure config through services
            contest_config = load_contest_config(
                self.config_path, self.contest_name, context.secrets
            )
            infra_config = load_infrastructure_config(self.config_path)

            # Verify problemset
            verify_problemset_service(
                infra=infra_config,
                contest=contest_config,
                secrets=context.secrets,
            )
            return OperationResult.success(None, "Problemset verification completed")
        except Exception as e:
            logger.error(f"Failed to verify problemset: {e}", exc_info=True)
            return OperationResult.failure(e, f"Failed to verify problemset: {e}")
