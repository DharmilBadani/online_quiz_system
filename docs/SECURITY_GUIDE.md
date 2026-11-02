# SECURITY & COMPLIANCE GUIDE

## 1. Security Principles
QuizVerse incorporates defensive engineering patterns aligned with OWASP Top 10 recommendations:

1. **ProxyFix Anti-Spoofing:** All client IP resolution uses Werkzeug's `ProxyFix` middleware when `TRUSTED_PROXIES` is set. Raw client `X-Forwarded-For` headers are never trusted directly.
2. **Authoritative Server Proctoring:** Hidden form fields such as `cheat_flags` are ignored during exam submission. Cheating violation metrics and tab switches are derived strictly from server-side proctoring telemetry received at `/api/proctor/event`.
3. **Session & Attempt Protection:** Attempt tokens are generated via `secrets.token_hex(24)` and bound to authenticated candidate sessions. Attempt tokens cannot be submitted across users.
4. **Idempotent Submission & Mutex Locks:** In-memory submission locks prevent duplicate grading from replayed POST requests.
5. **CSRF Protection:** All mutating routes enforce anti-CSRF token verification (`_csrf_token` in form data or `X-CSRFToken` in AJAX headers).
6. **Insecure Direct Object Reference (IDOR) Defense:** Results export endpoints (`/export-result/<id>` and `/api/export-result/<id>`) require verified ownership or administrator role.
7. **CSV Injection Sanitization:** Spreadsheet formulas starting with `=`, `+`, `-`, or `@` are prepended with `'` during CSV exports.
8. **Permanent Demo Admin Lockout:** `/demo-login/admin` returns HTTP 403 unconditionally; demo fast-pass logins are disabled in production via `ALLOW_DEMO_LOGINS=false`.

---

## 2. Realistic Proctoring Limitations

> [!WARNING]
> **Proctoring Scope:** The built-in proctoring subsystem monitors client-side browser blur, fullscreen exit, and tab switching events. It cannot detect external hardware monitors, virtual machines, physical books, or mobile devices. For high-stakes institutional examinations, physical proctors or dedicated lockdown browsers are advised.

