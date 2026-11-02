# QuizVerse v2.0 - Final Documentation Corrections & Standardized Specifications

**Document ID:** QZ-COR-2026-001  
**Author:** Principal Software Architect & Release Management  
**Scope:** Universal Reconciliation of All Technical and Operational Claims  
**Effective Date:** November 2, 2026  
**Status:** AUTHORITATIVE BASELINE  

---

## 1. Executive Summary

This document establishes the definitive, unified specifications for QuizVerse v2.0, resolving every inconsistency discovered during the staging inspection. All deployment runbooks, architecture diagrams, and operational guides are bound by the standardized values declared below.

---

## 2. Reconciled Technical Specifications

### 2.1 Test Suite Accounting: 61/61 Tests (Not Stale 58/58)
- **Previous Finding:** Earlier audit summaries cited 58 passing tests.
- **Root Cause:** Three additional automated test cases were implemented in `test_addendum_validations.py` to prevent regressions:
  - `test_07_unauthorized_proctor_telemetry_blocked`: Verifies proctor event session authorization.
  - `test_08_unauthenticated_user_cannot_submit_authenticated_token`: Verifies token hijack defense.
  - `test_09_backup_and_recovery_utility_verification`: Verifies SQLite hot backup creation, `--keep` retention pruning, and live restoration.
- **Authoritative Standard:** The official automated regression suite contains **61 test cases across 6 test modules**. All reports must cite **61 / 61 tests passing (100% pass rate)**.

### 2.2 Session Lifetime vs. Attempt Expiration (4 Hours vs. 24 Hours)
- **Previous Finding:** Documentation appeared to conflict between 4-hour and 24-hour expiration periods.
- **Root Cause:** Two completely separate security mechanisms exist:
  1. **Authentication Session Cookie Lifetime (`PERMANENT_SESSION_LIFETIME = 14400` / 4 Hours):** Governs student and faculty browser login sessions. Minimizes risk on shared campus computer lab terminals.
  2. **Active Exam Attempt Token Validity Window (`86400` / 24 Hours):** In `submit_quiz()`, the server checks `time.time() - active_session_row["start_timestamp"] > 86400`. This allows a student whose laptop loses power or whose network drops mid-exam to resume within 24 hours without an immediate failure.
- **Authoritative Standard:** Both values are correct and serve complementary security functions:
  - **Login Session Cookie:** 4 Hours.
  - **In-Flight Exam Attempt Token Ceiling:** 24 Hours.

### 2.3 Database Permissions & Ownership (`0600` vs. `0660`)
- **Previous Finding:** Some sections recommended `0600` while others recommended `0660`.
- **Authoritative Standard:**
  - **Dedicated User Ownership (`quizverse:quizverse`):** Set permissions to `0600` (read/write exclusively for the application user).
  - **Shared Group Deployment (`quizverse:www-data`):** Set permissions to `0660` so that both the Gunicorn worker process (`quizverse`) and the Nginx group (`www-data`) or backup daemon have necessary read/write access to `quiz.db`, `quiz.db-wal`, and `quiz.db-shm`.

### 2.4 Empirical Benchmark vs. Estimated Student Cohort Capacity
- **Previous Finding:** Conflation of tested worker threads with active examinees.
- **Authoritative Standard:**
  - **Empirically Measured Benchmark Load:** Up to **25 concurrent worker threads** (isolated) and **20 concurrent workers** (blended) at **30.7 writes/sec** and **937.6 reads/sec**.
  - **Estimated Institutional Cohort Capacity:** **300 to 500 active staggered examinees** on single-node hardware. Derived using Little's Law, assuming typical student exam pacing of one request every 20–40 seconds (0.025–0.05 RPS per student).
  - **Mandate:** Technical documentation must never claim 300–500 students as an empirical benchmark result; it must always be labeled as modeled cohort capacity.

