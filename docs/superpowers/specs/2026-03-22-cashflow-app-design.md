# CashFlow App — Design Spec
**Date:** 2026-03-22
**Status:** Approved

---

## Overview

A Dockerized personal cash flow management application (FastAPI backend + React frontend + SQLite) that replicates the logic of an existing Excel-based cash flow tracker. Covers transaction entry, monthly summaries, asset tracking, salary calculation, and planning via recurring/installment transactions. Responsive for web and mobile.

Data starts from **2026-01-01**. No historical data import.

**Single-user data model:** All data tables are global (no `user_id` column). Authentication exists only for access control. Multiple user accounts can log in but share the same data set. This is intentional — it is a personal household finance tool.

---

## Architecture

```
Docker Compose
├── frontend  (React + Vite + Tailwind, served via Nginx)  :3000
└── backend   (FastAPI + Uvicorn)                          :8000
                    │
              SQLite (bind mount: ./data directory → /app/data)
              file: /app/data/cashflow.db
```

- Frontend communicates with backend via REST API (`/api/v1/...`)
- Backend owns all business logic, calculation, and DB access
- Auth handled by backend; JWT cookie issued to frontend after login
- OIDC provider: Authentik (on existing `prd-oci-vm1-arm` node)

---

## Authentication

Two auth methods, both enabled independently via env vars:

**Basic Auth**
- `POST /api/v1/auth/login` with email + password
- Credentials stored in `users` table (bcrypt hashed)
- Returns JWT as httpOnly cookie

**OIDC (Authentik)**
- Redirect to Authentik → callback to `/api/v1/auth/oidc/callback`
- Backend validates token, creates/matches user by `oidc_sub`
- Returns JWT as httpOnly cookie

**JWT:** httpOnly cookie, configurable expiry via `JWT_EXPIRE_DAYS` env var (default: 30 days). No refresh token — long-lived tokens are acceptable for a personal app. On expiry the user re-authenticates.

---

## Data Model

Database migrations managed with **Alembic**. `alembic upgrade head` runs automatically on container start.

### `users`
```
id, email, hashed_password (nullable for OIDC-only), oidc_sub (nullable), name, created_at
```

### `app_settings`
```
key (PK), value, updated_at
```
Stores global app-level settings including:
- `opening_bank_balance` — initial bank balance for the first tracked month (2026-01)
- `opening_saving_balance_{name}` — initial balance per saving account
- `opening_investment_balance_{name}` — initial balance per investment account

### `payment_methods`
```
id, name, type (bank | credit_card | revolving), is_main_bank (bool), is_active
```
Seeded: BB-FINECO (main bank, type=bank), CC-AMEXGC (credit_card), CC-AMEXB (credit_card), CC-FINDOMESTIC (revolving), CC-FINECO (credit_card), CC-YOU (credit_card).

`is_main_bank` flag determines which account drives bank balance calculations. Exactly one active payment method has `is_main_bank = true` at any time.

Constraint: only `bank`-type methods can have `is_main_bank = true`.

### `categories`
```
id, type, sub_type, is_active
```
Seeded types and sub-types:

| Type     | Sub-types |
|----------|-----------|
| Housing  | Home, Garage, Bills |
| Mobility | Car, Fuel |
| Bills    | Phone + Internet, Bills |
| Personal | Food, Wellness |
| Leisure  | Trip, Restaurants, Vars, Gifts |
| Salary   | Income |
| Saving   | Saving, Investments, Transfer, Inv-Transfer, Inv-Outcome |

### `transactions`
```
id, date, detail, amount, payment_method_id, category_id,
transaction_direction (income | credit | debit),
billing_month (date — first day of the month this counts toward),
recurrence_months (null = one-off, N = generate N total occurrences),
installment_total (null = full amount, N = split into N months),
installment_index (1..N),
parent_transaction_id (FK to self, for generated children),
notes, created_at, updated_at
```

**Validation constraints (enforced in API):**
- `recurrence_months` and `installment_total` are mutually exclusive — both cannot be set on the same transaction. The API returns HTTP 422 if both are provided.
- `installment_total` can only be set when `payment_method.type` is `credit_card` or `revolving`. Bank transactions cannot be split into installments.

