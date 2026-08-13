# AI SWE Command

AI SWE Command is an auditable software-engineering agent platform. It loads a GitHub or local repository, retrieves relevant code, produces a validated plan, applies controlled changes, runs tests, scans the modified code for security signals, and records a final review.

The interface is a blue gaming-style command center with a public landing page, secure operator login, live pipeline telemetry, diffs, test output, security findings, and a final review verdict.

## Features

- Repository loading from GitHub HTTPS/SSH URLs or a local path
- Repository analysis: source inventory, language/dependency detection, test discovery, and framework hints
- Targeted retrieval over chunked source files instead of sending an entire repository to an LLM
- Explicit LangGraph pipeline: analyzer → retriever → planner → implementation → testing → security → review
- Audited file changes with before/after content and reason
- Guarded test execution with command checks and timeouts
- JWT-protected API; task and project endpoints require an authenticated operator
- PostgreSQL/pgvector-ready Docker Compose deployment; SQLite works for local backend development

## Quick start with Docker

1. Copy the example environment file:

   ```cmd
   copy .env.example .env
   ```

2. Change `SECRET_KEY` and `INITIAL_ADMIN_PASSWORD` in `.env` before exposing the application beyond your computer.

3. Build and start the stack:

   ```cmd
   docker compose up --build
   ```

4. Open the application at [http://localhost:3000](http://localhost:3000). API documentation is available at [http://localhost:8000/docs](http://localhost:8000/docs).

For later starts, use:

```cmd
docker compose up
```

## First login

The backend creates an initial administrator on startup using these environment variables:

```text
INITIAL_ADMIN_EMAIL=admin@example.com
INITIAL_ADMIN_PASSWORD=change-this-before-production
```

Use those values on the sign-in screen only for local development. Set a strong unique password in `.env` before deploying.

## Operator flow

1. Open the landing page and select **Enter Command Center**.
2. Sign in as an operator.
3. Enter a GitHub repository URL or a local repository path.
4. Describe the engineering task.
5. Launch the agent and inspect the pipeline, mission log, file changes, test results, and review outcome.

## Architecture

```text
React/Vite command center
          │ JWT
          ▼
FastAPI API ──► LangGraph lifecycle
                   │
                   ├─ Repository analyzer + retrieval
                   ├─ Planner + controlled implementation
                   ├─ Test runner + timeout policy
                   └─ Security scan + reviewer
          │
          ▼
PostgreSQL + pgvector
```

The system persists projects, tasks, agent runs, file changes, test runs, security findings, and reviews. The backend includes a deterministic end-to-end implementation capability for adding a FastAPI health-check endpoint.

## Local backend development

```cmd
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload
pytest -q
```

On macOS/Linux, activate the environment with `source .venv/bin/activate`.

## Environment variables

See [.env.example](.env.example) for all configuration. Important settings include:

| Variable | Purpose |
| --- | --- |
| `SECRET_KEY` | Signs JWT sessions; use a long random value. |
| `INITIAL_ADMIN_EMAIL` | Initial local operator email. |
| `INITIAL_ADMIN_PASSWORD` | Initial local operator password. |
| `DATABASE_URL` | PostgreSQL in Docker, SQLite for simple local development. |
| `GITHUB_TOKEN` | Optional token for private repository access. |
| `MAX_DEBUG_ITERATIONS` | Maximum autonomous debugging attempts. |
| `EXECUTION_TIMEOUT_SECONDS` | Maximum duration of a test command. |

Never commit `.env`, tokens, or credentials.

## Safety and current scope

This project records every supported file edit and blocks unsafe path traversal and destructive command patterns. Tests have timeouts and commands are validated before execution.

The implementation agent is deliberately narrow and deterministic in this version, supporting the tested FastAPI health-check task. A production deployment should add a validated structured LLM adapter and run repository code in a separate, locked-down sandbox with restricted network, filesystem, and resource permissions. Do not treat the current test runner as safe for arbitrary untrusted repositories.
