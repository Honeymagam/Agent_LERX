from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session
from .database import get_db
from .models import AgentRun, FileChange, Project, Review, SecurityFinding, Task, TestRun
from .schemas import AnalyzeRequest, ProjectCreate, TaskCreate
from .agents.workflow import run_task
from .services.repository import analyze_repository, checkout_repository, repository_name

router = APIRouter(prefix="/api")

@router.post("/projects", status_code=201)
def create_project(body: ProjectCreate, db: Session = Depends(get_db)):
    existing = db.scalar(select(Project).where(Project.repository_url == body.repository_url))
    if existing: return {"id": existing.id, "repository_url": existing.repository_url}
    project = Project(name=body.name or repository_name(body.repository_url), repository_url=body.repository_url)
    db.add(project); db.commit(); db.refresh(project)
    return {"id": project.id, "repository_url": project.repository_url}

@router.post("/analyze")
def analyze(body: AnalyzeRequest, db: Session = Depends(get_db)):
    project = db.get(Project, body.project_id)
    if not project: raise HTTPException(404, "Project not found")
    try:
        root = checkout_repository(project.repository_url); project.repository_path = str(root); project.summary = analyze_repository(root); db.commit()
        return project.summary
    except Exception as exc: raise HTTPException(400, str(exc))

@router.post("/tasks", status_code=201)
def create_task(body: TaskCreate, db: Session = Depends(get_db)):
    if not db.get(Project, body.project_id): raise HTTPException(404, "Project not found")
    task = Task(project_id=body.project_id, request=body.request); db.add(task); db.commit(); db.refresh(task)
    return {"id": task.id, "status": task.status}

@router.post("/tasks/{task_id}/run", status_code=202)
def start_run(task_id: int, background: BackgroundTasks, db: Session = Depends(get_db)):
    if not db.get(Task, task_id): raise HTTPException(404, "Task not found")
    background.add_task(_run_in_session, task_id)
    return {"task_id": task_id, "status": "scheduled"}

def _run_in_session(task_id: int):
    from .database import SessionLocal
    with SessionLocal() as db: run_task(db, task_id)

@router.get("/tasks/{task_id}")
def task_detail(task_id: int, db: Session = Depends(get_db)):
    task = db.get(Task, task_id)
    if not task: raise HTTPException(404, "Task not found")
    return {"id": task.id, "project_id": task.project_id, "request": task.request, "status": task.status, "plan": task.plan}

@router.get("/tasks/{task_id}/status")
def status(task_id: int, db: Session = Depends(get_db)):
    run = db.scalar(select(AgentRun).where(AgentRun.task_id == task_id).order_by(AgentRun.id.desc()))
    return {"status": "queued"} if not run else {"id": run.id, "status": run.status, "current_agent": run.current_agent, "error": run.error}

@router.get("/tasks/{task_id}/logs")
def logs(task_id: int, db: Session = Depends(get_db)):
    run = db.scalar(select(AgentRun).where(AgentRun.task_id == task_id).order_by(AgentRun.id.desc()))
    return [] if not run else run.logs

@router.get("/tasks/{task_id}/changes")
def changes(task_id: int, db: Session = Depends(get_db)): return [{"path": c.path, "reason": c.reason, "original": c.original, "modified": c.modified} for c in db.scalars(select(FileChange).where(FileChange.task_id == task_id))]

@router.get("/tasks/{task_id}/tests")
def tests(task_id: int, db: Session = Depends(get_db)): return [{"status": t.status, "command": t.command, "stdout": t.stdout, "stderr": t.stderr, "exit_code": t.exit_code} for t in db.scalars(select(TestRun).where(TestRun.task_id == task_id))]

@router.get("/tasks/{task_id}/review")
def review(task_id: int, db: Session = Depends(get_db)):
    review = db.scalar(select(Review).where(Review.task_id == task_id)); findings = db.scalars(select(SecurityFinding).where(SecurityFinding.task_id == task_id)).all()
    return {"review": None if not review else {"verdict": review.verdict, "summary": review.summary, "details": review.details}, "security_findings": [{"severity": x.severity, "rule": x.rule, "path": x.path, "detail": x.detail} for x in findings]}