### `transfers`
```
id, date, detail, amount,
from_account_type (bank | saving | investment),
from_account_name,
to_account_type (bank | saving | investment),
to_account_name,
billing_month (date — first day of the month this counts toward, always = date's own month),
recurrence_months,
notes, created_at
```
Transfers always count toward the month of their `date` (no next-month offset; transfers are direct bank movements). `billing_month` is auto-set on save.

### `assets`
```
id, year, asset_type (pension | saving | investment),
asset_name (e.g. "CAAB", "DIRECTA", "AXA"),
manual_override (nullable),
notes
```
The `assets` table stores **only manual overrides**. No explicit asset row creation is required. `GET /assets/{year}` derives all account names dynamically from `app_settings` keys and transfer history, computes `computed_amount` at query time, then joins `assets` rows (if any) to apply `manual_override`. `final_amount = manual_override ?? computed_amount`. The Assets page shows a live year-to-date figure that updates as transfers are added.

**Net salary is entered as a regular income transaction by the user each month** (category: Salary/Income, transaction_direction: income). The `salary_config` is a reference calculator only — it does not auto-post salary transactions.

### `salary_config`
```
id, valid_from (YYYY-MM-01),
ral, inps_rate (default 0.0919), employer_contrib_rate, voluntary_contrib_rate,
regional_tax_rate, municipal_tax_rate,
meal_vouchers_annual, welfare_annual,
manual_net_override (nullable),
computed_net_monthly  ← stored, recomputed and updated on every POST/PUT; seed migration runs the formula at insert time
```
Multiple rows supported. The applicable config for a given month is the row with the highest `valid_from ≤ that month`. The last row applies indefinitely into the future — there is no end date. A mid-year raise adds a new row; past months are never retroactively modified.

**Deletion constraint:** The earliest row (lowest `valid_from`) cannot be deleted. Any other row can be deleted. This ensures every tracked month always has an applicable config. The API returns HTTP 400 if the earliest row deletion is attempted.

---

## Business Logic

### 1. Billing Month Assignment

| Payment method type | `billing_month` |
|---|---|
| `bank` | First day of transaction's own month |
| `credit_card` | First day of **next** month |
| `revolving` | First day of **next** month |

This is automatic on save. The UI shows a read-only hint: "Billed in: February 2026".

### 2. Installment Splitting (credit_card and revolving only)
- `installment_total = N`: backend creates N child transactions
- Each child: `amount / N`, `billing_month` = next month + (installment_index − 1) months
- Linked via `parent_transaction_id`; `installment_index` runs 1..N
- Editing the parent re-generates all children
- UI shows badge: "2/6", "3/6" etc.
- Children appear individually in the Transactions list

