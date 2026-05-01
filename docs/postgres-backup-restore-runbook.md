# PostgreSQL Backup and Restore Runbook

Короткая инструкция для резервного копирования и восстановления трех PostgreSQL баз проекта:

- `auth`
- `event`
- `booking`

## Где лежат backup-файлы

По умолчанию `scripts/backup_postgres.sh` сохраняет дампы сюда:

```bash
backups/postgres/YYYYMMDD_HHMMSS/
```

Внутри одной директории должны быть три файла:

```text
auth.dump
event.dump
booking.dump
```

Срок хранения по умолчанию: `14` дней. Его можно изменить через переменную `BACKUP_RETENTION_DAYS`.

## Сделать backup вручную

Из корня проекта:

```bash
./scripts/backup_postgres.sh
```

Условия:

- файл `.env` существует в корне проекта;
- контейнеры `booking_postgres_auth`, `booking_postgres_event`, `booking_postgres_booking` запущены;
- у пользователя есть доступ к Docker.

После успешного запуска скрипт напечатает путь вида:

```text
Backup completed: /path/to/project/backups/postgres/YYYYMMDD_HHMMSS
```

## Автоматический запуск через systemd timer

Ежедневный backup запускается через user-level `systemd timer`.

Unit-файлы лежат здесь:

```text
~/.config/systemd/user/booking-postgres-backup.service
~/.config/systemd/user/booking-postgres-backup.timer
```

`booking-postgres-backup.service` описывает, какую команду запускать. `booking-postgres-backup.timer` описывает, когда ее запускать.

Проверить расписание:

```bash
systemctl --user list-timers booking-postgres-backup.timer
```

Проверить последний запуск:

```bash
systemctl --user status booking-postgres-backup.service
```

Посмотреть лог backup-а:

```bash
tail -n 50 backups/backup.log
```

Изменить время запуска:

```bash
nano ~/.config/systemd/user/booking-postgres-backup.timer
```

В timer-файле изменить строку:

```ini
OnCalendar=*-*-* 02:30:00
```

Например, для запуска каждый день в `04:00`:

```ini
OnCalendar=*-*-* 04:00:00
```

Применить изменения:

```bash
systemctl --user daemon-reload
systemctl --user restart booking-postgres-backup.timer
systemctl --user list-timers booking-postgres-backup.timer
```

Отключить автоматический backup:

```bash
systemctl --user disable --now booking-postgres-backup.timer
```

`Persistent=true` в timer-файле означает, что если компьютер был выключен во время планового запуска, backup выполнится после следующего запуска user systemd-сессии.

## Восстановить одну базу

Формат команды:

```bash
./scripts/restore_postgres.sh <service> <backup_file.dump>
```

Где `<service>` может быть:

- `auth`
- `event`
- `booking`

Примеры:

```bash
./scripts/restore_postgres.sh auth backups/postgres/20260501_120000/auth.dump
./scripts/restore_postgres.sh event backups/postgres/20260501_120000/event.dump
./scripts/restore_postgres.sh booking backups/postgres/20260501_120000/booking.dump
```

Важно: restore выполняется с `--clean --if-exists`, поэтому существующие объекты в выбранной базе будут удалены и восстановлены из дампа.

## Проверить результат restore

После восстановления проверить, что база доступна и в ней есть таблицы.

Auth:

```bash
docker exec booking_postgres_auth psql -U "$AUTH_POSTGRES_USER" -d "$AUTH_POSTGRES_DB" -c "\dt auth.*"
docker exec booking_auth_service alembic current
curl http://127.0.0.1:8002/health
```

Event:

```bash
docker exec booking_postgres_event psql -U "$EVENT_POSTGRES_USER" -d "$EVENT_POSTGRES_DB" -c "\dt event.*"
docker exec booking_event_service alembic current
curl http://127.0.0.1:8001/health
```

Booking:

```bash
docker exec booking_postgres_booking psql -U "$BOOKING_POSTGRES_USER" -d "$BOOKING_POSTGRES_DB" -c "\dt booking.*"
docker exec booking_booking_service alembic current
curl http://127.0.0.1:8003/health
```

Если shell не подставляет переменные из `.env`, сначала загрузи их:

```bash
set -a
source .env
set +a
```

Минимальная успешная проверка:

- команда restore завершилась без ошибки;
- `psql -c "\dt <schema>.*"` показывает таблицы в нужной схеме;
- `alembic current` показывает текущую ревизию миграций;
- `/health` нужного сервиса возвращает успешный ответ.

## Восстановить все три базы из одного backup-набора

```bash
BACKUP_DIR=backups/postgres/20260501_120000

./scripts/restore_postgres.sh auth "$BACKUP_DIR/auth.dump"
./scripts/restore_postgres.sh event "$BACKUP_DIR/event.dump"
./scripts/restore_postgres.sh booking "$BACKUP_DIR/booking.dump"
```

После этого выполните проверки для всех трех сервисов из раздела выше.

## Быстрый rollback-план

Перед рискованным restore сначала сделай свежий backup:

```bash
./scripts/backup_postgres.sh
```

Если восстановление пошло не так, восстанови нужную базу из самого свежего backup-набора.

## Частые проблемы

`Missing .env file in project root`

Запусти команду из корня проекта и проверь, что файл `.env` существует.

`Container not found`

Проверь, что Docker Compose стек запущен:

```bash
docker compose ps
```

Если контейнеры остановлены:

```bash
docker compose up -d
```

`Backup file not found`

Проверь путь к `.dump` файлу:

```bash
ls -lah backups/postgres
```

`pg_restore` завершился с ошибкой прав или владельцев

Скрипт уже использует `--no-owner --no-privileges`. Если ошибка остается, проверь, что restore выполняется в правильный контейнер и правильную базу из `.env`.
