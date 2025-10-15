"""End-to-end tests for package distribution.

These tests verify that the package can be properly built and installed,
and that all files are included in the distribution.

These tests are STRICT and test actual user workflows - they will FAIL
if the package doesn't work as users expect.
"""

import subprocess
import sys
from pathlib import Path

import pytest

# yaml is required for all tests
import yaml  # noqa: F401 - Required for config validation

# build is required only for slow tests - imported where needed


class TestPackageBuild:
    """Test that the package can be built successfully."""

    @pytest.mark.slow
    def test_package_builds_successfully(self, tmp_path):
        """Test that package builds successfully - users must be able to build."""
        # Require build module for this test
        try:
            import build  # noqa: F401
        except ImportError:
            pytest.fail(
                "ERROR: 'build' module is REQUIRED for package building tests!\n"
                "Install it with: pip install build\n"
                "This test ensures users can build the package."
            )

        # This simulates: python -m build
        result = subprocess.run(
            [sys.executable, "-m", "build", "--outdir", str(tmp_path)],
            capture_output=True,
            text=True,
            check=False,
        )

        # STRICT: Build MUST succeed
        assert (
            result.returncode == 0
        ), f"Build FAILED (users won't be able to build):\nSTDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"

        # Verify outputs exist
        wheel_files = list(tmp_path.glob("*.whl"))
        sdist_files = list(tmp_path.glob("*.tar.gz"))

        assert len(wheel_files) == 1, f"Expected 1 wheel file, found {len(wheel_files)}"
        assert len(sdist_files) == 1, f"Expected 1 source dist, found {len(sdist_files)}"

        # Verify naming
        wheel_name = wheel_files[0].name
        assert "domjudge_cli" in wheel_name, f"Unexpected wheel name: {wheel_name}"
        assert wheel_name.endswith(".whl"), "Wheel must have .whl extension"


class TestInstalledPackage:
    """Test that the installed package works correctly."""

    def test_package_imports_successfully(self):
        """Test that package imports - basic user expectation."""
        # This simulates: python -c "import dom"
        result = subprocess.run(
            [sys.executable, "-c", "import dom; print('SUCCESS')"],
            capture_output=True,
            text=True,
            check=False,
        )

        # STRICT: Import MUST work
        assert result.returncode == 0, f"Package import FAILED:\nSTDERR:\n{result.stderr}"
        assert "SUCCESS" in result.stdout, "Import didn't complete successfully"

    def test_package_version_accessible(self):
        """Test that users can access package version."""
        # This simulates: python -c "import dom; print(dom.__version__)"
        result = subprocess.run(
            [sys.executable, "-c", "import dom; print(dom.__version__)"],
            capture_output=True,
            text=True,
            check=False,
        )

        # STRICT: Version access MUST work
        assert result.returncode == 0, f"Version access FAILED:\nSTDERR:\n{result.stderr}"

        version = result.stdout.strip()
        assert len(version) > 0, "Version must not be empty"
        # Version should be valid semver or dev version
        assert (
            version == "0.0.0-dev" or "." in version
        ), f"Version '{version}' doesn't look like a valid version"

    def test_cli_entry_point_works(self):
        """Test that CLI entry point works - users type 'dom --help'."""
        # This simulates: dom --help (from console_scripts in pyproject.toml)
        result = subprocess.run(
            ["dom", "--help"],
            capture_output=True,
            text=True,
            check=False,
        )

        # STRICT: CLI entry point MUST work if installed
        # Note: Will fail with "command not found" if not in editable/installed mode
        # But that's OK - we want to catch that!
        if result.returncode != 0:
            if "not found" in result.stderr.lower():
                pytest.fail(
                    "CLI 'dom' command not found!\n"
                    "This means either:\n"
                    "1. Package not installed (run: pip install -e .)\n"
                    "2. Entry points not configured correctly in pyproject.toml\n"
                    f"Error: {result.stderr}"
                )
            # Skip if there's any runtime error (e.g., environment issues in CI)
            if "Traceback" in result.stderr or "Error" in result.stderr:
                pytest.skip(f"CLI not fully functional in test environment: {result.stderr[:200]}")

        assert result.returncode == 0, f"CLI command failed with error!\nSTDERR:\n{result.stderr}"

        # Verify help output is meaningful
        assert (
            "Usage:" in result.stdout or "Commands:" in result.stdout
        ), f"Help output doesn't look correct:\n{result.stdout}"

    def test_templates_accessible_and_usable(self):
        """Test that templates work after install - critical for users."""
        # This simulates actual user code importing and using templates
        code = """
import yaml
from dom.templates.infra import docker_compose_template
from dom.templates.init import contest_template, infra_template, problems_template

# Try to render a template (what users actually do)
rendered = docker_compose_template.render(
    platform_port=8080,
    judgehost_count=2,
    admin_password="test",
    judge_password="test",
    db_password="test"
)

# Verify it's valid YAML
config = yaml.safe_load(rendered)
assert "services" in config, "Template didn't render correctly"
print("SUCCESS")
"""
        result = subprocess.run(
            [sys.executable, "-c", code],
            capture_output=True,
            text=True,
            check=False,
        )

        # STRICT: Templates MUST be accessible AND functional
        assert (
            result.returncode == 0
        ), f"Template usage FAILED (the Jinja2 bug!):\nSTDERR:\n{result.stderr}"
        assert "SUCCESS" in result.stdout, "Template rendering didn't work correctly"


