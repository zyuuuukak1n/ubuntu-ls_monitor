# Ubuntu-LS Monitor: Public Deployment Guide (DEPLOYMENT_GUIDE.md)

This document provides a generalized, production-ready deployment guide for setting up **Ubuntu-LS Monitor** on an Ubuntu/Debian server.

---

## Architecture Overview
- **Backend**: Python 3.11+ (FastAPI + Uvicorn), WebAuthn (`py_webauthn`), SQLite (`0600` permissions), structured JSON audit logs.
- **Frontend**: SPA (React, TypeScript, Tailwind CSS, `@github/webauthn-json`).
- **Authentication**: FIDO2 / WebAuthn passwordless Passkey with invite-token bootstrapping.
- **Sandbox**: Executed under an unprivileged system user (`<service-user>`), restricted `sudoers` whitelist for privileged operations.
- **Reverse Proxy**: Apache2 / Nginx + Cloudflare Tunnel.

---

## 1. Prerequisites
- Ubuntu 22.04 LTS / 24.04 LTS
- Python 3.10+ & `python3-venv`
- Node.js 18+ & `npm`
- Cloudflare Tunnel or Reverse Proxy (Apache / Nginx)

---

## 2. Server User & Directory Setup

```bash
# 1. Create dedicated non-login service user
sudo useradd -r -s /usr/sbin/nologin -d /var/www/<app-name> <service-user>
sudo usermod -aG docker <service-user>

# 2. Clone repository
sudo mkdir -p /var/www/<app-name>
sudo chown -R $USER:www-data /var/www/<app-name>
cd /var/www/<app-name>
git clone <repository-url> .

# 3. Create persistent directories
mkdir -p backend/data backend/logs
sudo chown -R <service-user>:<service-user> backend/data backend/logs
sudo chmod 700 backend/data backend/logs
```

---

## 3. Backend & Frontend Build

### Backend
```bash
cd /var/www/<app-name>/backend
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
deactivate
```

### Frontend
```bash
cd /var/www/<app-name>/frontend
npm install
npm run build
```

---

## 4. Configuration & Privileged Sandboxing

### Sudoers Whitelist (`/etc/sudoers.d/dashboard`)
```bash
sudo cp deploy/dashboard.sudoers /etc/sudoers.d/dashboard
sudo chmod 0440 /etc/sudoers.d/dashboard
sudo visudo -cf /etc/sudoers.d/dashboard
```

### Environment Variables (`.env`)
```bash
cd /var/www/<app-name>/backend
cp ../.env.example .env
vi .env
```
Ensure you configure:
- `RP_NAME`: Your chosen human-readable name.
- `RP_ID`: Your effective domain (e.g. `monitor.example.com`).
- `EXPECTED_ORIGIN`: Your exact FQDN with protocol (e.g. `https://monitor.example.com`).
- `SESSION_SECRET`: 64-char random hex string (`python3 -c "import secrets; print(secrets.token_hex(32))"`).

Secure the configuration file:
```bash
chmod 600 .env
sudo chown <service-user>:<service-user> .env
```

---

## 5. Systemd Service Daemon

```bash
sudo cp deploy/dashboard.service /etc/systemd/system/dashboard.service
sudo systemctl daemon-reload
sudo systemctl enable dashboard.service
sudo systemctl start dashboard.service
```

---

## 6. Initial Admin Passkey Bootstrapping

Because open user registration is completely disabled, generate a 15-minute one-time bootstrap invite link on the server:

```bash
cd /var/www/<app-name>/backend
source venv/bin/activate
python manage.py create-invite
```

1. Navigate to the generated URL (`https://<domain>/#invite=<token>`).
2. Enter your desired administrator username and device label.
3. Complete the biometric / hardware prompt on your browser.
4. The token is consumed immediately upon successful Passkey creation.
