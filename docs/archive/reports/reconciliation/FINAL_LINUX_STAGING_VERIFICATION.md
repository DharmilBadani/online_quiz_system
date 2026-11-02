# FINAL LINUX STAGING VERIFICATION REPORT — QUIZVERSE v2.0.0
**Product:** QuizVerse — Institutional Online Examination & Assessment Platform  
**Target Release:** v2.0.0 Institutional Production Release Candidate  
**Inspection Date:** November 2, 2026  
**Auditor:** Principal DevOps & Infrastructure Reliability Engineer  
**Linux Staging Release Gate:** **NOT VERIFIED (EXECUTION ENVIRONMENT UNAVAILABLE)**  

---

## 1. Operating Environment Disclosure & Verification Boundary

In strict compliance with independent auditing standards, this report explicitly documents that all automated QA tests, code executions, database benchmarks, and simulated concurrency loads were performed on:
- **Host Operating System:** Microsoft Windows 11 Enterprise (AMD64 build 10.0.26300)
- **Host Runtime:** Python 3.12.10, SQLite 3.49.1, Pytest 8.2.2
- **Virtualization Status:** Windows Subsystem for Linux (WSL) is **not installed**; Docker daemon is **not installed**.

No remote Linux staging server or live virtualized Linux container was provisioned in this environment. Consequently, the **Linux Staging Deployment release gate is formally certified as NOT VERIFIED**.

Static architectural validation, syntactic verification of deployment units, and production configuration hardening have been completed and are detailed below for institutional sysadmins.

---

## 2. Linux Production Blueprint & Critical Defect Rectifications

### 2.1 Resolution of the Gunicorn Worker Class Mismatch
- **Previous Defect:** Earlier runbooks specified `--workers 4 --threads 2 --worker-class sync`. Under Gunicorn, synchronous (`sync`) workers operate as single-threaded processes; the `--threads` argument is ignored.
- **Remediated Configuration:** Standardized to the threaded worker class:
  ```bash
  --workers 4 --threads 2 --worker-class gthread
  ```
  This guarantees that 4 worker processes spawn 2 execution threads each, providing 8 concurrent request handlers per server instance.

### 2.2 Resolution of the `/run` tmpfs Reboot Socket Deletion Defect
- **Identified Defect:** On Linux distributions, `/run` is mounted as an in-memory `tmpfs` that is erased on reboot. If `/run/quizverse` does not exist, Gunicorn crashes with `[CRITICAL] Error: '/run/quizverse/gunicorn.sock' is not writable`.
- **Hardened Systemd Fix:** Configured `RuntimeDirectory=quizverse` and `RuntimeDirectoryMode=0755` inside the systemd service unit. Systemd automatically provisions the directory and assigns ownership to `User=quizverse` before launching Gunicorn on boot.

### 2.3 Systemd Service Unit (`/etc/systemd/system/quizverse.service`)
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

# Authoritative tmpfs runtime directory management
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

# Linux Security Sandboxing
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=/var/lib/quizverse /var/log/quizverse /run/quizverse
PrivateTmp=true
NoNewPrivileges=true

[Install]
WantedBy=multi-user.target
```

---

## 3. Nginx Edge Reverse Proxy & Rate Limiting

To resolve process-local rate limiting limitations across multiple Gunicorn workers, Nginx enforces shared-memory edge rate limiting:

```nginx
# /etc/nginx/sites-available/quizverse.conf
limit_req_zone $binary_remote_addr zone=quiz_edge_general:10m rate=15r/s;
limit_req_zone $binary_remote_addr zone=quiz_edge_auth:10m rate=3r/s;

upstream quizverse_sock {
    server unix:/run/quizverse/gunicorn.sock fail_timeout=0;
}

server {
    listen 80;
    server_name exams.university.edu;
    return 301 https://$host$request_uri;
}

server {
    listen 443 ssl http2;
    server_name exams.university.edu;

    ssl_certificate /etc/letsencrypt/live/exams.university.edu/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/exams.university.edu/privkey.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;

    client_max_body_size 16M;

    # Static assets served directly from disk by Nginx
    location /static/ {
        alias /var/www/quizverse/static/;
        expires 7d;
        add_header Cache-Control "public, max-age=604800, immutable";
        access_log off;
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
```

---

## 4. File Ownership, Permissions & Least Privilege

| Path | Owner:Group | Mode | Access Policy & Isolation |
| :--- | :--- | :--- | :--- |
| `/var/www/quizverse` | `root:quizverse` | `0755` | Application source files are read-only to Gunicorn process. |
| `/var/www/quizverse/.env` | `root:quizverse` | `0640` | Secret key and config readable by app, unwriteable. |
| `/var/www/quizverse/static`| `root:www-data` | `0755` | Static assets readable by Nginx directly. |
| `/var/lib/quizverse` | `quizverse:quizverse` | `0700` | Database and backup root directory; closed to other users. |
| `/var/lib/quizverse/quiz.db*`| `quizverse:quizverse` | `0600` | SQLite database and WAL logs; strictly unreadable by Nginx/www-data. |
| `/var/log/quizverse` | `quizverse:quizverse` | `0750` | Gunicorn application execution logs. |
| `/run/quizverse` | `quizverse:quizverse` | `0755` | In-memory socket managed via systemd `RuntimeDirectory`. |

---

## 5. Linux Staging Verification Gate Status
- **Status:** **NOT VERIFIED (ENVIRONMENT UNAVAILABLE)**
- **Prerequisite for Full Institutional Go-Live:** The deploying system administrator must execute Section 2 and Section 3 on the target Ubuntu/Debian server and verify successful socket startup, HTTP 200 response on `/api/admin/health`, and reboot survival.

