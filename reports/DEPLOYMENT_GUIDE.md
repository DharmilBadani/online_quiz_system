# QuizVerse Enterprise Production Deployment Guide

**Document ID:** QZ-DEP-2026-003  
**Target Systems:** Ubuntu 22.04 / Debian 12 / Rocky Linux 9 / Windows Server 2022  
**Target Application:** QuizVerse v2.0 Institutional Release  
**Architecture:** Nginx (TLS 1.3 Reverse Proxy) + Gunicorn (WSGI) + Flask + SQLite (WAL Mode)  

---

## 1. System Requirements & Architecture Overview

QuizVerse is architectured as a high-efficiency Python WSGI application backed by an optimized SQLite database running in Write-Ahead Logging (WAL) mode.

```
                      Internet / Campus LAN
                                |
                                v [HTTPS / Port 443]
                     +---------------------+
                     |    Nginx 1.20+      |  (TLS Termination, Static File Cache,
                     |   Reverse Proxy     |   Rate Limiting, Security Headers)
                     +---------------------+
                                |
                                v [Unix Domain Socket / Localhost HTTP:5000]
                     +---------------------+
                     |    Gunicorn WSGI    |  (4 Workers, 2 Threads per worker,
                     | Application Server  |   Worker class: gthread)
                     +---------------------+
                                |
                                v
                     +---------------------+
                     |   Flask Application |  (Auth, Quiz Engine, Proctoring API,
                     |    (QuizVerse Core) |   Dynamic Syllabus, Cognitive Radar)
                     +---------------------+
                                |
                                v
                     +---------------------+
                     |     SQLite 3.45     |  (PRAGMA journal_mode=WAL;
                     |     (quiz.db)       |   PRAGMA busy_timeout=5000;
                     |                     |   Composite Leaderboard Indexes)
                     +---------------------+
```

### Minimum Institutional Hardware Specifications:
- **Processor:** 4 x86_64 Cores (Intel Xeon or AMD EPYC / Ryzen)
- **Memory (RAM):** 8 GB DDR4 ECC
- **Storage:** 50 GB NVMe SSD (fast random I/O is critical for database commits)
- **Network:** 1 Gbps NIC, Static IP, FQDN with DNS A record pointing to host

---

## 2. Linux Production Setup (Ubuntu 22.04 / Debian 12)

### 2.1 Dedicated System User & Directory Setup
Isolate application execution under a non-privileged system user:
```bash
sudo useradd -r -s /bin/false -d /opt/quizverse quizverse
sudo mkdir -p /opt/quizverse /var/log/quizverse /var/backups/quizverse
sudo chown -R quizverse:www-data /opt/quizverse /var/log/quizverse /var/backups/quizverse
sudo chmod 750 /opt/quizverse /var/log/quizverse
```

### 2.2 Repository Deployment & Python Environment
Deploy application source code to `/opt/quizverse`:
```bash
cd /opt/quizverse
git clone <repository_url> .
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
pip install gunicorn
```

### 2.3 Secret Configuration & Environment File
Create `/opt/quizverse/.env` with strict permissions (`chmod 600`):
```bash
python3 -c "import secrets; print('FLASK_SECRET_KEY=' + secrets.token_hex(32))" > /opt/quizverse/.env
```
Populate the complete `.env`:
```ini
# Production Environment Mode (Mandatory for strict security guards)
FLASK_ENV=production

# Cryptographically Secure Session Signing Key (64 hex characters)
FLASK_SECRET_KEY=9a8b7c6d5e4f3a2b1c0d9e8f7a6b5c4d3e2f1a0b9c8d7e6f5a4b3c2d1e0f9a8b

# Google Gemini API Key (Optional: circuit breaker engages graceful fallback if omitted)
GEMINI_API_KEY=AIzaSyYourProductionGeminiKeyHere

# 1-Click Fast Pass Logins (MUST be false in production)
ALLOW_DEMO_LOGINS=false

# Binding configuration
FLASK_HOST=127.0.0.1
FLASK_PORT=5000
```
Secure file permissions:
```bash
sudo chown quizverse:quizverse /opt/quizverse/.env
sudo chmod 600 /opt/quizverse/.env
```

### 2.4 Database Initialization & Non-Destructive Migration
Initialize the SQLite schema in Write-Ahead Logging mode:
```bash
sudo -u quizverse /opt/quizverse/venv/bin/python /opt/quizverse/database/init_db.py
```
Verify WAL mode status:
```bash
sqlite3 /opt/quizverse/quiz.db "PRAGMA journal_mode;"
# Output: wal
```

