import hashlib
import os
import re
import shutil
from pathlib import Path
from git import Repo
from ..config import get_settings

IGNORED = {".git", "node_modules", ".venv", "venv", "dist", "build", "__pycache__", ".next", "coverage"}
SOURCE_SUFFIXES = {".py", ".js", ".ts", ".tsx", ".jsx", ".go", ".rs", ".java", ".rb", ".php", ".cs", ".md", ".yml", ".yaml", ".json"}


def repository_name(url: str) -> str:
    clean = url.rstrip("/")
    return clean.rsplit("/", 1)[-1].removesuffix(".git") or "repository"


def validate_url(url: str) -> None:
    if url.startswith(("https://github.com/", "git@github.com:")) or Path(url).is_dir():
        return
    raise ValueError("Repository must be a GitHub HTTPS/SSH URL or an existing local path")


def checkout_repository(url: str) -> Path:
    validate_url(url)
    source = Path(url)
    if source.is_dir():
        return source.resolve()
    digest = hashlib.sha256(url.encode()).hexdigest()[:12]
    target = get_settings().workspace_root / f"{repository_name(url)}-{digest}"
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists():
        return target
    Repo.clone_from(url, target, depth=1)
    return target


def analyze_repository(root: Path) -> dict:
    files: list[str] = []
    languages: dict[str, int] = {}
    manifests: list[str] = []
    tests: list[str] = []
    for path in root.rglob("*"):
        if any(part in IGNORED for part in path.parts) or not path.is_file() or path.suffix.lower() not in SOURCE_SUFFIXES:
            continue
        rel = path.relative_to(root).as_posix()
        if path.stat().st_size > 1_000_000:
            continue
        files.append(rel)
        suffix = path.suffix.lower().lstrip(".") or "text"
        languages[suffix] = languages.get(suffix, 0) + 1
        if path.name in {"pyproject.toml", "requirements.txt", "package.json", "go.mod", "Cargo.toml", "pom.xml"}:
            manifests.append(rel)
        if re.search(r"(^|/)(test|tests|__tests__)(/|$)|(^|_)test_", rel, re.I):
            tests.append(rel)
    framework = "unknown"
    content = "\n".join(files + manifests).lower()
    if "fastapi" in content or "requirements.txt" in content and any("main.py" in f for f in files): framework = "FastAPI/Python"
    elif "next.config" in content or "next.config" in content: framework = "Next.js"
    elif "package.json" in content: framework = "Node.js"
    return {"root": str(root), "files": files[:5000], "file_count": len(files), "languages": languages,
            "manifests": manifests, "tests": tests[:500], "framework": framework}


def code_chunks(root: Path, max_chars: int = 1800) -> list[dict]:
    chunks = []
    for rel in analyze_repository(root)["files"]:
        path = root / rel
        try: text = path.read_text(encoding="utf-8", errors="ignore")
        except OSError: continue
        for start in range(0, len(text), max_chars):
            body = text[start:start + max_chars]
            if body.strip(): chunks.append({"path": rel, "start_line": text[:start].count("\n") + 1, "end_line": text[:start + len(body)].count("\n") + 1, "content": body})
    return chunks


def retrieve(root: Path, query: str, limit: int = 8) -> list[dict]:
    terms = set(re.findall(r"[a-zA-Z_]{3,}", query.lower()))
    ranked = []
    for chunk in code_chunks(root):
        haystack = (chunk["path"] + " " + chunk["content"]).lower()
        score = sum(term in haystack for term in terms)
        if score: ranked.append((score, chunk))
    return [item for _, item in sorted(ranked, key=lambda pair: pair[0], reverse=True)[:limit]]
