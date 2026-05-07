"""Tests for the operations framework: @operation, run(), Step/Steps."""

from unittest.mock import MagicMock

import pytest
import typer

from dom.core.operations import Context, Step, Steps, operation, run
from dom.types.secrets import SecretsProvider


@pytest.fixture
def context():
    return Context(secrets=MagicMock(spec=SecretsProvider))


# ---------------------------------------------------------------- single-step


@operation("Single step", summary=lambda v: f"got {v}")
def _single(_ctx: Context, value: str) -> str:
    return value


def test_single_step_returns_value(context, capsys):
    result = run(_single("hello"), context)
    assert result == "hello"
    out = capsys.readouterr().out
    assert "got hello" in out


@operation("Single step without summary")
def _single_no_summary(_ctx: Context) -> int:
    return 42


def test_single_step_without_summary_prints_label(context, capsys):
    result = run(_single_no_summary(), context)
    assert result == 42
    assert "Single step without summary" in capsys.readouterr().out


@operation("Failing single step")
def _single_failure(_ctx: Context) -> str:
    raise RuntimeError("boom")


def test_single_step_failure_raises_typer_exit(context, capsys):
    with pytest.raises(typer.Exit) as excinfo:
        run(_single_failure(), context)
    assert excinfo.value.exit_code == 1
    out = capsys.readouterr().out
    assert "Failing single step" in out
    assert "boom" in out


# ---------------------------------------------------------------- multi-step


@operation("Multi step")
def _multi(_ctx: Context, sink: list[str]) -> Steps:
    return Steps(
        steps=[
            Step("first", lambda: sink.append("a")),
            Step("second", lambda: sink.append("b")),
            Step("third", lambda: sink.append("c")),
        ]
    )


def test_multi_step_executes_steps_in_order(context):
    sink: list[str] = []
    result = run(_multi(sink), context)
    assert result is None
    assert sink == ["a", "b", "c"]


@operation("Multi step with summary")
def _multi_with_summary(_ctx: Context) -> Steps:
    return Steps(
        steps=[Step("noop", lambda: None)],
        summary="custom summary",
    )


def test_multi_step_with_steps_wrapper_uses_summary(context, capsys):
    run(_multi_with_summary(), context)
    assert "custom summary" in capsys.readouterr().out


@operation("Multi step with failing step")
def _multi_failing(_ctx: Context, sink: list[str]) -> Steps:
    return Steps(
        steps=[
            Step("ok", lambda: sink.append("ok")),
            Step("bad", lambda: (_ for _ in ()).throw(ValueError("step boom"))),
            Step("never", lambda: sink.append("never")),
        ]
    )


def test_multi_step_failure_stops_at_failing_step(context):
    sink: list[str] = []
    with pytest.raises(typer.Exit):
        run(_multi_failing(sink), context)
    assert sink == ["ok"]


# ---------------------------------------------------------------- dry run


def test_dry_run_skips_execution_for_multi_step(context, capsys):
    sink: list[str] = []
    dry_ctx = Context(secrets=context.secrets, dry_run=True)
    result = run(_multi(sink), dry_ctx)
    assert result is None
    assert sink == []
    out = capsys.readouterr().out
    assert "Dry run" in out
    assert "first" in out


def test_dry_run_skips_execution_for_single_step(context, capsys):
    dry_ctx = Context(secrets=context.secrets, dry_run=True)
    # _single would otherwise return its arg; in dry-run it returns None
    result = run(_single("hello"), dry_ctx)
    assert result is None
    assert "Dry run" in capsys.readouterr().out


# ---------------------------------------------------------------- build errors


@operation("Validating op")
def _validating(_ctx: Context, ok: bool) -> str:
    if not ok:
        raise FileNotFoundError("missing")
    return "fine"


def test_build_errors_become_typer_exit(context, capsys):
    with pytest.raises(typer.Exit):
        run(_validating(False), context)
    out = capsys.readouterr().out
    assert "Validating op" in out
    assert "missing" in out


# ---------------------------------------------------------------- show_progress


@operation("No-progress op", show_progress=False)
def _no_progress(_ctx: Context, sink: list[int]) -> Steps:
    return Steps(steps=[Step("only", lambda: sink.append(1))])


def test_show_progress_false_still_executes(context):
    sink: list[int] = []
    run(_no_progress(sink), context)
    assert sink == [1]
