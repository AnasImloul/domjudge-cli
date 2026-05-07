"""Single shared rich Console instance.

All output and input flows through this object so styling, capture, and
width detection stay consistent across the CLI. Nothing else in the codebase
should call ``rich.console.Console()`` directly.
"""

from rich.console import Console

console: Console = Console()
