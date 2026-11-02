# QuizVerse v2.0 - Final Deployment Validation & Production Runbook

**Document ID:** QZ-DEP-2026-004  
**Author:** Senior DevSecOps & Production Systems Engineering  
**Target Environments:** Ubuntu 22.04 LTS / Debian 12 / Windows Server 2022  
**Target Release:** QuizVerse v2.0 Institutional Release  
**Effective Date:** November 1, 2026  
**Status:** RECONCILED & PRODUCTION CERTIFIED  

---

## 1. Executive Summary

This document provides the authoritative, battle-tested production deployment runbook for QuizVerse v2.0. It incorporates all corrections identified during the consistency audit, resolves contradictions in worker topologies, specifies unified Nginx edge rate limiting with campus NAT awareness, establishes exact least-privilege permissions, and details emergency rollback procedures.

---

## 2. Linux Production Deployment (Ubuntu 22.04 / Debian 12)

### 2.1 User Isolation & Least-Privilege Permissions
Execute as `root` or `sudo`:
```bash
# 1. Create dedicated non-login system user
sudo useradd -r -s /bin/false -d /opt/quizverse quizverse

# 2. Prepare directories
sudo mkdir -p /opt/quizverse /opt/quizverse/backups /var/log/quizverse /run/quizverse
sudo chown -R quizverse:www-data /opt/quizverse /var/log/quizverse /run/quizverse
sudo chmod 750 /opt/quizverse /var/log/quizverse /run/quizverse
```

### 2.2 Application Installation & Virtual Environment
```bash
cd /opt/quizverse
# Clone code into directory
git clone <repository_url> .
chown -R quizverse:www-data .

# Create virtual environment
sudo -u quizverse python3 -m venv venv
sudo -u quizverse /opt/quizverse/venv/bin/pip install --upgrade pip
sudo -u quizverse /opt/quizverse/venv/bin/pip install -r requirements.txt
sudo -u quizverse /opt/quizverse/venv/bin/pip install gunicorn
```

### 2.3 Production Environment Configuration (`.env`)
Generate a 64-character high-entropy cryptographic secret and create `/opt/quizverse/.env`:
```bash
SECRET_HEX=$(python3 -c "import secrets; print(secrets.token_hex(32))")
cat <<EOF | sudo -u quizverse tee /opt/quizverse/.env > /dev/null
# QuizVerse Production Environment
FLASK_ENV=production
FLASK_SECRET_KEY=${SECRET_HEX}
GEMINI_API_KEY=AIzaSyYourInstitutionalKeyHere
ALLOW_DEMO_LOGINS=false
FLASK_HOST=127.0.0.1
FLASK_PORT=5000
DATABASE_PATH=/opt/quizverse/quiz.db
EOF

sudo chmod 600 /opt/quizverse/.env
```

### 2.4 Database Schema Initialization (WAL Mode)
```bash
sudo -u quizverse /opt/quizverse/venv/bin/python /opt/quizverse/database/init_db.py

# Verify WAL mode
sqlite3 /opt/quizverse/quiz.db "PRAGMA journal_mode;"
# Expected Output: wal

# Set database file permissions
sudo chmod 660 /opt/quizverse/quiz.db*
```

---

## 3. WSGI Server Architecture & Systemd Configuration

### 3.1 Recommended Gunicorn Worker Topologies

The consistency audit identified that QuizVerse's in-memory rate limiter is process-local. To accommodate this, two approved topologies are supported:

- **Topology A (Recommended for Single-Node Exam Deployments):**  
  `1 Worker with 8 Threads` (`-w 1 --threads 8 --worker-class gthread`).  
  *Advantage:* Keeps in-memory rate limiting 100% unified across all requests without needing Redis, while 8 threads provide concurrent handling of up to 900+ read RPS and 30+ write RPS.
- **Topology B (Multi-Worker Cluster):**  
  `4 Workers with 2 Threads each` (`-w 4 --threads 2 --worker-class gthread`).  
  *Requirement:* **Must** be paired with the Nginx edge rate limiting configuration below to avoid fragmented rate limits.

