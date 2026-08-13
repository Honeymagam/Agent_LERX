from pathlib import Path

BLOCKED_COMMANDS = ("rm -rf", "del /", "format ", "mkfs", ":(){", "shutdown", "reboot")


def safe_path(root: Path, relative: str) -> Path:
    candidate = (root / relative).resolve()
    if root.resolve() not in candidate.parents and candidate != root.resolve():
        raise ValueError("Path escapes repository workspace")
    return candidate


def validate_command(command: list[str]) -> None:
    joined = " ".join(command).lower()
    if any(token in joined for token in BLOCKED_COMMANDS):
        raise ValueError("Command rejected by execution policy")
