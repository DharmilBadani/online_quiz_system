# RELEASE MANIFEST & INTEGRITY CHECKSUMS — QUIZVERSE v2.0.0
**Product:** QuizVerse Institutional Online Examination Platform  
**Release Tag:** `v2.0.0-institutional-prod`  
**Git Commit SHA:** `f0620296eb32db5d40651111f9dd91150d284c7b`  
**Build Date:** November 2, 2026  
**Architecture:** Python 3.12 / Flask 3.0+ / SQLite3 WAL / Jinja2 / Vanilla JS  
**Target Release Archive:** `dist/QuizVerse_v2.0.0_Clean_Release.zip`  

---

## 1. Release Inventory & Core Source SHA-256 Checksums

The following cryptographic hashes represent the verified, audited state of the QuizVerse v2.0.0 institutional codebase:

| Filename / Relative Path | Size (Bytes) | SHA-256 Cryptographic Checksum | Purpose / Description |
| :--- | :--- | :--- | :--- |
| `app.py` | 100,528 | `ca8b061673d2ef97c2c22f499d2e45739fa9fce9332af2621f4538d85a997fc7` | Primary Flask WSGI controller, routing, session lifecycle, security middleware. |
| `major_services.py` | 32,844 | `56b6b4a5350f78158205d13c4cd9ba8dce3c846d7aac537f9da2706a8c41d565` | AI cascade, 3-state circuit breaker, Socratic tutor, Viva Voce examiner. |
| `dynamic_question_engine.py`| 16,389 | `444d814f40d70a8cb509900739cd85fc61bfd01547a545b8ae9fc8e33f99a943` | Parameterized question generation, candidate hash tracking (0-repetition). |
| `curriculum_catalog.py` | 9,845 | `e25307b56f7a0dd84daa701349d1ea290ed77843a9f4148f0cfc4681eea1526f` | Master curriculum taxonomy (8 subjects, 80 granular subtopics). |
| `database/init_db.py` | 14,530 | `91c479d23a109c4617e4436642021cf444864eaf6eedb768233a6bb60409ea02` | Idempotent schema initialization, WAL mode, composite indexes. |
| `database/backup_db.py` | 7,427 | `9af33de19dd496244e11a18eca4860d994d422a0e47534321c5d34999db620e3` | Tier-isolated backup utility (`daily`, `exam_window`, `manual`). |
| `requirements.txt` | 412 | `27eff5c6281e680d49be06d6797ad1c3966985bd202aa3a183100594548952af` | Direct pinned dependencies for production and automated QA. |
| `.env.example` | 1,024 | `0b9085b6b63b27b2a6eca807e6515ebd7f2da1d258544889ff1a7816b387d74c` | Sanitized configuration template with environment variables documentation. |
| `.gitignore` | 640 | `168ff39613ec3bb54613ceec23666f218db8d7f882edd0f73bacabb54057f094` | Strict exclusion rules protecting secrets, databases, and local artifacts. |

---

## 2. Release Archive Inclusion Manifest

The production release package (`dist/QuizVerse_v2.0.0_Clean_Release.zip`) contains the following components:

1. **Application Core:** `app.py`, `major_services.py`, `dynamic_question_engine.py`, `curriculum_catalog.py`, `requirements.txt`, `pyrightconfig.json`, `README.md`, `.gitignore`, `.env.example`.
2. **Database Management:** `database/init_db.py`, `database/backup_db.py`, `database/generate_800_questions.py`, `database/__init__.py`.
3. **Frontend Templates (16 Jinja2 Files):** `admin_dashboard.html`, `ai_generator.html`, `analytics.html`, `arena.html`, `base.html`, `faculty_studio.html`, `index.html`, `ingest.html`, `landing.html`, `leaderboard.html`, `login.html`, `profile.html`, `quiz.html`, `register.html`, `result.html`, `sandbox.html`, `student_bookmarks.html`, `viva.html`.
4. **Static Assets:** `static/css/style.css`, client JavaScript utilities, and icons.
5. **Automated Test Harness (6 Suites):** `test_addendum_validations.py`, `test_app.py`, `test_comprehensive_audit.py`, `test_major_features.py`, `test_security_and_hardening.py`, `test_upgrades_and_security.py`.
6. **Performance & Benchmarking:** `staging_load_test.py`, `benchmark_load_test.py`, `reproduce_performance_benchmark.py`.
7. **Comprehensive Audit Documentation:** All 12 final remediation reports in `reports/final_remediation/`.

---

## 3. Strict Distribution Exclusion List

To comply with enterprise security and data privacy mandates, the following files and directories are **STRICTLY EXCLUDED** from the release zip archive:

- `*.env` and `.env` (prevents compromise of live API keys, session secrets, or private credentials).
- `quiz.db`, `quiz.db-wal`, `quiz.db-shm`, `*.db` (prevents distribution of test database records, user accounts, or stale test attempts; database must be initialized fresh via `init_db.py`).
- `backups/` (prevents packaging historical database snapshots).
- `.git/` and `.pytest_cache/` (excludes internal version control and testing cache objects).
- `dist/` (excludes recursive zip nesting).
