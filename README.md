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

Удаление задачи физическое: комментарии снимает `ON DELETE CASCADE`. Роль через регистрацию передать нельзя, лишние поля отклоняются.

## Безопасность

- Пароли хеширует Argon2id. В ответах и в тексте ошибок валидации пароль не возвращается.
- Access-токен живёт 30 минут и не отзывается до `exp`. Это осознанный обмен: на каждом запросе мы и так читаем пользователя из базы, но не держим список отозванных JWT. Короткий срок ограничивает окно.
- Refresh-токен непрозрачный, в базе хранится только его SHA-256. Обновление и выход отзывают старый токен. Повторное использование старого refresh даёт `401`.
- Неверный пароль и отключённый пользователь получают один и тот же ответ.
- В `production` нельзя включить `debug` и нельзя оставить секрет со строкой `dev-only`.

Локальный администратор создаётся при старте API, если заданы `BOOTSTRAP_ADMIN_EMAIL` и `BOOTSTRAP_ADMIN_PASSWORD`. Повторный старт пароль не перезаписывает.

## Запуск

```bash
docker compose up --build -d --force-recreate migrate api tests
```

Контейнер `migrate` накатывает миграции и завершается. API и тесты стартуют только после его выхода с кодом 0. Повторный `up` без `--force-recreate` не запускает уже успешный `migrate` заново, поэтому новая ревизия применяется через `make up` или `make migrate`.

- API: http://localhost:8000/docs
- логин администратора: `admin@example.com` / `Adminpass1`
- PostgreSQL на `localhost:5432`, база `tasktracker`

Контейнер `tests` поднят рядом и ждёт команды. Код приложения и тесты примонтированы, поэтому править их можно без пересборки. Новые зависимости требуют `docker compose up --build -d`.

```bash
docker compose exec tests pytest
docker compose logs -f api
docker compose down
```

`docker compose down -v` удаляет данные Postgres.

Локально без пересборки образа, когда база уже запущена:

```bash
poetry install
cp .env.example .env
poetry run alembic upgrade head
PYTHONPATH=src poetry run uvicorn tasktracker.main:app --reload
```

## Тесты

Тесты ходят в ту же базу PostgreSQL, что и API. После каждого теста таблицы очищаются.

```bash
docker compose exec tests pytest
```

С хоста, против проброшенного порта:

```bash
DATABASE_URL=postgresql+asyncpg://tasktracker:tasktracker@localhost:5432/tasktracker \
  poetry run pytest
```

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

Префикс `/api/v1`.

| Метод | Путь | Назначение |
| --- | --- | --- |
| POST | `/auth/register` | Регистрация |
| POST | `/auth/login` | Вход JSON |
| POST | `/auth/token` | Вход формой для Authorize в Swagger (`username` = email) |
| POST | `/auth/refresh` | Поворот refresh-токена |
| POST | `/auth/logout` | Отзыв refresh-токена |
| GET | `/auth/me` | Текущий пользователь |
| GET | `/users` | Кого можно назначить |
| POST | `/tasks` | Создать |
| GET | `/tasks` | Список: `status`, `priority`, `assignee_id`, `author_id`, `search`, `sort`, `order`, `page` |
| PATCH | `/tasks/{id}` | Изменить, нужна `version` |
| POST | `/tasks/{id}/complete` | Выполнить |
| POST | `/tasks/{id}/reopen` | Вернуть в `todo` |
| DELETE | `/tasks/{id}` | Удалить |
| POST | `/tasks/{id}/comments` | Комментарий |
| PATCH | `/tasks/{id}/comments/{id}` | Правка комментария |

Ошибки приходят как `{"detail", "code", "request_id"}`. У `422` есть ещё `errors`.
