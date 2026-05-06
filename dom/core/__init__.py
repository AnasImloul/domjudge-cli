"""Core layer for DomJudge CLI.

This package is split into two sublayers with a strict boundary:

**`dom.core.operations`** — declarative orchestration.
    An *Operation* describes WHAT happens by enumerating named steps; a
    *Step*'s `execute()` is a thin one-liner that delegates to a service.
    Operations also build human-readable result messages and (when needed)
    invoke presenters in `_build_result`.

    Operations MUST NOT contain business logic, I/O, or infrastructure
    construction. If an `execute()` reaches for `subprocess`, `DockerClient`,
    `APIClientFactory`, or filesystem helpers, that logic belongs in a service.

**`dom.core.services`** — declarative business logic.
    A *Service* knows HOW. It owns the API client / Docker client / secrets
    interaction and exposes intent-named methods (`apply_contest`,
    `start_service`, `regenerate_compose`, `check_status`, etc.). Services
    may compose other services. Services MUST NOT import from
    `dom.core.operations` or `dom.cli` (enforced by import-linter).

The reference implementation of this split is the infrastructure pipeline:
`dom.core.services.infra.service.InfraService` exposes all infrastructure
verbs; `dom.core.operations.infrastructure.apply.ApplyInfrastructureOperation`
sequences them into named, progress-tracked steps.

Layering: `dom.cli` -> `dom.core.operations` -> `dom.core.services` ->
`dom.infrastructure`. Reverse imports are forbidden.
"""
