# 🤖 CLI-Agent — Local Isolated Coding Agent

> A fully local, air-gapped AI coding agent with sandbox isolation.  
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

- **Code execution is isolated inside a hardened sandbox** (Podman rootless, Kata Containers roadmap), so generated code never runs on your host directly.
- **Secrets are scrubbed bidirectionally** before reaching the LLM and before any diff is applied.
- **The agent never touches your real repo** — it works on an ephemeral shadow clone stored in RAM (`/dev/shm`) and proposes changes as a diff for human validation.
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
│                        │  - Shadow Clone (RAM)        │  │
│  ┌──────────────┐      │  - Diff validation          │  │
│  │  Ollama      │      │  - git apply                │  │
│  │  deepseek-   │      └────────────┬────────────────┘  │
│  │  coder-v2    │                   │                   │
│  └──────┬───────┘                   │ stdio             │
│         │                           │                   │
│         │         ┌─────────────────▼────────────────┐  │
│         └────────►│          MCP Server              │  │
│                   │  - ReAct protocol (5 iterations) │  │
│                   │  - Scrubber DLP (in + out)       │  │
│                   │  - Token counter (tiktoken)      │  │
│                   │  - Telemetry → SQLite            │  │
│                   └─────────────────┬────────────────┘  │
│                                     │ crun (kata: todo) │
│            ┌────────────────────────▼────────────────┐  │
│            │         SANDBOX                         │  │
│            │  Podman rootless — hardened-agent-      │  │
│            │  sandbox:1.0 (Alpine 3.21, non-root)    │  │
│            │  No network — 2vCPU/2GB                 │  │
│            │  /workspace — Shadow Clone (rw, noexec) │  │
│            │  /docs      — Documentation (ro)        │  │
│            └─────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────┘
```

For a detailed interactive diagram, see [`docs/architecture.md`](docs/architecture.md).

---

## 🔧 Key Design Decisions

### Why Podman rootless?

Docker requires a root daemon — a persistent, privileged process that is a high-value attack target. Podman operates without a daemon and maps container UIDs to unprivileged host UIDs, significantly reducing the blast radius of any container escape.

### Why a Shadow Clone in RAM?

The agent mounts an ephemeral copy of the project in `/dev/shm` (tmpfs), never the original. This means:
- A catastrophic LLM hallucination cannot corrupt your git history.
- The `.git/` directory on the host is never exposed to the sandbox.
- The shadow clone is mounted `noexec` — nothing written by the agent can be executed directly on the host.
- Changes are only integrated after explicit human validation of the proposed diff.
- On teardown, the clone is wiped from RAM — no residue on disk.

### Why a hardened custom image?

The sandbox runs `localhost/hardened-agent-sandbox:1.0`, a minimal Alpine 3.21 image built locally:
- Non-root user `agent` (UID 1000)
- Only Python 3.12, pytest, and git — no `curl`, `wget`, or `nc`
- Read-only filesystem except `/workspace`

### Why Kata Containers? (roadmap)

Standard container runtimes share the host kernel. Kata Containers runs each sandbox inside a lightweight VM (using VT-x/AMD-V), providing hardware-level isolation. Currently blocked on Podman rootless + Kata 3.x compatibility — tracked in the roadmap.

### Why local token counting?

Before committing to any paid cloud API, it's critical to know the actual token cost per task type. The MCP server tracks `prompt_tokens` and `completion_tokens` per task/feature/project in a local SQLite database so you can make data-driven decisions about model selection and prompt optimization.

### Why a ReAct loop?

Instead of a single prompt → response cycle, the agent iterates: Thought → Action → Observation, up to 5 iterations. Available actions: `read_file`, `write_file`, `run_tests`, `task_complete`. This allows the agent to read context, make targeted edits, and verify its work before signaling completion.

---

## 📁 Project Structure

```
hardened-agentic-coder/
├── README.md
├── CONTRIBUTING.md
├── CHANGELOG.md
├── .gitignore
│
├── docs/
│   └── architecture.md     # Detailed architecture diagrams
│
├── orchestrator/
│   ├── main.py             # CLI entry point (Typer)
│   ├── lifecycle.py        # Container spin-up / teardown / actions
│   ├── reconciler.py       # Diff validation + git apply
│   └── requirements.txt
│
├── mcp-server/
│   ├── server.py           # MCP protocol + ReAct loop
│   ├── scrubber.py         # DLP middleware (in/out)
│   ├── token_counter.py    # tiktoken wrapper with lru_cache
│   ├── telemetry.py        # SQLite session logger
│   └── requirements.txt
│
└── sandbox/
    ├── Containerfile       # Hardened Alpine image definition
    └── kata-config.toml    # Kata Containers runtime config (roadmap)
