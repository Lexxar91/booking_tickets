# 🎫 BookingTickets

**Production-like микросервисная платформа для бронирования билетов на мероприятия.**

Система позволяет пользователям регистрироваться, просматривать каталог мероприятий, бронировать билеты и получать PDF-подтверждения на email. Администраторы управляют мероприятиями через защищённый API.

---

## ✨ Возможности

| Функция | Описание |
|---|---|
| **Аутентификация** | Регистрация, логин, JWT (RS256), refresh-токены с отзывом |
| **Каталог мероприятий** | CRUD операций, пагинация, фильтрация |
| **Бронирование** | Создание и отмена бронирований, защита от double-booking |
| **Email-уведомления** | Асинхронная отправка писем с PDF-билетами |
| **Мониторинг** | Prometheus + Grafana, алерты, health-checks |

---

## 🏗️ Архитектура

```
                    ┌──────────────┐
                    │   Ingress    │
                    │  (NGINX/TLS) │
                    └──────┬───────┘
                           │
           ┌───────────────┼───────────────┐
           │               │               │
    ┌──────▼──────┐ ┌──────▼──────┐ ┌──────▼──────┐
    │   Auth      │ │   Event     │ │  Booking    │
    │  Service    │ │  Service    │ │  Service    │
    │  :8002      │ │  :8001      │ │  :8003      │
    └──────┬──────┘ └──────┬──────┘ └──────┬──────┘
           │               │               │
      ┌────▼────┐     ┌────▼────┐    ┌─────▼──────┐
      │PostgreSQL│     │PostgreSQL│    │ PostgreSQL │
      │  auth   │     │  event   │    │  booking   │
      └─────────┘     └─────────┘    └─────┬──────┘
                                           │
                                    ┌──────▼──────┐
                                    │  RabbitMQ   │
                                    └──────┬──────┘
                                           │
                                    ┌──────▼──────────┐
                                    │  Notification   │
                                    │    Worker       │
                                    │  (Celery)       │
                                    └──────┬──────────┘
                                           │
                                    ┌──────▼──────┐
                                    │    SMTP     │
                                    └─────────────┘
```

### Технологический стек

| Компонент | Технология |
|---|---|
| **Язык** | Python 3.12 |
| **Фреймворк** | FastAPI + Uvicorn |
| **ORM** | SQLAlchemy 2.0 (async) |
| **Миграции** | Alembic |
| **JWT** | python-jose (RS256) |
| **Пароли** | Argon2 |
| **Очереди** | Celery + RabbitMQ |
| **БД** | PostgreSQL 16 |
| **Контейнеризация** | Docker (multi-stage) |
| **Оркестрация** | Docker Compose / Kubernetes |
| **Мониторинг** | Prometheus + Grafana + cAdvisor |

---

## 📁 Структура репозитория

```
├── services/
│   ├── auth_service/          # Аутентификация и авторизация
│   ├── event_service/         # Управление мероприятиями
│   ├── booking_service/       # Бронирование билетов
│   └── notification_service/  # Celery worker для email-уведомлений
├── deploy/
│   ├── k8s/                   # Kubernetes манифесты
│   └── nginx/                 # NGINX конфигурация
├── monitoring/
│   ├── prometheus/            # Prometheus конфигурация и алерты
│   └── grafana/               # Grafana provisioning
├── scripts/                   # Вспомогательные скрипты
├── secrets/                   # JWT ключи (не коммитить!)
├── docker-compose.yml
├── docker-compose.monitoring.yml
└── .env.example
```

---

## 🚀 Быстрый старт

### Предварительные требования

- Docker + Docker Compose plugin
- OpenSSL (для генерации JWT-ключей)

### 1. Клонировать репозиторий

```bash
git clone <repository-url>
cd booking_tickets
```

### 2. Настроить окружение

```bash
cp .env.example .env
# Отредактируйте .env — укажите пароли для PostgreSQL, RabbitMQ, SMTP
```

### 3. Сгенерировать JWT-ключи

```bash
mkdir -p secrets/jwt
openssl genpkey -algorithm RSA -out secrets/jwt/private.pem -pkeyopt rsa_keygen_bits:2048
openssl rsa -pubout -in secrets/jwt/private.pem -out secrets/jwt/public.pem
chmod 600 secrets/jwt/private.pem
chmod 644 secrets/jwt/public.pem
```

### 4. Запустить сервисы

```bash
docker compose up -d --build
```

### 5. Применить миграции

```bash
docker exec booking_auth_service alembic upgrade head
docker exec booking_event_service alembic upgrade head
docker exec booking_booking_service alembic upgrade head
```

### 6. Создать администратора

```bash
# Регистрация пользователя
curl -X POST http://127.0.0.1:8002/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@example.com","password":"StrongPass123!"}'

# Выдача роли admin
docker exec booking_postgres_auth psql -U auth_user -d auth_db \
  -c "UPDATE auth.users SET role='admin' WHERE email='admin@example.com';"
```

### 7. Проверить работоспособность

```bash
curl http://127.0.0.1:8001/health
curl http://127.0.0.1:8002/health
curl http://127.0.0.1:8003/health
```

Swagger-документация доступна по адресам:

