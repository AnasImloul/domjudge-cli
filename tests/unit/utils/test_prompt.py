"""Tests for interactive prompt helpers in dom.utils.prompt."""

from unittest.mock import MagicMock, patch

from dom.utils.prompt import ask, ask_bool, ask_choice
from dom.utils.validators import Invalid


class TestAsk:
    """Tests for ask() — single prompt with parser & re-prompt loop."""

    def test_returns_raw_input_when_no_parser(self):
        console = MagicMock()
        with patch("dom.utils.prompt.Prompt.ask", return_value="hello"):
            assert ask("Q", console=console) == "hello"

    def test_runs_parser_and_returns_parsed_value(self):
        console = MagicMock()
        with patch("dom.utils.prompt.Prompt.ask", return_value="42"):
            assert ask("Q", console=console, parser=int) == 42

    def test_reprompts_after_invalid_then_succeeds(self):
        """When parser raises Invalid, the prompt loops; on a valid value, returns it."""
        console = MagicMock()

        def parser(s: str) -> int:
            if s == "bad":
                raise Invalid("nope")
            return int(s)

        with patch("dom.utils.prompt.Prompt.ask", side_effect=["bad", "7"]):
            assert ask("Q", console=console, parser=parser) == 7

        # The error message should have been displayed before re-prompting
        assert console.print.called

    def test_reprompts_after_generic_exception(self):
        """Non-Invalid exceptions also trigger a re-prompt with a generic error."""
        console = MagicMock()

        def parser(s: str) -> int:
            if s == "bad":
                raise RuntimeError("boom")
            return int(s)

        with patch("dom.utils.prompt.Prompt.ask", side_effect=["bad", "1"]):
            assert ask("Q", console=console, parser=parser) == 1


class TestAskBool:
    def test_delegates_to_rich_confirm(self):
        console = MagicMock()
        with patch("dom.utils.prompt.Confirm.ask", return_value=True) as mock_confirm:
            assert ask_bool("Continue?", console=console, default=False) is True

        mock_confirm.assert_called_once()
        kwargs = mock_confirm.call_args.kwargs
        assert kwargs["default"] is False
        assert kwargs["console"] is console


class TestAskChoice:
    """Tests for ask_choice() — fixed set of choices with optional normalizer."""

    def test_returns_chosen_value_when_valid(self):
        console = MagicMock()
        with patch("dom.utils.prompt.Prompt.ask", return_value="yes"):
            result = ask_choice("Pick", console=console, choices=["yes", "no"])
        assert result == "yes"

    def test_normalizer_maps_input_back_to_original_choice(self):
        """Normalizer is applied to user input; the original (un-normalized) value is returned."""
        console = MagicMock()

        # Choices stored case-sensitive; user input normalized to lower
        with patch("dom.utils.prompt.Prompt.ask", return_value="yes"):
            result = ask_choice(
                "Pick",
                console=console,
                choices=["YES", "NO"],
                normalizer=str.lower,
            )

        assert result == "YES"