---

## 3. WSGI Server Configuration (Gunicorn & systemd)

### 3.1 systemd Unit File
Create `/etc/systemd/system/quizverse.service`:
```ini
[Unit]
Description=QuizVerse Examination Platform WSGI Service
After=network.target

[Service]
Type=notify
User=quizverse
Group=www-data
WorkingDirectory=/opt/quizverse
Environment="PATH=/opt/quizverse/venv/bin"
EnvironmentFile=/opt/quizverse/.env
ExecStart=/opt/quizverse/venv/bin/gunicorn \
    --workers 4 \
    --threads 2 \
    --worker-class gthread \
    --bind 127.0.0.1:5000 \
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

### 3.2 Activating the Service
```bash
sudo systemctl daemon-reload
sudo systemctl enable quizverse
sudo systemctl start quizverse
sudo systemctl status quizverse
```

---

## 4. Nginx Reverse Proxy with TLS 1.3 & Hardened Headers

### 4.1 Nginx Server Block
Create `/etc/nginx/sites-available/quizverse.conf`:
```nginx
# Upstream WSGI cluster
upstream quizverse_cluster {
    server 127.0.0.1:5000 fail_timeout=0;
}

# HTTP to HTTPS redirect
server {
    listen 80;
    listen [::]:80;
    server_name exams.university.edu;
    return 301 https://$host$request_uri;
}

# HTTPS Production Server
server {
    listen 443 ssl http2;
    listen [::]:443 ssl http2;
    server_name exams.university.edu;

    # SSL / TLS 1.3 Certificate Configuration
    ssl_certificate /etc/letsencrypt/live/exams.university.edu/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/exams.university.edu/privkey.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256:ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384;
    ssl_prefer_server_ciphers off;
    ssl_session_cache shared:SSL:10m;
    ssl_session_timeout 1d;
    ssl_session_tickets off;

    # Enterprise Security Headers
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header Referrer-Policy "strict-origin-when-cross-origin" always;
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains; preload" always;

    # Static Assets Direct Delivery (Offloads WSGI)
    location /static/ {
        alias /opt/quizverse/static/;
        expires 30d;
        add_header Cache-Control "public, no-transform";
        access_log off;
    }

    # Upload Limit (Syllabus PDF / Text Ingestion)
    client_max_body_size 16M;

    # Application Proxy
    location / {
        proxy_pass http://quizverse_cluster;
        proxy_http_version 1.1;
        proxy_set_header Connection "";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 90;
        proxy_connect_timeout 10;
        proxy_buffering on;
        proxy_buffers 8 16k;
    }
}
```

Enable site configuration:
```bash
sudo ln -s /etc/nginx/sites-available/quizverse.conf /etc/nginx/sites-enabled/
sudo nginx -t && sudo systemctl reload nginx
```

---

## 5. Log Rotation & Maintenance

Create `/etc/logrotate.d/quizverse`:
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
        /bin/kill -USR1 $(cat /opt/quizverse/gunicorn.pid 2>/dev/null) 2>/dev/null || true
    endscript
}
```

---

## 6. Windows Server 2022 Alternative Deployment

For institutions standardizing on Windows Server:

1. **Python Installation:** Install Python 3.12 (x64) for all users with PATH enabled.
2. **Production WSGI Server (Waitress):**
   ```powershell
   pip install waitress
   ```
3. **Run as Windows Service via NSSM (Non-Sucking Service Manager):**
   ```powershell
   nssm install QuizVerseService "C:\Python312\python.exe" "-m waitress --listen=127.0.0.1:5000 --threads=8 app:app"
   nssm set QuizVerseService AppDirectory "E:\Major Project\online_quiz_system"
   nssm set QuizVerseService AppStdout "E:\Major Project\online_quiz_system\logs\service_out.log"
   nssm set QuizVerseService AppStderr "E:\Major Project\online_quiz_system\logs\service_err.log"
   nssm start QuizVerseService
   ```
4. **IIS Reverse Proxy:** Configure IIS URL Rewrite and ARR (Application Request Routing) to forward requests from Port 443 to `http://127.0.0.1:5000`.

---

## 7. Graceful Reload & Maintenance Protocol

To perform zero-downtime updates without terminating active student exams:
```bash
# Graceful worker restart (finishes active requests before spawning new workers)
sudo systemctl reload quizverse

# Verification of live health
curl -s -k https://127.0.0.1:5000/health
```
