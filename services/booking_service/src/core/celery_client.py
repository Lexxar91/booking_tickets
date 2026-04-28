from celery import Celery
import os


RABBITMQ_USER = os.getenv("RABBITMQ_USER", "booking_rabbit")
RABBITMQ_PASSWORD = os.getenv("RABBITMQ_PASSWORD", "password")
RABBITMQ_HOST = os.getenv("RABBITMQ_HOST", "rabbitmq")
RABBITMQ_PORT = os.getenv("RABBITMQ_PORT", "5672")
RABBITMQ_VHOST = os.getenv("RABBITMQ_VHOST", "booking")


broker_url = (
    f"amqp://{RABBITMQ_USER}:{RABBITMQ_PASSWORD}"
    f"@{RABBITMQ_HOST}:{RABBITMQ_PORT}/{RABBITMQ_VHOST}"
)


celery_client = Celery("booking_service", broker=broker_url)
celery_client.conf.task_serializer = "json"
celery_client.conf.accept_content = ["json"]


celery_client.conf.task_default_queue = "default"
celery_client.conf.task_default_exchange = "default"
celery_client.conf.task_default_routing_key = "default"
