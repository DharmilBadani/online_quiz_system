# VERIFIED RELEASE MANIFEST — QUIZVERSE v2.0.0
**Product Name:** QuizVerse Institutional Online Examination Platform  
**Target Release:** v2.0.0 Institutional Production Release Candidate  
**Build Timestamp:** 2026-11-02 15:05:00 UTC+05:30  
**Authoritative Git Commit SHA:** `e7dc900d8ca7f2d4c38c0d09c7ad8d22ab3176e3`  
**Git Release Tag:** `v2.0.0-institutional-prod`  
**Release Artifact Filename:** `dist/FINAL_RELEASE_ARTIFACT.zip`  
**Release Artifact SHA-256:** `2592a9169ca14b56404904edaf64f64366856655ec984b3abc59096453f7e08b`  
**Evidence Bundle Filename:** `dist/FINAL_EVIDENCE_BUNDLE.zip`  
**Evidence Bundle SHA-256:** `a7b65c80a8e4adcbc5ba64be1d5261270532a3d1e6fe19aac618e3efc37cbf98`  
**Automated QA Execution ID:** `task-1605` (64 / 64 Tests Passed, 100% Pass Rate)  

---

## 1. Core Source Cryptographic Hashes (SHA-256)

Every critical application, database, configuration, and documentation file included in the release candidate has been cryptographically fingerprinted:

| File Path | Size (Bytes) | SHA-256 Hash | Technical Purpose |
| :--- | :--- | :--- | :--- |
| `app.py` | 100,528 | `ca8b061673d2ef97c2c22f499d2e45739fa9fce9332af2621f4538d85a997fc7` | Primary WSGI web controller, routing, session lifecycle, security middleware, RBAC. |
| `major_services.py` | 32,844 | `56b6b4a5350f78158205d13c4cd9ba8dce3c846d7aac537f9da2706a8c41d565` | AI cascade, 3-state circuit breaker, Socratic tutor, Viva Voce oral examiner. |
| `dynamic_question_engine.py` | 16,389 | `444d814f40d70a8cb509900739cd85fc61bfd01547a545b8ae9fc8e33f99a943` | Parameterized question generation, candidate hash tracking (0-repetition guarantee). |
| `curriculum_catalog.py` | 9,845 | `e25307b56f7a0dd84daa701349d1ea290ed77843a9f4148f0cfc4681eea1526f` | Institutional curriculum master taxonomy (8 core domains, 80 granular subtopics). |
| `database/init_db.py` | 14,530 | `91c479d23a109c4617e4436642021cf444864eaf6eedb768233a6bb60409ea02` | Idempotent schema DDL, WAL configuration, composite indexes, 800-question seed. |
| `database/backup_db.py` | 7,614 | `1b818bb1abc2d0092ff361c3b336c91db6f47f2db59c9abb06fdcfca420767ee` | Tier-isolated backup utility (`daily`, `exam_window`, `manual`) and atomic restoration. |
| `requirements.txt` | 412 | `27eff5c6281e680d49be06d6797ad1c3966985bd202aa3a183100594548952af` | Pinned dependency manifest for production deployment and test automation. |
| `.env.example` | 1,024 | `0b9085b6b63b27b2a6eca807e6515ebd7f2da1d258544889ff1a7816b387d74c` | Sanitized configuration template with environment variable documentation. |
| `.gitignore` | 640 | `168ff39613ec3bb54613ceec23666f218db8d7f882edd0f73bacabb54057f094` | Version control exclusion rules isolating secrets, databases, and build artifacts. |

---

## 2. Release Distribution Inclusion Manifest

The clean release distribution archive (`dist/FINAL_RELEASE_ARTIFACT.zip`) contains exactly 106 verified source files:

1. **Application Core:** `app.py`, `major_services.py`, `dynamic_question_engine.py`, `curriculum_catalog.py`, `requirements.txt`, `pyrightconfig.json`, `README.md`, `.gitignore`, `.env.example`.
2. **Database Management & Seeds:** `database/init_db.py`, `database/backup_db.py`, `database/generate_800_questions.py`, `database/__init__.py`.
3. **Frontend Templates (16 HTML Files):** `templates/admin_dashboard.html`, `templates/ai_generator.html`, `templates/analytics.html`, `templates/arena.html`, `templates/base.html`, `templates/faculty_studio.html`, `templates/index.html`, `templates/ingest.html`, `templates/landing.html`, `templates/leaderboard.html`, `templates/login.html`, `templates/profile.html`, `templates/quiz.html`, `templates/register.html`, `templates/result.html`, `templates/sandbox.html`, `templates/student_bookmarks.html`, `templates/viva.html`.
4. **Static Assets:** `static/css/style.css` and associated client assets.
5. **Automated QA Test Suites (6 Files):** `test_addendum_validations.py`, `test_app.py`, `test_comprehensive_audit.py`, `test_major_features.py`, `test_security_and_hardening.py`, `test_upgrades_and_security.py`.
6. **Performance Harnesses:** `staging_load_test.py`, `benchmark_load_test.py`, `reproduce_performance_benchmark.py`.
7. **Comprehensive Audit Documentation:** All reports in `reports/final_remediation/` and `reports/reconciliation/`.

---

## 3. Strict Distribution Exclusion Register

The following items are **STRICTLY EXCLUDED** from the release archive to guarantee zero secret leakage and data privacy:

- `*.env` and `.env` (Never distribute live API keys, session secrets, or private credentials).
- `quiz.db`, `quiz.db-wal`, `quiz.db-shm`, `*.db` (Never distribute local development or testing database records; database must be initialized fresh via `init_db.py`).
- `backups/` directory (Historical local snapshots are isolated).
- `.git/` internal directory.
- `__pycache__/` and `.pytest_cache/` bytecode caches.
- `dist/` build directory.
