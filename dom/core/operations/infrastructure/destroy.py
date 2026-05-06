"""Destroy DOMjudge infrastructure (containers, optionally volumes)."""

from dom.core.operations.framework import Context, Step, Steps, operation
from dom.core.services.infra.service import InfraService


@operation("Destroy infrastructure")
def destroy_infrastructure_op(ctx: Context, remove_volumes: bool = False) -> Steps:
    svc = InfraService(ctx.secrets)
    label = (
        "Stop containers and remove volumes (PERMANENT)"
        if remove_volumes
        else "Stop all containers"
    )
    summary = (
        "All containers stopped • Volumes deleted permanently"
        if remove_volumes
        else "All containers stopped • Volumes preserved"
    )
    return Steps(
        steps=[Step(label, lambda: svc.destroy(remove_volumes=remove_volumes))],
        summary=summary,
    )
