"""Unified validation system for DOMjudge CLI.

This module provides a single source of truth for all validation rules.
The same validators are used for:
- Config file loading (Pydantic)
- CLI arguments (Typer)
- Interactive prompts (init command)

This prevents "split brain" where validation rules differ across the codebase.
"""

from .adapters import for_prompt, for_pydantic, for_typer, optional_for_pydantic
from .rules import ValidationRules

__all__ = ["ValidationRules", "for_prompt", "for_pydantic", "for_typer", "optional_for_pydantic"]
