"""Operation runner with declarative execution flow."""

from typing import Generic, TypeVar

from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

from dom.logging_config import get_logger

from .base import Operation, OperationContext, OperationResult

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
                console.print(f"[red]✗ Validation failed:[/red] {error_msg}")
            logger.error(f"Validation failed for {description}: {error_msg}")
            return OperationResult.failure(ValueError(f"Validation failed: {error_msg}"), error_msg)

        # Handle dry-run mode
        if context.dry_run:
            if not self.silent:
                console.print(f"[yellow]⊙ Dry run:[/yellow] {description}")
            logger.info(f"Dry run: {description}")
            return OperationResult.skipped("Dry run - operation not executed")

        # Execute with progress indicator
        if self.show_progress and not self.silent:
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console,
            ) as progress:
                progress.add_task(description=description, total=None)
                result = self._execute_operation(context)
        else:
            result = self._execute_operation(context)

        # Display result
        if not self.silent:
            self._display_result(result, description)

        # Log result
        if result.is_success():
            logger.info(
                f"Operation completed successfully: {description}",
                extra={"operation": description, "message": result.message},
            )
        elif result.is_failure():
            logger.error(
                f"Operation failed: {description}",
                exc_info=result.error,
                extra={"operation": description, "error": str(result.error)},
            )

        return result

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
            message = result.message or description
            console.print(f"[green]✓[/green] {message}")
        elif result.is_failure():
            error_msg = result.message or str(result.error)
            console.print(f"[red]✗[/red] {description}")
            console.print(f"[red]  Error:[/red] {error_msg}")
        elif result.status.value == "skipped":
            message = result.message or description
            console.print(f"[yellow]⊙[/yellow] Skipped: {message}")


class BatchOperationRunner:
    """
    Runner for executing multiple operations as a batch.

    Provides declarative way to run multiple operations with
    unified error handling and progress tracking.

    Example:
        >>> operations = [
        ...     LoadConfigOperation(path),
        ...     ValidateConfigOperation(),
        ...     ApplyConfigOperation(),
        ... ]
        >>> runner = BatchOperationRunner(operations)
        >>> results = runner.run_all(context)
        >>> if all(r.is_success() for r in results):
        ...     print("All operations successful")
    """

    def __init__(self, operations: list[Operation], stop_on_error: bool = True):
        """
        Initialize batch runner.

        Args:
            operations: List of operations to run
            stop_on_error: Stop execution on first error
        """
        self.operations = operations
        self.stop_on_error = stop_on_error

    def run_all(self, context: OperationContext) -> list[OperationResult]:
        """
        Execute all operations.

        Args:
            context: Execution context

        Returns:
            List of operation results
        """
        results: list[OperationResult] = []

        for operation in self.operations:
            runner = OperationRunner(operation)
            result = runner.run(context)
            results.append(result)

            if self.stop_on_error and result.is_failure():
                logger.warning(f"Stopping batch execution due to error in: {operation.describe()}")
                break

        # Summary
        success_count = sum(1 for r in results if r.is_success())
        failure_count = sum(1 for r in results if r.is_failure())

        logger.info(
            f"Batch execution complete: {success_count} succeeded, {failure_count} failed",
            extra={
                "total": len(results),
                "success": success_count,
                "failure": failure_count,
            },
        )

        return results
