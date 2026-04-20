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
Returns `403` if `BASIC_AUTH_ENABLED=false`.

### Passwords

Stored as bcrypt hashes (bcrypt with random salt). Never stored or logged in plaintext.

### Change password

`PUT /api/v1/users/me/password`

```json
{ "current_password": "old-secret", "new_password": "new-secret" }
```

Requires the authenticated user to supply their current password. Returns:
- `200 {"ok": true}` on success
- `401` if `current_password` is wrong
- `422` if `new_password` is shorter than 8 characters
- `400` if the account is OIDC-only (no password to change)

The "Change password" button in **Settings → Account** is visible only to users who have `has_password: true`.

### Current user

`GET /api/v1/auth/me` — returns the currently authenticated user.

Response includes `has_password` and `has_oidc` fields (see [UserOut fields](#userout-fields) below).

### Disabling

Setting `BASIC_AUTH_ENABLED=false` disables both `/register` and `/login`. OIDC sign-in is unaffected. Password-based users cannot authenticate with email/password again until the setting is re-enabled.

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
5. Backend exchanges the code for tokens, validates the ID token, matches the user by `oidc_sub`, and creates a new user row if that provider subject has not been seen before
6. Two httpOnly cookies are set:
   - `access_token` — JWT (same as basic auth)
   - `oidc_id_token` — AES-GCM encrypted raw ID token (used for RP-initiated logout)

### Logout flow

Two logout entrypoints exist:

- `POST /api/v1/auth/logout` — general logout endpoint used by API clients
- `GET /api/v1/auth/oidc/logout` — explicit browser redirect entrypoint

Both endpoints clear `access_token` and `oidc_id_token` cookies. When the provider advertises `end_session_endpoint` and the encrypted `oidc_id_token` cookie is present, they perform RP-initiated logout by redirecting to the provider with `id_token_hint` and `post_logout_redirect_uri`. If the provider does not support RP-initiated logout, or the OIDC session cookie is absent/expired, logout falls back to local-only sign-out.

---

## Account Merging

Accounts are linked by OIDC subject (`oidc_sub`), not by email.

The backend does not auto-link an incoming OIDC login to an existing password-auth account that happens to share the same email. This avoids accidental or malicious account takeover through an IdP-controlled email claim.

If the OIDC provider returns a verified email and that email is not already used by another account, it is stored on the OIDC user row. If the email is missing, unverified, or already claimed by another user, the account is still created and identified only by `oidc_sub`.

---

## JWT

- httpOnly cookie named `access_token`
- HS256, signed with `SECRET_KEY`
- Expiry configured via `JWT_EXPIRE_DAYS` (default: 30 days)
- No refresh token — on expiry the user re-authenticates
- All authenticated endpoints read the cookie automatically; the frontend never handles the token directly

---

## UserOut fields

`UserOut` is returned by `/auth/register`, `/auth/login`, and `/auth/me`. In addition to `id`, `email`, and `name`, it includes:

| Field | Type | Description |
|---|---|---|
| `has_password` | `bool` | Whether the user has a password set (i.e., registered via basic auth). |
| `has_oidc` | `bool` | Whether the user has an OIDC link (`oidc_sub` is set). |

These fields drive frontend behavior — for example, whether to show a password prompt before account deletion.

---

## Account Deletion

`DELETE /api/v1/users/me`

Permanently deletes the authenticated user's account and all associated data.

- **Request body (JSON):** `{"password": "<current_password>"}` for password-auth accounts, or `{}` for OIDC-only accounts
- Returns `401` if the password is wrong or absent for a password-auth account
- On success: clears the `access_token` and `oidc_id_token` cookies and returns `{"ok": true}`

**OIDC-only users** (no password set) must supply an empty `{}` body (the field is optional). They are exempt from the password check.

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
