from datetime import datetime
from pydantic import BaseModel, Field, HttpUrl


class ProjectCreate(BaseModel):
    repository_url: str = Field(min_length=1, max_length=2048)
    name: str | None = Field(default=None, max_length=120)


class TaskCreate(BaseModel):
    project_id: int
    request: str = Field(min_length=3, max_length=10000)


class Plan(BaseModel):
    summary: str
    affected_files: list[str] = []
    steps: list[str] = []
    risks: list[str] = []
    tests: list[str] = []


class RunStatus(BaseModel):
    id: int
    task_id: int
    status: str
    current_agent: str | None
    started_at: datetime | None
    completed_at: datetime | None
    error: str | None


class TaskDetail(BaseModel):
    id: int
    project_id: int
    request: str
    status: str
    plan: Plan | None = None


class AnalyzeRequest(BaseModel):
    project_id: int
