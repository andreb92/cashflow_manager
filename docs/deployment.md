# Deployment Guide

## Prerequisites

- Docker Engine 24+ and Docker Compose v2
- A host directory for persistent data (the SQLite database)
- Ports 80 (or your chosen port) available, or a reverse proxy

---

## Quick Deploy

```bash
cd deploy/
cp .env.example .env
# edit .env — at minimum set SECRET_KEY, SESSION_ENCRYPTION_KEY, APP_UID, APP_GID
docker compose up -d
```

The app is available at `http://<host>:80`.

The `deploy/data/` directory holds the SQLite database. Back it up regularly.

---

## Production Checklist

- [ ] `SECRET_KEY` is a random 32-byte hex string (not the default)
- [ ] `SESSION_ENCRYPTION_KEY` is a random 32-byte hex string (not the default)
- [ ] `APP_UID` / `APP_GID` match the owner of `deploy/data/` on the host
- [ ] `ALLOWED_ORIGINS` is set to your actual domain (e.g. `https://cashflow.example.com`)
- [ ] Traffic is served over HTTPS (via a reverse proxy)
- [ ] `deploy/.env` is not committed to version control

Generate secrets:

```bash
python3 -c "import secrets; print(secrets.token_hex(32))"
```

---

## Reverse Proxy

### Nginx

```nginx
server {
    listen 443 ssl;
    server_name cashflow.example.com;

    ssl_certificate     /etc/ssl/certs/cashflow.crt;
    ssl_certificate_key /etc/ssl/private/cashflow.key;

    location / {
        proxy_pass         http://127.0.0.1:8080;
        proxy_set_header   Host $host;
        proxy_set_header   X-Real-IP $remote_addr;
        proxy_set_header   X-Forwarded-Proto https;
    }
}
```

Update `deploy/docker-compose.yml` to expose only `127.0.0.1:8080:8080` (bind to loopback) and set `ALLOWED_ORIGINS=https://cashflow.example.com` in `.env`.

### Caddy

```caddy
cashflow.example.com {
    reverse_proxy localhost:8080
}
```

Caddy handles TLS automatically via Let's Encrypt.

### Traefik

Label the service in `docker-compose.yml`:

```yaml
services:
  app:
    image: ghcr.io/your-username/cashflow-manager:latest
    labels:
      - "traefik.enable=true"
      - "traefik.http.routers.cashflow.rule=Host(`cashflow.example.com`)"
      - "traefik.http.routers.cashflow.entrypoints=websecure"
      - "traefik.http.routers.cashflow.tls.certresolver=letsencrypt"
      - "traefik.http.services.cashflow.loadbalancer.server.port=8080"
```

---

## Upgrading

The image version is set in `deploy/docker-compose.yml`. To upgrade:

```bash
cd deploy/
# edit docker-compose.yml: update image tag to new version
docker compose pull
docker compose up -d
```

Alembic migrations run automatically on startup — no manual migration step is needed.

The CI/CD pipeline auto-updates `deploy/docker-compose.yml` with the latest version on every release (via semantic-release). If you track the `main` branch, pull the repo and re-deploy:

```bash
git pull
cd deploy/
docker compose pull
docker compose up -d
```

---

## Backup and Restore

The entire application state lives in one file:

```bash
# Backup
cp deploy/data/cashflow.db deploy/data/cashflow.db.bak
# or with timestamp:
cp deploy/data/cashflow.db "deploy/data/cashflow-$(date +%Y%m%d).db"

# Restore
docker compose down
cp cashflow-20260101.db deploy/data/cashflow.db
docker compose up -d
```

For automated backups, consider a cron job or a tool like `litestream` for continuous replication.

---

## User Management

There is no admin panel. Users register themselves via the `/register` page when `BASIC_AUTH_ENABLED=true`. To force OIDC-only access or disable all password-based authentication, set `BASIC_AUTH_ENABLED=false`. That disables both `/register` and `/login`; OIDC sign-in continues to work if configured.

To delete a user, connect to the database directly:

```bash
sqlite3 deploy/data/cashflow.db "DELETE FROM users WHERE email = 'user@example.com';"
```

All user-owned data (transactions, payment methods, etc.) will cascade-delete.

---

## OIDC Setup

See [authentication.md](authentication.md) for the full OIDC configuration walkthrough.

Summary of required env vars:

```env
OIDC_ENABLED=true
OIDC_ISSUER_URL=https://auth.example.com/realms/myrealm/
OIDC_CLIENT_ID=cashflow
OIDC_CLIENT_SECRET=<your-client-secret>
OIDC_REDIRECT_URI=https://cashflow.example.com/api/v1/auth/oidc/callback
```

---

## Container User Mapping

The container runs as the UID/GID supplied via `APP_UID` / `APP_GID` in `.env`. This must match the owner of the `deploy/data/` directory so the process can read and write the SQLite database.

```bash
# Find your host user's UID and GID
id -u    # e.g. 1000
id -g    # e.g. 1000
```

Set these in `.env`:

```env
APP_UID=1000
APP_GID=1000
```

If you see permission errors on startup, verify ownership:

```bash
ls -la deploy/data/
# should match APP_UID:APP_GID
chown -R 1000:1000 deploy/data/
```
