from __future__ import annotations

import os
from pathlib import Path
import subprocess
import sys
import tempfile


def main() -> int:
    project_root = Path(__file__).resolve().parents[1]
    with tempfile.TemporaryDirectory(prefix="asean-backend-tests-", ignore_cleanup_errors=True) as directory:
        runtime = Path(directory)
        environment = {
            **os.environ,
            "APP_ENV": "test",
            "SUPERADMIN_USERNAME": "backend_test_admin",
            "SUPERADMIN_PASSWORD": "backend-tests-only-not-production",
            "PYTHONPATH": str(project_root / "backend"),
            "DATABASE_PATH": str(runtime / "test.sqlite3"),
            "UPLOAD_DIR": str(runtime / "uploads"),
            "REPORT_DIR": str(runtime / "reports"),
            "ASSISTANT_KNOWLEDGE_DIR": str(runtime / "knowledge"),
            "DATA_DIR": str(project_root / "backend/data"),
            "RULES_DIR": str(project_root / "backend/rules"),
            "GLM_API_KEY": "",
            "DEEPSEEK_API_KEY": "",
            "MODEL_PROVIDER": "",
            "MONITORING_ENABLED": "false",
            "IFLYTEK_API_PASSWORD": "",
            "LLM_API_KEY": "",
            "GEMINI_API_KEY": "",
        }
        result = subprocess.run(
            [sys.executable, "-m", "pytest", "backend/tests", "-q", *sys.argv[1:]],
            cwd=project_root,
            env=environment,
            check=False,
        )
        return result.returncode


if __name__ == "__main__":
    sys.exit(main())
