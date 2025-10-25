"""Declarative operations for infrastructure management."""

from pathlib import Path

from dom.core.config.loaders import load_infrastructure_config
from dom.core.services.infra.apply import apply_infra_and_platform
from dom.core.services.infra.destroy import destroy_infra_and_platform
from dom.core.services.infra.status import (
    check_infrastructure_status,
    print_status_human_readable,
    print_status_json,
)
from dom.logging_config import get_logger
from dom.types.infra import InfraConfig, InfrastructureStatus
from dom.utils.validation import (
    validate_infrastructure_prerequisites,
    warn_if_privileged_port,
)

from .base import Operation, OperationContext, OperationResult

logger = get_logger(__name__)


class LoadInfraConfigOperation(Operation[InfraConfig]):
    """Load infrastructure configuration from file."""

    def __init__(self, config_path: Path | None = None):
        """
        Initialize infra config loading operation.

        Args:
            config_path: Optional path to configuration file
        """
        self.config_path = config_path

    def describe(self) -> str:
        """Describe what this operation does."""
        path_str = str(self.config_path) if self.config_path else "default location"
        return f"Load infrastructure configuration from {path_str}"

    def validate(self, context: OperationContext) -> list[str]:  # noqa: ARG002
        """Validate that config file exists if path provided."""
        if self.config_path and not self.config_path.exists():
            return [f"Configuration file not found: {self.config_path}"]
        return []

    def execute(self, context: OperationContext) -> OperationResult[InfraConfig]:  # noqa: ARG002
        """Execute configuration loading."""
        try:
            config = load_infrastructure_config(self.config_path)
            return OperationResult.success(config, "Infrastructure configuration loaded")
        except Exception as e:
            logger.error(f"Failed to load infrastructure configuration: {e}", exc_info=True)
            return OperationResult.failure(e, f"Failed to load infrastructure configuration: {e}")


class ApplyInfrastructureOperation(Operation[None]):
    """Apply infrastructure configuration (setup Docker containers, etc.)."""

    def __init__(self, config: InfraConfig):
        """
        Initialize infrastructure application operation.

        Args:
            config: Infrastructure configuration
        """
        self.config = config

    def describe(self) -> str:
        """Describe what this operation does."""
        return "Deploy infrastructure and platform components"

    def execute(self, context: OperationContext) -> OperationResult[None]:
        """Execute infrastructure deployment."""
        try:
            # Validate prerequisites before deployment
            validate_infrastructure_prerequisites(self.config.port)
            warn_if_privileged_port(self.config.port)

            apply_infra_and_platform(self.config, context.secrets)
            return OperationResult.success(None, "Infrastructure deployed successfully")
        except Exception as e:
            logger.error(f"Failed to deploy infrastructure: {e}", exc_info=True)
            return OperationResult.failure(e, f"Failed to deploy infrastructure: {e}")


class DestroyInfrastructureOperation(Operation[None]):
    """Destroy all infrastructure components."""

    def __init__(self, remove_volumes: bool = False):
        """
        Initialize infrastructure destruction operation.

        Args:
            remove_volumes: If True, delete volumes (PERMANENT DATA LOSS)
        """
        self.remove_volumes = remove_volumes

    def describe(self) -> str:
        """Describe what this operation does."""
        return "Destroy all infrastructure and platform components"

    def execute(self, context: OperationContext) -> OperationResult[None]:
        """Execute infrastructure destruction."""
        try:
            destroy_infra_and_platform(context.secrets, self.remove_volumes)
            return OperationResult.success(None, "Infrastructure destroyed successfully")
        except Exception as e:
            logger.error(f"Failed to destroy infrastructure: {e}", exc_info=True)
            return OperationResult.failure(e, f"Failed to destroy infrastructure: {e}")


class CheckInfrastructureStatusOperation(Operation[InfrastructureStatus]):
    """Check the health status of infrastructure components."""

    def __init__(self, config: InfraConfig | None = None):
        """
        Initialize status check operation.

        Args:
            config: Optional infrastructure configuration for expected state
        """
        self.config = config

    def describe(self) -> str:
        """Describe what this operation does."""
        return "Check infrastructure health status"

    def execute(self, context: OperationContext) -> OperationResult[InfrastructureStatus]:  # noqa: ARG002
        """Execute infrastructure status check."""
        try:
            status = check_infrastructure_status(self.config)
            message = (
                "Infrastructure is healthy" if status.is_healthy() else "Infrastructure has issues"
            )
            return OperationResult.success(status, message)
        except Exception as e:
            logger.error(f"Failed to check infrastructure status: {e}", exc_info=True)
            return OperationResult.failure(e, f"Failed to check status: {e}")


class PrintInfrastructureStatusOperation(Operation[None]):
    """Check and print infrastructure status."""

    def __init__(self, config: InfraConfig | None = None, json_output: bool = False):
        """
        Initialize status print operation.

        Args:
            config: Optional infrastructure configuration for expected state
            json_output: Output in JSON format if True
        """
        self.config = config
        self.json_output = json_output

    def describe(self) -> str:
        """Describe what this operation does."""
        return "Check and display infrastructure status"

    def execute(self, context: OperationContext) -> OperationResult[None]:  # noqa: ARG002
        """Execute infrastructure status check and print."""
        try:
            status = check_infrastructure_status(self.config)

            # Print status
            if self.json_output:
                print_status_json(status)
            else:
                print_status_human_readable(status)

            # Always return success - the status check itself succeeded
            # The status output shows whether infrastructure is healthy or not
            message = (
                "Infrastructure is healthy"
                if status.is_healthy()
                else "Infrastructure is not healthy"
            )
            return OperationResult.success(None, message)
        except Exception as e:
            logger.error(f"Failed to check infrastructure status: {e}", exc_info=True)
            return OperationResult.failure(e, f"Failed to check status: {e}")
