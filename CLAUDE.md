# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

Hadmind: Django 6.1 site that will replace the current static site at hadmind.com.co. Planned in phases, each a Django app under `apps/`:
1. `apps/landing` — public landing page (first launch; replaces the current site).
2. `apps/blog` — public blog.
3. `apps/bots` — AI chat bots that interview SMEs (pymes) about their needs and suggest automations; results become leads in the CRM.
4. `apps/crm` — private internal app (clients, calls, reminders), reached via an unlisted link but protected with login + 2FA for the whole team (planned: django-allauth MFA).

`core/` holds shared, cross-app code. Shared templates live in `templates/` (`base.html`), shared static assets in `static/`. Each app keeps its own templates under `apps/<app>/templates/<app>/`. Apps are registered as `apps.<name>` (set `name = 'apps.<name>'` in their `AppConfig`). Site copy is in Spanish.

## Stack

- Python 3.13 (Docker image and local `venv/`), Django 6.1.2, PostgreSQL 17 via `psycopg` 3. No SQLite fallback.
- gunicorn in production; WhiteNoise serves static files (manifest/hashed storage when `DEBUG` is off, so `collectstatic` must have run — the Dockerfile does it at build time).
- Locale: `es-co`, `America/Bogota`.

## Configuration

All environment-specific settings come from `.env` (template: `.env.example`), loaded by docker-compose `env_file`, not by Django. `DJANGO_DEBUG=1` enables debug; when it is off, settings also enable `SECURE_PROXY_SSL_HEADER` and secure cookies (the app runs behind Nginx terminating HTTPS). `DJANGO_CSRF_TRUSTED_ORIGINS` must list the `https://` origins in production or admin/form POSTs fail. In production `DJANGO_ALLOWED_HOSTS` must include `localhost` because the web container's healthcheck requests `http://localhost:8000/`.

Run `manage.py` inside the `web` container; the host `venv/` is for editor tooling only (`POSTGRES_HOST=db` doesn't resolve on the host).

## Commands

Development (`docker-compose.yml`: runserver, source bind-mounted for live reload, Postgres published on host 5432):

```sh
docker compose up --build
docker compose exec web python manage.py migrate
docker compose exec web python manage.py makemigrations
docker compose exec web python manage.py test                                    # all tests
docker compose exec web python manage.py test apps.landing.tests.HomeTests.test_home_responde   # single test
```

Rebuild after changing `requirements.txt`. Keep it UTF-8 (`pip freeze | Out-File -Encoding utf8 requirements.txt` in PowerShell; `>` writes UTF-16). No linter/formatter configured.

Production/staging (`docker-compose.prod.yml`): gunicorn bound to `127.0.0.1:${WEB_PORT}`, migrations run on container start, Postgres not published. `COMPOSE_PROJECT_NAME` and `WEB_PORT` in each deployment's `.env` keep the two VPS copies apart (production `hadmind-web`/8003, staging `hadmind-staging`/8004).

```sh
docker compose -f docker-compose.prod.yml up -d --build
```

## Branches

- `develop` — day-to-day work; commit here.
- `staging` — what is deployed to `staging.hadmind.com.co` for review; updated by merging `develop`.
- `main` — production (`hadmind.com.co`); updated only by merging `staging`.

Changes flow `develop → staging → main`; never commit directly to `staging` or `main`.

## Deployment target

Hostinger VPS shared with other projects (each its own compose + own Postgres container, web on `127.0.0.1:800X`, host Nginx + Certbot in front). Production lives in `/opt/hadmind-web` (branch `main`, port 8003); staging in `/opt/hadmind-staging` (branch `staging`, port 8004). The current static site is in `/var/www/hadmind` (Nginx site `hadmind`) — do not deploy into that directory. Rollout: staging at `staging.hadmind.com.co` first; at launch, switch the `hadmind` Nginx site from `root /var/www/hadmind` to `proxy_pass http://127.0.0.1:8003`, keeping a backup of the old site for rollback.
