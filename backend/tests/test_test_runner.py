from contextlib import nullcontext
from pathlib import Path
import runpy
import subprocess
import sys
import tempfile


runner_path = Path(__file__).resolve().parents[2] / "scripts/test_backend.py"


def test_importing_backend_runner_does_not_start_another_pytest(monkeypatch):
    def reject_execution(*arguments, **options):
        raise AssertionError("Importing the runner must not execute tests")

    monkeypatch.setattr(subprocess, "run", reject_execution)
    monkeypatch.setattr(tempfile, "TemporaryDirectory", reject_execution)

    namespace = runpy.run_path(str(runner_path))

    assert callable(namespace["main"])


def test_backend_runner_limits_collection_and_isolates_data(monkeypatch, tmp_path):
    monkeypatch.setattr(tempfile, "TemporaryDirectory", lambda **options: nullcontext(str(tmp_path)))
    monkeypatch.setattr(sys, "argv", [str(runner_path), "-k", "feature"])
    monkeypatch.setenv("GLM_API_KEY", "not-a-real-key")
    calls = []

    def record_execution(command, **options):
        calls.append((command, options))
        return subprocess.CompletedProcess(command, 3)

    monkeypatch.setattr(subprocess, "run", record_execution)
    namespace = runpy.run_path(str(runner_path))

    assert namespace["main"]() == 3
    assert len(calls) == 1
    command, options = calls[0]
    assert command == [sys.executable, "-m", "pytest", "backend/tests", "-q", "-k", "feature"]
    assert options["env"]["DATABASE_PATH"] == str(tmp_path / "test.sqlite3")
    assert options["env"]["GLM_API_KEY"] == ""
    assert options["env"]["APP_ENV"] == "test"
