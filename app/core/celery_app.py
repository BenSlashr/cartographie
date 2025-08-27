from celery import Celery
from app.core.config import settings

celery_app = Celery(
    "cartographie",
    broker="redis://localhost:6379/0",
    backend="redis://localhost:6379/0",
    include=["app.tasks.embeddings_tasks"]
)

celery_app.conf.update(
    task_track_started=True,
    task_serializer='json',
    result_serializer='json',
    accept_content=['json'],
    timezone='Europe/Paris',
    enable_utc=True,
)