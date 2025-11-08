"""Infrastructure state comparison and change detection."""

import re
import subprocess  # nosec B404
from dataclasses import dataclass
from enum import Enum

from pydantic import SecretStr

from dom.constants import ContainerNames
from dom.core.services.base import StateComparatorService
from dom.infrastructure.secrets.manager import SecretsManager
from dom.logging_config import get_logger
from dom.shared.filesystem import ensure_dom_directory, get_container_prefix
from dom.types.config.processed import InfraConfig

logger = get_logger(__name__)


class InfraChangeType(str, Enum):
    """Types of infrastructure changes."""

    CREATE = "create"  # New infrastructure
    SCALE_JUDGES = "scale_judges"  # Only judgehost count changed
    PORT_CHANGE = "port_change"  # Port changed (requires restart)
    PASSWORD_CHANGE = "password_change"  # nosec B105  # Password changed (requires restart)
    FULL_RESTART = "full_restart"  # Multiple changes requiring full restart
    NO_CHANGE = "no_change"  # No changes


@dataclass
class InfraChangeSet:
    """Represents detected infrastructure changes."""

    change_type: InfraChangeType
    old_config: InfraConfig | None
    new_config: InfraConfig
    judge_diff: int = 0  # Positive = scale up, negative = scale down

    @property
    def is_safe_live_change(self) -> bool:
        """Check if this change can be applied to running infrastructure safely."""
        return self.change_type in (InfraChangeType.SCALE_JUDGES, InfraChangeType.NO_CHANGE)

    @property
    def requires_restart(self) -> bool:
        """Check if this change requires full infrastructure restart."""
        return self.change_type in (
            InfraChangeType.PORT_CHANGE,
            InfraChangeType.PASSWORD_CHANGE,
            InfraChangeType.FULL_RESTART,
        )

    def summary(self) -> str:
        """Get human-readable summary of changes."""
        if self.change_type == InfraChangeType.CREATE:
            return "[green]CREATE[/green] new infrastructure"

        if self.change_type == InfraChangeType.NO_CHANGE:
            return "[dim]NO CHANGES[/dim] to infrastructure"

        if self.change_type == InfraChangeType.SCALE_JUDGES:
            assert self.old_config is not None  # SCALE_JUDGES always has old_config
            if self.judge_diff > 0:
                return f"[green]SCALE UP[/green] judgehosts: {self.old_config.judges} → {self.new_config.judges} (safe live change)"
            else:
                return f"[yellow]SCALE DOWN[/yellow] judgehosts: {self.old_config.judges} → {self.new_config.judges} (safe live change)"

        if self.change_type == InfraChangeType.PORT_CHANGE:
            assert self.old_config is not None  # PORT_CHANGE always has old_config
            return f"[red]PORT CHANGE[/red]: {self.old_config.port} → {self.new_config.port} [bold](requires restart)[/bold]"

        if self.change_type == InfraChangeType.PASSWORD_CHANGE:
            return "[yellow]PASSWORD CHANGE[/yellow] [bold](requires restart)[/bold]"

        return "[red]MULTIPLE CHANGES[/red] [bold](requires full restart)[/bold]"


