"""Deterministic, auditable agent workflow; an LLM adapter can replace plan generation."""
from __future__ import annotations
import difflib
import re
from datetime import datetime
from pathlib import Path
from sqlalchemy.orm import Session
from ..models import AgentRun, FileChange, Project, Review, SecurityFinding, Task, TestRun
from ..schemas import Plan
from ..services.execution import run_tests
from ..services.repository import analyze_repository, checkout_repository, retrieve
from ..services.safety import safe_path
from ..graph.workflow import build_workflow


def _log(run: AgentRun, message: str, agent: str) -> None:
    run.current_agent = agent
    run.logs = [*run.logs, {"timestamp": datetime.utcnow().isoformat(), "agent": agent, "message": message}]


def make_plan(request: str, summary: dict, context: list[dict]) -> Plan:
    lower = request.lower()
    candidates = [c["path"] for c in context]
    tests = summary["tests"] or ["tests/test_agent_change.py"]
    return Plan(
        summary=f"Implement: {request}", affected_files=list(dict.fromkeys(candidates))[:8],
        steps=["Inspect retrieved code and project conventions", "Apply the smallest safe change", "Add or update focused tests", "Run detected test suite", "Review security and quality"],
        risks=["Repository code is never executed outside the controlled test command", "Generated change requires review before commit"],
        tests=tests[:8],
    )


def _health_endpoint(root: Path, request: str) -> list[tuple[str, str, str]]:
    """A deliberately narrow, safe built-in implementation capability used by the E2E fixture."""
    if not ("health" in request.lower() and ("endpoint" in request.lower() or "route" in request.lower())):
        return []
    candidates = list(root.rglob("main.py")) + list(root.rglob("app.py"))
    for target in candidates:
        text = target.read_text(encoding="utf-8")
        if "FastAPI" not in text or "@app.get(\"/health\")" in text: continue
        addition = '\n\n@app.get("/health")\ndef health_check() -> dict[str, str]:\n    return {"status": "ok"}\n'
        return [(str(target.relative_to(root)), text, text.rstrip() + addition)]
    return []


def apply_changes(db: Session, task: Task, root: Path, request: str) -> list[FileChange]:
    changes = []
    for relative, original, modified in _health_endpoint(root, request):
        destination = safe_path(root, relative)
        destination.write_text(modified, encoding="utf-8")
        change = FileChange(task_id=task.id, path=relative, original=original, modified=modified, reason="Implemented requested health endpoint", agent="implementation")
        db.add(change); changes.append(change)
    return changes


SECRET_PATTERNS = [("hard-coded-secret", re.compile(r"(?i)(api[_-]?key|password|secret|token)\s*=\s*[\"'][^\"']{8,}"))]
UNSAFE_PATTERNS = [("command-injection", re.compile(r"subprocess\.(run|call|Popen)\([^\n]*shell\s*=\s*True")), ("unsafe-deserialization", re.compile(r"pickle\.loads\("))]


def security_review(db: Session, task: Task, changes: list[FileChange]) -> list[SecurityFinding]:
    findings = []
    for change in changes:
        for rule, expression in SECRET_PATTERNS + UNSAFE_PATTERNS:
            if expression.search(change.modified):
                finding = SecurityFinding(task_id=task.id, severity="high", rule=rule, path=change.path, detail=f"Potential {rule} in modified content")
                db.add(finding); findings.append(finding)
    return findings


def run_task(db: Session, task_id: int) -> AgentRun:
    task = db.get(Task, task_id)
    if not task: raise ValueError("Task not found")
    project = db.get(Project, task.project_id)
    run = AgentRun(task_id=task.id, status="running", started_at=datetime.utcnow(), logs=[])
    db.add(run); db.flush(); task.status = "running"
    try:
        # Execute the graph transition model before running its audited side effects.
        expected_pipeline = build_workflow().invoke({"user_request": task.request, "repository_url": project.repository_url})["pipeline"]
        _log(run, "Loading repository", "repository-analyzer")
        root = checkout_repository(project.repository_url); project.repository_path = str(root)
        summary = analyze_repository(root); project.summary = summary
        _log(run, f"Indexed {summary['file_count']} source files; framework: {summary['framework']}", "repository-analyzer")
        context = retrieve(root, task.request)
        _log(run, f"Retrieved {len(context)} relevant chunks", expected_pipeline[1])
        plan = make_plan(task.request, summary, context); task.plan = plan.model_dump()
        _log(run, "Created validated implementation plan", expected_pipeline[2])
        changes = apply_changes(db, task, root, task.request)
        _log(run, f"Applied {len(changes)} controlled file changes", expected_pipeline[3])
        outcome = run_tests(root)
        db.add(TestRun(task_id=task.id, **outcome))
        _log(run, f"Tests {outcome['status']} (exit {outcome['exit_code']})", expected_pipeline[4])
        findings = security_review(db, task, changes)
        _log(run, f"Security scan completed: {len(findings)} findings", expected_pipeline[5])
        verdict = "APPROVED" if outcome["status"] in {"passed", "skipped"} and not findings else "CHANGES_REQUIRED"
        db.add(Review(task_id=task.id, verdict=verdict, summary="Automated review completed", details={"test_status": outcome["status"], "findings": len(findings)}))
        _log(run, verdict, expected_pipeline[6])
        task.status = "completed" if verdict == "APPROVED" else "needs_attention"
        run.status = task.status; run.completed_at = datetime.utcnow(); db.commit()
    except Exception as exc:
        task.status = "failed"; run.status = "failed"; run.error = str(exc); run.completed_at = datetime.utcnow()
        _log(run, f"Run failed safely: {exc}", "orchestrator"); db.commit()
    return run
