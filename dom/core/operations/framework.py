"""Declarative operations framework.

An *operation* is a named, runnable unit of work. There are two shapes:

* **Multi-step** — function returns :class:`Steps` (a list of labeled
  steps with an optional final summary). The runner executes each step
  with progress UI.
* **Single-step** — function returns the operation's result value
  directly. A ``summary=`` callback on the decorator can format the
  success line.

Use ``@operation(label, summary=...)`` to declare. Calling the decorated
function with its non-context arguments returns an :class:`Operation`
bound to those arguments; pass it to :func:`run` with a :class:`Context`.

Example (multi-step)::

    @operation("Deploy infrastructure")
    def apply_infra(ctx: Context, config: InfraConfig) -> Steps:
        svc = InfraService(ctx.secrets)
        return Steps(steps=[
            Step("Validate prerequisites", lambda: svc.validate_prerequisites(config.port)),
            Step("Start MariaDB",          lambda: svc.start_service("mariadb")),
        ])

    run(apply_infra(config), Context(secrets=mgr))

Example (single-step)::

    @operation("Load configuration", summary=lambda c: f"{len(c.contests)} contests")
    def load_config_op(ctx: Context, path: Path | None) -> DomConfig:
        return load_config(path, ctx.secrets)

    config = run(load_config_op(path), Context(secrets=mgr))

Errors propagate as exceptions. The runner logs and renders them, then
raises ``typer.Exit(1)``. Dry-run mode prints labels without executing.
"""

from __future__ import annotations

import functools
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any, Generic, NoReturn, TypeVar, Union

import typer
from rich.progress import (
    BarColumn,
    MofNCompleteColumn,
    Progress,
    SpinnerColumn,
    TextColumn,
    TimeElapsedColumn,
)

from dom.logging_config import console, get_logger
from dom.types.secrets import SecretsProvider

logger = get_logger(__name__)

T = TypeVar("T")


@dataclass(frozen=True)
class Context:
    """Execution context shared across operations."""

    secrets: SecretsProvider
    dry_run: bool = False
    verbose: bool = False


@dataclass(frozen=True)
class Step:
    """A labeled unit of work within a multi-step operation."""

    label: str
    fn: Callable[[], Any]


@dataclass(frozen=True)
class Steps:
    """Multi-step plan with an optional final success message."""

    steps: list[Step] = field(default_factory=list)
    summary: str = ""


@dataclass(frozen=True)
class _Value(Generic[T]):
    """Wrapper marking a single-step op's return value.

    Internal to the framework — operations don't construct this directly.
    Together with :class:`Steps`, it forms the discriminated ``Plan``
    union the runner dispatches on, replacing the prior heuristic
    isinstance-on-list classification.
    """

    value: T


# A plan is what an operation function returns once normalized: either a
# multi-step ``Steps`` or a wrapped single-step ``_Value``. Any other
# return is wrapped as ``_Value`` at normalization time.
Plan = Union[Steps, "_Value[T]"]


@dataclass(frozen=True)
class Operation(Generic[T]):
    """A bound operation, ready to be executed by :func:`run`."""

    label: str
    build: Callable[[Context], Plan[T]]
    summary: Callable[[T], str] | None = None
    show_progress: bool = True


def operation(
    label: str,
    *,
    summary: Callable[[T], str] | None = None,
    show_progress: bool = True,
) -> Callable[[Callable[..., Any]], Callable[..., Operation[T]]]:
    """Mark a function as an operation.

    The decorated function takes ``(ctx: Context, *args, **kwargs)`` and
    returns either a :class:`Steps` (multi-step) or any value (single-step,
    auto-wrapped). Calling the decorated function with its non-context
    arguments returns an :class:`Operation` bound to those arguments.
    """

    def decorator(fn: Callable[..., Any]) -> Callable[..., Operation[T]]:
        @functools.wraps(fn)
        def factory(*args: Any, **kwargs: Any) -> Operation[T]:
            def build(ctx: Context) -> Plan[T]:
                return _normalize(fn(ctx, *args, **kwargs))

            return Operation(
                label=label,
                build=build,
                summary=summary,
                show_progress=show_progress,
            )

        return factory

    return decorator


