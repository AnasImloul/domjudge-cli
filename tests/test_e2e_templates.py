"""End-to-end tests for template loading and rendering.

These tests ensure that templates are properly packaged and accessible
in both development and installed environments.
"""

from jinja2 import Template


class TestTemplateLoading:
    """Test that all templates can be loaded successfully."""

    def test_infra_docker_compose_template_loads(self):
        """Test that docker-compose template can be loaded."""
        from dom.templates.infra import docker_compose_template

        assert docker_compose_template is not None
        assert isinstance(docker_compose_template, Template)
        assert docker_compose_template.name == "infra/docker-compose.yml.j2"

    def test_init_contest_template_loads(self):
        """Test that contest init template can be loaded."""
        from dom.templates.init import contest_template

        assert contest_template is not None
        assert isinstance(contest_template, Template)
        assert contest_template.name == "init/contest.yml.j2"

    def test_init_infra_template_loads(self):
        """Test that infra init template can be loaded."""
        from dom.templates.init import infra_template

        assert infra_template is not None
        assert isinstance(infra_template, Template)
        assert infra_template.name == "init/infra.yml.j2"

    def test_init_problems_template_loads(self):
        """Test that problems init template can be loaded."""
        from dom.templates.init import problems_template

        assert problems_template is not None
        assert isinstance(problems_template, Template)
        assert problems_template.name == "init/problems.yml.j2"

    def test_all_templates_exported(self):
        """Test that all templates are exported from their modules."""
        from dom.templates import infra, init

        # Check infra module exports
        assert hasattr(infra, "docker_compose_template")
        assert "docker_compose_template" in infra.__all__

        # Check init module exports
        assert hasattr(init, "contest_template")
        assert hasattr(init, "infra_template")
        assert hasattr(init, "problems_template")
        assert "contest_template" in init.__all__
        assert "infra_template" in init.__all__
        assert "problems_template" in init.__all__


class TestTemplateRendering:
    """Test that templates can be rendered with valid data."""

    def test_docker_compose_template_renders(self):
        """Test docker-compose template renders without errors."""
        from dom.templates.infra import docker_compose_template

        rendered = docker_compose_template.render(
            platform_port=12345,
            judgehost_count=2,
            admin_password="test_password",
            judge_password="judge_password",
            db_password="db_password",
        )

        assert rendered is not None
        assert "domserver:" in rendered
        assert "mariadb:" in rendered
        assert "judgehost" in rendered
        assert "12345" in rendered

    def test_contest_template_renders(self):
        """Test contest init template renders without errors."""
        from dom.templates.init import contest_template

        rendered = contest_template.render(
            name="Test Contest",
            shortname="test2024",
            start="2024-01-01T00:00:00",
            duration="5:00:00",
            penalty_time="20",
            allow_submit=True,
        )

        assert rendered is not None
        assert "test2024" in rendered
        assert "5:00:00" in rendered
        assert "Test Contest" in rendered

    def test_infra_template_renders(self):
        """Test infra init template renders without errors."""
        from dom.templates.init import infra_template

        rendered = infra_template.render(
            port=12345,
            judges=3,
        )

        assert rendered is not None
        assert "port:" in rendered
        assert "12345" in rendered
        assert "judges:" in rendered
        assert "3" in rendered

    def test_problems_template_renders(self):
        """Test problems init template renders without errors."""
        from dom.templates.init import problems_template

        rendered = problems_template.render(
            archive="problems/test.zip",
            platform="Polygon",
            color="#FF0000",
        )

        assert rendered is not None
        assert "problems/test.zip" in rendered
        assert "Polygon" in rendered
        assert "#FF0000" in rendered


class TestTemplateCache:
    """Test that template caching works correctly."""

    def test_templates_are_cached(self):
        """Test that templates are cached and return same instance."""
        from dom.templates.infra import docker_compose_template as template1
        from dom.templates.infra import docker_compose_template as template2

        # Should be the exact same object due to caching
        assert template1 is template2

    def test_template_get_function_caches(self):
        """Test that the get() function properly caches templates."""
        from dom.templates.base import get

        template1 = get("infra/docker-compose.yml.j2")
        template2 = get("infra/docker-compose.yml.j2")

        assert template1 is template2
