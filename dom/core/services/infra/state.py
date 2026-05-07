"""Infrastructure state comparison and change detection."""

import re
import subprocess  # nosec B404
from collections.abc import Callable
from dataclasses import dataclass
from enum import Enum

from pydantic import SecretStr

from dom.constants import ContainerNames
from dom.logging_config import get_logger
from dom.types.infra import InfraConfig
from dom.utils.cli import get_container_prefix, get_secrets_manager

logger = get_logger(__name__)


def _run_docker(args: list[str], *, check: bool = False) -> subprocess.CompletedProcess | None:
    """Invoke ``docker`` and return the completed process, or ``None`` on failure.

    "Failure" here means the docker CLI itself couldn't run — not
    installed, permission denied, killed. A nonzero exit code is *not*
    a failure: some callers rely on it to detect "container doesn't
    exist". Anything outside this contract is a programmer bug and is
    re-raised.
    """
    try:
        return subprocess.run(  # nosec B603 B607
            args, capture_output=True, text=True, check=check
        )
    except (FileNotFoundError, OSError, subprocess.SubprocessError) as e:
        logger.warning(f"docker {' '.join(args[1:3])}: {e}")
        return None


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
        """Render a markup-decorated summary line for the CLI to print."""
        return _SUMMARY_RENDERERS[self.change_type](self)


def _summary_scale(cs: "InfraChangeSet") -> str:
    direction = "[green]SCALE UP[/green]" if cs.judge_diff > 0 else "[yellow]SCALE DOWN[/yellow]"
    old = cs.old_config.judges if cs.old_config else "?"
    return f"{direction} judgehosts: {old} → {cs.new_config.judges} " "(safe live change)"


def _summary_port(cs: "InfraChangeSet") -> str:
    old = cs.old_config.port if cs.old_config else "?"
    return (
        f"[red]PORT CHANGE[/red]: {old} → {cs.new_config.port} " "[bold](requires restart)[/bold]"
    )


_SUMMARY_RENDERERS: dict[InfraChangeType, Callable[["InfraChangeSet"], str]] = {
    InfraChangeType.CREATE: lambda _cs: "[green]CREATE[/green] new infrastructure",
    InfraChangeType.NO_CHANGE: lambda _cs: "[dim]NO CHANGES[/dim] to infrastructure",
    InfraChangeType.SCALE_JUDGES: _summary_scale,
    InfraChangeType.PORT_CHANGE: _summary_port,
    InfraChangeType.PASSWORD_CHANGE: lambda _cs: (
        "[yellow]PASSWORD CHANGE[/yellow] [bold](requires restart)[/bold]"
    ),
    InfraChangeType.FULL_RESTART: lambda _cs: (
        "[red]MULTIPLE CHANGES[/red] [bold](requires full restart)[/bold]"
    ),
}


# Each entry: which combination of changed fields maps to which change type.
# Anything not listed (i.e. >1 field changed in an unrecognized combination)
# falls through to FULL_RESTART.
_CHANGE_TYPE_BY_FIELDS: dict[frozenset[str], InfraChangeType] = {
    frozenset(): InfraChangeType.NO_CHANGE,
    frozenset({"judges"}): InfraChangeType.SCALE_JUDGES,
    frozenset({"port"}): InfraChangeType.PORT_CHANGE,
    frozenset({"password"}): InfraChangeType.PASSWORD_CHANGE,
}


def _detect_changed_fields(old: InfraConfig, new: InfraConfig) -> frozenset[str]:
    """Return the set of infra fields whose value differs between old and new."""
    field_extractors: dict[str, Callable[[InfraConfig], object]] = {
        "port": lambda c: c.port,
        "password": lambda c: c.password,
        "judges": lambda c: c.judges,
    }
    changed = {name for name, get in field_extractors.items() if get(old) != get(new)}
    for name in changed:
        logger.debug(f"Infra field changed: {name}")
    return frozenset(changed)


class InfraStateComparator:
    """
    Service for comparing infrastructure state to detect safe vs unsafe changes.

    Uses Docker as the single source of truth - no state files needed!
    Queries running containers directly to determine current infrastructure state.

    This enables intelligent infrastructure updates:
    - Safe: Scaling judgehost count (hot swap)
    - Unsafe: Port changes, password changes (require restart)
    """

    def __init__(self):
        """Initialize infrastructure state comparator."""
        self.container_prefix = get_container_prefix()

    def compare_infrastructure(self, new_config: InfraConfig) -> InfraChangeSet:
        """Compute an :class:`InfraChangeSet` from the live Docker state."""
        old_config = self._load_current_state()
        if old_config is None:
            return InfraChangeSet(
                change_type=InfraChangeType.CREATE,
                old_config=None,
                new_config=new_config,
            )

        changed = _detect_changed_fields(old_config, new_config)
        return InfraChangeSet(
            change_type=_CHANGE_TYPE_BY_FIELDS.get(changed, InfraChangeType.FULL_RESTART),
            old_config=old_config,
            new_config=new_config,
            judge_diff=new_config.judges - old_config.judges,
        )

    def _load_current_state(self) -> InfraConfig | None:
        """Query Docker for the current deployed infrastructure state.

        Returns ``None`` for a fresh deployment (no domserver container)
        or when Docker can't be reached at all.
        """
        domserver = ContainerNames.DOMSERVER.with_prefix(self.container_prefix)
        result = _run_docker(["docker", "inspect", domserver])
        if result is None or result.returncode != 0:
            logger.debug("No domserver container found (new deployment)")
            return None

        port = self._get_container_port(domserver)
        if port is None:
            logger.warning("Could not determine port from domserver container")
            return None

        password = get_secrets_manager().get("admin_password")
        if not password:
            logger.warning("Admin password not found in secrets")
            return None

        judges = self._count_judgehost_containers()
        logger.debug(f"Current infrastructure state from Docker: port={port}, judges={judges}")
        return InfraConfig(port=port, judges=judges, password=SecretStr(password))

    def _get_container_port(self, container_name: str) -> int | None:
        """Return the host port mapped to container port 80, or ``None``."""
        result = _run_docker(["docker", "port", container_name, "80"])
        if result is None or result.returncode != 0:
            return None
        match = re.search(r":(\d+)", result.stdout.strip())
        if match is None:
            return None
        try:
            port = int(match.group(1))
        except ValueError:
            logger.warning(f"Unexpected port output for {container_name}: {result.stdout!r}")
            return None
        logger.debug(f"Found port {port} for container {container_name}")
        return port

    def _count_judgehost_containers(self) -> int:
        """Return the number of running judgehost containers (0 on failure)."""
        result = _run_docker(
            [
                "docker",
                "ps",
                "--filter",
                f"name={self.container_prefix}-judgehost",
                "--format",
                "{{.Names}}",
            ],
            check=True,
        )
        if result is None:
            return 0
        count = sum(1 for line in result.stdout.splitlines() if line.strip())
        logger.debug(f"Found {count} judgehost containers")
        return count
