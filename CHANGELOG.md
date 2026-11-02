# QUIZVERSE CHANGELOG

## [2.0.0] - 2026-11-02
### Added
- Multi-tier isolated backup storage architecture (`backups/daily/`, `backups/exam_window/`, `backups/manual/`) with independent retention policies.
- Automated 30-student multi-account load test harness in `scripts/load_test_30_students.py`.
- WSGI server entry point (`wsgi.py`) configured for Gunicorn `gthread` workers.
- Comprehensive documentation suite under `docs/` (`ARCHITECTURE.md`, `DEPLOYMENT_RUNBOOK.md`, `SECURITY_GUIDE.md`, `BACKUP_AND_RECOVERY.md`, `API_REFERENCE.md`).
- Separated `requirements.txt` (production) and `requirements-dev.txt` (testing and development).

### Changed
- Standardized project directory structure: tests moved to `tests/` with `conftest.py`, benchmarking scripts moved to `scripts/`.
- Reconciled `database/backup_db.py` CLI actions supporting `create`, `backup`, `list`, `prune`, and `restore`.
- Standardized Gunicorn worker blueprint to `--worker-class gthread --workers 4 --threads 2`.
- Standardized Nginx blueprint with edge rate-limiting zones (`limit_req_zone`).

### Fixed
- Resolved client IP rate limiter bypass by wrapping WSGI app with `werkzeug.middleware.proxy_fix.ProxyFix` and inspecting `request.remote_addr`.
- Resolved `/run` tmpfs socket deletion on Linux reboots via systemd `RuntimeDirectory=quizverse`.
- Resolved client-side proctor tampering by deriving violations strictly from server-side telemetry records.
- Resolved IDOR vulnerability on result export endpoints by enforcing attempt ownership checks.
- Resolved cross-tier backup pruning collisions.

### Removed
- Removed obsolete intermediate audit reports from root directory and archived them under `docs/archive/`.
- Removed redundant staging rollback snapshots from active source tree.
- Removed Python bytecode caches and temporary artifacts.