def run(op: Operation[T], ctx: Context) -> T | None:
    """Execute an operation with progress UI, dry-run support, error handling.

    Returns the operation's result value (or ``None`` for multi-step ops).
    On failure, logs and renders the error, then raises ``typer.Exit(1)``.
    """
    logger.info(
        f"Executing operation: {op.label}",
        extra={"operation": op.label, "dry_run": ctx.dry_run},
    )

    try:
        plan: Plan[T] = op.build(ctx)
    except Exception as exc:
        _fail(op.label, exc)

    if ctx.dry_run:
        _print_dry_run(op.label, plan.steps if isinstance(plan, Steps) else None)
        return None

    if isinstance(plan, Steps):
        try:
            _execute_steps(
                op.label, plan.steps, show_progress=op.show_progress, verbose=ctx.verbose
            )
        except Exception as exc:
            _fail(op.label, exc)
        _print_success(op.label, plan.summary)
        logger.info(f"Operation completed: {op.label}", extra={"operation": op.label})
        return None

    message = _resolve_summary(op, plan.value)
    _print_success(op.label, message)
    logger.info(f"Operation completed: {op.label}", extra={"operation": op.label})
    return plan.value


# ---------------------------------------------------------------- internals


def _normalize(plan: Any) -> Plan[Any]:
    """Wrap an operation function's return into the discriminated ``Plan``.

    A :class:`Steps` is returned as-is; everything else (including
    ``None`` and lists of any kind) is wrapped in ``_Value``. This
    eliminates the prior ambiguity where a bare ``list[Step]`` was
    inferred via ``all(isinstance(...))`` — multi-step ops must now
    return :class:`Steps` explicitly.
    """
    if isinstance(plan, Steps):
        return plan
    return _Value(plan)


def _resolve_summary(op: Operation[T], value: T) -> str:
    if op.summary is None:
        return ""
    try:
        return op.summary(value) or ""
    except Exception:
        logger.debug("summary callback raised", exc_info=True)
        return ""


def _execute_steps(label: str, steps: list[Step], *, show_progress: bool, verbose: bool) -> None:
    if verbose:
        console.print(f"[cyan]Execution plan ({len(steps)} steps):[/cyan]")
        for i, step in enumerate(steps, 1):
            console.print(f"[cyan]  {i}. {step.label}[/cyan]")
        console.print()

    if not show_progress or not steps:
        for step in steps:
            logger.debug(f"Step: {step.label}")
            step.fn()
        return

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(bar_width=30),
        MofNCompleteColumn(),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        TimeElapsedColumn(),
        console=console,
    ) as progress:
        task = progress.add_task(label, total=len(steps))
        for step in steps:
            progress.update(task, description=f"{label} - {step.label}")
            logger.debug(f"Step: {step.label}")
            step.fn()
            progress.advance(task)
        progress.update(task, description=label)


def _print_dry_run(label: str, steps: list[Step] | None) -> None:
    console.print(f"[yellow]* Dry run:[/yellow] {label}")
    if steps:
        console.print("[yellow]  Steps that would be executed:[/yellow]")
        for i, step in enumerate(steps, 1):
            console.print(f"[yellow]    {i}. {step.label}[/yellow]")


def _print_success(label: str, message: str) -> None:
    console.print(f"[green]+[/green] {message or label}")


def _fail(label: str, exc: Exception) -> NoReturn:
    logger.error(f"Operation failed: {label}", exc_info=exc, extra={"operation": label})
    console.print(f"[red]x[/red] {label}")
    console.print(f"[red]  Error:[/red] {exc}")
    raise typer.Exit(code=1)
