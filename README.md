# HAIntly Vacancy Service (`vacancy-service`)

Сервис сбора вакансий и управления их состоянием относительно пользователя.

Сервис владеет локальными реляционными справочниками HH. Внутренний read-only namespace `/internal/dictionaries` требует UUID в `X-User-Id`. Worker синхронизирует семь независимых полных снимков, Beat ежечасно проверяет актуальность. Адреса HH/PostgreSQL/Redis, таймауты и период актуальности задаются окружением из `.env.example`.

## Ответственность

- фоновый сбор и повторный сбор вакансий для выбранного резюме;
- хранение вакансий и пользовательских статусов;
- выдача списка вакансий;
- скрытие вакансии навсегда;
- ручная отметка об отклике;
- постановка заданий на AI-оценку и генерацию письма;
- публикация событий для уведомлений.

## Технологии

FastAPI, PostgreSQL, aiohttp, Celery и NATS JetStream.

## Интеграции

- HTTP ← `main-be`;
- HTTP → `profile-service`;
- HTTPS ↔ HH API;
- NATS JetStream ↔ `ai-service`;
- NATS JetStream → `notification-service`.

## Границы

- Сервис владеет вакансиями и их статусами, но не HH-токенами.
- AI score и письмо вычисляются `ai-service`.
- Celery используется только для внутренней фоновой работы; broker/backend определяются отдельным design.
- Endpoint, NATS subjects, retry и idempotency policy фиксируются в OpenSpec.
- Персональные данные резюме не логируются и не копируются без необходимости.

Будущая документация должна добавить модели статусов, flow сбора, env, миграции, команды и контракты событий.

## Локальный rebuild справочников

Операция допустима только для local/test БД `vacancy-service`. Сначала остановите
`app`, `worker` и `beat`, затем явно подтвердите имя целевой БД и выполните:

```shell
docker compose -f .docker-compose/docker-compose.vacancy.yml stop app worker beat
CONFIRM_VACANCY_DICTIONARY_RESET=vacancy_db make vacancy-reset
make vacancy-migrate
make vacancy-seed
make vacancy
```

Reset удаляет только таблицы справочников в подтверждённой vacancy-БД. Он
отказывает для production-like окружения, другого имени БД или отсутствующего
подтверждения. Production выполняет только недеструктивный migration upgrade и
отдельно контролируемый seed.

Общие границы проекта: [SERVICES.md](../../SERVICES.md).
