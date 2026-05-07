"""Rich-flavored renderer for the operations framework.

The framework is presentation-agnostic; this module wires its events
to ``dom.ui`` (markup, blank lines, success/error styling) and to a
``rich.Progress`` widget for multi-step operations.

Importing this module installs the renderer as the framework's default,
so every subsequent ``dom.core.operations.run(...)`` call picks it up
without having to thread a ``renderer=`` argument through.
"""

from __future__ import annotations

from rich.progress import (
    BarColumn,
    MofNCompleteColumn,
    Progress,
    SpinnerColumn,
    TextColumn,
    TimeElapsedColumn,
)

from dom import ui
from dom.core.operations.framework import (
    Renderer,
    Step,
    StepProgress,
    set_default_renderer,
)
from dom.ui import console


class _NullProgress:
    def step(self, step_label: str, index: int) -> None:  # noqa: ARG002
        return None

    def finish(self) -> None:
        return None


class _RichProgress:
    def __init__(self, label: str, total: int) -> None:
        self._label = label
        self._progress = Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(bar_width=30),
            MofNCompleteColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            TimeElapsedColumn(),
            console=console,
        )
        self._progress.start()
        self._task = self._progress.add_task(label, total=total)

    def step(self, step_label: str, index: int) -> None:
        self._progress.update(self._task, description=f"{self._label} - {step_label}")
        if index > 1:
            self._progress.advance(self._task)

    def finish(self) -> None:
        self._progress.advance(self._task)
        self._progress.update(self._task, description=self._label)
        self._progress.stop()


class RichRenderer:
    """Renders operation events with ``dom.ui`` markup and Rich progress."""

    def dry_run(self, label: str, steps: list[Step] | None) -> None:
        ui.write(f"[yellow]* Dry run:[/yellow] {label}")
        if steps:
            ui.warn("  Steps that would be executed:")
            for i, step in enumerate(steps, 1):
                ui.warn(f"    {i}. {step.label}")

    def plan(self, steps: list[Step]) -> None:
        ui.write(f"Execution plan ({len(steps)} steps):", style="cyan")
        for i, step in enumerate(steps, 1):
            ui.write(f"  {i}. {step.label}", style="cyan")
        ui.blank()

    def steps_started(self, label: str, total: int, *, show_progress: bool) -> StepProgress:
        if not show_progress or total == 0:
            return _NullProgress()
        return _RichProgress(label, total)

    def success(self, label: str, message: str) -> None:
        ui.write(f"[green]+[/green] {message or label}")

    def failure(self, label: str, exc: Exception) -> None:
        ui.write(f"[red]x[/red] {label}")
        ui.write(f"[red]  Error:[/red] {exc}")


_renderer: Renderer = RichRenderer()
set_default_renderer(_renderer)
