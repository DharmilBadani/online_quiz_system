# QuizVerse v2.0 - Operations & Monitoring Guide (Day-2 Runbook)

**Document ID:** QZ-OPS-2026-008  
**Author:** Site Reliability Engineering (SRE) & Systems Operations  
**Audience:** Campus IT Administrators, DevOps Engineers, and Exam Coordinators  
**Target Release:** QuizVerse v2.0 Institutional Edition  
**Effective Date:** November 1, 2026  

---

## 1. Overview & Operational Principles

This document provides day-2 operational guidance, continuous monitoring procedures, metric thresholds, log triage standards, and step-by-step incident response playbooks for maintaining QuizVerse in production.

---

## 2. Health Check & Diagnostic Endpoints

QuizVerse provides two built-in health check endpoints designed for uptime monitoring systems and administrative troubleshooting:

### 2.1 Public Lightweight Health Check (`GET /health`)
- **Purpose:** Used by Nginx upstream monitors, AWS Route 53, or Uptime Kuma for continuous health checks.
- **Access:** Public (no authentication required).
- **Latency:** < 2 ms.
- **Response Format:**
  ```json
  {
    "status": "healthy",
    "timestamp": "2026-11-01T19:47:00Z",
    "version": "2.0.0"
  }
  ```

### 2.2 Deep Administrative Health Diagnostic (`GET /admin/health`)
- **Purpose:** Comprehensive database, filesystem, and circuit breaker diagnostic.
- **Access:** Restricted to authenticated `admin` role.
- **Checks Performed:**
  - SQLite database integrity check (`PRAGMA integrity_check;`).
  - Journal mode verification (`PRAGMA journal_mode;` must equal `wal`).
  - Table record counts (users, active sessions, questions, attempts).
  - External Gemini API Circuit Breaker state (consecutive failures, cooldown remaining).
  - Disk storage utilization for database and backup partitions.
- **Response Format:**
  ```json
  {
    "status": "ok",
    "database": {
      "integrity": "ok",
      "journal_mode": "wal",
      "total_attempts": 262,
      "total_questions": 853,
      "active_sessions": 4
    },
    "circuit_breaker": {
      "gemini_circuit_open": false,
      "consecutive_failures": 0
    },
    "system_timestamp": "2026-11-01T19:47:00Z"
  }
  ```

---

## 3. Key Telemetry & Monitoring Metrics

Configure your monitoring agent (Prometheus node_exporter, Datadog, or Netdata) with the following alert thresholds:

| Metric | Normal Range | Warning Threshold | Critical Alert Threshold | Recommended Action |
| :--- | :--- | :--- | :--- | :--- |
| **Gunicorn Process RSS Memory** | 45 MB – 65 MB | > 120 MB | > 250 MB | Inspect for memory leak; reload workers (`systemctl reload quizverse`). |
| **P95 Submission Latency** | 100 ms – 300 ms | > 800 ms | > 2,000 ms | Check SQLite disk I/O; verify WAL checkpoint frequency. |
| **HTTP 5xx Error Rate** | < 0.05% | > 1.0% | > 5.0% | Inspect `/var/log/quizverse/error.log` for unhandled exceptions. |
| **HTTP 429 Rate Limit Hits** | 0 – 5 / min | > 50 / min | > 200 / min | Potential brute-force attack; inspect source IPs in Nginx logs. |
| **Disk Space Usage** | < 70% | > 85% | > 92% | Prune old backup snapshots (`/var/backups/quizverse`). |
| **Database Lock Timeouts** | 0 | 1 in 10 mins | > 5 in 10 mins | Excessive simultaneous writes; force WAL checkpoint. |

---

## 4. Log Inspection & Triage Procedures

QuizVerse routes application telemetry to standard structured log destinations:

- **Gunicorn Access Logs:** `/var/log/quizverse/access.log`
- **Gunicorn Error Logs:** `/var/log/quizverse/error.log`
- **Nginx Access & TLS Logs:** `/var/log/nginx/access.log`
- **Database Backup Logs:** `/var/log/quizverse/backup.log`

