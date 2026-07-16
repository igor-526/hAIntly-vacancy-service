import os
import subprocess
import sys
from pathlib import Path

RUNTIME_ENVIRONMENT_VARIABLES = (
    "HH_APP_TOKEN",
    "HH_API_URL",
    "HH_USER_AGENT",
    "CELERY_BROKER_URL",
    "CELERY_RESULT_BACKEND",
    "DICTIONARY_LOCK_URL",
    "VACANCY_DICTIONARY_MAX_AGE_HOURS",
    "PROFILE_SERVICE_URL",
)


def test_pytest_collection_without_runtime_environment(tmp_path: Path) -> None:
    service_root = Path(__file__).resolve().parents[1]
    environment = os.environ.copy()
    for variable in RUNTIME_ENVIRONMENT_VARIABLES:
        environment.pop(variable, None)
    environment["PYTHONPATH"] = str(service_root / "src")

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            "--collect-only",
            "-q",
            "-c",
            str(service_root / "pyproject.toml"),
            str(service_root / "tests"),
        ],
        cwd=tmp_path,
        env=environment,
        capture_output=True,
        text=True,
        check=False,
        timeout=60,
    )

    assert result.returncode == 0, result.stdout + result.stderr
