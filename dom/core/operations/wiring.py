"""Wiring helpers for operations.

Operations depend on services, and services depend on a DOMjudge API
client. The factory that builds the client lives in the infrastructure
layer; this module is the single place the operations layer touches it,
so services never have to. Services accept an already-built client
typed against ``DomJudgeAPIProtocol`` and stay decoupled from
infrastructure construction.
"""

from __future__ import annotations

from dom.core.services.protocols import DomJudgeAPIProtocol
from dom.infrastructure.api.factory import APIClientFactory
from dom.types.infra import InfraConfig
from dom.types.secrets import SecretsProvider


def wire_admin_api(infra: InfraConfig, secrets: SecretsProvider) -> DomJudgeAPIProtocol:
    """Build an admin API client from infra config + secrets.

    Centralizes the one factory call that used to be sprinkled across
    operations and (incorrectly) the services layer. Returns the
    protocol so call sites depend on shape, not on the concrete
    ``DomJudgeAPI`` class.
    """
    return APIClientFactory().create_admin_client(infra, secrets)
