# DOMjudge CLI Architecture

## Overview

This document describes the architectural patterns and design principles used in the DOMjudge CLI tool.

## Core Principles

1. **Clean Architecture** - Clear separation between layers with defined dependencies
2. **SOLID Principles** - Single responsibility, dependency inversion, etc.
3. **Domain-Driven Design** - Business logic organized by domain concepts
4. **Explicit is Better Than Implicit** - Clear, self-documenting code

## Layer Architecture

The codebase follows a strict layered architecture:

```
┌─────────────────────────────────────────┐
│              CLI Layer                   │
│         (dom/cli/*.py)                   │
│  User interface, argument parsing        │
└──────────────┬──────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────┐
│          Operations Layer                │
│      (dom/core/operations/*.py)          │
│  High-level workflows, orchestration     │
└──────────────┬──────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────┐
│           Services Layer                 │
│       (dom/core/services/*.py)           │
│  Business logic, domain services         │
└──────────────┬──────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────┐
│       Infrastructure Layer               │
│   (dom/infrastructure/api/*.py)          │
│  HTTP API, Docker, file system           │
└─────────────────────────────────────────┘
```

**Dependency Rule**: Higher layers can depend on lower layers, but never the reverse.

## Service Layer Patterns

The service layer is organized into three distinct patterns:

### 1. Entity Services

Entity services manage a specific type of entity (Problem, Team, etc.) and inherit from `Service[TEntity]`.

**Characteristics:**
- Inherit from `Service[TEntity]` and optionally `BulkOperationMixin[TEntity]`
- Provide CRUD operations with business logic
- Use `ServiceContext` for dependencies
- Return `ServiceResult[T]` for error handling
- Located in `dom/core/services/<entity>/`

**Examples:**
- `ProblemService` - Manages problem entities
- `TeamService` - Manages team entities

**Structure:**
```python
class ProblemService(Service[ProblemPackage], BulkOperationMixin[ProblemPackage]):
    """Entity service for managing problems."""
    
    def entity_name(self) -> str:
        return "Problem"
    
    def create(self, entity: ProblemPackage, context: ServiceContext) -> ServiceResult[ProblemPackage]:
        """Add a problem to a contest."""
        # Business logic here
```

### 2. Orchestrator Services

Orchestrator services coordinate multiple entity services to implement complex workflows.

