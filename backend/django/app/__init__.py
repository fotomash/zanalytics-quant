"""Backend Django app initialization."""

from pathlib import Path
import sys

# Add repo root to PYTHONPATH for access to top-level packages.
# ``__file__`` → backend/django/app/__init__.py → repo root is three levels up
REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.append(str(REPO_ROOT))

from .celery import app as celery_app

__all__ = ["celery_app"]

