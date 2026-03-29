# Authentication

CashFlow Manager supports two authentication methods, independently configurable via environment variables. Both can be active simultaneously.

---

## Basic Auth (Username/Password)

Enabled when `BASIC_AUTH_ENABLED=true` (default).

### Registration

`POST /api/v1/auth/register` — public endpoint.

```json
{ "email": "user@example.com", "password": "secret" }
```

Returns a `200` with an `access_token` httpOnly cookie set. Returns `409` if the email is already registered.

### Login

`POST /api/v1/auth/login`

```json
{ "email": "user@example.com", "password": "secret" }
```

Returns `200` with `access_token` cookie. Returns `401` on invalid credentials.

### Passwords

Stored as bcrypt hashes. Never stored or logged in plaintext.

### Disabling

Setting `BASIC_AUTH_ENABLED=false` disables the `/register` and `/login` endpoints. Existing basic-auth users who also have an OIDC account (same email) can still log in via OIDC. Existing basic-auth-only users cannot log in until the setting is re-enabled.

---

## OIDC

Enabled when `OIDC_ENABLED=true`. Requires a configured OIDC provider.

### Required env vars

```env
OIDC_ENABLED=true
OIDC_ISSUER_URL=https://auth.example.com/realms/myrealm/
OIDC_CLIENT_ID=cashflow
OIDC_CLIENT_SECRET=<client-secret>
OIDC_REDIRECT_URI=https://cashflow.example.com/api/v1/auth/oidc/callback
```

### Provider setup

Register a confidential client in your OIDC provider with:

- **Redirect URI:** `https://cashflow.example.com/api/v1/auth/oidc/callback`
- **Scopes:** `openid email profile`
- **Grant type:** Authorization Code

The application discovers provider endpoints automatically from `{OIDC_ISSUER_URL}/.well-known/openid-configuration`.

### Login flow

1. User clicks "Login with SSO"
2. Browser redirects to `GET /api/v1/auth/oidc/login` → backend redirects to provider authorization endpoint
3. User authenticates at the provider
4. Provider redirects to `OIDC_REDIRECT_URI` with an authorization code
5. Backend exchanges the code for tokens, validates the ID token, creates or updates the user record
6. Two httpOnly cookies are set:
   - `access_token` — JWT (same as basic auth)
   - `oidc_id_token` — AES-GCM encrypted raw ID token (used for RP-initiated logout)

### Logout flow

`GET /api/v1/auth/oidc/logout`

1. Clears `access_token` and `oidc_id_token` cookies
2. If the provider advertises `end_session_endpoint` and `oidc_id_token` cookie is present, performs RP-initiated logout (redirects to provider's logout page with `id_token_hint` and `post_logout_redirect_uri`)
3. Falls back to local-only logout if the provider does not support `end_session_endpoint` or the cookie is absent/expired

---

## Account Merging

Email is the merge key. A user who registered via basic auth and later logs in via OIDC with the same email gets their `oidc_sub` written to the existing row — one account, both login methods work.

If the OIDC provider does not include an email claim, merging is not possible and a new separate user is created identified only by `oidc_sub`.

---

## JWT

- httpOnly cookie named `access_token`
- HS256, signed with `SECRET_KEY`
- Expiry configured via `JWT_EXPIRE_DAYS` (default: 30 days)
- No refresh token — on expiry the user re-authenticates
- All authenticated endpoints read the cookie automatically; the frontend never handles the token directly

---

## No Admin Role

All authenticated users have equal access to their own data. Access control is purely by ownership (`user_id`). There is no separate administrator concept.

---

## Common Provider Examples

### Authentik

```env
OIDC_ISSUER_URL=https://authentik.example.com/application/o/cashflow/
OIDC_CLIENT_ID=cashflow
OIDC_CLIENT_SECRET=<secret>
OIDC_REDIRECT_URI=https://cashflow.example.com/api/v1/auth/oidc/callback
```

Create an OAuth2/OIDC provider in Authentik pointing to the redirect URI above, with scopes `openid email profile`.

### Keycloak

```env
OIDC_ISSUER_URL=https://keycloak.example.com/realms/myrealm/
OIDC_CLIENT_ID=cashflow
OIDC_CLIENT_SECRET=<secret>
OIDC_REDIRECT_URI=https://cashflow.example.com/api/v1/auth/oidc/callback
```

Create a confidential client in the realm with the redirect URI and scopes `openid email profile`.

### Auth0

```env
OIDC_ISSUER_URL=https://your-tenant.auth0.com/
OIDC_CLIENT_ID=<client-id>
OIDC_CLIENT_SECRET=<client-secret>
OIDC_REDIRECT_URI=https://cashflow.example.com/api/v1/auth/oidc/callback
```

Add the redirect URI to the allowed callback URLs in the Auth0 application settings.
