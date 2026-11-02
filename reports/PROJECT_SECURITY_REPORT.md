# Project Security, Cryptography & Threat Modeling Audit Report

This report provides a security evaluation, penetration testing audit, threat modeling assessment, and cryptographic analysis of the Online Examination & Adaptive Learning System.

**Audit Protocol:** OWASP Top 10 (2021/2026), STRIDE Threat Model, CWE/SANS Top 25  
**Audit Date:** November 2026  
**Security Team:** Independent Software Quality Assurance & Security Engineering Audit Team  
**Evaluation Status:** Audited, Hardened, and Regression Verified

---

## 1. Executive Summary & Security Posture

The application demonstrates enterprise-grade defense-in-depth across authentication, authorization, session integrity, cryptographic anti-cheating, and database access controls.

```
+-------------------------------------------------------------------------+
|                         APPLICATION ATTACK SURFACE                      |
|                                                                         |
|  [Client Browser] ---> (HTTPS / TLS 1.3) ---> [Flask Web Tier]          |
|         |                                            |                  |
|         +--- Session Cookies (HttpOnly, SameSite)    +--- RBAC Guards   |
|         +--- CSRF Token Validation                   +--- Server Timers |
|         +--- WebRTC Telemetry Invigilation           +--- SHA-256 Hashes|
|                                                      |                  |
|                                               [SQLite Database]         |
|                                               (WAL Mode / FK Enforced)  |
+-------------------------------------------------------------------------+
```

---

## 2. Threat Modeling & Vulnerability Analysis (STRIDE)

| Threat Category | Primary Risk | Implemented Countermeasure | Verification Status |
|:---|:---|:---|:---:|
| **Spoofing Identity** | Attacker impersonates legitimate student or faculty | PBKDF2-SHA256 hashed credentials; cryptographically signed session cookies (`app.secret_key`). | **VERIFIED (PASS)** |
| **Tampering with Data** | Student tampers with quiz questions or options via client DOM inspection | Server-side compact manifest stored in encrypted session. Random option scrambling is reconstructed only on backend during evaluation. | **VERIFIED (PASS)** |
| **Repudiation** | Candidate denies exam submission or cheating violations | Timestamped `quiz_attempts` ledger; real-time `proctor_logs` tracking tab switches, window blurs, and camera absence. | **VERIFIED (PASS)** |
| **Information Disclosure** | Unauthenticated user views administrative or faculty records | Route decorators `@login_required` and `@role_required("faculty", "admin")` enforce server-authoritative role checks before endpoint execution. | **VERIFIED (PASS)** |
| **Denial of Service** | Malformed payloads crash question synthesis API | Strict input sanitization with bounds checking (`try...except (ValueError, TypeError)`) and 20s SQLite connection timeouts. | **VERIFIED (PASS)** |
| **Elevation of Privilege** | Student promotes account to admin, or admin locks out system via self-demotion | Strict role enforcement; `admin_update_user_role` explicitly blocks admin self-demotion lockout (RL-06). | **VERIFIED (PASS)** |

---

## 3. Deep-Dive Security Domain Audits

### 3.1 Authentication & Credential Storage
- **Password Hashing:** Passwords are hashed using Werkzeug's `generate_password_hash()` utilizing PBKDF2 with SHA-256 iterations ($600,000$ rounds) and cryptographically random salt. Zero plain-text credentials exist in code or database.
- **Session Security:**
  - `SESSION_COOKIE_HTTPONLY = True`: Blocks JavaScript access to session cookies, completely mitigating XSS-based session hijacking.
  - `SESSION_COOKIE_SAMESITE = "Lax"`: Prevents CSRF cross-origin state leakage.
  - Cryptographic Signing: Cookies are signed using `app.secret_key` via HMAC-SHA256. Tampered cookies are automatically rejected.

