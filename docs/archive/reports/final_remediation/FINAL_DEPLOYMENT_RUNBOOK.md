# FINAL PRODUCTION DEPLOYMENT RUNBOOK — QUIZVERSE v2.0.0
**Target OS Platform:** Linux Ubuntu 22.04 LTS / 24.04 LTS / Debian 12  
**Platform Version:** QuizVerse v2.0.0 Institutional Release Candidate  
**Target Release Archive:** `dist/QuizVerse_v2.0.0_Clean_Release.zip`  
**Target Audience:** Institutional System Administrators, DevOps Engineers & Site Reliability Leads  

---

## 1. Prerequisites & Server Sizing

Ensure the host virtual machine or bare-metal server meets the minimum institutional sizing:
- **Processor:** 4 vCPUs (Intel Xeon / AMD EPYC)
- **Memory:** 8 GB RAM (ECC recommended)
- **Disk:** 50 GB NVMe SSD storage (High IOPS for WAL operations)
- **Network:** 1 Gbps NIC with TLS 443 inbound access

---

## 2. Step-by-Step Installation Procedure

### Step 1: Install System Packages
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
# 1. Create unprivileged system user
sudo adduser --system --group --no-create-home --shell /bin/false quizverse

# 2. Create standardized directory structure
sudo mkdir -p /var/www/quizverse
sudo mkdir -p /var/lib/quizverse/backups/{daily,exam_window,manual}
sudo mkdir -p /var/log/quizverse

# 3. Assign initial ownership
sudo chown -R root:quizverse /var/www/quizverse
sudo chown -R quizverse:quizverse /var/lib/quizverse /var/log/quizverse
sudo chmod 0700 /var/lib/quizverse
sudo chmod 0750 /var/log/quizverse
```

### Step 3: Extract Release Distribution & Setup Virtual Environment
```bash
# 1. Unpack release package to /var/www/quizverse
sudo unzip QuizVerse_v2.0.0_Clean_Release.zip -d /var/www/quizverse

# 2. Setup Python virtual environment
cd /var/www/quizverse
sudo python3.12 -m venv venv
sudo venv/bin/pip install --upgrade pip
sudo venv/bin/pip install -r requirements.txt
sudo venv/bin/pip install gunicorn
```

### Step 4: Configure Production Environment Variables
Generate a cryptographically unguessable 64-character hexadecimal session key:
```bash
python3 -c "import secrets; print(secrets.token_hex(32))"
```
Create `/var/www/quizverse/.env`:
```bash
sudo bash -c 'cat > /var/www/quizverse/.env' << 'EOF'
FLASK_ENV=production
FLASK_SECRET_KEY=PASTE_GENERATED_64_CHAR_HEX_KEY_HERE
GEMINI_API_KEY=YOUR_INSTITUTIONAL_GEMINI_KEY_OR_LEAVE_EMPTY_FOR_OFFLINE
DATABASE_PATH=/var/lib/quizverse/quiz.db
TRUSTED_PROXIES=1
ALLOW_DEMO_LOGINS=false
EOF

# Lock down .env permissions
sudo chown root:quizverse /var/www/quizverse/.env
sudo chmod 0640 /var/www/quizverse/.env
```

### Step 5: Initialize the Production Database
```bash
cd /var/www/quizverse
sudo -u quizverse venv/bin/python database/init_db.py

# Verify database files and apply strict least-privilege permissions
sudo chmod 0600 /var/lib/quizverse/quiz.db*
sqlite3 /var/lib/quizverse/quiz.db "PRAGMA journal_mode; PRAGMA integrity_check;"
# Expected output:
# wal
# ok
```

### Step 6: Configure Systemd Service (`quizverse.service`)
```bash
sudo bash -c 'cat > /etc/systemd/system/quizverse.service' << 'EOF'
[Unit]
Description=QuizVerse Institutional Online Examination Platform
After=network.target

[Service]
Type=notify
User=quizverse
Group=quizverse
WorkingDirectory=/var/www/quizverse
Environment="PATH=/var/www/quizverse/venv/bin"
EnvironmentFile=/var/www/quizverse/.env

RuntimeDirectory=quizverse
RuntimeDirectoryMode=0755

ExecStart=/var/www/quizverse/venv/bin/gunicorn \
    --workers 4 \
    --threads 2 \
    --worker-class sync \
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

### Step 7: Configure Nginx & TLS
```bash
sudo bash -c 'cat > /etc/nginx/sites-available/quizverse.conf' << 'EOF'
upstream quizverse_sock {
    server unix:/run/quizverse/gunicorn.sock fail_timeout=0;
}

server {
    listen 80;
    server_name exams.university.edu;

    client_max_body_size 16M;

    location /static/ {
        alias /var/www/quizverse/static/;
        expires 7d;
        add_header Cache-Control "public, max-age=604800, immutable";
    }

    location / {
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

# Obtain Free Automated SSL/TLS Certificate
sudo certbot --nginx -d exams.university.edu --non-interactive --agree-tos -m admin@university.edu
```

### Step 8: Configure High-Frequency Exam Backup Timers
```bash
sudo bash -c 'cat > /etc/systemd/system/quizverse-backup.service' << 'EOF'
[Unit]
Description=QuizVerse Database Backup Service

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
Description=Execute Exam Window Backup Every 15 Minutes

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

## 3. Post-Deployment Verification & Health Checks

Run the following checks from the server command line:

```bash
# 1. Verify Gunicorn service status
sudo systemctl status quizverse --no-pager

# 2. Check internal socket responsiveness
curl -s http://127.0.0.1/api/admin/health | jq .
# Expected output:
# {
#   "status": "healthy",
#   "database": { "connected": true, "journal_mode": "wal" },
#   "ai_circuit_breaker": { "state": "CLOSED" }
# }

# 3. Test backup snapshot creation
sudo -u quizverse venv/bin/python database/backup_db.py create --tier manual
sudo -u quizverse venv/bin/python database/backup_db.py list
```

---

## 4. Emergency Rollback Procedure
If a critical operational issue occurs:
```bash
# 1. Stop service
sudo systemctl stop quizverse

# 2. Restore previous known-good database snapshot
sudo -u quizverse venv/bin/python database/backup_db.py restore /var/lib/quizverse/backups/daily/quiz_backup_daily_LATEST.db

# 3. Restart service
sudo systemctl start quizverse
```
