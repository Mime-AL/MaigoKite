# NanamiGopher

An AI-powered agent platform with a multi-language architecture combining Go, Python, and Vue.js.

## Overview

NanamiGopher provides a unified interface for AI agent interactions, featuring:

- **Go API** – High-performance REST/gRPC backend
- **Python Agent** – LangChain/LangGraph-based AI orchestration
- **Vue.js Frontend** – Modern web dashboard
- **ChromaDB** – Vector storage for semantic memory

## Tech Stack

| Component  | Technology                          |
| ---------- | ----------------------------------- |
| Backend    | Go 1.22, Gin, gRPC, WebSocket       |
| Agent      | Python 3.12, LangChain, LangGraph   |
| Frontend   | Vue 3, Vite, TypeScript             |
| Database   | SQLite (relational), ChromaDB (vector) |
| Infra      | Docker Compose, Nginx               |
| Observability | OpenTelemetry, LangFuse          |

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
- Python Agent: http://localhost:8081
- Vue Frontend: http://localhost:5173

### Docker Deployment

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

- **models** – LLM providers, fallback order, embedding settings
- **permissions** – Circuit breaker, blocked command patterns
- **memory** – SQLite path, vector database provider
- **observability** – OpenTelemetry, LangFuse integration

Environment-specific configs override the base config automatically based on `APP_ENV`.

## Project Structure

```
├── config/            # YAML configuration files
├── deploy/            # Deployment configs (nginx, etc.)
├── go/                # Go API server
│   └── cmd/api/       # Main entry point
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
├── pyproject.toml     # Python project config
└── go.mod             # Go module definition
```

## Development Guide

### Adding a New Skill

1. Create a skill file in `~/.nanamigopher/skills/` or `./skills/`
2. Define the skill manifest with name, description, and command spec
3. Restart the agent to pick up the new skill

### Modifying Models

Edit `config/config.yaml` under `models.chat` and `models.embedding` sections.
The local fallback chain is: `ollama -> lm_studio -> vllm`.

### Security

The circuit breaker blocks dangerous shell patterns by default. Configure
`permissions.circuit_breaker.blocked_patterns` to customize.

## License

MIT License – see [LICENSE](LICENSE) for details.
