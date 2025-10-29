from __future__ import annotations

from celery import Celery

from .config import settings


# Create Celery app and configure per Phase 3
celery_app = Celery("webrag")

celery_app.conf.update(
    broker_url=settings.CELERY_BROKER_URL,
    result_backend=settings.CELERY_RESULT_BACKEND,
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    # Track task started state
    task_track_started=True,
    # Terminate tasks that run longer than 5 minutes
    task_time_limit=300,
    # default retry policy
    task_default_retry_delay=60,
    task_default_max_retries=3,
    # Ensure our tasks module is imported and registered on worker startup
    imports=["app.tasks.ingestion"],
)


# Defensive import so that running the web API in non-worker environments does
# not crash the process while still attempting to register tasks.
try:
    import app.tasks.ingestion  # noqa: F401
except Exception as exc:  # pragma: no cover - surfaced during container startup
    import sys

    print("Warning: failed to import app.tasks.ingestion; tasks may not be registered:", exc, file=sys.stderr)
