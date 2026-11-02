# FINAL PRODUCTION RELEASE & DEPLOYMENT RUNBOOK — QUIZVERSE v2.0.0
**Product:** QuizVerse — Institutional Online Examination & Assessment Platform  
**Target Release:** v2.0.0 Institutional Production Release Candidate  
**Target Platform:** Linux Ubuntu 22.04 LTS / 24.04 LTS / Debian 12  
**Target Distribution Package:** `dist/FINAL_RELEASE_ARTIFACT.zip`  
**Target Audience:** Enterprise DevOps Engineers, System Administrators & Site Reliability Leads  

---

## 1. System Requirements & Hardware Baseline

Before commencing installation, ensure the host machine meets the institutional profile:
- **CPU:** 4 vCPUs (Intel Xeon / AMD EPYC)
- **RAM:** 8 GB RAM (ECC recommended)
- **Disk:** 50 GB NVMe SSD (High IOPS for SQLite WAL operations)
- **Network:** 1 Gbps NIC with TLS port 443 inbound access

---

## 2. Step-by-Step Installation & Provisioning Runbook

### Step 1: Install System Prerequisites
```bash
sudo apt-get update && sudo apt-get install -y \
    python3.12 \
    python3.12-venv \
    python3-pip \
    nginx \
    sqlite3 \
    certbot \
    python3-certbot-nginx \
    curl \
    unzip
```

### Step 2: Create Dedicated Service User & Directories
```bash
# 1. Create isolated system service user without shell access
sudo adduser --system --group --no-create-home --shell /bin/false quizverse

# 2. Create standardized directory hierarchy
sudo mkdir -p /var/www/quizverse
sudo mkdir -p /var/lib/quizverse/backups/{daily,exam_window,manual}
sudo mkdir -p /var/log/quizverse

# 3. Configure baseline permissions
sudo chown -R root:quizverse /var/www/quizverse
sudo chown -R quizverse:quizverse /var/lib/quizverse /var/log/quizverse
sudo chmod 0700 /var/lib/quizverse
sudo chmod 0750 /var/log/quizverse
```

### Step 3: Unpack Release Package & Configure Python Virtual Environment
```bash
# 1. Unzip release package into /var/www/quizverse
sudo unzip FINAL_RELEASE_ARTIFACT.zip -d /var/www/quizverse

# 2. Setup Python 3.12 virtual environment
cd /var/www/quizverse
sudo python3.12 -m venv venv
sudo venv/bin/pip install --upgrade pip
sudo venv/bin/pip install -r requirements.txt gunicorn
```

### Step 4: Configure Environment Variables & Mandatory Secret Generation
Generate a cryptographically unguessable 64-character hexadecimal session key:
```bash
python3 -c "import secrets; print(secrets.token_hex(32))"
```
Create `/var/www/quizverse/.env`:
```bash
sudo bash -c 'cat > /var/www/quizverse/.env' << 'EOF'
FLASK_ENV=production
FLASK_SECRET_KEY=PASTE_GENERATED_64_CHAR_HEX_KEY_HERE
GEMINI_API_KEY=YOUR_INSTITUTIONAL_GEMINI_KEY_OR_LEAVE_BLANK_FOR_OFFLINE
DATABASE_PATH=/var/lib/quizverse/quiz.db
TRUSTED_PROXIES=1
ALLOW_DEMO_LOGINS=false
EOF

# Enforce least-privilege permissions on secrets
sudo chown root:quizverse /var/www/quizverse/.env
sudo chmod 0640 /var/www/quizverse/.env
```

### Step 5: Initialize the Production Database
```bash
cd /var/www/quizverse
sudo -u quizverse venv/bin/python database/init_db.py

# Verify SQLite WAL configuration and apply strict file permissions
sudo chmod 0600 /var/lib/quizverse/quiz.db*
sqlite3 /var/lib/quizverse/quiz.db "PRAGMA journal_mode; PRAGMA integrity_check;"
# Expected output:
# wal
# ok
```