```

---

## 🚀 Getting Started

### Prerequisites

- Ubuntu 24.04 LTS
- AMD/Intel CPU with VT-x/AMD-V enabled
- [Podman](https://podman.io/) ≥ 4.x (rootless mode)
- [Ollama](https://ollama.com/) with `deepseek-coder-v2:16b` pulled
- Python ≥ 3.11

### 1 — Validate your environment

```bash
# Verify virtualization is enabled (AMD)
cat /sys/module/kvm_amd/parameters/nested  # expect: 1
# or Intel:
cat /sys/module/kvm_intel/parameters/nested

# Verify Podman rootless
podman run --rm docker.io/library/alpine echo "podman ok"

# Start Podman socket
systemctl --user enable --now podman.socket

# Pull the model
ollama pull deepseek-coder-v2:16b
```

### 2 — Build the sandbox image

```bash
podman build -t localhost/hardened-agent-sandbox:1.0 -f sandbox/Containerfile .
```

### 3 — Install dependencies

```bash
# Orchestrator
cd orchestrator
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# MCP server
cd ../mcp-server
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 4 — Run the agent

```bash
cd orchestrator
source .venv/bin/activate

# Basic usage
python main.py --repo /path/to/your/repo --task "add type hints to all functions"

# With documentation
python main.py --repo /path/to/your/repo --docs /path/to/docs --task "refactor according to the API spec in /docs/api.md"

# With verbose ReAct loop
AGENT_VERBOSE=1 python main.py --repo /path/to/your/repo --task "fix the bug in auth.py"
```

---

## 🗺 Roadmap

| Phase | Description | Status |
|-------|-------------|--------|
| **Phase 1** | Ubuntu + Podman rootless setup & validation | ✅ Done |
| **Phase 2** | Python orchestrator — full container lifecycle | ✅ Done |
| **Phase 3** | MCP server — ReAct, scrubbing, token counting, telemetry | ✅ Done |
| **Phase 4** | Hardened sandbox image + docs volume + pipeline e2e | ✅ Done |
| **Phase 5** | Continue.dev integration | 🔲 Todo |
| **Phase 6** | Kata Containers — hardware-level isolation | 🔲 Todo |

---

## 📊 Observability

The MCP server writes telemetry to a local `telemetry.db` (SQLite):

| Column | Type | Description |
|--------|------|-------------|
| `session_id` | TEXT (PK) | Unique task identifier |
| `feature_tag` | TEXT (enum) | Task type (refactor, debug, feature, test) |
| `project_id` | TEXT | Associated project |
| `task` | TEXT | The actual task submitted (scrubbed) |
| `prompt_tokens` | INTEGER | Input tokens |
| `completion_tokens` | INTEGER | Output tokens |
| `started_at` | TIMESTAMP | Sandbox execution start |
| `ended_at` | TIMESTAMP | Sandbox execution end |

Target metrics:

- **Token Efficiency** — tokens / valid line of code
- **Success Rate** — % of diffs validated vs rejected
- **Resource Impact** — peak RAM/CPU per sandbox
- **Latency** — TTFT < 30s for ~2,000 token requests

---

## 🤝 Contributing

This is a solo portfolio project, but feedback and suggestions are welcome.  
See [`CONTRIBUTING.md`](CONTRIBUTING.md) for conventions.