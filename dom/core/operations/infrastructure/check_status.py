"""Check infrastructure health status."""

from dom.core.operations.framework import Context, operation
from dom.core.services.infra.service import InfraService
from dom.types.infra import InfrastructureStatus


def _summary(status: InfrastructureStatus) -> str:
    return "Infrastructure is healthy" if status.is_healthy() else "Infrastructure has issues"


@operation("Check infrastructure status", summary=_summary)
def check_infra_status_op(ctx: Context) -> InfrastructureStatus:
    return InfraService(ctx.secrets).check_status()
