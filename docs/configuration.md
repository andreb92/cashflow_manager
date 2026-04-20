# Configuration Reference

All configuration is via environment variables. In production, place them in `deploy/.env`. In development, use the root `.env` file (see `.env.example`).

---

## Required Variables

These have no safe default and **must** be set in production.

| Variable | Description | How to generate |
|---|---|---|
| `SECRET_KEY` | JWT signing key. Rotating this logs all users out. | `python3 -c "import secrets; print(secrets.token_hex(32))"` |
| `SESSION_ENCRYPTION_KEY` | AES-GCM key for encrypting OIDC `id_token` cookies. Rotating this invalidates all OIDC sessions. | `python3 -c "import secrets; print(secrets.token_hex(32))"` |

---

## Database

| Variable | Default | Description |
|---|---|---|
| `DB_PATH` | `/app/data/cashflow.db` | Absolute path inside the container. The directory must be writable and bind-mounted from the host. Do not change unless you have a specific reason. |

---

## Security & Sessions

| Variable | Default | Description |
|---|---|---|
| `JWT_EXPIRE_DAYS` | `30` | JWT token lifetime in days. Users are logged out after this period. |
| `ALLOWED_ORIGINS` | `http://localhost:3000` | Comma-separated list of CORS-allowed origins. In production set to your exact domain, e.g. `https://cashflow.example.com`. |

---

## Authentication

| Variable | Default | Description |
|---|---|---|
| `BASIC_AUTH_ENABLED` | `true` | Enable username/password registration (`POST /api/v1/auth/register`) and login (`POST /api/v1/auth/login`). Set to `false` to disable password auth entirely or force OIDC-only. |
| `OIDC_ENABLED` | `false` | Enable OIDC login. Requires the four `OIDC_*` variables below. |
| `OIDC_ISSUER_URL` | — | Base URL of the OIDC provider, e.g. `https://auth.example.com/realms/myrealm/`. Must include trailing slash. Used for OIDC discovery (appends `.well-known/openid-configuration`). |
| `OIDC_CLIENT_ID` | — | Client ID registered with the OIDC provider. |
| `OIDC_CLIENT_SECRET` | — | Client secret. |
| `OIDC_REDIRECT_URI` | — | Callback URL that the OIDC provider redirects to after authentication. Must be registered with the provider. Example: `https://cashflow.example.com/api/v1/auth/oidc/callback`. |

---

## Container & Runtime

| Variable | Default | Description |
|---|---|---|
| `APP_UID` | `1000` | Host UID that the container process runs as. Must own `deploy/data/`. |
| `APP_GID` | `1000` | Host GID that the container process runs as. |
| `TZ` | `Europe/Rome` | Container timezone. Affects timestamp display, billing month boundaries, and recurring transaction scheduling. Use a valid TZ database name (e.g. `America/New_York`, `UTC`). |

---

## Development-only

These variables are read by Vite during the frontend build and are not used at runtime.

| Variable | Default | Description |
|---|---|---|
| `VITE_API_BASE_URL` | — | API base URL for the frontend. Only needed when running Vite's dev server against a remote backend. In production the Nginx proxy makes this unnecessary. |
| `DEVELOPMENT_MODE` | `false` | When `true`, bypasses the startup insecure-defaults check. Required for local development when using non-production `SECRET_KEY`/`SESSION_ENCRYPTION_KEY`. |

---

## Full `.env` Template

See `deploy/.env.example` for the production template, or `.env.example` at the repo root for the development template.

---

## Notes

- All variables are optional except `SECRET_KEY` and `SESSION_ENCRYPTION_KEY` in production (without them the backend will raise a `ValueError` and fail to start unless `DEVELOPMENT_MODE=true`).
- `BASIC_AUTH_ENABLED` and `OIDC_ENABLED` can be toggled independently without data loss. OIDC users are matched by provider subject (`oidc_sub`); the backend does not auto-link them to an existing password-auth account by shared email.
- Changing `TZ` does not retroactively shift stored timestamps; it affects how new timestamps and billing boundaries are computed.