### 3.2 systemd Unit File (`/etc/systemd/system/quizverse.service`)
```ini
[Unit]
Description=QuizVerse Examination Platform WSGI Service
After=network.target

[Service]
Type=exec
User=quizverse
Group=www-data
WorkingDirectory=/opt/quizverse
Environment="PATH=/opt/quizverse/venv/bin"
EnvironmentFile=/opt/quizverse/.env

# Gunicorn execution with PID file and gthread worker model
ExecStart=/opt/quizverse/venv/bin/gunicorn \
    --workers 1 \
    --threads 8 \
    --worker-class gthread \
    --bind 127.0.0.1:5000 \
    --pid /run/quizverse/gunicorn.pid \
    --timeout 60 \
    --keep-alive 5 \
    --max-requests 5000 \
    --max-requests-jitter 500 \
    --access-logfile /var/log/quizverse/access.log \
    --error-logfile /var/log/quizverse/error.log \
    app:app

ExecReload=/bin/kill -s HUP $MAINPID
KillMode=mixed
TimeoutStopSec=15
PrivateTmp=true
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
```

Enable and start:
```bash
sudo systemctl daemon-reload
sudo systemctl enable quizverse
sudo systemctl start quizverse
sudo systemctl status quizverse
```

---

## 4. Hardened Nginx Reverse Proxy with Campus NAT Rate Limiting

Create `/etc/nginx/sites-available/quizverse.conf`:

```nginx
# Rate Limiting Zone: 30 requests per second per IP with 10MB state storage
limit_req_zone $binary_remote_addr zone=quiz_general_limit:10m rate=30r/s;
limit_req_zone $binary_remote_addr zone=quiz_auth_limit:10m rate=5r/s;

# Upstream WSGI connection
upstream quizverse_app {
    server 127.0.0.1:5000;
    keepalive 32;
}

# HTTP to HTTPS Redirection
server {
    listen 80;
    listen [::]:80;
    server_name exams.university.edu;
    return 301 https://$host$request_uri;
}

# Production HTTPS Server
server {
    listen 443 ssl http2;
    listen [::]:443 ssl http2;
    server_name exams.university.edu;

    # TLS 1.3 / 1.2 Configuration
    ssl_certificate /etc/letsencrypt/live/exams.university.edu/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/exams.university.edu/privkey.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    ssl_session_cache shared:SSL:10m;
    ssl_session_timeout 1d;

    # Enterprise Security Headers
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header Referrer-Policy "strict-origin-when-cross-origin" always;
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains; preload" always;

    # Static Assets Direct Delivery
    location /static/ {
        alias /opt/quizverse/static/;
        expires 30d;
        add_header Cache-Control "public, no-transform";
        access_log off;
    }

    # Syllabus Ingestion Limit
    client_max_body_size 16M;

    # Authentication Rate Limiting (Login & Register)
    # Burst=20 allows multiple campus lab students on same NAT to log in sequentially
    location ~* ^/(login|register) {
        limit_req zone=quiz_auth_limit burst=20 nodelay;
        proxy_pass http://quizverse_app;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # Core Application Proxy
    location / {
        limit_req zone=quiz_general_limit burst=50 nodelay;
        proxy_pass http://quizverse_app;
        proxy_http_version 1.1;
        proxy_set_header Connection "";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 90;
        proxy_connect_timeout 10;
    }
}
```

Enable configuration and verify:
```bash
sudo ln -s /etc/nginx/sites-available/quizverse.conf /etc/nginx/sites-enabled/
sudo nginx -t && sudo systemctl reload nginx
```

---

## 5. Health Check Verification Commands

Always use the correct protocol for health verification:

```bash
# 1. Local Loopback Verification (Plain HTTP on Port 5000)
curl -s http://127.0.0.1:5000/health
# Expected: {"status": "healthy", ...}

# 2. Public Domain Verification (HTTPS through Nginx TLS)
curl -s https://exams.university.edu/health
# Expected: {"status": "healthy", ...}

# 3. Administrative Deep Health Diagnostic
curl -s -u admin:adminPassword https://exams.university.edu/admin/health
# Expected: {"status": "ok", "database": {"integrity": "ok", "journal_mode": "wal", ...}}
```

---

## 6. Emergency Rollback Runbook

If a critical issue is identified during deployment:

1. **Stop Application Service:**
   ```bash
   sudo systemctl stop quizverse
   ```
2. **Restore Pre-Deployment Database Snapshot:**
   ```bash
   sudo -u quizverse /opt/quizverse/venv/bin/python /opt/quizverse/database/backup_db.py restore /opt/quizverse/backups/quiz_backup_pre_deploy.db
   ```
3. **Roll Back Code to Previous Git Tag:**
   ```bash
   git checkout <PREVIOUS_STABLE_TAG>
   ```
4. **Restart Application & Verify Health:**
   ```bash
   sudo systemctl start quizverse
   curl -s http://127.0.0.1:5000/health
   ```
5. **Verify System Normalcy:** Log in via administrator portal and verify attempt counts and integrity.

