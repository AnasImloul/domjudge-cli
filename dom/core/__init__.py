"""Core layer for DomJudge CLI.

This package is split into two sublayers with a strict boundary:

**`dom.core.operations`** — declarative orchestration.
    An *operation* is a function decorated with ``@operation`` that returns
    either a list of named ``Step``\\s (multi-step) or a result value
    (single-step). Operations sequence service calls and shape the success
    line; they MUST NOT contain business logic, I/O, or infrastructure
    construction. If an operation reaches for ``subprocess``, ``DockerClient``,
    ``APIClientFactory``, or filesystem helpers, that logic belongs in a
    service.

**`dom.core.services`** — declarative business logic.
    A *Service* knows HOW. It owns the API client / Docker client / secrets
    interaction and exposes intent-named methods (``apply_contest``,
    ``start_service``, ``regenerate_compose``, ``check_status``, etc.).
    Services may compose other services. Services MUST NOT import from
    ``dom.core.operations`` or ``dom.cli`` (enforced by import-linter).

The reference implementation of this split is the infrastructure pipeline:
``dom.core.services.infra.service.InfraService`` exposes all infrastructure
verbs; ``dom.core.operations.infrastructure.apply.apply_infrastructure_op``
sequences them into named, progress-tracked steps.

Layering: ``dom.cli`` -> ``dom.core.operations`` -> ``dom.core.services`` ->
``dom.infrastructure``. Reverse imports are forbidden.
"""