### Useful Troubleshooting Commands:
```bash
# Follow live application errors in real time
tail -f /var/log/quizverse/error.log

# Monitor rate limit triggers (HTTP 429)
grep "429" /var/log/nginx/access.log | tail -n 50

# Inspect recent database backup executions
tail -n 30 /var/log/quizverse/backup.log

# Check Gunicorn systemd journal logs
sudo journalctl -u quizverse.service -n 50 --no-pager
```

---

## 5. Incident Response Playbooks

### Playbook 1: Gemini API Quota Exhaustion or Outage
- **Symptoms:** High latency on question generation, log messages noting API error 429/500, or circuit breaker activation.
- **Expected Application Behavior:** The Gemini Circuit Breaker trips after 3 consecutive failures, entering a 45-second cooldown. The application automatically redirects all dynamic requests to the offline algorithmic curriculum synthesizer. **Students experience zero disruption.**
- **Action Steps:**
  1. Inspect circuit breaker state via `/admin/health`.
  2. Check Google Cloud Console for API billing, quota limits, or regional outages.
  3. If quota is exhausted for the month, leave the system in place; offline synthesis will seamlessly serve all quizzes.
  4. Once quota is restored, circuit breaker automatically resets upon the first successful call.

### Playbook 2: Database Busy Timeout / Lock Contention
- **Symptoms:** Log entries containing `sqlite3.OperationalError: database is locked` or submission response times > 5 seconds.
- **Root Cause:** A heavy write transaction is holding the lock, or WAL log file has grown without checkpointing.
- **Action Steps:**
  1. Force an immediate WAL checkpoint via the command line:
     ```bash
     sqlite3 /opt/quizverse/quiz.db "PRAGMA wal_checkpoint(TRUNCATE);"
     ```
  2. Verify busy timeout in `database/init_db.py` is configured to at least 5000 ms.
  3. If exam cohort exceeds 500 simultaneous examinees clicking submit at the same second, instruct exam proctors to stagger final submissions by room/row over a 60-second window.

### Playbook 3: High Rate of Proctoring Violations Alert
- **Symptoms:** Multiple proctoring violation warnings logged in quick succession.
- **Action Steps:**
  1. Navigate to `/faculty/dashboard` or `/admin/dashboard`.
  2. Inspect the live active attempt logs for candidate names, violation types (`fullscreen_exit`, `tab_switch`, `blur`), and timestamps.
  3. Review the student's browser user agent. Legitimate violations typically coincide with brief 2-second switches (chat apps, browser searches).
  4. System automatically deducts integrity points based on server violation counts. Faculty can review flagged sessions post-exam before confirming grades.

### Playbook 4: Suspected Brute-Force or Denial of Service Attack
- **Symptoms:** Flood of requests to `/login` or `/register` resulting in numerous HTTP 429 Too Many Requests errors.
- **Action Steps:**
  1. Identify offending IP addresses from Nginx logs:
     ```bash
     awk '{print $1}' /var/log/nginx/access.log | sort | uniq -c | sort -nr | head -n 20
     ```
  2. Block abusive IP addresses immediately using UFW firewall:
     ```bash
     sudo ufw insert 1 deny from <OFFENDING_IP> to any
     ```
  3. If attack is distributed across a large botnet, enable Cloudflare Under Attack mode or deploy Nginx `limit_req_zone` IP rate limiting at the edge.

### Playbook 5: Candidate Browser Crash or Power Loss During Active Exam
- **Symptoms:** Student's computer loses power or browser closes mid-quiz.
- **Application Recovery Feature:**
  1. Active quiz state and questions are stored server-side in `active_quiz_sessions`.
  2. Within the 24-hour expiration window, the student can reopen the browser, navigate to the portal, and log in.
  3. The active attempt token remains bound to their authenticated session, allowing them to resume the quiz with their questions and time intact.

