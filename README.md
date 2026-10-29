# Task Tracker

API управления задачами: создание, назначение, выполнение и комментарии. Пользователи входят по email и паролю, данные лежат в PostgreSQL, схема меняется только миграциями.

## Стек

- Python 3.12, Poetry
- FastAPI, Pydantic v2
- SQLAlchemy 2.0 (async) и asyncpg
- Alembic
- PostgreSQL 16
- JWT access-токен и отзываемый refresh-токен (Argon2id для паролей)
- pytest, Docker Compose

## Как устроено

Запрос проходит три слоя:

1. Роутер принимает схему и код ответа, без правил предметной области.
2. Сервис проверяет права, версии и переходы статуса.
3. Репозиторий собирает SQL. Сортировка и поиск не склеиваются из строк клиента.

Один HTTP-запрос — одна транзакция. Изменяющие операции блокируют строку `SELECT … FOR UPDATE` и сверяют `version`, чтобы параллельное редактирование вернуло `409`, а не затёрло чужие правки.

Это внутренний трекер одной команды: любой вошедший пользователь видит все задачи. Отдельных организаций в задании нет.

## Права

| Действие | Автор | Исполнитель | Другой пользователь | Админ |
| --- | --- | --- | --- | --- |
| Менять название, описание, срок, приоритет, исполнителя | да | нет | нет | да |
| Менять статус и отмечать выполнение | да | да | нет | да |
| Удалять задачу | да | нет | нет | да |
| Читать и комментировать | да | да | да | да |
| Менять и удалять чужой комментарий | нет | нет | нет | да |

`POST /tasks/{id}/complete` идемпотентен. `POST /tasks/{id}/reopen` переводит только выполненную задачу обратно в `todo`. Пустой `description` сохраняется как `null`. `assignee_id: null` снимает исполнителя. Поле `version` в `PATCH` обязательно.

Удаление задачи физическое: комментарии снимает `ON DELETE CASCADE`. Удаление пользователя — soft-delete: `DELETE /users/{id}` ставит `is_active=false`, строка остаётся; логин и refresh после этого не работают. Роль через регистрацию передать нельзя (всегда `user`), публичного API смены роли нет — админ только через bootstrap или БД. Лишние поля в теле отклоняются.

## Безопасность

- Пароли хеширует Argon2id. В ответах и в тексте ошибок валидации пароль не возвращается.
- Access-токен живёт 30 минут и не отзывается до `exp`. Это осознанный обмен: на каждом запросе мы и так читаем пользователя из базы, но не держим список отозванных JWT. Короткий срок ограничивает окно.
- Refresh-токен непрозрачный, в базе хранится только его SHA-256. Обновление и выход отзывают старый токен. Повторное использование старого refresh даёт `401`.
- Неверный пароль и отключённый пользователь получают один и тот же ответ (`invalid_credentials`).
- В `production` нельзя включить `debug` и нельзя оставить секрет со строкой `dev-only`.

Локальный администратор создаётся при старте API, если заданы `BOOTSTRAP_ADMIN_EMAIL` и `BOOTSTRAP_ADMIN_PASSWORD`. Повторный старт пароль не перезаписывает. В unit-тестах bootstrap отключён.

## Запуск

```bash
make up
```

Контейнер `migrate` накатывает миграции и завершается. API и тесты стартуют только после его выхода с кодом 0. Повторный `docker compose up` без `--force-recreate` не запускает уже успешный `migrate` заново, поэтому новая ревизия применяется через `make up` или `make migrate`.

- API: http://localhost:8000/docs
- логин администратора: `admin@example.com` / `Adminpass1`
- PostgreSQL на `localhost:5432`, база `tasktracker`

Контейнеры `tests-unit` и `tests-e2e` подняты рядом и ждут команды. Для локальной разработки примонтированы `src`/`tests` (unit) и `tests/e2e` (e2e), поэтому править тесты можно без пересборки. Образ e2e намеренно без кода приложения — только HTTP к `E2E_BASE_URL`. Новые зависимости требуют пересборки (`make up`).

