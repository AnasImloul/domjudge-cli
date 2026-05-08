# Contributing to dom-cli

Thanks for working on this project. This guide covers the architecture
and the steps to add a new CLI command end-to-end. For coding style
(ruff, mypy, bandit) and tests, see the `Makefile` — `make check` runs
everything.

## Setup

```sh
make setup       # install package + dev deps + pre-commit hooks
make check       # format, lint, typecheck, test
```

## Architecture

The codebase is split into four layers, with imports allowed only
top-down. The contracts are enforced by `import-linter` (`.importlinter`):

```
dom.cli            ← presentation: Typer commands, ui, decorators
   │
   ▼
dom.core.operations ← orchestration: declarative @operation steps
   │
   ▼
dom.core.services   ← business logic: knows HOW; owns I/O
   │
   ▼
dom.infrastructure  ← Docker, API client, secrets, templates
```

Two cross-cutting rules:

- **No reverse imports.** Services and infrastructure cannot see
  operations or CLI.
- **UI is `dom.cli`-only.** Anything outside `dom.cli` that wants to
  show something must return structured data; the CLI renders it.

Supporting packages (`dom.types`, `dom.utils`, `dom.validation`,
`dom.templates`, `dom.exceptions`) are leaf-style: they're consumed by
all layers and import nothing layer-specific.

### Roles

| Layer | What it does | What it must NOT do |
|---|---|---|
| `dom.cli` | Parse args, load config, render output, handle errors | Business logic, I/O, Docker calls |
| `dom.core.operations` | Sequence service calls into named `Step`s; build a `Plan`/`Steps` | Reach for `subprocess`, `DockerClient`, `requests`, files |
| `dom.core.services` | Talk to API/Docker/secrets; expose intent-named verbs | Touch `dom.ui`, import operations or CLI |
| `dom.infrastructure` | Concrete clients, retry, cache, templates | Know about contests/teams/problems as domain concepts |

The reference implementation of the operation→service split is the
infrastructure pipeline:
`dom.core.operations.infrastructure.apply.apply_infrastructure_op`
sequences `InfraService` verbs into named, progress-tracked steps.

## Adding a new CLI command

Suppose we want `dom contest freeze` — freeze the scoreboard of a
running contest. Wire it in five files:

### 1. Add a service method (`dom/core/services/contest/...`)

Services own the actual work. Either extend an existing service or
create a new one. The service receives the API client (or other deps)
in `__init__`:

```python
# dom/core/services/contest/scoreboard.py
from dom.core.services.protocols import DomJudgeAPIProtocol


class ScoreboardService:
    def __init__(self, client: DomJudgeAPIProtocol):
        self.client = client

    def freeze(self, contest_id: str) -> None:
        self.client.contests.freeze(contest_id)
```

### 2. Wrap it in an operation (`dom/core/operations/contest/...`)

Operations are decorated with `@operation` and return either a `Steps`
list (multi-step, progress-tracked) or a single value:

```python
# dom/core/operations/contest/freeze.py
from dom.core.operations.framework import Context, Step, Steps, operation
from dom.core.operations.wiring import wire_admin_api
from dom.core.services.contest.scoreboard import ScoreboardService
from dom.types.config.processed import DomJudgeConfig


@operation("Freeze contest scoreboard")
def freeze_contest_op(ctx: Context, config: DomJudgeConfig) -> Steps:
    api = wire_admin_api(config.infra, ctx.secrets)
    svc = ScoreboardService(api)
    return Steps(
        steps=[
            Step(f"Freeze contest {c.shortname}", lambda c=c: svc.freeze(c.shortname))
            for c in config.contests
        ],
        summary=f"Froze {len(config.contests)} contest(s)",
    )
```

### 3. Add the CLI command (`dom/cli/contest/...`)

The CLI loads config + secrets, then runs the operation:

```python
# dom/cli/contest/freeze.py
from pathlib import Path
import typer

from dom.cli.contest.helpers import load_dom_config_with_secrets
from dom.cli.decorators import add_global_options, cli_command
from dom.cli.validators import validate_file_path
from dom.core.operations import Context, run
from dom.core.operations.contest.freeze import freeze_contest_op


@add_global_options
@cli_command
def freeze_command(
    file: Path = typer.Option(
        None, "-f", "--file", help="Path to configuration YAML file",
        callback=validate_file_path,
    ),
    dry_run: bool = typer.Option(False, "--dry-run"),
    verbose: bool = False,
    no_color: bool = False,  # noqa: ARG001
) -> None:
    """Freeze scoreboards for all configured contests."""
    config, secrets = load_dom_config_with_secrets(file, verbose)
    run(
        freeze_contest_op(config),
        Context(secrets=secrets, dry_run=dry_run, verbose=verbose),
    )
```

### 4. Register it (`dom/cli/contest/__init__.py`)

```python
contest_command.command("freeze")(freeze_command)
```

The top-level `dom/cli/__init__.py` already wires `contest_command` to
`app`, so nothing else is needed there.

### 5. Test it

Three test layers, in order of preference:

- **Service unit tests** — mock the API client; test the verb's
  contract. See `tests/unit/services/test_problem_service.py` for the
  pattern.
- **Operation tests** — patch the service class; assert the step labels
  and order, plus that the right service methods get called. See
  `tests/unit/operations/test_infrastructure_apply.py`.
- **CLI integration tests** — use Typer's `CliRunner` to invoke the
  command. See `tests/integration/test_cli.py`.

Run `make test` (or `pytest`) before opening a PR. `make check` also
runs lint and typecheck.

## Common pitfalls

- **Don't import `dom.ui` from outside `dom.cli`.** Return data; let
  the CLI render. `import-linter` will fail the build if you do.
- **Don't put logic in operations.** If a Step lambda does anything
  beyond calling a service method, the logic belongs in the service.
- **Don't reach into `requests` / `subprocess` / `DockerClient` from
  operations.** That's the service layer's job. Operations get an
  injected client via `wire_admin_api(config.infra, ctx.secrets)`.
- **Avoid amending commits.** Pre-commit hooks will fail and roll back
  cleanly; create a new commit instead.

## Where things live

| Concern | Location |
|---|---|
| Typer command definitions | `dom/cli/<group>/<verb>.py` |
| Global CLI options + error handling | `dom/cli/decorators.py` |
| Operations (orchestration) | `dom/core/operations/<group>/<verb>.py` |
| Services (business logic) | `dom/core/services/<group>/...` |
| API client + retry + cache | `dom/infrastructure/api/` |
| Docker client | `dom/infrastructure/docker/` |
| Secrets | `dom/infrastructure/secrets/` |
| Domain types (Pydantic) | `dom/types/` |
| Cross-cutting helpers | `dom/utils/` |
| Validation rules | `dom/validation/` |
| Jinja templates | `dom/templates/` |
| Layering contracts | `.importlinter` |
