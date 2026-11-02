# QuizVerse v2.0 - Documentation Consistency Audit & Reconciliation Matrix

**Document ID:** QZ-DOC-2026-001  
**Auditor:** Principal Software Architect & Release Management Team  
**Review Target:** Complete 11-Document Release Package  
**Audit Date:** November 1, 2026  
**Final Status:** RECONCILED & STANDARDIZED  

---

## 1. Executive Summary

An independent, rigorous consistency audit was conducted across the entire suite of 11 production release documents. Each document was evaluated against the latest source code (`app.py`, `database/init_db.py`, `database/backup_db.py`), actual configuration files (`.env`, `.env.example`), and live test results.

The audit discovered several significant discrepancies across documents regarding Gunicorn worker topologies, landing-page benchmark throughput numbers, backup CLI syntax and execution schedules, health-check URLs, and systemd service types.

This document establishes the **authoritative reconciliation matrix**, identifies the root causes of each discrepancy, and enforces single, unified operational values across all project documentation.

---

## 2. Documents Audited

1. `DEPLOYMENT_GUIDE.md`
2. `BACKUP_AND_DISASTER_RECOVERY.md`
3. `FINAL_QA_AND_REGRESSION_REPORT.md`
4. `FINAL_SECURITY_ASSESSMENT.md`
5. `GO_LIVE_CHECKLIST.md`
6. `KNOWN_LIMITATIONS_AND_FUTURE_ROADMAP.md`
7. `OPERATIONS_AND_MONITORING_GUIDE.md`
8. `PERFORMANCE_CAPACITY_AND_LIMITATIONS.md`
9. `PRODUCTION_CONFIGURATION_GUIDE.md`
10. `PRODUCTION_READINESS_AUDIT.md`
11. `RELEASE_NOTES.md`

---

## 3. Comprehensive Documentation Contradiction Matrix

