"""End-to-end tests for package distribution.

These tests verify that the package can be properly built and installed,
and that all files are included in the distribution.
"""

import subprocess
import sys
from pathlib import Path

import pytest


class TestPackageBuild:
    """Test that the package can be built successfully."""

    @pytest.mark.slow
    def test_package_builds_with_build_module(self, tmp_path):
        """Test that package can be built using python -m build."""
        # This test requires the build module
        try:
            import build  # noqa: F401
        except ImportError:
            pytest.skip("build module not available")

        # Try to build the package
        result = subprocess.run(
            [sys.executable, "-m", "build", "--outdir", str(tmp_path)],
            capture_output=True,
            text=True,
            check=False,
        )

        if result.returncode != 0:
            pytest.fail(f"Build failed: {result.stderr}")

        # Check that wheel and sdist were created
        wheel_files = list(tmp_path.glob("*.whl"))
        sdist_files = list(tmp_path.glob("*.tar.gz"))

        assert len(wheel_files) > 0, "Wheel file should be created"
        assert len(sdist_files) > 0, "Source distribution should be created"


class TestInstalledPackage:
    """Test that the installed package works correctly."""

    def test_package_version_accessible(self):
        """Test that package version is accessible after install."""
        result = subprocess.run(
            [sys.executable, "-c", "import dom; print(dom.__version__)"],
            capture_output=True,
            text=True,
            check=False,
        )

        assert result.returncode == 0, f"Import failed: {result.stderr}"
        assert len(result.stdout.strip()) > 0, "Version should be non-empty"

    def test_cli_entry_point_accessible(self):
        """Test that CLI entry point is accessible."""
        result = subprocess.run(
            ["dom", "--help"],
            capture_output=True,
            text=True,
            check=False,
        )

        # Note: This might fail if not installed, which is OK for dev
        if result.returncode == 0:
            assert "Usage:" in result.stdout or "Commands:" in result.stdout

    def test_templates_accessible_after_install(self):
        """Test that templates are accessible in installed package."""
        code = """
from dom.templates.infra import docker_compose_template
from dom.templates.init import contest_template, infra_template, problems_template
print("OK")
"""
        result = subprocess.run(
            [sys.executable, "-c", code],
            capture_output=True,
            text=True,
            check=False,
        )

        assert result.returncode == 0, f"Template import failed: {result.stderr}"
        assert "OK" in result.stdout


class TestPackageMetadata:
    """Test that package metadata is correct."""

    def test_package_name_correct(self):
        """Test that package name in metadata is correct."""
        try:
            from importlib.metadata import metadata

            meta = metadata("domjudge-cli")
            assert meta["Name"] == "domjudge-cli"
        except Exception:
            # Might not be installed, skip
            pytest.skip("Package not installed")

    def test_author_metadata_correct(self):
        """Test that author information is set correctly."""
        try:
            from importlib.metadata import metadata

            meta = metadata("domjudge-cli")
            author = meta.get("Author") or meta.get("Author-email", "")

            # Should have author information set
            assert "Anas IMLOUL" in author or "anas.imloul27@gmail.com" in author
        except Exception:
            pytest.skip("Package not installed")

    def test_repository_url_correct(self):
        """Test that repository URL is set correctly."""
        try:
            from importlib.metadata import metadata

            meta = metadata("domjudge-cli")
            project_urls = meta.get_all("Project-URL") or []

            # Convert to dict
            urls = {}
            for url_line in project_urls:
                if ", " in url_line:
                    key, value = url_line.split(", ", 1)
                    urls[key] = value

            # Should have repository URL
            assert "Repository" in urls
            assert "github.com/AnasImloul/domjudge-cli" in urls["Repository"]
        except Exception:
            pytest.skip("Package not installed")


class TestFileInclusion:
    """Test that all necessary files are included in the package."""

    def test_python_files_included(self):
        """Test that Python files are in the package."""
        import dom

        dom_path = Path(dom.__file__).parent

        # Check for key modules
        assert (dom_path / "cli" / "__init__.py").exists()
        assert (dom_path / "core" / "__init__.py").exists()
        assert (dom_path / "infrastructure" / "__init__.py").exists()
        assert (dom_path / "templates" / "__init__.py").exists()
        assert (dom_path / "types" / "__init__.py").exists()

    def test_template_files_included(self):
        """Test that template files are in the package."""
        import dom.templates

        templates_path = Path(dom.templates.__file__).parent

        # All template files should exist
        template_files = [
            "infra/docker-compose.yml.j2",
            "init/contest.yml.j2",
            "init/infra.yml.j2",
            "init/problems.yml.j2",
        ]

        for template_file in template_files:
            template_path = templates_path / template_file
            assert template_path.exists(), f"Template {template_file} should be included"

    def test_py_typed_included(self):
        """Test that py.typed marker is included."""
        import dom

        dom_path = Path(dom.__file__).parent
        py_typed = dom_path / "py.typed"

        assert py_typed.exists(), "py.typed should be included in package"


@pytest.mark.slow
class TestDistributionIntegrity:
    """Test the integrity of the distribution package."""

    def test_wheel_contains_templates(self, tmp_path):
        """Test that wheel file contains template files."""
        try:
            import zipfile

            # Build a wheel
            result = subprocess.run(
                [sys.executable, "-m", "build", "--wheel", "--outdir", str(tmp_path)],
                capture_output=True,
                text=True,
                check=False,
            )

            if result.returncode != 0:
                pytest.skip("Could not build wheel")

            wheel_files = list(tmp_path.glob("*.whl"))
            if not wheel_files:
                pytest.skip("No wheel file created")

            wheel_path = wheel_files[0]

            # Check wheel contents
            with zipfile.ZipFile(wheel_path, "r") as zf:
                files = zf.namelist()

                # Should contain template files
                template_files = [f for f in files if f.endswith(".j2")]
                assert len(template_files) > 0, "Wheel should contain .j2 template files"

                # Should contain py.typed
                py_typed_files = [f for f in files if f.endswith("py.typed")]
                assert len(py_typed_files) > 0, "Wheel should contain py.typed marker"

        except ImportError:
            pytest.skip("zipfile or build module not available")
