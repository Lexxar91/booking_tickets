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

# в дальнейшим заменить на Redis
result_backend = (
    f"rpc://{RABBITMQ_USER}:{RABBITMQ_PASSWORD}"
    f"@{RABBITMQ_HOST}:{RABBITMQ_PORT}/{RABBITMQ_VHOST}"
)


task_serializer = "json"
result_serializer = "json"
accept_content = ["json"]


timezone = "UTC"
enable_utc = True


broker_connection_retry_on_startup = True


task_queues = {
    "high": {"exchange": "high", "routing_key": "high"},
    "default": {"exchange": "default", "routing_key": "default"},
    "low": {"exchange": "low", "routing_key": "low"},
}

task_default_queue = "default"
task_default_exchange = "default"
task_default_routing_key = "default"
