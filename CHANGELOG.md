# Changelog

All notable changes to this project are documented here.  
Format follows [Keep a Changelog](https://keepachangelog.com/). Versioning follows the project phases.

---

## [Unreleased]

### Phase 4 — Continue.dev Integration (PoC)
- [ ] Continue.dev configuration for local MCP server
- [ ] End-to-end test on Bash script target
- [ ] Document tested Continue.dev version

### Phase 3 — MCP Server & Security
- [ ] MCP server with ReAct protocol
- [ ] Bidirectional Scrubber DLP (Regex + TruffleHog entropy)
- [ ] Severity-based alert vs block policy
- [ ] Token counter (HuggingFace Tokenizers)
- [ ] SQLite telemetry schema + writer
- [ ] Unix Socket with strict permissions (chmod 600)

### Phase 2 — Orchestrator
- [ ] Full container lifecycle (provisioning → extraction → purge)
- [ ] Shadow Clone management
- [ ] Unified Diff validation + git apply
- [ ] Orchestrator integrity check at startup (hash)

### Phase 1 — Infrastructure
- [ ] Ubuntu 24.04 + nested virtualization setup
- [ ] Podman rootless installation and configuration
- [ ] Kata Containers runtime integration
- [ ] Alpine Linux sandbox image (hardened)
- [ ] cgroups v2 resource limits (2 vCPU / 2 GB RAM)
- [ ] Baseline TTFT benchmark on target hardware

---

## [0.0.1] — Project Initialization

### Added
- Project scoping document (`docs/cadrage.md`)
- Architecture documentation with Mermaid diagrams (`docs/architecture.md`)
- Repository structure and conventions (`CONTRIBUTING.md`, `.gitignore`)
