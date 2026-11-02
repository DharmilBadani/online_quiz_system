# QuizVerse v2.0 - Final Production Deployment Runbook & Operating Procedures

**Document ID:** QZ-RUN-2026-001  
**Target Environments:** Ubuntu 22.04 LTS / Debian 12 (Linux Server)  
**WSGI Architecture:** Gunicorn 22.0.0 (`gthread`) + Nginx 1.20+ (TLS 1.3) + SQLite 3.45+ (WAL Mode)  
**Effective Date:** November 2, 2026  
**Status:** AUTHORITATIVE INSTITUTIONAL RUNBOOK  

---

## 1. System Requirements & Hardware Sizing

- **Target Exam Cohort:** Up to 500 active staggered examinees per single node.
- **Minimum Hardware:** 4 x86_64 CPU cores (Intel Xeon or AMD EPYC), 8 GB RAM, 50 GB NVMe SSD storage.
- **Operating System:** Ubuntu 22.04 LTS Server or Debian 12 (fresh minimal install).
- **Network:** 1 Gbps NIC, dedicated public IP, DNS A record (e.g. `exams.university.edu`).

---

## 2. Step-by-Step Production Installation

### Step 2.1: System Preparation & User Isolation
```bash
# Update system packages
sudo apt update && sudo apt upgrade -y
sudo apt install -y python3 python3-venv python3-pip sqlite3 nginx certbot python3-certbot-nginx awscli

# Create non-login application service user
sudo useradd -r -s /bin/false -d /opt/quizverse quizverse

# Create application and log directories with least privilege
sudo mkdir -p /opt/quizverse /opt/quizverse/backups /var/log/quizverse /run/quizverse
sudo chown -R quizverse:www-data /opt/quizverse /var/log/quizverse /run/quizverse
sudo chmod 750 /opt/quizverse /var/log/quizverse /run/quizverse
```

### Step 2.2: Application Deployment & Virtual Environment
```bash
cd /opt/quizverse
git clone <institutional_repo_url> .
sudo chown -R quizverse:www-data .

# Create virtual environment
sudo -u quizverse python3 -m venv venv
sudo -u quizverse /opt/quizverse/venv/bin/pip install --upgrade pip
sudo -u quizverse /opt/quizverse/venv/bin/pip install -r requirements.txt
sudo -u quizverse /opt/quizverse/venv/bin/pip install gunicorn
```

### Step 2.3: Environment Configuration (`.env`)
Generate a unique 64-character cryptographic secret and write the production environment file:
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

### Step 2.4: Database Initialization in WAL Mode
```bash
# Initialize schema and apply composite indexes
sudo -u quizverse /opt/quizverse/venv/bin/python /opt/quizverse/database/init_db.py

# Verify WAL mode
sqlite3 /opt/quizverse/quiz.db "PRAGMA journal_mode;"
# Output must be: wal

# Secure database permissions
sudo chmod 660 /opt/quizverse/quiz.db*
```

---

## 3. WSGI Server Configuration (Gunicorn & Systemd)

Create `/etc/systemd/system/quizverse.service`:

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

# Gunicorn execution: 1 worker with 8 threads (preserves unified in-memory rate limiting)
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

Enable and start service:
```bash
sudo systemctl daemon-reload
sudo systemctl enable quizverse
sudo systemctl start quizverse
sudo systemctl status quizverse
```

---

## 4. Hardened Nginx Reverse Proxy with Campus NAT Accommodation

Create `/etc/nginx/sites-available/quizverse.conf`:

```nginx
# Rate Limiting Zones
limit_req_zone $binary_remote_addr zone=quiz_general_limit:10m rate=30r/s;
limit_req_zone $binary_remote_addr zone=quiz_auth_limit:10m rate=5r/s;

upstream quizverse_cluster {
    server 127.0.0.1:5000;
    keepalive 32;
}

server {
    listen 80;
    listen [::]:80;
    server_name exams.university.edu;
    return 301 https://$host$request_uri;
}

server {
    listen 443 ssl http2;
    listen [::]:443 ssl http2;
    server_name exams.university.edu;

    # SSL / TLS 1.3 Certificate Configuration
    ssl_certificate /etc/letsencrypt/live/exams.university.edu/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/exams.university.edu/privkey.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    ssl_prefer_server_ciphers off;
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

    # Upload Limit (Syllabus PDF Ingestion)
    client_max_body_size 16M;

    # Authentication Endpoints with Burst Allowance for Campus NAT IPs
    location ~* ^/(login|register) {
        limit_req zone=quiz_auth_limit burst=20 nodelay;
        proxy_pass http://quizverse_cluster;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # Core Application Proxy
    location / {
        limit_req zone=quiz_general_limit burst=50 nodelay;
        proxy_pass http://quizverse_cluster;
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

Enable site:
```bash
sudo ln -s /etc/nginx/sites-available/quizverse.conf /etc/nginx/sites-enabled/
sudo nginx -t && sudo systemctl reload nginx
```

---

## 5. Automated Backup Schedules & Off-Site Replication

Create `/etc/cron.d/quizverse_backup`:

```cron
# Standard Daily Backup at 02:00 AM (Retains 30 daily snapshots)
0 2 * * * quizverse /opt/quizverse/venv/bin/python /opt/quizverse/database/backup_db.py backup --keep 30 >> /var/log/quizverse/backup.log 2>&1

# Exam Window High-Frequency Backup (Every 15 minutes during campus exam hours 08:00 - 18:00 Mon-Fri)
*/15 8-18 * * 1-5 quizverse /opt/quizverse/venv/bin/python /opt/quizverse/database/backup_db.py backup --keep 40 >> /var/log/quizverse/backup.log 2>&1

# Daily Off-Site S3 Synchronization at 02:30 AM
30 2 * * * quizverse aws s3 sync /opt/quizverse/backups/ s3://university-quizverse-backups/ --exclude "*" --include "quiz_backup_*.db" --sse aws:kms >> /var/log/quizverse/s3_sync.log 2>&1
```

---

## 6. Log Rotation (`/etc/logrotate.d/quizverse`)

```text
/var/log/quizverse/*.log {
    daily
    missingok
    rotate 14
    compress
    delaycompress
    notifempty
    create 0640 quizverse www-data
    sharedscripts
    postrotate
        /bin/systemctl reload quizverse > /dev/null 2>&1 || true
    endscript
}
```

---

## 7. Verification & Health Monitoring Commands

```bash
# 1. Local loopback health check (HTTP)
curl -s http://127.0.0.1:5000/health

# 2. Public domain health check (HTTPS)
curl -s https://exams.university.edu/health

# 3. Administrative deep diagnostic
curl -s -u admin:adminPassword https://exams.university.edu/admin/health

# 4. View live application errors
tail -f /var/log/quizverse/error.log
```

---

## 8. Emergency Rollback Runbook

1. **Stop Application Service:** `sudo systemctl stop quizverse`
2. **Restore Pre-Deployment Snapshot:**  
   `sudo -u quizverse /opt/quizverse/venv/bin/python /opt/quizverse/database/backup_db.py restore /opt/quizverse/backups/quiz_backup_pre_deploy.db`
3. **Roll Back Code:** `git checkout <PREVIOUS_STABLE_TAG>`
4. **Restart Service & Verify Health:**  
   `sudo systemctl start quizverse && curl -s http://127.0.0.1:5000/health`

