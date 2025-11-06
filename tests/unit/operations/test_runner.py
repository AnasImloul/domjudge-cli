"""Tests for the operation runner."""

import pytest

from dom.core.operations.base import (
    ExecutableStep,
    Operation,
    OperationContext,
    OperationResult,
    OperationStatus,
    SteppedOperation,
)
from dom.core.operations.runner import OperationRunner


class SimpleOperation(Operation[str]):
    """A simple test operation that returns success."""

    def describe(self) -> str:
        return "Simple test operation"

    def validate(self, context: OperationContext) -> list[str]:
        return []

    def execute(self, context: OperationContext) -> OperationResult[str]:
        return OperationResult.success("Success!", "Operation completed successfully")


class FailingOperation(Operation[str]):
    """An operation that always fails."""

    def describe(self) -> str:
        return "Failing test operation"

    def validate(self, context: OperationContext) -> list[str]:
        return []

    def execute(self, context: OperationContext) -> OperationResult[str]:
        return OperationResult.failure("Operation failed")


class ValidatingOperation(Operation[str]):
    """An operation with validation errors."""

    def describe(self) -> str:
        return "Validating operation"

    def validate(self, context: OperationContext) -> list[str]:
        return ["Validation error 1", "Validation error 2"]

    def execute(self, context: OperationContext) -> OperationResult[str]:
        return OperationResult.success("Should not reach here")


class MockStep(ExecutableStep):
    """A simple mock step for testing."""

    def __init__(self, step_name: str, should_fail: bool = False):
        super().__init__(step_name, f"Execute {step_name}")
        self.should_fail = should_fail

    def execute(self, context: OperationContext) -> str:
        if self.should_fail:
            raise ValueError(f"Step {self.name} failed")
        return f"Result from {self.name}"


class SimpleSteppedOperation(SteppedOperation[str]):
    """A simple stepped operation for testing."""

    def __init__(self, steps: list[ExecutableStep]):
        self.steps_to_execute = steps

    def describe(self) -> str:
        return "Simple stepped operation"

    def validate(self, context: OperationContext) -> list[str]:
        return []

    def define_steps(self) -> list[ExecutableStep]:
        return self.steps_to_execute

    def _build_result(
        self, step_results: dict[str, object], context: OperationContext
    ) -> OperationResult[str]:
        return OperationResult.success("All steps completed", "Stepped operation done")


class TestOperationRunner:
    """Tests for OperationRunner."""

    @pytest.fixture
    def context(self, tmp_path):
        """Create an OperationContext for testing."""
        from dom.infrastructure.secrets.manager import SecretsManager

        secrets = SecretsManager(tmp_path)
        return OperationContext(secrets=secrets, dry_run=False)

    def test_run_simple_operation_success(self, context):
        """Test running a simple successful operation."""
        operation = SimpleOperation()
        runner = OperationRunner(operation, silent=True)

        result = runner.run(context)

        assert result.is_success()
        assert result.data == "Success!"
        assert not result.is_failure()
        assert result.status == OperationStatus.SUCCESS

    def test_run_failing_operation(self, context):
        """Test running an operation that fails."""
        operation = FailingOperation()
        runner = OperationRunner(operation, silent=True)

        result = runner.run(context)

        assert result.is_failure()
        assert not result.is_success()

    def test_run_operation_with_validation_errors(self, context):
        """Test that validation errors prevent execution."""
        operation = ValidatingOperation()
        runner = OperationRunner(operation, silent=True)

        result = runner.run(context)

        assert result.is_failure()
        assert "validation" in result.message.lower()

    def test_run_operation_in_dry_run_mode(self, tmp_path):
        """Test that dry_run mode skips execution."""
        from dom.infrastructure.secrets.manager import SecretsManager

        secrets = SecretsManager(tmp_path)
        dry_run_context = OperationContext(secrets=secrets, dry_run=True)
        operation = SimpleOperation()
        runner = OperationRunner(operation, silent=True)

        result = runner.run(dry_run_context)

        assert result.status == OperationStatus.SKIPPED
        assert "dry" in result.message.lower()

    def test_run_stepped_operation_success(self, context):
        """Test running a stepped operation where all steps succeed."""
        steps = [
            MockStep("step1"),
            MockStep("step2"),
            MockStep("step3"),
        ]
        operation = SimpleSteppedOperation(steps)
        runner = OperationRunner(operation, silent=True)

        result = runner.run(context)

        assert result.is_success()

    def test_run_stepped_operation_with_failing_step(self, context):
        """Test running a stepped operation where one step fails."""
        steps = [
            MockStep("step1"),
            MockStep("step2", should_fail=True),
            MockStep("step3"),
        ]
        operation = SimpleSteppedOperation(steps)
        runner = OperationRunner(operation, silent=True)

        result = runner.run(context)

        assert result.is_failure()
        assert "step" in result.message.lower() or "failed" in result.message.lower()

    def test_operation_result_status_checks(self):
        """Test OperationResult status checking methods."""
        success = OperationResult.success("data", "Success message")
        failure = OperationResult.failure(ValueError("Failure message"))
        skipped = OperationResult.skipped("Skipped message")

        # Success checks
        assert success.is_success()
        assert not success.is_failure()
        assert success.status == OperationStatus.SUCCESS

        # Failure checks
        assert failure.is_failure()
        assert not failure.is_success()
        assert failure.status == OperationStatus.FAILURE

        # Skipped checks
        assert skipped.status == OperationStatus.SKIPPED
        assert not skipped.is_success()
        assert not skipped.is_failure()

    def test_operation_result_data_access(self):
        """Test accessing data from OperationResult."""
        result = OperationResult.success("test_data", "Success")

        assert result.data == "test_data"
        assert result.message == "Success"

    def test_operation_context_dry_run_flag(self, tmp_path):
        """Test OperationContext dry_run flag."""
        from dom.infrastructure.secrets.manager import SecretsManager

        secrets = SecretsManager(tmp_path)

        # Normal context
        normal_context = OperationContext(secrets=secrets, dry_run=False)
        assert not normal_context.dry_run

        # Dry-run context
        dry_run_context = OperationContext(secrets=secrets, dry_run=True)
        assert dry_run_context.dry_run


class TestExecutableStep:
    """Tests for ExecutableStep."""

    def test_step_initialization(self):
        """Test that steps are initialized correctly."""
        step = MockStep("test_step")

        assert step.name == "test_step"
        assert step.description == "Execute test_step"

    def test_step_execution(self, tmp_path):
        """Test that steps can be executed."""
        from dom.infrastructure.secrets.manager import SecretsManager

        secrets = SecretsManager(tmp_path)
        context = OperationContext(secrets=secrets, dry_run=False)
        step = MockStep("test_step")

        result = step.execute(context)

        assert "test_step" in result

    def test_step_execution_failure(self, tmp_path):
        """Test that step execution failures are handled."""
        from dom.infrastructure.secrets.manager import SecretsManager

        secrets = SecretsManager(tmp_path)
        context = OperationContext(secrets=secrets, dry_run=False)
        step = MockStep("failing_step", should_fail=True)

        with pytest.raises(ValueError, match="failed"):
            step.execute(context)
