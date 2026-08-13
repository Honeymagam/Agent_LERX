import subprocess
from pathlib import Path
from .safety import validate_command
from ..config import get_settings


def detect_test_command(root: Path) -> list[str] | None:
    if (root / "pytest.ini").exists() or (root / "pyproject.toml").exists() or list(root.glob("test*.py")) or (root / "tests").exists(): return ["python", "-m", "pytest", "-q"]
    if (root / "package.json").exists(): return ["npm", "test", "--", "--runInBand"]
    return None


def run_tests(root: Path) -> dict:
    command = detect_test_command(root)
    if not command: return {"status": "skipped", "command": "", "stdout": "No supported test framework detected", "stderr": "", "exit_code": 0}
    validate_command(command)
    try:
        proc = subprocess.run(command, cwd=root, text=True, capture_output=True, timeout=get_settings().execution_timeout_seconds, shell=False)
        return {"status": "passed" if proc.returncode == 0 else "failed", "command": " ".join(command), "stdout": proc.stdout[-20000:], "stderr": proc.stderr[-20000:], "exit_code": proc.returncode}
    except subprocess.TimeoutExpired as exc:
        return {"status": "failed", "command": " ".join(command), "stdout": str(exc.stdout or ""), "stderr": "Test timeout", "exit_code": 124}