**Characteristics:**
- Standalone classes (don't inherit from `Service[TEntity]`)
- Coordinate multiple entity services
- Implement complex multi-step workflows
- Handle cross-cutting concerns (transactions, error handling, concurrency)
- Located in `dom/core/services/<domain>/`

**Examples:**
- `ContestApplicationService` - Orchestrates contest creation with problems and teams
- Uses `ProblemService`, `TeamService`, and `ContestStateComparator`

**Structure:**
```python
class ContestApplicationService:
    """Orchestrator service for applying contest configurations."""
    
    def __init__(self, client, secrets: SecretsProvider):
        self.client = client
        self.problem_service = ProblemService(client)
        self.team_service = TeamService(client)
        self.state_comparator = ContestStateComparator(client)
    
    def apply_contest(self, contest: ContestConfig) -> str:
        """Apply a complete contest configuration."""
        # Orchestrate multiple services
```

### 3. State Comparison Services

State comparison services compare desired state with current state to enable idempotent operations.

**Characteristics:**
- Standalone classes (don't inherit from `Service[TEntity]`)
- Stateless comparisons (no side effects)
- Return structured change sets
- Enable idempotent operations and safe updates
- Located in `dom/core/services/<domain>/state.py`

**Examples:**
- `ContestStateComparator` - Compares desired contest config with API state
- `InfraStateComparator` - Compares desired infra config with Docker state

**Structure:**
```python
class ContestStateComparator:
    """State comparison service for contest configurations."""
    
    def compare_contest(
        self, desired: ContestConfig, current: dict | None = None
    ) -> ContestChangeSet:
        """Compare desired state with current state."""
        # Return structured change set
```

## Infrastructure vs Core Services

There are **two distinct layers** of services with different responsibilities:

### Infrastructure API Services (`dom.infrastructure.api.services.*`)

**Purpose:** Thin wrappers around HTTP API calls

**Characteristics:**
- Named with `*APIService` suffix (e.g., `ProblemAPIService`, `TeamAPIService`)
- Handle serialization, caching, rate limiting
- No business logic - pure HTTP operations
- Return raw API responses or simple models

**Examples:**
```python
class ProblemAPIService:
    """Infrastructure API service for managing problems."""
    
    def add_to_contest(self, contest_id: str, problem_package: ProblemPackage) -> str:
        """HTTP POST to add problem to contest."""
        # Direct HTTP API call
```

### Core Domain Services (`dom.core.services.*`)

**Purpose:** Business logic and orchestration

**Characteristics:**
- Use infrastructure services internally
- Enforce domain rules and invariants
- Implement business workflows
- Return domain-specific results

**Examples:**
```python
class ProblemService(Service[ProblemPackage]):
    """Core domain service for managing problems."""
    
    def create(self, entity: ProblemPackage, context: ServiceContext) -> ServiceResult[ProblemPackage]:
        """Add problem with business logic and error handling."""
        # Business logic + calls to infrastructure API service
        problem_id = self.client.problems.add_to_contest(context.contest_id, entity)
```

## Directory Structure

### By Domain

```
dom/
├── cli/                    # CLI layer
│   ├── helpers.py          # CLI-specific utilities
│   ├── contest/            # Contest CLI commands
│   └── infrastructure/     # Infrastructure CLI commands
│
├── core/                   # Core business logic
│   ├── operations/         # High-level workflows
│   ├── services/           # Domain services
│   │   ├── base.py         # Base service abstractions
│   │   ├── contest/        # Contest domain services
│   │   │   ├── apply.py    # ContestApplicationService
│   │   │   ├── state.py    # ContestStateComparator
│   │   │   └── plan.py     # Contest planning
│   │   ├── problem/        # Problem domain services
│   │   ├── team/           # Team domain services
│   │   └── infra/          # Infrastructure domain services
│   └── config/             # Configuration management
│
├── infrastructure/         # Infrastructure layer
│   ├── api/                # HTTP API clients
│   │   ├── client.py       # Base HTTP client
│   │   ├── domjudge.py     # Main API facade
│   │   └── services/       # Infrastructure API services
│   │       ├── problems.py # ProblemAPIService
│   │       ├── teams.py    # TeamAPIService
│   │       └── ...
│   ├── docker/             # Docker integration
│   └── secrets/            # Secrets management
│
├── domain/                 # Domain logic
│   ├── team_id_generator.py
│   └── problem_labeling.py
│
├── security/               # Security utilities
│   └── password_hasher.py
│
├── shared/                 # Shared utilities
│   ├── filesystem.py       # Generic filesystem utilities
│   └── prompts.py          # Generic prompt functions
│
└── types/                  # Type definitions
    ├── api/                # API models
    ├── config/             # Configuration models
    └── ...
```

## Import Rules (Enforced by import-linter)

### Layering Contracts

1. **CLI → Operations → Services → Infrastructure**
   - CLI can import from Operations, Services, Infrastructure
   - Operations can import from Services, Infrastructure
   - Services can import from Infrastructure
   - Infrastructure cannot import from Services, Operations, CLI

2. **Shared Utilities**
   - `dom.shared` can be imported by any layer (layer-agnostic)
   - `dom.cli.helpers` can only be imported by CLI layer

3. **Domain Logic**
   - `dom.domain` contains business logic (team IDs, problem labeling)
   - Can be used by Services layer

4. **Security**
   - `dom.security` contains security utilities (password hashing)
   - Used by Infrastructure layer

## Key Design Patterns

### 1. Service Context Pattern

Services receive dependencies through a `ServiceContext` rather than individual parameters:

```python
@dataclass
class ServiceContext:
    client: DomJudgeAPI
    contest_id: str | None = None
    contest_shortname: str | None = None
    team_group_id: str | None = None
```

**Benefits:**
- Easy to add new context without changing signatures
- Clear dependency injection
- Context can be transformed for nested operations

### 2. Result Pattern

Services return `ServiceResult[T]` instead of raising exceptions:

```python
@dataclass
class ServiceResult(Generic[TOutput]):
    success: bool
    data: TOutput | None = None
    error: Exception | None = None
    message: str = ""
    created: bool = False
```

**Benefits:**
- Explicit error handling
- Can accumulate results for bulk operations
- Supports partial failures

### 3. State Comparison Pattern

Before applying changes, compare desired state with current state:

```python
change_set = state_comparator.compare_contest(desired_config)

if change_set.change_type == ChangeType.CREATE:
    # Create new contest
elif change_set.has_changes:
    # Apply updates
else:
    # No changes needed
```

**Benefits:**
- Idempotent operations
- Safe live changes
- Clear change visibility

### 4. Facade Pattern (API Client)

The `DomJudgeAPI` class provides a clean facade over infrastructure services:

```python
class DomJudgeAPI:
    def __init__(self, base_url: str, username: str, password: str):
        self.client = DomJudgeClient(base_url, username, password)
        
        # Compose infrastructure API services
        self.contests = ContestAPIService(self.client)
        self.problems = ProblemAPIService(self.client)
        self.teams = TeamAPIService(self.client)
```

**Benefits:**
- Single point of access
- Service composition
- Dependency injection

## Testing Strategy

### Unit Tests
- Test individual services in isolation
- Mock infrastructure dependencies
- Focus on business logic

### Integration Tests
- Test service interactions
- Use test doubles for external APIs
- Verify workflows

### End-to-End Tests
- Test complete CLI workflows
- Use Docker for DOMjudge instance
- Verify real-world scenarios

## Migration Guidelines

When adding new features:

1. **Determine the pattern:**
   - Managing an entity? → Entity Service (inherit from `Service[TEntity]`)
   - Coordinating services? → Orchestrator Service (standalone class)
   - Comparing state? → State Comparison Service (standalone class)

2. **Choose the layer:**
   - HTTP API call? → Infrastructure API Service (`*APIService`)
   - Business logic? → Core Domain Service

3. **Follow conventions:**
   - Use `ServiceContext` for dependencies
   - Return `ServiceResult[T]` for operations
   - Add comprehensive docstrings with architecture pattern
   - Follow layering rules (check with import-linter)

4. **Document:**
   - Add class docstring explaining the pattern
   - Document complex business rules
   - Update this ARCHITECTURE.md if introducing new patterns

## Best Practices

### Do's ✅

- Use type hints everywhere
- Return `ServiceResult[T]` from service methods
- Pass dependencies through `ServiceContext`
- Keep infrastructure services thin (no business logic)
- Use state comparison for idempotent operations
- Document architecture patterns in class docstrings

### Don'ts ❌

- Don't put business logic in infrastructure services
- Don't violate layering rules (checked by import-linter)
- Don't create circular dependencies
- Don't use global state or singletons
- Don't inherit from `Service[TEntity]` for orchestrators or comparators
- Don't duplicate utility code (use `dom.shared` or `dom.domain`)

## Validation

Run these commands to validate architecture:

```bash
# Run all checks (format, lint, typecheck, test)
make check

# Check layering rules
make lint-imports

# Run tests
make test

# Type check
make typecheck
```

## References

- [Clean Architecture by Robert C. Martin](https://blog.cleancoder.com/uncle-bob/2012/08/13/the-clean-architecture.html)
- [Domain-Driven Design](https://martinfowler.com/bliki/DomainDrivenDesign.html)
- [SOLID Principles](https://en.wikipedia.org/wiki/SOLID)