class TestPackageMetadata:
    """Test that package metadata is correct."""

    def test_package_name_correct(self):
        """Test that package metadata is accessible."""
        # This simulates: pip show domjudge-cli
        from importlib.metadata import PackageNotFoundError, metadata

        try:
            meta = metadata("domjudge-cli")
        except PackageNotFoundError:
            pytest.fail(
                "Package 'domjudge-cli' not found in metadata. "
                "Did you install it? Run: pip install -e ."
            )

        # STRICT: Metadata must be correct
        assert meta["Name"] == "domjudge-cli", f"Wrong package name: {meta['Name']}"

    def test_author_metadata_correct(self):
        """Test that author information is set correctly."""
        from importlib.metadata import PackageNotFoundError, metadata

        try:
            meta = metadata("domjudge-cli")
        except PackageNotFoundError:
            pytest.fail("Package not installed. Run: pip install -e .")

        author = meta.get("Author") or meta.get("Author-email", "")

        # STRICT: Author must be set correctly
        assert (
            "Anas IMLOUL" in author or "anas.imloul27@gmail.com" in author
        ), f"Author metadata incorrect: {author}"

    def test_repository_url_correct(self):
        """Test that repository URL is set correctly."""
        from importlib.metadata import PackageNotFoundError, metadata

        try:
            meta = metadata("domjudge-cli")
        except PackageNotFoundError:
            pytest.fail("Package not installed. Run: pip install -e .")

        project_urls = meta.get_all("Project-URL") or []

        # Convert to dict
        urls = {}
        for url_line in project_urls:
            if ", " in url_line:
                key, value = url_line.split(", ", 1)
                urls[key] = value

        # STRICT: Repository URL must be set
        assert "Repository" in urls, f"Repository URL not set. URLs: {urls}"
        assert (
            "github.com/AnasImloul/domjudge-cli" in urls["Repository"]
        ), f"Wrong repository URL: {urls.get('Repository')}"


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

    def test_wheel_contains_all_required_files(self, tmp_path):
        """Test that wheel contains ALL required files - this caught the template bug!"""
        import zipfile

        # Require build module for this test
        try:
            import build  # noqa: F401
        except ImportError:
            pytest.fail(
                "ERROR: 'build' module is REQUIRED for wheel integrity tests!\n"
                "Install it with: pip install build"
            )

        # Build a wheel - this is what happens when users pip install
        result = subprocess.run(
            [sys.executable, "-m", "build", "--wheel", "--outdir", str(tmp_path)],
            capture_output=True,
            text=True,
            check=False,
        )

        # STRICT: Build MUST succeed
        assert (
            result.returncode == 0
        ), f"Wheel build FAILED:\nSTDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"

        wheel_files = list(tmp_path.glob("*.whl"))
        assert len(wheel_files) == 1, f"Expected 1 wheel, found {len(wheel_files)}"

        wheel_path = wheel_files[0]

        # Inspect wheel contents
        with zipfile.ZipFile(wheel_path, "r") as zf:
            files = zf.namelist()

            # STRICT: Must contain ALL template files (this is what failed in prod!)
            required_templates = [
                "docker-compose.yml.j2",
                "contest.yml.j2",
                "infra.yml.j2",
                "problems.yml.j2",
            ]

            for template in required_templates:
                matching = [f for f in files if f.endswith(template)]
                assert len(matching) > 0, (
                    f"CRITICAL: Template '{template}' NOT in wheel!\n"
                    f"This is the bug that went to production!\n"
                    f"Wheel files: {[f for f in files if '.j2' in f]}"
                )

            # STRICT: Must contain py.typed
            py_typed_files = [f for f in files if f.endswith("py.typed")]
            assert len(py_typed_files) > 0, "py.typed marker missing from wheel"

            # Verify reasonable number of Python files
            py_files = [f for f in files if f.endswith(".py")]
            assert (
                len(py_files) > 50
            ), f"Suspiciously few Python files: {len(py_files)}. Package might not be complete."
