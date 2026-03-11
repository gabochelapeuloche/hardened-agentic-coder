# Contributing to CLI-Agent

This is a solo portfolio project. External contributions are not expected, but issues, feedback, and suggestions are welcome.

This document serves primarily as a reference for consistent development practices.

---

## Commit Convention

This project follows [Conventional Commits](https://www.conventionalcommits.org/).

### Format

```
<type>(<scope>): <short description>

[optional body]

[optional footer]
```

### Types

| Type | When to use |
|------|-------------|
| `feat` | A new feature or capability |
| `fix` | A bug fix |
| `infra` | Infrastructure / environment setup (Podman, Kata, etc.) |
| `sec` | Security-related change (scrubber, isolation, secrets) |
| `obs` | Observability / telemetry (token counting, SQLite, logging) |
| `refactor` | Code restructuring without behavior change |
| `test` | Adding or updating tests |
| `docs` | Documentation only |
| `chore` | Tooling, deps, config (no production code change) |

### Scopes

| Scope | Component |
|-------|-----------|
| `orchestrator` | Python orchestrator |
| `mcp` | MCP server |
| `sandbox` | Containerfile, Kata config, Alpine scripts |
| `telemetry` | SQLite schema, token counter |
| `scrubber` | DLP middleware |
| `ci` | GitHub Actions workflows |
| `docs` | Documentation files |

### Examples

```bash
# Good
infra(sandbox): add Kata runtime config with cgroups v2 limits
feat(mcp): implement bidirectional scrubber with TruffleHog entropy
sec(scrubber): add severity-based alert vs block policy
obs(telemetry): create telemetry.db schema with session and token fields
fix(orchestrator): handle empty diff edge case in reconciler
docs: add architecture Mermaid diagrams

# Bad — too vague
fix: bug fix
update stuff
wip
```

---

## Branching Strategy

```
main          ← stable, tagged releases only
└── dev       ← integration branch
    ├── phase/1-infra
    ├── phase/2-orchestrator
    ├── phase/3-mcp
    └── phase/4-integration
```

- Work happens on `phase/*` branches.
- Merge to `dev` when a phase acceptance criterion is met.
- Merge to `main` and tag a release at each phase completion.

### Branch naming

```
phase/<N>-<short-description>     # phase work
fix/<short-description>           # bug fixes
docs/<short-description>          # documentation
```

---

## GitHub Issues

Each roadmap phase has a corresponding milestone. Tasks within a phase are tracked as issues.

Label convention:

| Label | Meaning |
|-------|---------|
| `phase:1` → `phase:4` | Associated phase |
| `security` | Security-related task |
| `observability` | Telemetry / monitoring task |
| `blocked` | Waiting on external dependency |
| `good first issue` | Well-scoped, low-risk task |

---

## Code Style

- **Python** : [Black](https://black.readthedocs.io/) formatter, [Ruff](https://docs.astral.sh/ruff/) linter.
- **Line length** : 100 characters.
- **Type hints** : required on all public functions.
- **Docstrings** : Google style.

```bash
# Format and lint before committing
black .
ruff check .
```

---

## Security Policy

If you discover a security issue, please open a **private** GitHub security advisory rather than a public issue.
