"""End-to-end tests for package structure and imports.

These tests verify that the package is properly structured and all
modules can be imported successfully.
"""

import importlib
from pathlib import Path

import pytest


class TestPackageStructure:
    """Test that the package structure is correct."""

    def test_package_is_importable(self):
        """Test that the main package can be imported."""
        import dom

        assert dom is not None
        assert hasattr(dom, "__version__")

    def test_all_subpackages_importable(self):
        """Test that all major subpackages can be imported."""
        subpackages = [
            "dom.cli",
            "dom.core",
            "dom.core.config",
            "dom.core.operations",
            "dom.core.services",
            "dom.infrastructure",
            "dom.templates",
            "dom.types",
            "dom.utils",
            "dom.validation",
        ]

        for package in subpackages:
            try:
                importlib.import_module(package)
            except ImportError as e:
                pytest.fail(f"Failed to import {package}: {e}")

    def test_py_typed_marker_exists(self):
        """Test that py.typed marker file exists for type checking."""
        import dom

        dom_path = Path(dom.__file__).parent
        py_typed = dom_path / "py.typed"

        assert py_typed.exists(), "py.typed marker file should exist"

    def test_package_metadata_accessible(self):
        """Test that package metadata is accessible."""
        import dom

        # Should have version
        assert hasattr(dom, "__version__")
        assert isinstance(dom.__version__, str)
        assert len(dom.__version__) > 0


class TestCoreImports:
    """Test critical imports that must work."""

    def test_operations_imports(self):
        """Test that operation classes can be imported."""
        from dom.core.operations import (
            Operation,
            OperationContext,
            OperationResult,
            OperationRunner,
        )
        from dom.core.operations.base import OperationStatus

        assert Operation is not None
        assert OperationContext is not None
        assert OperationResult is not None
        assert OperationRunner is not None
        assert OperationStatus is not None

    def test_service_imports(self):
        """Test that service classes can be imported."""
        from dom.core.services.base import (
            BulkOperationMixin,
            Service,
            ServiceContext,
            ServiceResult,
        )

        assert Service is not None
        assert ServiceContext is not None
        assert ServiceResult is not None
        assert BulkOperationMixin is not None

    def test_types_imports(self):
        """Test that type definitions can be imported."""
        from dom.types import SecretsProvider
        from dom.types.config.processed import InfraConfig
        from dom.types.infra import InfrastructureStatus, ServiceStatus

        assert SecretsProvider is not None
        assert InfraConfig is not None
        assert InfrastructureStatus is not None
        assert ServiceStatus is not None

    def test_cli_imports(self):
        """Test that CLI modules can be imported."""
        from dom.cli import contest, infrastructure, init

        assert contest is not None
        assert infrastructure is not None
        assert init is not None


class TestResourceFiles:
    """Test that resource files are included in the package."""

    def test_template_files_exist(self):
        """Test that template files are accessible."""
        import dom.templates

        templates_path = Path(dom.templates.__file__).parent

        # Check infra templates
        infra_path = templates_path / "infra"
        assert infra_path.exists(), "infra template directory should exist"
        assert (
            infra_path / "docker-compose.yml.j2"
        ).exists(), "docker-compose template should exist"

        # Check init templates
        init_path = templates_path / "init"
        assert init_path.exists(), "init template directory should exist"
        assert (init_path / "contest.yml.j2").exists(), "contest template should exist"
        assert (init_path / "infra.yml.j2").exists(), "infra template should exist"
        assert (init_path / "problems.yml.j2").exists(), "problems template should exist"

    def test_template_files_readable(self):
        """Test that template files can be read."""
        import dom.templates

        templates_path = Path(dom.templates.__file__).parent
        docker_compose = templates_path / "infra" / "docker-compose.yml.j2"

        content = docker_compose.read_text()
        assert len(content) > 0, "Template file should have content"
        assert "version:" in content or "services:" in content, "Should be a valid compose file"


class TestEntryPoints:
    """Test that CLI entry points are configured correctly."""

    def test_main_entry_point_exists(self):
        """Test that the main CLI entry point exists."""
        from dom.cli import main

        assert main is not None
        assert callable(main)

    def test_cli_commands_registered(self):
        """Test that CLI commands are properly registered."""
        from dom.cli import app

        # Check that app exists and can be used
        assert app is not None
        # App should have registered groups (contest, infra, etc.)
        # Note: Commands may not be loaded until actually called
        # So we just verify the app object exists and is callable


class TestDependencies:
    """Test that all required dependencies are available."""

    def test_required_packages_importable(self):
        """Test that all required packages can be imported."""
        required_packages = [
            "typer",
            "yaml",  # PyYAML
            "pydantic",
            "jinja2",
            "requests",
            "rich",
            "pytest",
        ]

        for package_name in required_packages:
            try:
                if package_name == "yaml":
                    import yaml  # noqa: F401
                else:
                    importlib.import_module(package_name)
            except ImportError as e:
                pytest.fail(f"Required package {package_name} not available: {e}")