| Сервис | URL |
|---|---|
| Auth | http://127.0.0.1:8002/docs |
| Events | http://127.0.0.1:8001/docs |
| Bookings | http://127.0.0.1:8003/docs |

---

## 📡 API Endpoints

### Auth Service (`:8002`)

| Метод | Путь | Описание |
|---|---|---|
| `POST` | `/api/v1/auth/register` | Регистрация |
| `POST` | `/api/v1/auth/login` | Логин (возвращает access + refresh) |
| `POST` | `/api/v1/auth/refresh` | Обновление access-токена |
| `POST` | `/api/v1/auth/logout` | Выход (отзыв refresh-токена) |

### Event Service (`:8001`)

| Метод | Путь | Описание | Auth |
|---|---|---|---|
| `POST` | `/api/v1/events/` | Создать мероприятие | `admin` |
| `GET` | `/api/v1/events/` | Список мероприятий | — |
| `GET` | `/api/v1/events/{id}` | Детали мероприятия | — |
| `PATCH` | `/api/v1/events/{id}` | Обновить мероприятие | `admin` |
| `DELETE` | `/api/v1/events/{id}` | Удалить мероприятие | `admin` |

### Booking Service (`:8003`)

| Метод | Путь | Описание | Auth |
|---|---|---|---|
| `POST` | `/api/v1/bookings/` | Забронировать билет | user |
| `GET` | `/api/v1/bookings/my` | Мои бронирования | user |
| `GET` | `/api/v1/bookings/{id}` | Детали бронирования | user |
| `POST` | `/api/v1/bookings/{id}/cancel` | Отменить бронирование | user |

---

## 🛡️ Безопасность

- **JWT (RS256)** — приватный ключ только в `auth_service`, публичный — в остальных сервисах
- **Refresh-токены** хранятся в БД и могут быть отозваны
- **Rate limiting** на логин — защита от brute-force (5 попыток / 5 мин, бан на 15 мин)
- **Role-based access control** — изменение мероприятий только для `admin`
- **SELECT FOR UPDATE** — защита от race condition при бронировании
- **Non-root контейнеры** — все сервисы запускаются от непривилегированного пользователя
- **Network Policies (K8s)** — zero-trust модель с явными правилами доступа между сервисами

---

## 📊 Мониторинг

```bash
docker compose -f docker-compose.monitoring.yml up -d
```

| Компонент | URL | Логин / Пароль |
|---|---|---|
| Prometheus | http://localhost:9090 | — |
| Grafana | http://localhost:3000 | admin / admin |
| cAdvisor | http://localhost:8080 | — |
| RabbitMQ UI | http://localhost:15672 | guest / guest |

### Алерты

| Алерт | Уровень | Условие |
|---|---|---|
| `ServiceDown` | 🔴 Critical | Сервис недоступен > 1 мин |
| `HighErrorRate` | 🟡 Warning | > 5% 5xx за 5 мин |
| `SlowResponses` | 🟡 Warning | p95 latency > 1с за 5 мин |
| `PostgresHighConnections` | 🟡 Warning | > 80% от max_connections |

---

## 🚢 Деплой в Kubernetes

Все манифесты находятся в `deploy/k8s/`.

### Порядок применения

```bash
# 1. Namespace
kubectl apply -f deploy/k8s/base/namespace.yaml

# 2. Secrets (скопировать из secrets.example.yaml и заполнить)
kubectl apply -f deploy/k8s/secrets.yaml

# 3. Infrastructure (PostgreSQL, RabbitMQ)
kubectl apply -f deploy/k8s/infrastructure/

# 4. Сервисы
kubectl apply -f deploy/k8s/base/
kubectl apply -f deploy/k8s/auth_service/
kubectl apply -f deploy/k8s/event_service/
kubectl apply -f deploy/k8s/booking_service/
kubectl apply -f deploy/k8s/notification_service/

# 5. Ingress
kubectl apply -f deploy/k8s/ingress.yaml

# 6. Миграции
kubectl exec -n booking-tickets deploy/auth-service -- alembic upgrade head
kubectl exec -n booking-tickets deploy/event-service -- alembic upgrade head
kubectl exec -n booking-tickets deploy/booking-service -- alembic upgrade head
```

---

## 🧪 Smoke-тесты после запуска

Чек-лист для проверки работоспособности:

- [ ] Все сервисы отвечают `200` на `/health`
- [ ] Регистрация и логин работают
- [ ] `refresh` возвращает новую пару токенов
- [ ] Повторное использование refresh-токена возвращает `401`
- [ ] Обычный пользователь получает `403` на изменение мероприятий
- [ ] `admin` может создавать, обновлять и удалять мероприятия
- [ ] Создание и отмена бронирования работают
- [ ] Notification worker получает задачу и отправляет email

---

## 📝 TODO

Следующие шаги для приближения к полноценному production:

- [ ] Unit и интеграционные тесты
- [ ] CI/CD пайплайн (GitHub Actions / GitLab CI)
- [ ] Линтеры и форматтеры (ruff, black, mypy)
- [ ] Структурированное логирование (JSON) + агрегация (Loki / ELK)
- [ ] Distributed tracing (OpenTelemetry / Jaeger)
- [ ] Redis вместо RPC для Celery result backend
- [ ] Интеграция платёжной системы

---

## 📄 Лицензия

MIT
