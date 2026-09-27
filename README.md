# NanamiGopher

A local-first general-purpose Agent that can operate a browser, orchestrate tools, keep durable task state, request approval for side effects, and extend through local Skills or MCP.

## Overview

NanamiGopher provides a unified interface for AI agent interactions, featuring:

- **Go Gateway** – REST/WebSocket boundary and gRPC client
- **Python Agent** – LangChain/LangGraph-based AI orchestration
- **Browser Runtime** – Playwright sessions governed by the same tool policy
- **Skill / MCP** – Declarative local instructions and process-isolated tool extensions
- **Vue.js Frontend** – Modern web dashboard
- **SQLite** – Phase-one relational storage; vector indexes are planned

## Tech Stack

| Component  | Technology                          |
| ---------- | ----------------------------------- |
| Backend    | Go 1.22, Gin, gRPC, WebSocket       |
| Agent      | Python 3.12, LangChain, LangGraph   |
| Frontend   | Vue 3, Vite, TypeScript             |
| Database   | SQLite (relational)                  |
| Infra      | Electron local supervisor            |
| Observability | Structured application events    |

## Quick Start

### Prerequisites

- Go 1.22+
- Python 3.12+
- Node.js 20+
- Docker & Docker Compose (optional, for containerized deployment)

### Local Development

```bash
# 1. Install dependencies
make setup

# 2. Start development servers (Go + Python + Vue)
make dev

# Or use the script directly:
bash scripts/dev.sh
```

Services will be available at:

- Go API: http://localhost:8080
- Python Agent: gRPC on localhost:8081
- Vue Frontend: http://localhost:5173

### Container Deployment (planned)

```bash
# Build and start all services
make docker-build
make docker-up

# Or deploy directly:
bash scripts/deploy.sh development
```

### Testing

```bash
make test
```

Runs Go tests, Python pytest, and Vue Vitest.

## Configuration

Configuration is managed through YAML files in the `config/` directory:

| File              | Purpose                   |
| ----------------- | ------------------------- |
| `config.yaml`     | Base configuration        |
| `config.dev.yaml` | Development overrides     |
| `config.prod.yaml`| Production overrides      |

Key configuration sections:

- **models** – LLM provider defaults; the UI persists multiple Workspace model profiles
- **workspace** – root exposed through the read-only file and Git Diff sidebar
- **permissions** – Circuit breaker, blocked command patterns
- **storage** – SQLite path (vector indexes are not part of the core release)
- **browser** – lazy Playwright/Chromium runtime
- **skills / mcp** – local Skill directories and trusted stdio MCP servers
- **observability** – OpenTelemetry, LangFuse integration

Pass the selected file explicitly with `--config` or `NANAMI_CONFIG`; environment variables override selected runtime values.

## Project Structure

```
├── config/            # YAML configuration files
├── deploy/            # Deployment configs (nginx, etc.)
├── gateway/           # Go Gateway module
│   └── cmd/gateway/   # Main entry point
├── python/            # Python agent backend
│   └── agent/         # Agent core modules
├── web/               # Vue.js frontend
├── scripts/           # Build and utility scripts
│   ├── setup.sh       # Environment initialization
│   ├── build.sh       # Multi-component build
│   ├── dev.sh         # Development server launcher
│   ├── run_tests.sh   # Test runner
│   └── deploy.sh      # Docker deployment
├── Dockerfile         # Multi-stage Docker build
├── docker-compose.yml # Service orchestration
├── Makefile           # Common commands
├── go.work            # Go workspace definition
├── proto/             # Canonical gRPC contract
├── python/pyproject.toml
└── gateway/go.mod
```

## Development Guide

### Adding a Local Skill

1. Create a skill file in `~/.nanamigopher/skills/` or `./skills/`
2. Add YAML front matter with `name`, `description`, optional `version` and `kind`, followed by auditable instructions
3. Restart the agent to pick up the new skill

Local Skills do not execute package code. Signed package installation, commands, grants and rollback are planned lifecycle features; executable integrations currently use deployment-configured MCP servers.

### Modifying Models

Start the application and open **Settings → Models**. The runtime supports OpenAI, Anthropic, Ollama, and OpenAI-compatible endpoints such as LM Studio or vLLM. You can save several named profiles and mark one as the default for new conversations. Each chat can then select a profile, response-speed budget, and execution approval mode directly above the composer.

The assistant name shown in conversations can be changed under **Settings → General**. It is stored as a per-user Workspace preference and does not rename the project or Workspace.

For headless deployments, configure `NANAMI_MODEL_PROVIDER`, `NANAMI_MODEL_NAME`, `NANAMI_MODEL_BASE_URL`, and the matching `OPENAI_API_KEY` or `ANTHROPIC_API_KEY`. API keys entered in the UI are isolated per model profile in the operating-system keychain and are never returned by the API.

The model field includes current recommendations for OpenAI, Anthropic, DeepSeek and Ollama. It remains editable rather than acting as a closed list, so any model exposed by an OpenAI-compatible endpoint can be used without changing code.

The right sidebar lazily lists the current Workspace, previews text files, and shows staged, unstaged, and untracked Git changes as per-file diffs. Set `NANAMI_WORKSPACE_ROOT` when the runtime should expose a directory other than its launch workspace.

### Phase-one examples

Run the examples from the repository root after `make setup`:

```bash
# Review a Python file with the default local Ollama endpoint.
PYTHONPATH=python .venv/bin/python -m examples.code_review python/agent/core.py

# Summarize a UTF-8 document with the same endpoint.
PYTHONPATH=python .venv/bin/python -m examples.document_summary docs/design/SystemDesign.md

# Or use an OpenAI-compatible endpoint.
PYTHONPATH=python .venv/bin/python -m examples.document_summary docs/design/SystemDesign.md \
  --provider openai_compatible --model your-model-id --base-url http://127.0.0.1:1234/v1
```

Both examples require a reachable model. For OpenAI or Anthropic, prefer the provider environment variable for the API key.

### Security

The circuit breaker blocks dangerous shell patterns by default. Configure
`permissions.circuit_breaker.blocked_patterns` to customize.

## License

MIT License – see [LICENSE](LICENSE) for details.
