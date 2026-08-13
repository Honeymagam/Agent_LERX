from pathlib import Path
import pytest
from app.services.repository import analyze_repository, retrieve
from app.services.safety import safe_path, validate_command


def test_analyzer_and_retrieval(tmp_path: Path):
    (tmp_path / "app.py").write_text("def authenticate(token):\n return token\n")
    (tmp_path / "requirements.txt").write_text("fastapi")
    summary = analyze_repository(tmp_path)
    assert summary["file_count"] == 2
    assert retrieve(tmp_path, "where is authentication implemented")[0]["path"] == "app.py"


def test_safety_blocks_escape_and_destructive_command(tmp_path: Path):
    with pytest.raises(ValueError): safe_path(tmp_path, "../outside")
    with pytest.raises(ValueError): validate_command(["rm", "-rf", "/"])
