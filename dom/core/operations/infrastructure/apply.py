"""Deploy DOMjudge infrastructure (Docker containers + bootstrap)."""

from dom.core.operations.framework import Context, Step, Steps, operation
from dom.core.services.infra.service import InfraService
from dom.types.infra import InfraConfig


@operation("Deploy infrastructure")
def apply_infrastructure_op(ctx: Context, config: InfraConfig) -> Steps:
    svc = InfraService(ctx.secrets)
    return Steps(
        steps=[
            Step("Validate prerequisites", lambda: svc.validate_prerequisites(config.port)),
            Step("Generate compose file", lambda: svc.generate_compose_bootstrap(config)),
            Step("Start MariaDB", lambda: svc.start_service("mariadb")),
            Step("Start MySQL client", lambda: svc.start_service("mysql-client")),
            Step("Start DOMserver", lambda: svc.start_service("domserver")),
            Step("Wait for DOMserver to be healthy", svc.wait_domserver_healthy),
            Step("Fetch judgedaemon password", svc.fetch_and_store_judge_password),
            Step("Regenerate compose with real password", lambda: svc.regenerate_compose(config)),
            Step(
                f"Start {config.judges} judgehost(s)", lambda: svc.start_judgehosts(config.judges)
            ),
            Step("Configure admin password", lambda: svc.configure_admin_password(config)),
        ],
        summary=(
            f"Infrastructure ready at http://0.0.0.0:{config.port}"
            f" • {config.judges} judgehost(s) running"
        ),
    )