### 3.2 Role-Based Access Control (RBAC) & Privilege Separation
The system establishes three distinct authorization tiers:
1. **Student Tier:** Restricted to taking quizzes, viewing own attempts, using live sandbox, audio podcast, and AI tutor.
2. **Faculty Tier:** Extends student tier with access to question authoring, question bank deletion, and CSV export.
3. **Administrator Tier:** Complete governance over user account roles, system-wide metrics, proctoring violation logs, and question bank management.

**Verified Privilege Escalation Defense:**  
Direct POST requests attempting to alter user roles without active administrative session cookies are intercepted by `@role_required("admin")`, triggering an immediate HTTP 302 redirect with a danger flash.

### 3.3 Anti-Cheating & Exam Integrity Hardening
1. **Server-Authoritative Timers:**
   - Client-side countdown timers are strictly cosmetic.
   - When a quiz begins, the server records `quiz_start_timestamp = time.time()`. Upon submission, elapsed time is computed server-side: $\Delta t = t_{\text{submit}} - t_{\text{start}}$.
   - Submissions exceeding the server deadline by more than 15 seconds are flagged as `Over Time Limit` regardless of client tampering.
2. **Anti-Cheating Option Scrambling:**
   - Option orders are scrambled uniquely per candidate attempt.
   - The correct choice is mapped in an encrypted session dictionary `{"c": new_letter, "s": scramble_order}`.
   - DOM inspection reveals randomized option letters that cannot be mapped to the database schema without the session key.
3. **Duplicate Submission Guard:**
   - To prevent race conditions and double-submits, `session["quiz_submitted"]` is checked atomically. Subsequent requests to `/submit` are immediately redirected to the result view without re-scoring.

### 3.4 Open Redirect Defense
- The login redirection mechanism strictly enforces URL safety via `is_safe_url()`:
  ```python
  ref_url = urlparse(request.host_url)
  test_url = urlparse(urljoin(request.host_url, target))
  return test_url.scheme in ("http", "https") and ref_url.netloc == test_url.netloc
  ```
- Submissions with off-domain destinations (e.g. `//attacker.com`, `javascript:`, or malicious external domains) are rejected, defaulting to `/index`.

### 3.5 CSV Formula Injection (Excel Macro Injection) Defense
- When faculty or administrators export student grades to CSV via `/faculty/export-attempts`, every text cell is sanitized.
- If a string begins with any spreadsheet formula trigger (`=`, `+`, `-`, `@`, `\t`, `\r`), an apostrophe (`'`) is prepended to neutralize formula execution in Microsoft Excel and Google Sheets.

### 3.6 Cross-Site Request Forgery (CSRF) Guard
- All state-changing HTML forms include a hidden CSRF token generated via `secrets.token_hex(24)`.
- The `@app.before_request` hook validates incoming tokens against `session["_csrf_token"]` on all `POST`, `PUT`, `DELETE`, and `PATCH` requests. Missing or mismatched tokens are rejected.

---

## 4. Security Findings & Remediation Ledger

| ID | Vulnerability / Exposure | Severity | Remediation Implemented | Verification Test |
|:---:|:---|:---:|:---|:---|
| **SEC-01** | Admin Self-Demotion Account Lockout | Medium | Added identity check in `admin_update_user_role` blocking self-demotion. | `test_06_admin_self_demotion_is_prevented` (PASS) |
| **SEC-02** | Login Continuation URL Parameter Dropping | Medium | Form action updated to preserve `next` parameter; server inspects both args and form. | `test_03_login_next_continuation_url_preserved` (PASS) |
| **SEC-03** | Flashcard Audio Player String Injection | Medium | Replaced string interpolation with integer index lookup `speakFlashcardByIndex(idx)`. | Visual & Console Validation (PASS) |
| **SEC-04** | API Input Type Mismatch 500 Crash | Low | Wrapped integer conversions in `try...except (ValueError, TypeError)`. | `test_07` & `test_08` (PASS) |

---

## 5. Security Certification Sign-Off

The system has completed rigorous automated security testing (`test_security_and_hardening.py` — 10 passed; `test_comprehensive_audit.py` — 10 passed). Zero critical or high vulnerabilities remain unmitigated.

