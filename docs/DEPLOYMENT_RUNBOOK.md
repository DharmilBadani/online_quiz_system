# PRODUCTION DEPLOYMENT & OPERATIONS RUNBOOK

## 1. Prerequisites
- **Target OS:** Ubuntu 22.04 LTS / 24.04 LTS / Debian 12
- **Runtime:** Python 3.12, Nginx, SQLite3, Certbot
- **Hardware:** 2–4 vCPUs, 4–8 GB RAM, NVMe SSD (Optimized for 30 concurrent examinees)

---

## 2. Step-by-Step Deployment

### Step 1: System Packages & Service User
```bash
sudo apt-get update && sudo apt-get install -y python3.12 python3.12-venv python3-pip nginx sqlite3 certbot python3-certbot-nginx curl unzip
sudo adduser --system --group --no-create-home --shell /bin/false quizverse
sudo mkdir -p /var/www/quizverse /var/lib/quizverse/backups/{daily,exam_window,manual} /var/log/quizverse
sudo chown -R root:quizverse /var/www/quizverse
sudo chown -R quizverse:quizverse /var/lib/quizverse /var/log/quizverse
sudo chmod 0700 /var/lib/quizverse
sudo chmod 0750 /var/log/quizverse
```

### Step 2: Unpack Release & Virtual Environment
```bash
sudo unzip QuizVerse_v2.0.0_Release.zip -d /var/www/quizverse
cd /var/www/quizverse
sudo python3.12 -m venv venv
sudo venv/bin/pip install --upgrade pip
sudo venv/bin/pip install -r requirements.txt
```

### Step 3: Production Environment Variables (`.env`)
Generate a secure 64-character secret key:
```bash
python3 -c "import secrets; print(secrets.token_hex(32))"
```
Create `/var/www/quizverse/.env`:
```ini
FLASK_ENV=production
FLASK_SECRET_KEY=PASTE_GENERATED_64_CHAR_HEX_KEY
GEMINI_API_KEY=YOUR_INSTITUTIONAL_GEMINI_KEY
DATABASE_PATH=/var/lib/quizverse/quiz.db
TRUSTED_PROXIES=1
ALLOW_DEMO_LOGINS=false
```
Set permissions:
```bash
sudo chown root:quizverse /var/www/quizverse/.env
sudo chmod 0640 /var/www/quizverse/.env
```

### Step 4: Initialize Fresh Database
```bash
sudo -u quizverse venv/bin/python database/init_db.py
sudo chmod 0600 /var/lib/quizverse/quiz.db*
```

### Step 5: Systemd Service Unit (`/etc/systemd/system/quizverse.service`)
```ini
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
    wsgi:app

Restart=always
RestartSec=3
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=/var/lib/quizverse /var/log/quizverse /run/quizverse
PrivateTmp=true
NoNewPrivileges=true

[Install]
WantedBy=multi-user.target
```
Enable and start:
```bash
sudo systemctl daemon-reload
sudo systemctl enable --now quizverse
```

### Step 6: Nginx Reverse Proxy with Edge Rate Limiting (`/etc/nginx/sites-available/quizverse.conf`)
```nginx
limit_req_zone $binary_remote_addr zone=quiz_edge_general:10m rate=15r/s;
limit_req_zone $binary_remote_addr zone=quiz_edge_auth:10m rate=3r/s;

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

    location ~* ^/(login|register) {
        limit_req zone=quiz_edge_auth burst=5 nodelay;
        proxy_pass http://quizverse_sock;
        proxy_set_header Host $http_host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

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
```
Enable site and reload:
```bash
sudo ln -sf /etc/nginx/sites-available/quizverse.conf /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/default
sudo nginx -t && sudo systemctl reload nginx
sudo certbot --nginx -d exams.university.edu --non-interactive --agree-tos -m admin@university.edu
```

---

## 3. Rollback Playbook
```bash
# 1. Stop service
sudo systemctl stop quizverse

# 2. Restore previous database snapshot
sudo -u quizverse venv/bin/python database/backup_db.py restore /var/lib/quizverse/backups/daily/quiz_backup_daily_LATEST.db

# 3. Restart service
sudo systemctl start quizverse
```