### 2.5 Synchronized Submission Queue Delays & SQLite Ceilings
- **Previous Finding:** Varying estimates of submission wait times under simultaneous write bursts.
- **Authoritative Empirical Queue Formula:** At sustained SQLite write throughput of 30.7 writes/sec:
  - **50 simultaneous submissions:** $\approx 1.6\text{ seconds}$ queue clearance.
  - **100 simultaneous submissions:** $\approx 3.3\text{ seconds}$ queue clearance.
  - **250 simultaneous submissions:** $\approx 8.1\text{ seconds}$ queue clearance.
  - **500 simultaneous submissions:** $\approx 16.3\text{ seconds}$ queue clearance (approaching 20,000 ms busy timeout).
- **Authoritative Mitigations:**
  1. Client-side randomized countdown jitter (0–3 seconds) in `templates/quiz.html`.
  2. Exam invigilators instruct students to submit upon completing rather than waiting for the final countdown bell.
  3. Cohorts $> 500$ in a single synchronized exam hall must be migrated to PostgreSQL.

### 2.6 Gunicorn Worker Topology & Rate Limiting Scope
- **Previous Finding:** 4 Gunicorn worker processes fragment the in-memory sliding-window rate limiter.
- **Authoritative Standard:**
  - **Standard Institutional Topology (Single Node):** Deploy Gunicorn with **1 worker and 8 threads** (`--workers 1 --threads 8 --worker-class gthread`). This eliminates process-local fragmentation and handles up to 900+ read RPS.
  - **Multi-Worker Topology (4 Workers x 2 Threads):** Only approved when paired with the standardized Nginx edge rate limiting configuration below.

### 2.7 Nginx Edge Rate Limiting with Campus NAT Accommodation
- **Previous Finding:** Generic rate limiting risked blocking campus computer labs sharing a single public IP.
- **Authoritative Configuration:**
  ```nginx
  limit_req_zone $binary_remote_addr zone=quiz_general_limit:10m rate=30r/s;
  limit_req_zone $binary_remote_addr zone=quiz_auth_limit:10m rate=5r/s;

  location ~* ^/(login|register) {
      # Burst=20 allows multiple campus lab students on same NAT to log in sequentially
      limit_req zone=quiz_auth_limit burst=20 nodelay;
      proxy_pass http://127.0.0.1:5000;
  }

  location / {
      # Burst=50 absorbs classroom navigation spikes
      limit_req zone=quiz_general_limit burst=50 nodelay;
      proxy_pass http://127.0.0.1:5000;
  }
  ```

### 2.8 Backup Schedule, RPO, RTO & Retention Policy
- **Previous Finding:** Conflicting RPO statements (hourly vs. 15 minutes) and retention periods (7 days vs. 30 days).
- **Authoritative Standard:**
  - **RPO (Recovery Point Objective):** $< 15\text{ minutes}$ during active exam windows (guaranteed by 15-minute cron schedule `*/15 8-18 * * 1-5`); 24 hours standard.
  - **RTO (Recovery Time Objective):** $< 1\text{ minute}$ (empirically measured restoration time: 0.84 seconds).
  - **Retention Policy:** Retain rolling 30 daily snapshots (`--keep 30`).
  - **Primary Path:** `/opt/quizverse/backups` (with `--dest` override support).
  - **Off-Site Replication:** Daily encrypted sync via AWS S3 / Cloudflare R2 CLI (`aws s3 sync ... --sse aws:kms`).

### 2.9 Health Check Protocol & Systemd PID Management
- **Previous Finding:** Documentation previously instructed `curl https://127.0.0.1:5000/health` (failing due to SSL handshake).
- **Authoritative Commands:**
  - **Loopback Health Check:** `curl -s http://127.0.0.1:5000/health` (plain HTTP against port 5000).
  - **Public Domain Health Check:** `curl -s https://exams.university.edu/health` (HTTPS through Nginx).
  - **Service Management:** Systemd unit uses `Type=exec` with `--pid /run/quizverse/gunicorn.pid`. Logrotate triggers graceful worker reload via `systemctl reload quizverse`.