### Step 6: Configure Systemd Application Service (`quizverse.service`)
```bash
sudo bash -c 'cat > /etc/systemd/system/quizverse.service' << 'EOF'
[Unit]
Description=QuizVerse Institutional Online Examination Platform
After=network.target

[Service]
Type=simple
User=quizverse
Group=quizverse
WorkingDirectory=/var/www/quizverse
Environment="PATH=/var/www/quizverse/venv/bin"
EnvironmentFile=/var/www/quizverse/.env

# Authoritative tmpfs runtime management (Survives system reboot)
RuntimeDirectory=quizverse
RuntimeDirectoryMode=0755

ExecStart=/var/www/quizverse/venv/bin/gunicorn \
    --workers 4 \
    --threads 2 \
    --worker-class gthread \
    --worker-tmp-dir /dev/shm \
    --bind unix:/run/quizverse/gunicorn.sock \
    --timeout 60 \
    --access-logfile /var/log/quizverse/access.log \
    --error-logfile /var/log/quizverse/error.log \
    app:app

ExecReload=/bin/kill -s HUP $MAINPID
KillMode=mixed
TimeoutStopSec=15
Restart=always
RestartSec=3

ProtectSystem=strict
ProtectHome=true
ReadWritePaths=/var/lib/quizverse /var/log/quizverse /run/quizverse
PrivateTmp=true
NoNewPrivileges=true

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable --now quizverse
```

### Step 7: Configure Nginx Reverse Proxy with Edge Rate Limiting & TLS
```bash
sudo bash -c 'cat > /etc/nginx/sites-available/quizverse.conf' << 'EOF'
limit_req_zone $binary_remote_addr zone=quiz_edge_general:10m rate=15r/s;
limit_req_zone $binary_remote_addr zone=quiz_edge_auth:10m rate=3r/s;

upstream quizverse_sock {
    server unix:/run/quizverse/gunicorn.sock fail_timeout=0;
}

server {
    listen 80;
    server_name exams.university.edu;

    client_max_body_size 16M;

    # Static assets served directly from disk by Nginx
    location /static/ {
        alias /var/www/quizverse/static/;
        expires 7d;
        add_header Cache-Control "public, max-age=604800, immutable";
    }

    # Edge rate-limited authentication routes
    location ~* ^/(login|register) {
        limit_req zone=quiz_edge_auth burst=5 nodelay;
        proxy_pass http://quizverse_sock;
        proxy_set_header Host $http_host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # General examination application traffic
    location / {
        limit_req zone=quiz_edge_general burst=20 nodelay;
        proxy_pass http://quizverse_sock;
        proxy_set_header Host $http_host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_buffering off;
        proxy_read_timeout 60s;
    }
}
EOF

sudo ln -sf /etc/nginx/sites-available/quizverse.conf /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/default
sudo nginx -t && sudo systemctl reload nginx

# Enable free automated TLS certificate via Let's Encrypt
sudo certbot --nginx -d exams.university.edu --non-interactive --agree-tos -m admin@university.edu
```

### Step 8: Configure Automated 15-Minute Exam Window Backup Timer
```bash
sudo bash -c 'cat > /etc/systemd/system/quizverse-backup.service' << 'EOF'
[Unit]
Description=QuizVerse Exam Window Database Backup

[Service]
Type=oneshot
User=quizverse
Group=quizverse
WorkingDirectory=/var/www/quizverse
Environment="PATH=/var/www/quizverse/venv/bin"
EnvironmentFile=/var/www/quizverse/.env
ExecStart=/var/www/quizverse/venv/bin/python database/backup_db.py create --tier exam_window --keep 40
EOF

sudo bash -c 'cat > /etc/systemd/system/quizverse-backup.timer' << 'EOF'
[Unit]
Description=Run Exam Window Backup Every 15 Minutes

[Timer]
OnCalendar=*:00,15,30,45
Persistent=true

[Install]
WantedBy=timers.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable --now quizverse-backup.timer
```

---

## 3. Post-Deployment Verification & Diagnostics

Run the following checks from the server command line:

```bash
# 1. Verify Gunicorn application status
sudo systemctl status quizverse --no-pager

# 2. Check internal socket health diagnostics
curl -s http://127.0.0.1/api/admin/health | jq .
# Expected output:
# {
#   "status": "healthy",
#   "database": { "connected": true, "journal_mode": "wal" },
#   "ai_circuit_breaker": { "state": "CLOSED" }
# }

# 3. Test on-demand backup snapshot
sudo -u quizverse venv/bin/python database/backup_db.py create --tier manual
sudo -u quizverse venv/bin/python database/backup_db.py list
```

---

## 4. Emergency Operational Rollback Procedure

If a critical incident or software defect occurs post-deployment:

```bash
# 1. Stop active Gunicorn service
sudo systemctl stop quizverse

# 2. Restore previous known-good database snapshot
sudo -u quizverse venv/bin/python database/backup_db.py restore /var/lib/quizverse/backups/daily/quiz_backup_LATEST.db

# 3. Re-link previous application code directory (if blue/green deployment used)
# or restore prior release zip
sudo unzip QuizVerse_Previous_Release.zip -d /var/www/quizverse

# 4. Restart service and verify health
sudo systemctl start quizverse
curl -s http://127.0.0.1/api/admin/health
```
