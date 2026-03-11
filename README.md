# 🤖 CLI-Agent — Local Isolated Coding Agent

> A fully local, air-gapped AI coding agent with hardware-level sandbox isolation.  
> No data leaves your machine. Ever.

![Status](https://img.shields.io/badge/status-in_development-yellow)
![Stack](https://img.shields.io/badge/stack-Python%20%7C%20Podman%20%7C%20Kata%20Containers%20%7C%20MCP-blue)
![License](https://img.shields.io/badge/license-MIT-green)

---

## 🧭 Table of Contents

- [Why This Project](#-why-this-project)
- [Architecture Overview](#-architecture-overview)
- [Key Design Decisions](#-key-design-decisions)
- [Project Structure](#-project-structure)
- [Getting Started](#-getting-started)
- [Roadmap](#-roadmap)
- [Observability](#-observability)
- [Contributing](#-contributing)

---

## 💡 Why This Project

Most AI coding assistants (Copilot, Cursor, etc.) send your source code to remote APIs. For proprietary or sensitive codebases, this is a non-starter.

**CLI-Agent** is a fully local alternative that goes further than just running a model offline:

- **Code execution is isolated inside a micro-VM** (Kata Containers), so generated code never runs on your host directly.
- **Secrets are scrubbed bidirectionally** before reaching the LLM and before any diff is applied.
- **The agent never touches your real repo** — it works on an ephemeral shadow clone and proposes changes as a PR.
- **Token usage is tracked locally** so you can measure the real cost of every task before considering any cloud migration.

This project is built around a **defense-in-depth** philosophy: each layer assumes the previous one can fail.

---

## 🏗 Architecture Overview

```
┌─────────────────────────────────────────────────────────┐
│                        HOST                             │
│                                                         │
│  ┌──────────────┐      ┌─────────────────────────────┐  │
│  │  VS Code     │      │        Orchestrator         │  │
│  │ Continue.dev │◄────►│  (Python / Podman SDK)      │  │
│  └──────────────┘      │  - Lifecycle management     │  │
│                        │  - Shadow Clone             │  │
│  ┌──────────────┐      │  - Diff validation          │  │
│  │  Ollama      │      │  - git apply                │  │
│  │  deepseek-   │      └────────────┬────────────────┘  │
│  │  coder-v2    │                   │                   │
│  └──────┬───────┘                   │ stdio / Unix      │
│         │                           │ Socket            │
│         │         ┌─────────────────▼────────────────┐  │
│         └────────►│          MCP Server              │  │
│                   │  - ReAct protocol                │  │
│                   │  - Scrubber DLP (in + out)       │  │
│                   │  - Token counter                 │  │
│                   │  - Telemetry → SQLite            │  │
│                   └─────────────────┬────────────────┘  │
│                                     │ Kata runtime      │
│            ┌────────────────────────▼────────────────┐  │
│            │         SANDBOX (Micro-VM)              │  │
│            │  Podman rootless + Kata Containers      │  │
│            │  Alpine Linux — No network — 2vCPU/2GB  │  │
│            │  Shadow Clone (read/write)              │  │
│            │  Docs (read-only volume)                │  │
│            └─────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────┘
```

For a detailed interactive diagram, see [`docs/architecture.md`](docs/architecture.md).

---

## 🔧 Key Design Decisions

### Why Kata Containers instead of standard runc?

Standard container runtimes share the host kernel. A malicious or buggy generated script could exploit kernel vulnerabilities to escape the container. Kata Containers runs each sandbox inside a lightweight VM (using VT-x/AMD-V), providing hardware-level isolation. The performance overhead is acceptable for an interactive coding workflow.

### Why Podman rootless?

Docker requires a root daemon — a persistent, privileged process that is a high-value attack target. Podman operates without a daemon and maps container UIDs to unprivileged host UIDs, significantly reducing the blast radius of any container escape.

### Why a Shadow Clone instead of direct repo access?

The agent mounts an ephemeral copy of the project, never the original. This means:
- A catastrophic LLM hallucination cannot corrupt your git history.
- The `.git/` directory on the host is never exposed to the sandbox.
- Changes are only integrated after explicit human validation of the proposed diff.

### Why local token counting?

Before committing to any paid cloud API, it's critical to know the actual token cost per task type (refactoring, debugging, feature writing). The MCP server tracks `prompt_tokens` and `completion_tokens` per task/feature/project in a local SQLite database so you can make data-driven decisions about model selection and prompt optimization.

---

## 📁 Project Structure

```
cli-agent/
├── README.md
├── CONTRIBUTING.md
├── CHANGELOG.md
├── .gitignore
│
├── docs/
│   ├── cadrage.md          # Project scoping document (FR)
│   └── architecture.md     # Detailed architecture + Mermaid diagrams
│
├── orchestrator/
│   ├── main.py             # Entry point
│   ├── lifecycle.py        # Container spin-up / teardown
│   ├── reconciler.py       # Diff validation + git apply
│   └── requirements.txt
│
├── mcp-server/
│   ├── server.py           # MCP protocol + ReAct loop
│   ├── scrubber.py         # DLP middleware (in/out)
│   ├── token_counter.py    # HuggingFace tokenizer wrapper
│   ├── telemetry.py        # SQLite writer
│   └── requirements.txt
│
└── sandbox/
    ├── Containerfile       # Alpine-based image definition
    ├── kata-config.toml    # Kata Containers runtime config
    └── scripts/            # Agent-side tooling (read, write, test)
```

---

## 🚀 Getting Started

### Prerequisites

- Ubuntu 24.04 LTS
- AMD/Intel CPU with VT-x/AMD-V and nested virtualization enabled
- [Podman](https://podman.io/) ≥ 4.x (rootless mode)
- [Kata Containers](https://katacontainers.io/) ≥ 3.x
- [Ollama](https://ollama.com/) with `deepseek-coder-v2:16b` pulled
- Python ≥ 3.11
- VS Code + [Continue.dev](https://continue.dev/) extension

### Phase 1 — Validate your environment

```bash
# Verify nested virtualization is enabled
cat /sys/module/kvm_intel/parameters/nested  # expect: 1
# or for AMD:
cat /sys/module/kvm_amd/parameters/nested

# Validate Kata runtime
podman run --runtime=kata-runtime docker.io/library/hello-world

# Pull the model
ollama pull deepseek-coder-v2:16b
```

> Full setup instructions will be added as each phase is completed.

---

## 🗺 Roadmap

| Phase | Description | Status |
|-------|-------------|--------|
| **Phase 1** | Ubuntu + Kata Containers + Podman setup & validation | 🔲 Todo |
| **Phase 2** | Python orchestrator — full container lifecycle | 🔲 Todo |
| **Phase 3** | MCP server — scrubbing, token counting, telemetry | 🔲 Todo |
| **Phase 4** | Continue.dev integration — PoC on a Bash script | 🔲 Todo |

See [open issues](../../issues) for the detailed task breakdown per phase.

---

## 📊 Observability

The MCP server writes telemetry to a local `telemetry.db` (SQLite):

| Column | Type | Description |
|--------|------|-------------|
| `session_id` | TEXT (PK) | Unique task identifier |
| `feature_tag` | TEXT (enum) | Task type (refactor, debug, feature, test) |
| `project_id` | TEXT | Associated project |
| `prompt_tokens` | INTEGER | Input tokens |
| `completion_tokens` | INTEGER | Output tokens |
| `started_at` | TIMESTAMP | Sandbox execution start |
| `ended_at` | TIMESTAMP | Sandbox execution end |

Target metrics:

- **Token Efficiency** — tokens / valid line of code
- **Success Rate** — % of PRs validated vs rejected
- **Resource Impact** — peak RAM/CPU per micro-VM
- **Latency** — TTFT < 30s for ~2,000 token requests

---

## 🤝 Contributing

This is a solo portfolio project, but feedback and suggestions are welcome.  
See [`CONTRIBUTING.md`](CONTRIBUTING.md) for conventions.
