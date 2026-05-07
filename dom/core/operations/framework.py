"""Declarative operations framework.

An *operation* is a named, runnable unit of work. There are two shapes:

* **Multi-step** — function returns :class:`Steps` (a list of labeled
  steps with an optional final summary). The runner executes each step
  via the configured :class:`Renderer`.
* **Single-step** — function returns the operation's result value
  directly. A ``summary=`` callback on the decorator can format the
  success line.

Use ``@operation(label, summary=...)`` to declare. Calling the decorated
function with its non-context arguments returns an :class:`Operation`
bound to those arguments; pass it to :func:`run` with a :class:`Context`.

The framework is presentation-agnostic: it emits events via a
:class:`Renderer` and never imports ``dom.ui`` or ``rich``. The CLI
layer supplies a Rich-flavored renderer; tests rely on the default
:class:`_PlainRenderer` which writes plain text to stdout.

Example (multi-step)::

    @operation("Deploy infrastructure")
    def apply_infra(ctx: Context, config: InfraConfig) -> Steps:
        svc = InfraService(ctx.secrets)
        return Steps(steps=[
            Step("Validate prerequisites", lambda: svc.validate_prerequisites(config.port)),
            Step("Start MariaDB",          lambda: svc.start_service("mariadb")),
        ])

    run(apply_infra(config), Context(secrets=mgr))

Errors propagate as exceptions. The runner asks the renderer to display
them, then raises ``typer.Exit(1)``. Dry-run mode emits labels via the
renderer without executing.
"""

from __future__ import annotations

import functools
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any, Generic, NoReturn, Protocol, TypeVar, Union

import typer

from dom.logging_config import get_logger
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
    """Wrapper marking a single-step op's return value."""

    value: T


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
    """Mark a function as an operation."""

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


# ---------------------------------------------------------------- renderer


class StepProgress(Protocol):
    """Per-execution handle returned by :meth:`Renderer.steps_started`.

    The runner calls :meth:`step` once per step and :meth:`finish` once
    at the end (in a ``try``/``finally``). Plain renderers can ignore
    these calls; Rich renderers drive a ``rich.Progress`` widget.
    """

    def step(self, step_label: str, index: int) -> None: ...
    def finish(self) -> None: ...


class Renderer(Protocol):
    """Sink for operation lifecycle events."""

    def dry_run(self, label: str, steps: list[Step] | None) -> None: ...
    def plan(self, steps: list[Step]) -> None: ...
    def steps_started(self, label: str, total: int, *, show_progress: bool) -> StepProgress: ...
    def success(self, label: str, message: str) -> None: ...
    def failure(self, label: str, exc: Exception) -> None: ...


class _PlainStepProgress:
    def step(self, step_label: str, index: int) -> None:  # noqa: ARG002
        return None

    def finish(self) -> None:
        return None


class _PlainRenderer:
    """Default renderer: plain stdout, no Rich, no ``dom.ui``.

    Used in tests and as a safe fallback when the CLI hasn't installed a
    fancier renderer. Output uses ASCII glyphs only.
    """

    def dry_run(self, label: str, steps: list[Step] | None) -> None:
        print(f"* Dry run: {label}")
        if steps:
            print("  Steps that would be executed:")
            for i, step in enumerate(steps, 1):
                print(f"    {i}. {step.label}")

    def plan(self, steps: list[Step]) -> None:
        print(f"Execution plan ({len(steps)} steps):")
        for i, step in enumerate(steps, 1):
            print(f"  {i}. {step.label}")
        print()

    def steps_started(
        self,
        label: str,  # noqa: ARG002
        total: int,  # noqa: ARG002
        *,
        show_progress: bool,  # noqa: ARG002
    ) -> StepProgress:
        return _PlainStepProgress()

    def success(self, label: str, message: str) -> None:
        print(f"+ {message or label}")

    def failure(self, label: str, exc: Exception) -> None:
        print(f"x {label}")
        print(f"  Error: {exc}")


_default_renderer: Renderer = _PlainRenderer()


def set_default_renderer(renderer: Renderer) -> None:
    """Install a process-wide default renderer for :func:`run`.

    Called once during CLI startup to swap in the Rich-flavored renderer.
    Tests leave the default :class:`_PlainRenderer` in place.
    """
    global _default_renderer  # noqa: PLW0603
    _default_renderer = renderer


def run(
    op: Operation[T],
    ctx: Context,
    *,
    renderer: Renderer | None = None,
) -> T | None:
    """Execute an operation. Returns the result value (or ``None`` for multi-step)."""
    r = renderer or _default_renderer

    logger.info(
        f"Executing operation: {op.label}",
        extra={"operation": op.label, "dry_run": ctx.dry_run},
    )

    try:
        plan: Plan[T] = op.build(ctx)
    except Exception as exc:
        _fail(r, op.label, exc)

    if ctx.dry_run:
        r.dry_run(op.label, plan.steps if isinstance(plan, Steps) else None)
        return None

    if isinstance(plan, Steps):
        try:
            _execute_steps(r, op.label, plan.steps, op.show_progress, ctx.verbose)
        except Exception as exc:
            _fail(r, op.label, exc)
        r.success(op.label, plan.summary)
        logger.info(f"Operation completed: {op.label}", extra={"operation": op.label})
        return None

    message = _resolve_summary(op, plan.value)
    r.success(op.label, message)
    logger.info(f"Operation completed: {op.label}", extra={"operation": op.label})
    return plan.value


# ---------------------------------------------------------------- internals


def _normalize(plan: Any) -> Plan[Any]:
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


def _execute_steps(
    renderer: Renderer,
    label: str,
    steps: list[Step],
    show_progress: bool,
    verbose: bool,
) -> None:
    if verbose and steps:
        renderer.plan(steps)

    progress = renderer.steps_started(label, len(steps), show_progress=show_progress)
    try:
        for i, step in enumerate(steps, 1):
            progress.step(step.label, i)
            logger.debug(f"Step: {step.label}")
            step.fn()
    finally:
        progress.finish()


def _fail(renderer: Renderer, label: str, exc: Exception) -> NoReturn:
    logger.error(f"Operation failed: {label}", exc_info=exc, extra={"operation": label})
    renderer.failure(label, exc)
    raise typer.Exit(code=1)
