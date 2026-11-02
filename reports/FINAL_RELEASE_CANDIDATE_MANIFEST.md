# QuizVerse v2.0 - Final Release Candidate Manifest & Integrity Inventory

**Document ID:** QZ-MAN-2026-001  
**Build Tag:** `v2.0.0-institutional-prod`  
**Execution Environment:** Windows 11 Enterprise (AMD64 build 10.0.26300)  
**Python Runtime:** Python 3.12.10 (MSC v.1943 64 bit)  
**Database Engine:** SQLite 3.49.1 with Write-Ahead Logging (`wal`)  
**Freeze Date:** November 2, 2026  
**Status:** FROZEN & CRYPTOGRAPHICALLY SECURED  

---

## 1. Executive Summary

This manifest freezes and cryptographically fingerprints the exact source code, database migration utilities, and automated test suites comprising the **QuizVerse v2.0.0 Institutional Release Candidate**.

A pre-release rollback snapshot has been preserved at `staging/rollback_snapshot/`.

---

## 2. Version Control & Environment Specification

- **Git Repository Status:** Not initialized as a local Git repository (`fatal: not a git repository`). System versioning is established via this SHA-256 cryptographic manifest.
- **Python Version:** `3.12.10 (tags/v3.12.10:0cc8128, Apr  8 2025, 12:21:36) [MSC v.1943 64 bit (AMD64)]`
- **SQLite Engine Version:** `3.49.1`
- **Key Python Dependencies:**
  - `Flask == 3.0.3`
  - `Werkzeug == 3.0.3`
  - `gunicorn == 22.0.0`
  - `pytest == 8.2.2`
  - `pytest-flask == 1.3.0`
  - `requests == 2.34.2`
  - `python-dotenv == 1.0.1`
  - `pypdf == 6.14.2`
  - `psutil == 7.2.2`

---

## 3. Cryptographic SHA-256 Release Manifest

| Relative File Path | Size (Bytes) | SHA-256 Checksum Digest |
| :--- | :--- | :--- |
| `app.py` | 94,295 | `a0a494889c06ef3749de1e96d1c1b72ffef9bf73743b8d42c42a2245da6eab44` |
| `major_services.py` | 41,525 | `56b6b4a5350f78158205d13c4cd9ba8dce3c846d7aac537f9da2706a8c41d565` |
| `dynamic_question_engine.py` | 52,346 | `444d814f40d70a8cb509900739cd85fc61bfd01547a545b8ae9fc8e33f99a943` |
| `curriculum_catalog.py` | 8,546 | `e25307b56f7a0dd84daa701349d1ea290ed77843a9f4148f0cfc4681eea1526f` |
| `requirements.txt` | 656 | `27eff5c6281e680d49be06d6797ad1c3966985bd202aa3a183100594548952af` |
| `.env.example` | 873 | `0ca144c972af74bb9dfcb753e1c70f389f485e552e26546bcc6ecf4cafee5f7f` |
| `database/init_db.py` | 14,427 | `ed948ce1d96d38c09b9744b3299ea5e28b589665730265b4770119b3ece206fc` |
| `database/backup_db.py` | 5,217 | `af6b0a172a739a3a2f853d503deb66bd596d99552b6d8173f302cd0795ac5d5e` |
| `test_app.py` | 6,801 | `5a8f16fd637ac6af053825e7b191c15d33b94f110e526ea1a00e33ed2f3ab705` |
| `test_major_features.py` | 20,486 | `46713e538c0789ea44445a61b3aed928fb06c56794166263d042237f472b7040` |
| `test_comprehensive_audit.py` | 10,233 | `c0d1406e00a48fb27abe944bf02c3bf0f2ea66de89ed59b194beee1b6a5cb167` |
| `test_security_and_hardening.py` | 13,171 | `49f2938d12360d55a67e0d650ee617d7008140ef46227ee554ff0bd6e6c322f2` |
| `test_upgrades_and_security.py` | 13,198 | `24748e9d0eb2cc0d8da05b41c7a0c9ed10a64939cbb96eebe7cff589b3179128` |
| `test_addendum_validations.py` | 15,546 | `e58f339b35e6cb5ac962355cf672fa1658180bf21554a3eb5e50f5a27ee81dfc` |

---

## 4. Rollback Snapshot Verification

A clean directory snapshot of the release candidate files was created:
- **Snapshot Path:** `staging/rollback_snapshot/`
- **Contents:** Clean copies of all 14 core source files, migration tools, and test suites.
- **Rollback Procedure:** If an unrecoverable failure occurs during staging or deployment, restoring the files from `staging/rollback_snapshot/` returns the application to its exact baseline state.

---

## 5. Release Lead Sign-Off

The release candidate is officially frozen. No further modifications to core business logic or security boundaries are permitted without a formal engineering change order.

**Sign-off:** Principal DevOps & QA Engineering Lead  
**Candidate Status:** **FROZEN FOR STAGING VALIDATION**

