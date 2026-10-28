import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_models_match_migrations():
    """Модели и миграции не разъезжаются."""
    result = subprocess.run(
        [sys.executable, '-m', 'alembic', 'check'],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    details = f'{result.stdout}\n{result.stderr}'
    assert result.returncode == 0, details
