from celery import Celery
from src import cel_config


celery_app = Celery("notification_service")
celery_app.config_from_object(cel_config)

celery_app.autodiscover_tasks(["src.tasks"])