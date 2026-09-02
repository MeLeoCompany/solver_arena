# Деплой

## Быстрый старт

```bash
cp .env.example .env        # заполнить пароль админа
docker compose up -d --build
```

Это всё. Поднимутся два контейнера — `backend` (FastAPI + солверы) и
`nginx` (отдаёт фронтенд и проксирует API). Без карты и без CUDA/cuOpt —
работают CPLEX/ALGLIB/QORE, cuOpt будет показан в `/solvers` как
недоступный. Открывать `http://localhost` (или `http://<IP-сервера>`, см.
раздел TLS ниже про предупреждение о незащищённом соединении).

Нужен cuOpt (GPU на хосте + установленный `nvidia-container-toolkit`) —
добавьте второй compose-файл при сборке:

```bash
docker compose -f docker-compose.yml -f docker-compose.gpu.yml up -d --build
```

Разница только в этой команде — `docker-compose.gpu.yml` не отдельный
деплой, а *довесок* к обычному: включает установку cuOpt/CUDA в образе
backend и пробрасывает GPU в контейнер.

| Команда | cuOpt | Когда использовать |
|---|---|---|
| `docker compose up -d --build` | нет | по умолчанию, любая машина, стенд без карты |
| `docker compose -f docker-compose.yml -f docker-compose.gpu.yml up -d --build` | да | на хосте есть GPU и `nvidia-container-toolkit` |

Пересобрать без пересоздания/запуска: `docker compose build backend`.
Остановить: `docker compose down` (данные в `backend/data/` не удаляются).

## `.env` vs флаг `INSTALL_CUOPT` — не путать

Это два разных механизма, отвечающих на разные вопросы:

- **`.env`** (в корне репозитория, из `.env.example`) — переменные
  окружения *внутри уже запущенных* контейнеров: пароль админа, домен для
  TLS и т.п. Меняются без пересборки образа, просто
  `docker compose up -d` (без `--build`) их подхватит.
- **`INSTALL_CUOPT`** — build-arg, участвует только в момент сборки
  Docker-образа backend (решает, ставить ли многогигабайтный CUDA/cuOpt
  стек). В `.env` его быть не должно — он уже прописан внутри
  `docker-compose.yml` (`"false"`) и переопределяется в
  `docker-compose.gpu.yml` (`"true"`). Выбирается тем, какую команду
  сборки из таблицы выше вы запускаете, а не переменной в `.env`.

## Что где собирается

- `backend/Dockerfile` — FastAPI-приложение: все 4 солвера, включая
  вендоренные бинарники CPLEX/ALGLIB/QORE из `backend/engines/` и
  отдельный интерпретатор CPython 3.8 для QORE. Миграции БД гоняются
  автоматически при старте — отдельный шаг не нужен.
- `frontend/Dockerfile` — многостадийная сборка: `npm run build`, затем
  готовые статические файлы отдаются через `nginx`, который также
  проксирует API-запросы на `backend` и (если задан домен) сам
  получает/продлевает TLS-сертификат через certbot — см. `deploy/nginx/`.

`backend/data/` смонтирован с хоста как volume — SQLite-база, загруженные
MPS-файлы, логи и результаты решений переживают пересоздание контейнера.

## TLS

Управляется одной переменной в `.env` — `DOMAIN`:

- **`DOMAIN` не задан** — nginx поднимается на порту 80, без шифрования.
  При старте контейнер печатает в лог явное предупреждение об этом.
  Подходит только для локальной проверки (`http://localhost`), **не для
  деплоя, доступного из интернета**.
- **`DOMAIN` задан** (домен должен уже указывать на публичный IP этого
  сервера) — nginx при первом запуске сам получает сертификат Let's
  Encrypt через `certbot` (webroot-метод, HTTP-01 challenge), дальше
  отдаёт сайт по HTTPS на 443 и продлевает сертификат в фоне каждые 12
  часов. Нужен ещё `CERTBOT_EMAIL` (контактный email для Let's Encrypt).
  Сертификаты лежат в `./deploy/letsencrypt` (смонтировано volume'ом,
  переживает пересоздание контейнера — не должно перезапрашиваться при
  каждом деплое, у Let's Encrypt есть лимиты на количество выдач).

Не забудьте выставить `SOLVER_SERVER_SESSION_COOKIE_SECURE=true` в `.env`,
когда включаете `DOMAIN` — иначе cookie сессии не помечается `Secure`
даже при работающем HTTPS.

Логика выбора конфига — `deploy/nginx/entrypoint.sh`: решает, какой из
трёх взять (`http.conf` / `bootstrap.conf.template` на время первичной
выдачи сертификата / `https.conf.template` после).

## Вендоренные бинарники солверов (не в git)

`backend/engines/**/*.so`/`*.dll`/`*.h` (CPLEX/ALGLIB/QORE) не хранятся в
git (см. корневой `.gitignore`) — доставляются на сервер отдельно:

1. Локально, из корня репозитория: `./deploy/pack-engines.sh` — собирает
   `engines-binaries.tar.gz` из всех `.so`/`.dll`/`.h` под
   `backend/engines/`.
2. Отправить на сервер: `scp engines-binaries.tar.gz <user>@<host>:~/`.
3. На сервере, из `deploy/` склонированного репозитория:
   `bash unpack-engines.sh ~/engines-binaries.tar.gz ~/solver_arena` —
   распаковывает обратно по местам и удаляет архив.

После этого — обычная сборка (см. «Быстрый старт» выше).
