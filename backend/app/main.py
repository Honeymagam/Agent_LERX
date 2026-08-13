from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .api import router
from .database import Base, engine
from .database import SessionLocal
from .auth import ensure_initial_admin

app = FastAPI(title="AI SWE Agent", version="0.1.0")
app.add_middleware(CORSMiddleware, allow_origins=["http://localhost:3000"], allow_methods=["*"], allow_headers=["*"])
app.include_router(router)

@app.on_event("startup")
def startup():
    Base.metadata.create_all(engine())
    with SessionLocal() as db: ensure_initial_admin(db)

@app.get("/health")
def health(): return {"status": "ok"}
