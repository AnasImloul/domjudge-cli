"""End-to-end tests for template loading and rendering.

These tests ensure that templates are properly packaged and accessible
in both development and installed environments, and that they render
correct, valid output.
"""

import pytest
import yaml
from jinja2 import Template, UndefinedError


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
    """Test that templates render valid, correct output."""

    def test_docker_compose_template_renders_valid_yaml(self):
        """Test docker-compose template renders valid YAML with correct structure."""
        from dom.templates.infra import docker_compose_template

        rendered = docker_compose_template.render(
            container_prefix="dom-cli",
            platform_port=12345,
            judgehost_count=2,
            admin_password="test_admin_pass",
            judgedaemon_password="test_judge_pass",
            db_password="test_db_pass",
        )

        # Must be valid YAML
        compose_data = yaml.safe_load(rendered)
        assert compose_data is not None

        # Validate structure
        assert "services" in compose_data
        services = compose_data["services"]

        # Required services must exist
        assert "mariadb" in services
        assert "domserver" in services
        assert "mysql-client" in services

        # Validate mariadb service
        mariadb = services["mariadb"]
        assert mariadb["image"] == "mariadb"
        assert mariadb["container_name"] == "dom-cli-mariadb"
        assert "MYSQL_DATABASE=domjudge" in mariadb["environment"]
        assert any("MYSQL_PASSWORD=" in env for env in mariadb["environment"])
        # MariaDB should NOT expose ports to allow multiple deployments
        assert "ports" not in mariadb, "MariaDB should not expose ports to host"

        # Validate domserver service
        domserver = services["domserver"]
        assert domserver["image"] == "domjudge/domserver:8.2.0"
        assert domserver["container_name"] == "dom-cli-domserver"
        assert "12345:80" in domserver["ports"]
        assert any("MYSQL_HOST=dom-cli-mariadb" in env for env in domserver["environment"])

        # Validate judgehosts
        judgehost_services = [k for k in services if k.startswith("judgehost-")]
        assert len(judgehost_services) == 2
        for i in range(1, 3):
            judgehost_name = f"judgehost-{i}"
            assert judgehost_name in services
            judgehost = services[judgehost_name]
            assert judgehost["image"] == "domjudge/judgehost:8.2.0"
            assert judgehost["container_name"] == f"dom-cli-{judgehost_name}"

    def test_docker_compose_template_fails_without_required_params(self):
        """Test template fails gracefully when required parameters are missing."""
        from dom.templates.infra import docker_compose_template

        # Should fail without required parameters
        with pytest.raises((UndefinedError, TypeError)):
            docker_compose_template.render()

    def test_contest_template_renders_valid_yaml(self):
        """Test contest template renders valid YAML with correct structure."""
        from dom.templates.init import contest_template

        rendered = contest_template.render(
            name="ACM ICPC 2024",
            shortname="icpc2024",
            start_time="2024-06-15T09:00:00",
            duration="5:00:00",
            penalty_time="20",
            allow_submit=True,
            teams="teams.csv",
            delimiter=",",
            rows="2-50",
            name_column=2,
            affiliation_column=3,
            country_column=4,
        )

        # Must be valid YAML
        config_data = yaml.safe_load(rendered)
        assert config_data is not None

        # Validate structure
        assert "contests" in config_data
        contests = config_data["contests"]
        assert isinstance(contests, list)
        assert len(contests) >= 1

        # Validate contest data
        contest = contests[0]
        assert contest["name"] == "ACM ICPC 2024"
        assert contest["shortname"] == "icpc2024"
        assert contest["start_time"] == "2024-06-15T09:00:00"
        assert contest["duration"] == "5:00:00"
        assert contest["penalty_time"] == 20
        assert contest["allow_submit"] is True

        # Validate required sections
        assert "problems" in contest
        assert "teams" in contest

    def test_infra_template_renders_valid_yaml(self):
        """Test infra template renders valid YAML with correct structure."""
        from dom.templates.init import infra_template

        rendered = infra_template.render(
            port=8080,
            judges=4,
            password="test_password",
        )

        # Must be valid YAML
        config_data = yaml.safe_load(rendered)
        assert config_data is not None

        # Validate structure
        assert "infra" in config_data
        infra = config_data["infra"]

        # Validate fields
        assert infra["port"] == 8080
        assert infra["judges"] == 4

    def test_infra_template_with_different_values(self):
        """Test infra template with various valid values."""
        from dom.templates.init import infra_template

        # Test with minimum values
        rendered = infra_template.render(port=80, judges=1, password="test")
        config_data = yaml.safe_load(rendered)
        assert config_data["infra"]["port"] == 80
        assert config_data["infra"]["judges"] == 1

        # Test with large values
        rendered = infra_template.render(port=65535, judges=10, password="test")
        config_data = yaml.safe_load(rendered)
        assert config_data["infra"]["port"] == 65535
        assert config_data["infra"]["judges"] == 10

    def test_problems_template_renders_valid_yaml(self):
        """Test problems template renders valid YAML with correct structure."""
        from dom.templates.init import problems_template

        rendered = problems_template.render(
            archive="problems/graph-problem-42$linux.zip",
            platform="Polygon",
            color="#FF5733",
        )

        # Must be valid YAML - the template renders a list directly
        config_data = yaml.safe_load(rendered)
        assert config_data is not None
        assert isinstance(config_data, list)
        assert len(config_data) >= 1

        # Validate problem data
        problem = config_data[0]
        assert problem["archive"] == "problems/graph-problem-42$linux.zip"
        assert problem["platform"] == "Polygon"
        assert problem["color"] == "#FF5733"

    def test_problems_template_color_format(self):
        """Test that problems template accepts valid hex colors."""
        from dom.templates.init import problems_template

        # Test various valid hex colors
        colors = ["#000000", "#FFFFFF", "#FF5733", "#abc123"]
        for color in colors:
            rendered = problems_template.render(
                archive="test.zip",
                platform="DOMjudge",
                color=color,
            )
            config_data = yaml.safe_load(rendered)
            assert config_data[0]["color"] == color


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
