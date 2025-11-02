"""Operation runner with declarative execution flow."""

from typing import Any, Generic, TypeVar

from rich.console import Console
from rich.progress import (
    BarColumn,
    MofNCompleteColumn,
    Progress,
    SpinnerColumn,
    TextColumn,
    TimeElapsedColumn,
)

from dom.logging_config import get_logger

from .base import (
    ExecutableStep,
    Operation,
    OperationContext,
    OperationResult,
    SteppedOperation,
)

logger = get_logger(__name__)
console = Console()

T = TypeVar("T")


class OperationRunner(Generic[T]):
    """
    Declarative runner for executing operations with consistent UI and logging.

    Handles:
    - Progress indication
    - Logging
    - Error display
    - Dry-run mode

    Example:
        >>> operation = LoadConfigOperation(path)
        >>> context = OperationContext(secrets=secrets_manager)
        >>> runner = OperationRunner(operation)
        >>> result = runner.run(context)
        >>> if result.is_success():
        ...     print(f"Loaded: {result.data}")
    """

    def __init__(
        self,
        operation: Operation[T],
        show_progress: bool = True,
        silent: bool = False,
    ):
        """
        Initialize the operation runner.

        Args:
            operation: Operation to run
            show_progress: Show progress indicator
            silent: Suppress console output
        """
        self.operation = operation
        self.show_progress = show_progress
        self.silent = silent

    def run(self, context: OperationContext) -> OperationResult[T]:
        """
        Execute the operation with proper UI and error handling.

        Args:
            context: Execution context

        Returns:
            Operation result
        """
        description = self.operation.describe()

        # Log execution start
        logger.info(
            f"Executing operation: {description}",
            extra={"dry_run": context.dry_run, "operation": description},
        )

        # Validate first
        validation_errors = self.operation.validate(context)
        if validation_errors:
            error_msg = "; ".join(validation_errors)
            if not self.silent:
                console.print(f"[red]x Validation failed:[/red] {error_msg}")
            logger.error(f"Validation failed for {description}: {error_msg}")
            return OperationResult.failure(ValueError(f"Validation failed: {error_msg}"), error_msg)

        # Handle dry-run mode
        if context.dry_run:
            if not self.silent:
                self._display_dry_run_plan(description)
            logger.info(f"Dry run: {description}")
            return OperationResult.skipped("Dry run - operation not executed")

        # Execute with progress indicator
        if self.show_progress and not self.silent:
            result = self._execute_with_progress(context)
        else:
            result = self._execute_operation(context)

        # Display result
        if not self.silent:
            self._display_result(result, description)

        # Log result
        if result.is_success():
            logger.info(
                f"Operation completed successfully: {description}",
                extra={"operation": description, "result_message": result.message},
            )
        elif result.is_failure():
            logger.error(
                f"Operation failed: {description}",
                exc_info=result.error,
                extra={"operation": description, "error": str(result.error)},
            )

        return result

    def _display_dry_run_plan(self, description: str) -> None:
        """Display what would be executed in dry-run mode."""
        console.print(f"[yellow]* Dry run:[/yellow] {description}")

        # If this is a SteppedOperation, show the steps
        if isinstance(self.operation, SteppedOperation):
            steps = self.operation.define_steps()
            if steps:
                console.print("[yellow]  Steps that would be executed:[/yellow]")
                for i, step in enumerate(steps, 1):
                    console.print(f"[yellow]    {i}. {step.description}[/yellow]")

    def _execute_with_progress(self, context: OperationContext) -> OperationResult[T]:
        """Execute operation with progress tracking."""
        # Check if this is a SteppedOperation
        if isinstance(self.operation, SteppedOperation):
            return self._execute_stepped_operation(context)
        else:
            # Legacy operation - show simple spinner
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                BarColumn(bar_width=30),
                TimeElapsedColumn(),
                console=console,
            ) as progress:
                progress.add_task(self.operation.describe(), total=None)
                return self._execute_operation(context)

    def _execute_stepped_operation(self, context: OperationContext) -> OperationResult[T]:
        """Execute a SteppedOperation with detailed progress tracking."""
        stepped_op = self.operation
        assert isinstance(stepped_op, SteppedOperation)

        steps = stepped_op.define_steps()

        # Display step plan in verbose mode
        if context.verbose:
            self._display_step_plan(steps)

        # Execute with progress bar showing each step
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(bar_width=30),
            MofNCompleteColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            TimeElapsedColumn(),
            console=console,
        ) as progress:
            # Calculate total weight
            total_weight = sum(step.weight for step in steps)

            # Add main task
            main_task = progress.add_task(
                stepped_op.describe(),
                total=total_weight,
            )

            # Execute steps
            step_results: dict[str, Any] = {}
            try:
                for step in steps:
                    # Update progress description to show current step
                    progress.update(
                        main_task,
                        description=f"{stepped_op.describe()} - {step.description}",
                    )

                    # Check if step should be executed
                    if not step.should_execute(context):
                        logger.info(f"Skipping step: {step.name}")
                        progress.advance(main_task, advance=step.weight)
                        continue

                    # Execute the step
                    logger.debug(f"Executing step: {step.name} - {step.description}")
                    result = step.execute(context)
                    step_results[step.name] = result

                    # Advance progress by step weight
                    progress.advance(main_task, advance=step.weight)

                # Build final result
                final_result = stepped_op._build_result(step_results, context)

                # Reset description to show completion
                progress.update(main_task, description=stepped_op.describe())

                return final_result

            except Exception as e:
                logger.error(
                    f"Step execution failed in {stepped_op.describe()}",
                    exc_info=True,
                )
                return OperationResult.failure(e, f"Step execution failed: {e}")

    def _display_step_plan(self, steps: list[ExecutableStep]) -> None:
        """Display the execution plan for a stepped operation."""
        console.print(f"[cyan]Execution plan ({len(steps)} steps):[/cyan]")
        for i, step in enumerate(steps, 1):
            console.print(f"[cyan]  {i}. {step.description}[/cyan]")
        console.print()  # Empty line for spacing

    def _execute_operation(self, context: OperationContext) -> OperationResult[T]:
        """Execute the operation with error handling."""
        try:
            return self.operation.execute(context)
        except Exception as e:
            logger.error(
                f"Unexpected error executing operation: {self.operation.describe()}",
                exc_info=True,
            )
            return OperationResult.failure(e, f"Unexpected error: {e}")

    def _display_result(self, result: OperationResult[T], description: str) -> None:
        """Display operation result to console."""
        if result.is_success():
            # Only show detailed message if it adds value beyond the description
            message = result.message or ""

            # Check if message is redundant
            is_redundant = (
                not message
                or message == description
                or message.endswith("completed successfully")
                or message.endswith("loaded")
                or message == f"{description} completed successfully"
            )

            if is_redundant:
                # Just show a simple checkmark for redundant messages
                console.print("[green]+[/green] Completed")
            else:
                # Show the message if it has useful information
                console.print(f"[green]+[/green] {message}")
        elif result.is_failure():
            error_msg = result.message or str(result.error)
            console.print(f"[red]x[/red] {description}")
            console.print(f"[red]  Error:[/red] {error_msg}")
        elif result.status.value == "skipped":
            message = result.message or description
            console.print(f"[yellow]-[/yellow] Skipped: {message}")