### 3. Recurrence
- `recurrence_months = N`: backend creates N total occurrences on the same day-of-month for N consecutive months (first occurrence = the original transaction's month)
- Each occurrence is independent (can be edited/deleted individually)
- Deleting any occurrence prompts: "Delete this one / Delete this and all future / Delete all in series"
- `recurrence_months` and `installment_total` cannot both be set (API validates)
- This same three-option cascade behavior applies to recurring **transfers** as well. `DELETE /transfers/{id}` accepts the same `cascade` query param (`single|future|all`).
- **Edit cascade (PUT):** Editing a recurring transaction prompts the same three options: "This occurrence only / This and all future / All in series". For installment children, editing the parent always re-generates all children (no prompt needed — installment amounts are always derived from the parent).

### 4. Monthly Summary Computation

Per billing month:
- `incomes` = sum of transactions with `transaction_direction = income` in that billing_month
- `outcomes_by_method` = sum of transactions grouped by payment_method in that billing_month
- `transfers_out_bank` = sum of transfers where `from_account_type = bank` and `billing_month = that month`
- `transfers_in_bank` = sum of transfers where `to_account_type = bank` and `billing_month = that month`
- `bank_balance`:
  - "from main bank" means: transactions where `payment_method.is_main_bank = true`, regardless of `transaction_direction`. All income transactions (salary, other income) must be linked to a payment method; income paid directly to the main bank account is assigned the main bank payment method. Credit card expenses are linked to their respective CC payment method and do not affect the bank balance directly (the CC monthly settlement does).
  - January 2026 (first month): `opening_bank_balance` (from `app_settings`) + income transactions on main bank − debit transactions on main bank − transfers_out_bank + transfers_in_bank
  - Subsequent months: `prev_month_bank_balance` + income transactions on main bank − debit transactions on main bank − transfers_out_bank + transfers_in_bank

### 5. Asset Computation (computed at query time, year-to-date)

**Opening balances** read from `app_settings` keys:
- `opening_saving_balance_{name}` (e.g. `opening_saving_balance_CAAB`)
- `opening_investment_balance_{name}`

**Saving (per account name):**
`= opening_saving_balance + Σ transfers_in (to_account_name = name, year-to-date) − Σ transfers_out (from_account_name = name, year-to-date)`

**Investment (per account name):**
`= opening_investment_balance + Σ transfers_in − Σ transfers_out (year-to-date)`

**Pension (AXA/Satispay):**
`= (employer_contrib_rate + voluntary_contrib_rate) × RAL × months_elapsed / 12`
Computed from `salary_config` periods overlapping the year. Manual override in `assets` table replaces this value.

`final_amount = manual_override ?? computed_amount`

### 6. Salary Calculator (Italian law, 2026)

**Step 1 — INPS (employee social security)**
`INPS = RAL × 9.19%`

**Step 2 — Deductible pension contributions**
`deductible = min(employer_contrib + voluntary_contrib, 5164.57)`
(Statutory annual cap for pension fund deductibility.)

**Step 3 — IRPEF taxable base (imponibile)**
`imponibile = RAL − INPS − deductible`

**Step 4 — IRPEF gross — MARGINAL brackets (Legge di Bilancio 2026)**
Applied progressively (cumulative marginal rates — not flat per band):
- First €28,000 → 23% → max €6,440
- €28,001–€50,000 → 33% → max €7,260
- Over €50,000 → 43%

Formula:
```
if imponibile <= 28000:
    irpef = imponibile × 0.23
elif imponibile <= 50000:
    irpef = 6440 + (imponibile − 28000) × 0.33
else:
    irpef = 6440 + 7260 + (imponibile − 50000) × 0.43
```

**Step 5 — Detrazioni per lavoro dipendente (full-year employment assumed)**
- imponibile ≤ €15,000 → **€1,955** (statutory fixed amount for full-year employment — this is intentionally different from the value at the start of the next band; the step discontinuity at the €15,000 boundary is correct per Italian law)
- €15,001–€28,000 → `1,910 + 1,190 × (28,000 − imponibile) / 13,000`
- €28,001–€50,000 → `1,910 × (50,000 − imponibile) / 22,000`
- Over €50,000 → **€0**

**Step 6 — Net IRPEF**
`irpef_netto = max(0, irpef_lordo − detrazione)`

**Step 7 — Regional + municipal add-ons** (applied on imponibile)
`addizionale_reg = imponibile × regional_tax_rate`
`addizionale_com = imponibile × municipal_tax_rate`

**Step 8 — Net annual**
`netto_annuale = RAL − INPS − voluntary_contrib − irpef_netto − addizionale_reg − addizionale_com`

**Step 9 — Net monthly**
`netto_mensile = netto_annuale / 12`

Manual override replaces step 9 only; the full breakdown remains visible in the UI.

Meal vouchers and welfare are non-taxable — displayed separately on top of net, not included in `netto_mensile`.

---

## Frontend Pages

All pages mobile-first responsive (Tailwind CSS breakpoints).

### Dashboard
- Current month card: bank balance, total incomes, total outcomes
- Outcome breakdown bar by payment method
- Asset summary strip: savings, investments, pension (year-to-date)
- Month navigator (prev/next month)
- Floating quick-add transaction button (mobile)

### Transactions
- List grouped by billing month; filterable by type, sub-type, payment method, date range
- Installment badge ("2/6"), recurring indicator per row
- Child installment transactions appear individually in the list
- Add/edit form:
  - All transaction fields
  - Payment method → if CC/revolving: "billing month: [next month]" read-only hint auto-shown
  - "Repeat for N months" recurrence selector
  - "Split into N installments" selector (shown only for credit_card/revolving methods)
  - Both recurrence and installments cannot be active simultaneously (UI enforces)
- Delete with cascade prompt for recurring series: "This / This and future / All"

### Monthly Summary
- Year grid: 12 columns × rows (bank balance, incomes, outcomes by payment method)
- Click month → drill into its transactions filtered by billing_month
- Current month highlighted

### Transfers
- List: from/to accounts, amounts, dates
- Add transfer form: from account type+name, to account type+name, amount, date, recurrence, notes
- Shows computed impact on asset balances

### Assets
- Per year: computed year-to-date amount vs manual override, shown side by side
- Manual override input per asset row
- Opening balances editable via Settings

### Salary Config
- RAL input with full computed breakdown:
  - INPS, imponibile, IRPEF per bracket, detrazione, addizionali, net annual, net monthly
- Manual net override toggle (when active, computed fields shown as reference only)
- Timeline of config periods with `valid_from` dates; "Add new period" button

### Settings
- **Payment methods:** add, rename, set `is_main_bank`, toggle type, deactivate
- **Categories:** add, rename, deactivate
- **Opening balances:** set initial bank, saving, investment balances for 2026-01
- **User management:** add/remove basic auth accounts, view OIDC-linked accounts
- **OIDC config:** display-only (driven by env vars)

---

## API Endpoints

All endpoints prefixed `/api/v1/`. All require authentication (JWT cookie) except auth routes.

### Auth
| Method | Path | Description |
|--------|------|-------------|
| POST | `/auth/login` | Basic auth login → JWT cookie |
| GET | `/auth/oidc/login` | Redirect to OIDC provider |
| GET | `/auth/oidc/callback` | OIDC callback → JWT cookie |
| POST | `/auth/logout` | Clear JWT cookie |

### Transactions
| Method | Path | Description |
|--------|------|-------------|
| GET | `/transactions` | List, filterable by `billing_month`, `type`, `payment_method_id`, `parent_id` (used internally by the edit form to load all installment children of a parent) |
| POST | `/transactions` | Create (handles recurrence + installment generation) |
| GET | `/transactions/{id}` | Get single |
| PUT | `/transactions/{id}` | Update (re-generates children if installments) |
| DELETE | `/transactions/{id}` | Delete with `cascade` query param: `single|future|all` |

### Transfers
| Method | Path | Description |
|--------|------|-------------|
| GET | `/transfers` | List, filterable by month, account |
| POST | `/transfers` | Create (handles recurrence) |
| PUT | `/transfers/{id}` | Update |
| DELETE | `/transfers/{id}` | Delete. Accepts `cascade` query param: `single|future|all` — identical behavior to transaction recurrence delete |

### Summary
| Method | Path | Description |
|--------|------|-------------|
| GET | `/summary/{year}` | Full year monthly grid |
| GET | `/summary/{year}/{month}` | Single month breakdown |

### Assets
| Method | Path | Description |
|--------|------|-------------|
| GET | `/assets/{year}` | Asset list with computed + override amounts |
| PUT | `/assets/{year}/{asset_type}/{asset_name}` | Set manual override |

### Salary
| Method | Path | Description |
|--------|------|-------------|
| GET | `/salary` | List all config periods |
| POST | `/salary` | Add new period (valid_from required) |
| PUT | `/salary/{id}` | Update period |
| DELETE | `/salary/{id}` | Delete period (not the last one) |
| GET | `/salary/calculate` | Compute net salary from params (no save). **Must be registered before `GET /salary/{id}` in FastAPI to avoid route conflict.** Query params: `ral`, `employer_contrib_rate`, `voluntary_contrib_rate`, `regional_tax_rate`, `municipal_tax_rate`. Returns full breakdown: `{ral, inps, deductible, imponibile, irpef_lordo, detrazione, irpef_netto, addizionale_reg, addizionale_com, netto_annuale, netto_mensile, meal_vouchers_monthly, welfare_monthly}` |

### Settings & Reference
| Method | Path | Description |
|--------|------|-------------|
| GET | `/payment-methods` | List |
| POST | `/payment-methods` | Create |
| PUT | `/payment-methods/{id}` | Update (includes is_main_bank toggle) |
| GET | `/categories` | List |
| POST | `/categories` | Create |
| PUT | `/categories/{id}` | Update |
| GET | `/settings` | Get app settings (opening balances etc.) |
| PUT | `/settings` | Update app settings |
| GET | `/users` | List users |
| POST | `/users` | Create basic auth user |
| DELETE | `/users/{id}` | Delete user |

**Error responses:** all errors return `{"detail": "message"}` with standard HTTP codes: 400 bad request, 401 unauthorized, 404 not found, 422 validation error.

**Deactivated items:** payment methods and categories with `is_active = false` are hidden from transaction creation/edit forms only. They remain visible in filter dropdowns and historical list views (to preserve the integrity of past transactions that used them).

**Pagination:** list endpoints support `?limit=50&offset=0` query params.

---

## Timezone

Transaction `date` fields are interpreted in the timezone configured via `TZ` env var (default: `Europe/Rome`). The backend must apply this timezone when computing `billing_month` from a date to avoid midnight-boundary misclassification.

---

## Docker & Deployment

### Services
```yaml
services:
  backend:
    build: ./backend
    ports: ["8000:8000"]
    volumes:
      - ./data:/app/data     # bind mount directory; SQLite file at /app/data/cashflow.db
    env_file: .env

  frontend:
    build: ./frontend
    ports: ["3000:3000"]
    environment:
      - VITE_API_BASE_URL=${VITE_API_BASE_URL:-http://localhost:8000}
    depends_on: [backend]
```

The `./data` directory is bind-mounted (directory, not file). Docker creates it if absent. The SQLite file is created inside by the backend on first run. This avoids the Docker file-mount-creates-directory footgun.

### Environment Variables (`.env`)
```
# Database
DB_PATH=/app/data/cashflow.db

# Auth
SECRET_KEY=<jwt-secret>
JWT_EXPIRE_DAYS=30
BASIC_AUTH_ENABLED=true

# OIDC
OIDC_ENABLED=true
OIDC_ISSUER_URL=https://auth.yourdomain.com/application/o/cashflow/
OIDC_CLIENT_ID=...
OIDC_CLIENT_SECRET=...
OIDC_REDIRECT_URI=https://cashflow.yourdomain.com/api/v1/auth/oidc/callback

# App
ALLOWED_ORIGINS=https://cashflow.yourdomain.com,http://localhost:3000
VITE_API_BASE_URL=http://localhost:8000
```

`localhost:3000` is always included in `ALLOWED_ORIGINS` to support local development without a separate compose override file. `ALLOWED_ORIGINS` is wired to FastAPI's `CORSMiddleware` at startup.

Account names used in transfers and `app_settings` keys must be alphanumeric with hyphens/underscores only (e.g. `CAAB`, `PAC-FINECO`). The API validates and returns HTTP 422 for invalid names.

### Project Structure
```
cashflow/
├── docker-compose.yml
├── .env.example
├── backend/
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── alembic/              # DB migrations
│   └── app/
│       ├── main.py
│       ├── models/           # SQLAlchemy models
│       ├── routers/          # API route handlers
│       ├── services/         # business logic (billing, installments, salary, assets)
│       └── schemas/          # Pydantic request/response schemas
├── frontend/
│   ├── Dockerfile
│   ├── nginx.conf
│   └── src/
│       ├── pages/
│       ├── components/
│       ├── api/              # typed API client
│       └── hooks/
└── data/                     # gitignored; SQLite + any exports live here
```

---

## Seed Data (on first run)

- Payment methods: BB-FINECO (main bank, type=bank), CC-AMEXGC (credit_card), CC-AMEXB (credit_card), CC-FINDOMESTIC (revolving), CC-FINECO (credit_card), CC-YOU (credit_card)
- Categories: all type/sub-type pairs from the table in the Data Model section
- Salary config: one row with `valid_from: 2026-01-01`, RAL €60,000, INPS 9.19%, regional 1.23%, municipal 0.80%
- App settings: `opening_bank_balance = 0` (user sets this in Settings on first login)
- No transaction data — user enters from 2026-01-01
