from celery import Celery
from src import cel_config


celery_app = Celery("notification_service")
celery_app.config_from_object(cel_config)

# autodiscover_tasks ищет файлы tasks.py в пакетах, поэтому указываем
# только имя пакета
celery_app.autodiscover_tasks(["src.tasks"])
