# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

A personal cashflow manager with a FastAPI backend and React/TypeScript frontend, containerized with Docker.

## Prerequisites

Python 3.14+, Node.js 22+, npm 10+.

## Commands

### Backend (from `backend/`)
```bash
pip install -r requirements.txt

uvicorn app.main:app --reload --port 8000

pytest                                        # all tests
pytest tests/test_auth.py -v                 # single file
pytest tests/test_auth.py::test_register -v  # single test
pytest --cov --cov-report=term-missing       # with coverage

alembic upgrade head                         # apply migrations
alembic revision --autogenerate -m "desc"    # new migration
alembic current                              # check status
alembic downgrade -1                         # rollback one step
```

> When running the backend outside Docker, set `DB_PATH=./data/cashflow.db` in `.env`.

### Frontend (from `frontend/`)
```bash
npm install
npm run dev          # Vite dev server on port 3000
npm run build        # TypeScript check + production build
npm run test         # Run tests once (Vitest)
npm run test:watch   # Watch mode

# Run a single test file
npm run test -- src/tests/transactions.test.ts
```

### E2E (from `e2e/`) — requires full app running
```bash
npx playwright install   # first time only
npx playwright test
npx playwright test --ui # interactive mode
```

### Docker
```bash
docker compose up    # Start both services (backend:8000, frontend:3000)
```

## Docs

- **[Architecture](docs/architecture.md)** — System design, component map, CI/CD
- **[Development](docs/development.md)** — Local setup, testing, migrations, conventions
- **[Deployment](docs/deployment.md)** — Production checklist, reverse proxy, upgrades, backup
- **[Configuration](docs/configuration.md)** — All environment variables documented
- **[Authentication](docs/authentication.md)** — Basic auth + OIDC flows, provider examples


## Architecture

### Backend (`backend/app/`)

FastAPI app with SQLAlchemy (SQLite) and Alembic migrations.

- **`main.py`** — App init, router registration, lifespan context
- **`config.py`** — Pydantic settings loaded from `.env` (`DB_PATH`, `SECRET_KEY`, OIDC config)
- **`database.py`** — SQLAlchemy `Base`, `get_session_factory()`
- **`deps.py`** — FastAPI dependencies: `get_db` (DB session), `get_current_user` (JWT auth)
- **`models/`** — SQLAlchemy ORM models: `User`, `PaymentMethod`, `Transaction`, `Transfer`, `Asset`, `Category`, `SalaryConfig`, `TaxConfig`, `Forecast`, `ForecastLine`, `ForecastAdjustment`, `MainBankHistory`, `UserSetting`
- **`routers/`** — One router per domain, all included at `/api/v1` prefix
- **`schemas/`** — Pydantic request/response schemas (separate from ORM models)
- **`services/`** — Business logic: `analytics`, `assets`, `auth`, `bank_balance`, `billing`, `forecasting`, `oidc`, `recurrence`, `salary`, `seed`, `summary`, `tax`

All models use UUID string PKs via `gen_uuid()`. Database is SQLite at `DB_PATH` (default `/app/data/cashflow.db`).

> **Local dev note:** Set `DEVELOPMENT_MODE=true` in your `.env` for local development. Since commit 770b89f, insecure defaults for `SECRET_KEY`/`SESSION_ENCRYPTION_KEY` raise a `ValueError` at startup rather than warn — `DEVELOPMENT_MODE=true` bypasses this check.

### Frontend (`frontend/src/`)

React 18 + TypeScript, Vite, TanStack Query, React Hook Form + Zod.

- **`App.tsx`** — Root: wraps with `QueryClientProvider`, `AuthProvider`, `OnboardingProvider`
- **`router.tsx`** — React Router v6 config; `AuthGuard` redirects unauthenticated users
- **`api/client.ts`** — Axios instance with base URL `/api/v1`, credentials enabled; Vite proxies `/api` → `http://localhost:8000`
- **`api/`** — One module per domain (e.g., `transactions.ts`, `forecasts.ts`), typed with interfaces from `types/api.ts`
- **`contexts/AuthContext.tsx`** — Auth state via React Context + React Query cache
- **`hooks/`** — `useAuth`, `useTheme`, and domain-specific hooks wrapping React Query
- **`pages/`** — Page-level components mapped to routes
- **`components/`** — Reusable UI components (forms, tables, charts via Recharts)

### Authentication Flow

- Register/Login set an httponly cookie (`access_token`, JWT HS256)
- All subsequent requests include credentials; the backend reads the cookie
- `GET /api/v1/auth/me` returns the current user
- Optional OIDC support configurable via `.env`

### Onboarding Flow

On first login, `AuthGuard` checks `GET /api/v1/onboarding/status`. If `complete: false`, users are redirected to `/setup` (`SetupPage`) regardless of the requested route. `SetupGuard` on the `/setup` route redirects already-onboarded users back to `/`. All authenticated routes are gated behind both guards.

### Commit Convention

Conventional commits are enforced — semantic-release derives versions and the changelog from them:
- `feat:` → minor bump
- `fix:` → patch bump
- `feat!:` / `BREAKING CHANGE:` footer → major bump
- `chore:`, `docs:`, `test:`, `refactor:` → no bump

### Testing Patterns

**Backend:** `conftest.py` creates an in-memory SQLite DB per test and overrides `get_db` via FastAPI's dependency override system.

**Frontend:** Vitest + Testing Library + MSW (Mock Service Worker) for API mocking; jsdom environment.

## Wiki Knowledge Base

Vault: `~/soulwaxx_brain` (read via `mcp__obsidian-vault__*`).

When you need context not already in this project:
1. Read `wiki/hot.md` first — recent context, under 500 words
2. Read `wiki/index.md` if more breadth is needed
3. Read the relevant domain index (files are named after the domain, not `INDEX.md`):
   - Satispay work: `wiki/satispay/satispay.md` → sub-domain e.g. `wiki/satispay/kubernetes/kubernetes.md`
   - Personal projects: `wiki/projects/projects.md`
   - Learning: `wiki/learning/learning.md`
   - Reference / cheatsheets: `wiki/reference/reference.md`
   - Concepts / entities / sources: `wiki/concepts/concepts-index.md`, `wiki/entities/entities-index.md`, `wiki/sources/sources-index.md`
4. Only then read individual pages

Do NOT consult the wiki for general coding questions or anything already in this project.
Do NOT read `wiki/overview.md` — it duplicates `hot.md` and `index.md`.
