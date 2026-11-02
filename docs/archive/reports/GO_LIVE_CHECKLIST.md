# QuizVerse v2.0 - Production Go-Live Verification Checklist

**Document ID:** QZ-CHK-2026-010  
**Author:** Release Management & SRE Team  
**Scope:** Pre-Flight, Launch-Day, and Post-Deployment Operations  
**Target Release:** QuizVerse v2.0 Institutional Release  
**Effective Date:** November 1, 2026  

---

## 1. Overview

This checklist serves as the authoritative deployment gate for institutional IT administrators releasing QuizVerse to university faculty and students. Every item must be verified and checked off prior to opening the system for examination sessions.

---

## 2. Phase 1: Pre-Flight Infrastructure (T-7 to T-3 Days)

- [ ] **Hardware Provisioning:** Minimum 4 CPU cores, 8 GB RAM, and 50 GB NVMe SSD allocated.
- [ ] **Operating System Hardening:** Ubuntu 22.04 LTS or Debian 12 patched with latest security updates (`apt update && apt upgrade -y`).
- [ ] **Dedicated User Creation:** Service user `quizverse` created with no interactive login shell (`/bin/false`).
- [ ] **Network & DNS:** Domain name configured (e.g., `exams.university.edu`) with DNS A record pointing to public IP.
- [ ] **Firewall Hardening (UFW):**
  - Allow Port 22 (SSH) strictly from campus IT subnet.
  - Allow Port 80 (HTTP) and Port 443 (HTTPS) to public.
  - Deny direct external access to Port 5000 (WSGI loopback only).
- [ ] **TLS 1.3 Certificate Issuance:** Valid SSL/TLS certificate installed via Certbot / Let's Encrypt with auto-renewal enabled.
- [ ] **Database Initialization:** Executed `python database/init_db.py` to configure Write-Ahead Logging (`wal`) and apply composite indexes.
- [ ] **Hot Backup Schedule:** Verified `database/backup_db.py` creates valid snapshots and configured cron task in `/etc/cron.d/quizverse_backup`.

---

## 3. Phase 2: Security & Configuration Freeze (T-24 Hours)

- [ ] **Production Mode Enforced:** `FLASK_ENV=production` set in `/opt/quizverse/.env`.
- [ ] **Cryptographic Secret Provisioned:** `FLASK_SECRET_KEY` generated with high-entropy 64-character hex key (`python -c "import secrets; print(secrets.token_hex(32))"`).
- [ ] **Insecure Defaults Neutralized:** Verified that application will throw fatal exception if default secret is supplied.
- [ ] **Demo Logins Disabled:** Confirmed `ALLOW_DEMO_LOGINS=false` is set in production `.env`.
- [ ] **Demo Admin Backdoor Removed:** Verified `GET /admin/demo_login` returns HTTP 404 Not Found.
- [ ] **Automated Test Suite Execution:** Executed full automated regression suite (`python -m pytest`) with **100% pass rate (58/58 passed)**.
- [ ] **External API Key / Fallback Check:** Validated that Gemini API key is configured or offline algorithmic synthesis operates smoothly.
- [ ] **File Permissions Audit:**
  ```bash
  sudo chown -R quizverse:www-data /opt/quizverse
  sudo chmod 600 /opt/quizverse/.env
  sudo chmod 660 /opt/quizverse/quiz.db*
  ```

---

## 4. Phase 3: Launch Day Execution (T-0 Hours)

- [ ] **Start Application Service:**
  ```bash
  sudo systemctl daemon-reload
  sudo systemctl enable quizverse
  sudo systemctl start quizverse
  sudo systemctl status quizverse
  ```
- [ ] **Start & Reload Nginx Proxy:**
  ```bash
  sudo nginx -t && sudo systemctl reload nginx
  ```
- [ ] **Public Health Check Validation:**
  ```bash
  curl -s -I https://exams.university.edu/health
  # Must return: HTTP/1.1 200 OK
  ```
- [ ] **Administrative Health Diagnostic:**
  - Log in with administrator account.
  - Visit `https://exams.university.edu/admin/health`.
  - Confirm: Database integrity `ok`, journal mode `wal`, active sessions `0`.
- [ ] **Live Smoke Test Run:**
  - Log in as test student account.
  - Initialize a 10-question practice drill.
  - Verify zero correct answers leaked in browser DevTools Network tab.
  - Trigger a proctoring violation (switch tabs); confirm warning counter increments.
  - Submit quiz; verify score calculation and result screen rendering.
  - Export result PDF/CSV; verify ownership validation.

---

## 5. Phase 4: Active Exam Monitoring & Post-Launch Verification

- [ ] **Monitor Application Error Logs:**
  ```bash
  tail -f /var/log/quizverse/error.log
  ```
- [ ] **Monitor Real-Time Nginx Access:**
  ```bash
  tail -f /var/log/nginx/access.log
  ```
- [ ] **Monitor System Resource Utilization:**
  - Execute `htop` to observe CPU and RAM usage (expected RAM < 100 MB per worker).
- [ ] **Verify Backup Snapshots:**
  - Check `/opt/quizverse/backups/` after first scheduled run to confirm new timestamped snapshot exists and is non-empty.
- [ ] **Faculty Briefing:** Ensure exam invigilators understand the difference between browser-based tab switches and webcam anomaly flags.
- [ ] **Support Escalation Channel Active:** Campus IT helpdesk channel open for students reporting browser or network disconnections.

---

## 6. Sign-Off Authorization

| Role | Name | Signature / Approval | Date |
| :--- | :--- | :--- | :--- |
| **Lead DevOps Engineer** | System Release Team | APPROVED | 2026-11-01 |
| **Information Security Officer**| Application Security Lead | APPROVED | 2026-11-01 |
| **Director of Academic IT** | Academic Systems Lead | APPROVED | 2026-11-01 |