class InfraStateComparator(StateComparatorService[InfraConfig, InfraChangeSet]):
    """
    State comparison service for infrastructure configurations.

    Inherits from StateComparatorService to provide a consistent interface
    for state comparison operations across the service layer.

    Architecture Pattern: State Comparison Service
    - Compares desired configuration with running Docker containers
    - Detects safe vs unsafe changes
    - Returns structured change sets (InfraChangeSet)
    - Enables intelligent infrastructure updates

    Uses Docker as the single source of truth - no state files needed!
    Queries running containers directly to determine current infrastructure state.

    This enables intelligent infrastructure updates:
    - Safe: Scaling judgehost count (hot swap)
    - Unsafe: Port changes, password changes (require restart)
    """

    def __init__(self) -> None:
        """Initialize infrastructure state comparator."""
        self.container_prefix = get_container_prefix()

    def compare(self, new_config: InfraConfig) -> InfraChangeSet:
        """
        Compare new configuration with current deployed state.

        Args:
            new_config: New infrastructure configuration

        Returns:
            InfraChangeSet describing changes
        """
        old_config = self._fetch_current_state("infrastructure")

        if old_config is None:
            return InfraChangeSet(
                change_type=InfraChangeType.CREATE,
                old_config=None,
                new_config=new_config,
            )

        # Detect what changed
        changes = []

        if old_config.port != new_config.port:
            changes.append("port")
            logger.debug(f"Port change detected: {old_config.port} → {new_config.port}")

        if old_config.password != new_config.password:
            changes.append("password")
            logger.debug("Password change detected")

        judges_changed = old_config.judges != new_config.judges
        if judges_changed:
            changes.append("judges")
            logger.debug(f"Judgehost count change: {old_config.judges} → {new_config.judges}")

        # Determine change type
        if not changes:
            return InfraChangeSet(
                change_type=InfraChangeType.NO_CHANGE,
                old_config=old_config,
                new_config=new_config,
            )

        if changes == ["judges"]:
            return InfraChangeSet(
                change_type=InfraChangeType.SCALE_JUDGES,
                old_config=old_config,
                new_config=new_config,
                judge_diff=new_config.judges - old_config.judges,
            )

        if "port" in changes and len(changes) == 1:
            return InfraChangeSet(
                change_type=InfraChangeType.PORT_CHANGE,
                old_config=old_config,
                new_config=new_config,
            )

        if "password" in changes and len(changes) == 1:
            return InfraChangeSet(
                change_type=InfraChangeType.PASSWORD_CHANGE,
                old_config=old_config,
                new_config=new_config,
            )

        # Multiple changes
        return InfraChangeSet(
            change_type=InfraChangeType.FULL_RESTART,
            old_config=old_config,
            new_config=new_config,
        )

    def _fetch_current_state(self, identifier: str) -> InfraConfig | None:  # noqa: ARG002
        """
        Query Docker to get current deployed infrastructure state.

        Uses Docker as the single source of truth - no state files needed!

        Args:
            identifier: Unused for infrastructure (Docker is queried directly)

        Returns:
            Current infrastructure config or None if not deployed
        """
        try:
            # Check if domserver container exists
            domserver_name = ContainerNames.DOMSERVER.with_prefix(self.container_prefix)

            # Get container info (will fail if not exists)
            result = subprocess.run(
                ["docker", "inspect", domserver_name],
                capture_output=True,
                text=True,
                check=False,  # nosec B603 B607
            )

            if result.returncode != 0:
                logger.debug("No domserver container found (new deployment)")
                return None

            # Extract port from container
            port = self._get_container_port(domserver_name)
            if port is None:
                logger.warning("Could not determine port from domserver container")
                return None

            # Count judgehost containers
            judges = self._count_judgehost_containers()

            # Get password from secrets (already stored there)
            secrets = SecretsManager(ensure_dom_directory())
            password = secrets.get("admin_password")

            if not password:
                logger.warning("Admin password not found in secrets")
                return None

            logger.debug(f"Current infrastructure state from Docker: port={port}, judges={judges}")

            return InfraConfig(
                port=port,
                judges=judges,
                password=SecretStr(password),
            )

        except Exception as e:
            logger.warning(f"Failed to query Docker for infrastructure state: {e}")
            return None

    def _get_container_port(self, container_name: str) -> int | None:
        """
        Get the exposed port from a container.

        Args:
            container_name: Name of the container

        Returns:
            Port number or None if not found
        """
        try:
            # Get port mapping using docker port command
            result = subprocess.run(
                ["docker", "port", container_name, "80"],
                capture_output=True,
                text=True,
                check=False,  # nosec B603 B607
            )

            if result.returncode != 0:
                return None

            # Parse output like "0.0.0.0:8080"
            match = re.search(r":(\d+)", result.stdout.strip())
            if match:
                port = int(match.group(1))
                logger.debug(f"Found port {port} for container {container_name}")
                return port

            return None

        except Exception as e:
            logger.warning(f"Failed to get port for {container_name}: {e}")
            return None

    def _count_judgehost_containers(self) -> int:
        """
        Count the number of running judgehost containers.

        Returns:
            Number of judgehost containers
        """
        try:
            # List containers with judgehost in the name
            result = subprocess.run(
                [
                    "docker",
                    "ps",
                    "--filter",
                    f"name={self.container_prefix}-judgehost",
                    "--format",
                    "{{.Names}}",
                ],
                capture_output=True,
                text=True,
                check=True,  # nosec B603 B607
            )

            # Count non-empty lines
            count = len([line for line in result.stdout.strip().split("\n") if line])
            logger.debug(f"Found {count} judgehost containers")
            return count

        except Exception as e:
            logger.warning(f"Failed to count judgehost containers: {e}")
            return 0
