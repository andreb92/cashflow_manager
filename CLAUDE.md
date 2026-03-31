# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

A personal cashflow manager with a FastAPI backend and React/TypeScript frontend, containerized with Docker.

## Commands

### Backend (from `backend/`)
```bash
# Install dependencies
pip install -r requirements.txt

# Run dev server
uvicorn app.main:app --reload --port 8000

# Run all tests
pytest

# Run a single test
pytest tests/test_auth.py::test_register_creates_user -v

# Run migrations
alembic upgrade head

# Create a new migration
alembic revision --autogenerate -m "description"
```

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
- **`services/`** — Business logic: `analytics`, `assets`, `auth`, `bank_balance`, `billing`, `forecasting`, `installments`, `oidc`, `recurrence`, `salary`, `seed`, `summary`, `tax`

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

### Testing Patterns

**Backend:** `conftest.py` creates an in-memory SQLite DB per test and overrides `get_db` via FastAPI's dependency override system.

**Frontend:** Vitest + Testing Library + MSW (Mock Service Worker) for API mocking; jsdom environment.
