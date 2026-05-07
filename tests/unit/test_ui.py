"""Tests for the dom.ui owner module (input + console output)."""

from unittest.mock import patch

from dom import ui
from dom.utils.validators import Invalid


class TestAsk:
    """Tests for ui.ask() — single prompt with parser & re-prompt loop."""

    def test_returns_raw_input_when_no_parser(self):
        with patch("dom.ui.input.Prompt.ask", return_value="hello"):
            assert ui.ask("Q") == "hello"

    def test_runs_parser_and_returns_parsed_value(self):
        with patch("dom.ui.input.Prompt.ask", return_value="42"):
            assert ui.ask("Q", parser=int) == 42

    def test_reprompts_after_invalid_then_succeeds(self):
        """When parser raises Invalid, the prompt loops; on a valid value, returns it."""

        def parser(s: str) -> int:
            if s == "bad":
                raise Invalid("nope")
            return int(s)

        with patch("dom.ui.input.Prompt.ask", side_effect=["bad", "7"]):
            assert ui.ask("Q", parser=parser) == 7

    def test_reprompts_after_generic_exception(self):
        """Non-Invalid exceptions also trigger a re-prompt with a generic error."""

        def parser(s: str) -> int:
            if s == "bad":
                raise RuntimeError("boom")
            return int(s)

        with patch("dom.ui.input.Prompt.ask", side_effect=["bad", "1"]):
            assert ui.ask("Q", parser=parser) == 1


class TestAskBool:
    def test_delegates_to_rich_confirm(self):
        with patch("dom.ui.input.Confirm.ask", return_value=True) as mock_confirm:
            assert ui.ask_bool("Continue?", default=False) is True

        mock_confirm.assert_called_once()
        kwargs = mock_confirm.call_args.kwargs
        assert kwargs["default"] is False
        assert kwargs["console"] is ui.console


class TestAskChoice:
    """Tests for ui.ask_choice() — fixed set of choices with optional normalizer."""

    def test_returns_chosen_value_when_valid(self):
        with patch("dom.ui.input.Prompt.ask", return_value="yes"):
            assert ui.ask_choice("Pick", choices=["yes", "no"]) == "yes"

    def test_normalizer_maps_input_back_to_original_choice(self):
        """Normalizer is applied to user input; the original (un-normalized) value is returned."""

        with patch("dom.ui.input.Prompt.ask", return_value="yes"):
            result = ui.ask_choice(
                "Pick",
                choices=["YES", "NO"],
                normalizer=str.lower,
            )

        assert result == "YES"


class TestOutputHelpers:
    """Output helpers should route through the shared console."""

    def test_write_with_style_wraps_in_markup(self):
        with patch.object(ui.console, "print") as mock_print:
            ui.write("hello", style="bold red")
        mock_print.assert_called_once_with("[bold red]hello[/bold red]")

    def test_write_without_style_passes_through(self):
        with patch.object(ui.console, "print") as mock_print:
            ui.write("plain")
        mock_print.assert_called_once_with("plain")

    def test_header_emits_blank_line_then_styled_title(self):
        with patch.object(ui.console, "print") as mock_print:
            ui.header("Section")
        assert mock_print.call_count == 2
        mock_print.assert_any_call()
        mock_print.assert_any_call("[bold cyan]Section[/bold cyan]")

    def test_header_without_spacer(self):
        with patch.object(ui.console, "print") as mock_print:
            ui.header("Section", spacer=False)
        mock_print.assert_called_once_with("[bold cyan]Section[/bold cyan]")

    def test_warn_uses_yellow(self):
        with patch.object(ui.console, "print") as mock_print:
            ui.warn("careful")
        mock_print.assert_called_once_with("[yellow]careful[/yellow]")

    def test_error_uses_red(self):
        with patch.object(ui.console, "print") as mock_print:
            ui.error("boom")
        mock_print.assert_called_once_with("[red]boom[/red]")

    def test_success_uses_green(self):
        with patch.object(ui.console, "print") as mock_print:
            ui.success("ok")
        mock_print.assert_called_once_with("[green]ok[/green]")
