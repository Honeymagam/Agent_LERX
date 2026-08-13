# AI SWE Agent

An auditable autonomous software-engineering platform. It loads a GitHub or local repository, uses targeted source retrieval, creates a validated plan, performs controlled edits, runs tests, scans changed code, and records a review.

## Architecture

`FastAPI API → workflow (analyzer → retrieval → planner → implementation → tests → security → reviewer) → PostgreSQL`

The backend keeps run logs, file before/after states, test transcripts, security findings, and review outcomes. Repository test commands are allowlisted and executed with timeouts; production should run the test runner in a separate locked-down sandbox container before enabling arbitrary repositories.

## Run with Docker

```bash
cp .env.example .env
docker compose up --build
```

Open `http://localhost:3000`. The API docs are at `http://localhost:8000/docs`.

## Local development

```bash
cd backend
python -m venv .venv
.venv/bin/pip install -r requirements.txt
python -m uvicorn app.main:app --reload
python -m pytest -q
```

On Windows activate the virtual environment with `.venv\\Scripts\\Activate.ps1`.

## Current implementation scope

The workflow is fully persisted and tested end-to-end for adding a FastAPI health endpoint. The implementation node is intentionally narrow and deterministic for that supported task type; attach an approved structured LLM adapter to expand code generation. This prevents unreviewed model output from becoming an unrestricted file-write or shell-execution capability.

Environment variables live in `.env.example`; never commit `.env` or tokens. Git branches/commits are deliberately not created automatically.
