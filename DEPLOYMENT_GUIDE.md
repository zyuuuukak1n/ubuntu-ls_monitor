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
- `PORT`: App port (e.g. `8005`).
- `RP_NAME`: Your chosen human-readable name.
- `RP_ID`: Your effective domain (e.g. `monitor.example.com`).
- `EXPECTED_ORIGIN`: Your exact FQDN with protocol (e.g. `https://monitor.example.com`).
- `SESSION_SECRET`: 64-char random hex string (`python3 -c "import secrets; print(secrets.token_hex(32))"`).

Secure the configuration file:
```bash
# Allow read access for non-root deployer user and service agent
sudo chown $USER:<service-user> .env
chmod 640 .env
```

---

## 5. Web Server / Reverse Proxy Setup (Apache2)

Configure Apache2 as a reverse proxy for SPA static files and FastAPI backend:

```bash
# Copy and edit configuration template
sudo cp deploy/apache-ubuntu-ls.conf /etc/apache2/sites-available/<app-name>.conf
sudo vi /etc/apache2/sites-available/<app-name>.conf

# Enable required Apache modules
sudo a2enmod proxy proxy_http headers rewrite

# Enable site and reload
sudo a2ensite <app-name>.conf
sudo apache2ctl configtest
sudo systemctl reload apache2
```

---

## 6. Cloudflare Tunnel Configuration & Routing

Cloudflare Tunnel exposes internal services securely to the internet without opening router ports.

### A. Identify Tunnel Management Mode

Check whether your `cloudflared` daemon is **Remotely-managed** (via Cloudflare Zero Trust Dashboard) or **Locally-managed** (via `/etc/cloudflared/config.yml`):

```bash
sudo journalctl -u cloudflared -n 25 --no-pager
```

- **Remotely-managed**: Log contains `Updated to new configuration config="..." version=...`. Settings in `/etc/cloudflared/config.yml` are ignored.
- **Locally-managed**: Log indicates reading config from `/etc/cloudflared/config.yml`.

---

### B. Setup for Remotely-managed Mode (Recommended / Standard)

1. Open [Cloudflare Zero Trust Dashboard](https://one.dash.cloudflare.com/).
2. Navigate to **Networks** > **Tunnels**.
3. Select your active tunnel (Status: `HEALTHY`) and click **Configure**.
4. Go to the **Public Hostnames** tab and click **Add a public hostname**:
   - **Subdomain**: `<subdomain>` (e.g. `monitor`)
   - **Domain**: `<your-domain.com>`
   - **Path**: Leave blank
   - **Service**:
     - **Type**: `HTTP`
     - **URL**: `localhost:80` (or `127.0.0.1:80` forwarding to Apache VirtualHost)
5. Click **Save hostname**.
   - Cloudflare automatically registers the CNAME DNS record and pushes config to `cloudflared` within seconds.

---

### C. Setup for Locally-managed Mode

1. Edit `/etc/cloudflared/config.yml`:
```bash
sudo vi /etc/cloudflared/config.yml
```
2. Insert ingress rule before the final catch-all (`- service: http_status:404`):
```yaml
  - hostname: monitor.example.com
    service: http://127.0.0.1:80
```
3. Route DNS record & validate:
```bash
cloudflared tunnel route dns <tunnel-uuid> monitor.example.com
sudo cloudflared tunnel --config /etc/cloudflared/config.yml ingress validate
sudo systemctl restart cloudflared
```

---

## 7. Systemd Service Daemon

```bash
sudo cp deploy/dashboard.service /etc/systemd/system/dashboard.service
sudo systemctl daemon-reload
sudo systemctl enable dashboard.service
sudo systemctl start dashboard.service
```

Verify backend health:
```bash
curl -s http://127.0.0.1:8005/api/health
# Response: {"status":"ok","app":"ubuntu-ls-monitor"}
```

---

## 8. Initial Admin Passkey Bootstrapping

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

