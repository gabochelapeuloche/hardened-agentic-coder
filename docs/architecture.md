# Architecture — CLI-Agent

This document details the architecture of CLI-Agent with interactive diagrams.

---

## 1. Component Overview

```mermaid
graph TB
    subgraph HOST["🖥️ Host — Ubuntu 24.04 LTS"]
        UI["VS Code\nContinue.dev"]
        ORCH["Orchestrator\nPython / Podman SDK"]
        MCP["MCP Server\nReAct Protocol"]
        LLM["Ollama\ndeepseek-coder-v2:16b"]
        DB[("telemetry.db\nSQLite")]

        subgraph SANDBOX["🔒 Sandbox — Kata Containers (Micro-VM)"]
            AGENT["Agent\nAlpine Linux"]
            CLONE["Shadow Clone\n(ephemeral)"]
            DOCS["Docs\n(read-only)"]
        end
    end

    UI -->|"user instruction"| MCP
    MCP -->|"ReAct loop"| LLM
    MCP -->|"stdio / Unix Socket"| AGENT
    AGENT -->|"read/write"| CLONE
    AGENT -->|"read"| DOCS
    ORCH -->|"podman run --runtime=kata"| SANDBOX
    ORCH -->|"extract diff"| CLONE
    MCP -->|"token count + logs"| DB
```

---

## 2. Agent Lifecycle (Sequence)

```mermaid
sequenceDiagram
    actor User
    participant Orch as Orchestrator
    participant MCP as MCP Server
    participant LLM as Ollama (LLM)
    participant SB as Sandbox (Micro-VM)

    User->>Orch: Trigger task (feature/fix)
    Orch->>Orch: git clone → Shadow Clone
    Orch->>SB: podman run --runtime=kata (cgroups: 2vCPU, 2GB)
    Orch->>MCP: Start session (session_id, feature_tag)

    loop ReAct Loop
        MCP->>LLM: Prompt (secrets scrubbed)
        LLM-->>MCP: Action (read / write / test)
        MCP->>SB: Execute tool on Shadow Clone
        SB-->>MCP: Tool result
        MCP->>MCP: Log tokens to telemetry.db
    end

    MCP->>Orch: Deliver Unified Diff
    Orch->>Orch: Validate diff integrity
    Orch->>Orch: git apply → agent/feature branch
    Orch->>User: PR ready for review
    Orch->>SB: Destroy micro-VM (zero persistence)
```

---

## 3. Security Layers (Defense in Depth)

```mermaid
graph LR
    subgraph L1["Layer 1 — Process Isolation"]
        A["Podman rootless\n--pid=private\n--ipc=private"]
    end
    subgraph L2["Layer 2 — Kernel Isolation"]
        B["Kata Containers\nMicro-VM\nVT-x / AMD-V"]
    end
    subgraph L3["Layer 3 — Network Isolation"]
        C["Air-gap\nNo networking\nDocs as read-only volume"]
    end
    subgraph L4["Layer 4 — Data Isolation"]
        D["Shadow Clone\nNo direct repo access\nNo .git/ exposure"]
    end
    subgraph L5["Layer 5 — Secret Protection"]
        E["Scrubber DLP\nBidirectional\nRegex + Entropy (TruffleHog)"]
    end
    subgraph L6["Layer 6 — Change Control"]
        F["Human validation\nUnified Diff\ngit apply on branch only"]
    end

    L1 --> L2 --> L3 --> L4 --> L5 --> L6
```

---

## 4. Scrubber DLP — Detection Policy

```mermaid
flowchart TD
    IN["Incoming token / diff"] --> SCAN["Scan\nRegex + Entropy"]
    SCAN --> SEV{Severity?}
    SEV -->|"High\n(known pattern + high entropy)"| BLOCK["🔴 BLOCK\nWorkflow halted\nUser alerted"]
    SEV -->|"Medium\n(possible false positive)"| ALERT["🟡 ALERT\nWorkflow continues\nWarning added to PR"]
    SEV -->|"None"| PASS["🟢 PASS\nToken forwarded"]
```

---

## 5. Telemetry Data Flow

```mermaid
graph LR
    MCP["MCP Server"]
    TC["Token Counter\nHuggingFace Tokenizers"]
    DB[("telemetry.db")]
    Q["Query / Dashboard\n(Continue.dev or CLI)"]

    MCP -->|"each exchange"| TC
    TC -->|"prompt_tokens\ncompletion_tokens\nsession_id\nfeature_tag\nproject_id\ntimestamps"| DB
    DB --> Q
```