| ID | Subject / Topic | Document & Section | Documented Claim | Conflicting Document & Claim | Implementation Evidence | Severity | Required Correction & Authoritative Decision |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **DOC-01** | **Gunicorn Worker Topology** | `DEPLOYMENT_GUIDE.md` §4 | Recommends 4 workers with 2 threads each (`--workers 4 --threads 2 --worker-class gthread`). | `PRODUCTION_READINESS_AUDIT.md` §4 mentions "4 sync/gevent workers or 1 multithreaded worker with 8 threads". | In `app.py`, `_RATE_LIMIT_BUCKETS` is an in-memory dictionary protected by a Python `threading.Lock()`. If 4 separate OS processes run, the rate limiter is process-local and buckets are not shared. | **HIGH** | **Authoritative Standard:** Standardize on Gunicorn with 1 worker and 8 threads (`-w 1 --threads 8`) for single-node deployments using the in-memory limiter, OR 4 workers (`-w 4 --threads 2`) WITH Nginx edge rate limiting (`limit_req_zone`). Update all documents to document both topologies clearly. |
| **DOC-02** | **Landing Page Benchmark RPS** | `PRODUCTION_READINESS_AUDIT.md` §3.1 & Release Notes §4 | Reports "140.2 RPS on read endpoints (`GET /`)". | `PERFORMANCE_REPORT.md` §2.1 reports 227.8 RPS (1 worker), 665.3 RPS (5 workers), and 485.9 RPS (25 workers). | The 140.2 RPS figure was drawn from a preliminary average test across mixed read endpoints, whereas `PERFORMANCE_REPORT.md` records direct empirical measurements of `GET /`. | **MEDIUM** | **Authoritative Standard:** Adopt the empirical figures from `PERFORMANCE_REPORT.md`: 227.8 RPS (1 worker), peaking at 665.3 RPS (5 workers). Deprecate the preliminary 140.2 figure. |
| **DOC-03** | **Backup Utility CLI Syntax** | `DEPLOYMENT_GUIDE.md` §3.2 | Documents command: `python database/backup_db.py --keep 7`. | `database/backup_db.py` previously only parsed `sys.argv[1]` as action (`backup`/`restore`); passing `--keep` printed a usage error and aborted. | Source code inspection of `backup_db.py` confirmed it lacked `--keep` and `--dest` argparse flags. | **HIGH** | **Correction Implemented:** Enhanced `database/backup_db.py` with `argparse` to natively support `--keep <N>` (retention pruning) and `--dest <DIR>`, while retaining backwards compatibility with `backup` and `restore <path>`. Verified with automated test `test_09`. |
| **DOC-04** | **Backup Directory Paths** | `DEPLOYMENT_GUIDE.md` §2.1 & 4.1 | Mentions `/var/backups/quizverse`. | `BACKUP_AND_DISASTER_RECOVERY.md` §3.1 and `backup_db.py` default to `/opt/quizverse/backups`. | `backup_db.py` defines `BACKUP_DIR = os.path.join(BASE_DIR, "backups")` which evaluates to `/opt/quizverse/backups` in a standard Linux installation. | **MEDIUM** | **Authoritative Standard:** Set default primary backup destination to `/opt/quizverse/backups`. Document `/var/backups/quizverse` as an optional dedicated mount partition via `--dest /var/backups/quizverse`. |
| **DOC-05** | **RPO & Backup Scheduling** | `BACKUP_AND_DISASTER_RECOVERY.md` §1 | States: "Automated hourly snapshots during active testing windows; WAL checkpoints every 1000 pages." | `BACKUP_AND_DISASTER_RECOVERY.md` §3.2 shows cron: `*/15 8-18 * * 1-5` (every 15 minutes). | To guarantee RPO < 15 minutes during active exams, the backup cron must run every 15 minutes, not hourly. | **MEDIUM** | **Authoritative Standard:** Clarify RPO: Standard off-peak is 24 hours (daily backup at 02:00 AM). During campus exam windows (08:00–18:00 Mon–Fri), backups run every 15 minutes, guaranteeing RPO < 15 minutes. |
| **DOC-06** | **Health Check URL Protocol** | `DEPLOYMENT_GUIDE.md` §7 | Documents: `curl -s -k https://127.0.0.1:5000/health`. | Gunicorn binds HTTP plaintext on port 5000; Nginx terminates TLS on port 443. Calling HTTPS on port 5000 causes an SSL handshake error (`SSL: WRONG_VERSION_NUMBER`). | Testing `https://127.0.0.1:5000/health` directly against Gunicorn confirms SSL protocol failure. | **HIGH** | **Correction Implemented:** Correct health-check command to `curl -s http://127.0.0.1:5000/health` for local loopback verification, and `curl -s https://exams.university.edu/health` for public domain verification through Nginx. |
| **DOC-07** | **Systemd Service Type & PID File** | `DEPLOYMENT_GUIDE.md` §3.1 & 5 | Configures `Type=notify` in systemd unit, and logrotate references `/opt/quizverse/gunicorn.pid`. | Gunicorn was started without `--pid /opt/quizverse/gunicorn.pid`, and `Type=notify` requires the Python `sd_notify` library to signal readiness. | Without `sd_notify`, `systemd` may hang waiting for notification. Without `--pid`, logrotate postrotate fails to find PID file. | **HIGH** | **Correction Implemented:** Set systemd unit to `Type=exec` (supported natively in modern systemd without external C libraries). Add `--pid /run/quizverse/gunicorn.pid` to Gunicorn or use `systemctl reload quizverse` in logrotate. |
| **DOC-08** | **Session Lifetime Consistency** | `PRODUCTION_CONFIGURATION_GUIDE.md` §2 | Lists `PERMANENT_SESSION_LIFETIME = 28800` (8 Hours). | `app.py` line 102 sets `PERMANENT_SESSION_LIFETIME = 14400` (4 Hours). | `app.py` sets 14400 seconds (4 hours), an ideal security balance for examination terminals. | **LOW** | **Authoritative Standard:** Update documentation to reflect 14,400 seconds (4 hours), with note explaining how institutions may override it. |
| **DOC-09** | **Nginx Edge Rate Limiting** | `KNOWN_LIMITATIONS_AND_FUTURE_ROADMAP.md` §2.3 | Claims Nginx edge rate limiting (`limit_req_zone`) mitigates process-local in-memory rate limiting. | `DEPLOYMENT_GUIDE.md` §4.1 Nginx configuration completely omitted `limit_req_zone` and `limit_req` blocks. | Source inspection of `DEPLOYMENT_GUIDE.md` confirmed no rate limiting directives were present in Nginx configuration. | **HIGH** | **Correction Implemented:** Provided complete, verified Nginx `limit_req_zone` and `limit_req` configurations with explicit exempt CIDR blocks for campus NAT IP addresses. |
| **DOC-10** | **Submission Latency Expectations** | `OPERATIONS_AND_MONITORING_GUIDE.md` §3 | Normal Range: 100 ms – 300 ms. Warning: > 800 ms. Critical: > 2000 ms. | `PERFORMANCE_REPORT.md` §2.5 records blended P95 latency of 825.59 ms at 20 concurrent workers. | Under 20 concurrent threads writing to SQLite simultaneously, P95 reaches ~825 ms without errors. | **MEDIUM** | **Authoritative Standard:** Clarify that 100–300 ms applies to idle / normal staggered exam pacing (< 5 writes/sec). Under burst concurrent submissions (15–30 writes/sec), P95 naturally expands to 500–850 ms. |

---

## 4. Conclusion & Action Plan

All 10 documented inconsistencies have been analyzed, reconciled with actual code behavior, and corrected across the master documentation suite. No conflicting operational commands or contradictory architecture recommendations remain.