```bash
make test-unit
make test-e2e
make lint
make logs
make down
```

`make down` останавливает стек (включая coverage-overlay) и удаляет volumes (данные Postgres тоже).

Локально без Docker, когда база уже запущена:

```bash
poetry install
cp .env.example .env
poetry run alembic upgrade head
PYTHONPATH=src poetry run uvicorn tasktracker.main:app --reload
```

## Тесты

- **unit** (`tests/unit`): ASGI-клиент + та же Postgres; после каждого теста таблицы `TRUNCATE`.
- **e2e** (`tests/e2e`): только HTTP к живому API (`E2E_BASE_URL`), без доступа к БД; созданные ресурсы снимаются через API после теста.

```bash
make test-unit
make test-e2e
make lint
```

В GitLab CI (`.gitlab-ci.yml`) те же шаги разнесены по stage: `lint` → `unit` → `e2e` → `coverage` (порог покрытия 80%).

С хоста, против проброшенного порта (unit):

```bash
DATABASE_URL=postgresql+asyncpg://tasktracker:tasktracker@localhost:5432/tasktracker \
  poetry run pytest tests/unit
```

## Coverage

Сбор через overlay `docker-compose.coverage.yml`: общий том, `ENABLE_COVERAGE=true`, параллельные файлы `.coverage.<host>.<pid>.*`. Долгоживущий `api` сбрасывает данные на SIGTERM. Unit пишет coverage в процессе тестов, e2e бьёт в api под coverage; отчёт забирается из volume через `docker cp` (`extract_coverage.sh`).

```bash
make coverage
```

Локально порог не проверяется; в CI job `coverage` падает при итоге ниже 80%. HTML: `htmlcov/index.html`, плюс `coverage.xml` (Cobertura). Когда появятся ещё app-сервисы, добавьте их в overlay и в `COVERAGE_APPS` в `Makefile`.

## Миграции

```bash
docker compose exec api alembic revision --autogenerate -m "describe the change"
make migrate
```

Новую ревизию лучше просмотреть руками: автогенерация не заменяет чтение diff.

## Переменные

Смотрите `.env.example`. В Compose значения по умолчанию уже подставлены, файл `.env` нужен для локального `poetry run`.

`DATABASE_URL` обязан начинаться с `postgresql+asyncpg://`.

## API

Префикс `/api/v1.0`. Вне префикса: `GET /health`, `GET /ready`, `GET /` → редирект на `/docs`.

| Метод | Путь | Назначение |
| --- | --- | --- |
| POST | `/auth/register` | Регистрация (роль всегда `user`) |
| POST | `/auth/login` | Вход JSON |
| POST | `/auth/token` | Вход формой для Authorize в Swagger (`username` = email) |
| POST | `/auth/refresh` | Поворот refresh-токена |
| POST | `/auth/logout` | Отзыв refresh-токена |
| GET | `/auth/me` | Текущий пользователь |
| GET | `/users` | Активные пользователи (назначение) |
| GET | `/users/{id}` | Профиль |
| DELETE | `/users/{id}` | Soft-delete: свой аккаунт или любой — для админа |
| POST | `/tasks` | Создать |
| GET | `/tasks` | Список: `status`, `priority`, `assignee_id`, `author_id`, `search`, `sort`, `order`, `page`, `page_size` |
| GET | `/tasks/{id}` | Одна задача |
| PATCH | `/tasks/{id}` | Изменить, нужна `version` |
| POST | `/tasks/{id}/complete` | Выполнить |
| POST | `/tasks/{id}/reopen` | Вернуть в `todo` |
| DELETE | `/tasks/{id}` | Удалить |
| POST | `/tasks/{id}/comments` | Комментарий |
| GET | `/tasks/{id}/comments` | Список комментариев |
| PATCH | `/tasks/{id}/comments/{id}` | Правка комментария (`version` обязателен) |
| DELETE | `/tasks/{id}/comments/{id}` | Удалить комментарий |

Ошибки приходят как `{"detail", "code", "request_id"}`. У `422` есть ещё `errors`.
