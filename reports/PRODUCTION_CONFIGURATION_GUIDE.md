# QuizVerse v2.0 - Production Configuration Guide & Environment Reference

**Document ID:** QZ-CFG-2026-007  
**Author:** DevOps & Systems Architecture Engineering  
**Application Target:** QuizVerse Institutional Edition v2.0  
**Security Classification:** Confidential / System Administrator Reference  
**Effective Date:** November 1, 2026  

---

## 1. Overview & Configuration Architecture

QuizVerse relies on twelve-factor application configuration principles. All operational parameters, cryptographic secrets, database file paths, and external API integrations are driven strictly through environment variables.

In development, these variables are loaded from a local `.env` file via `python-dotenv`. In production, variables must be managed via systemd unit configurations or secure secret managers, with file-level read permissions restricted to the application service user.

---

## 2. Complete Configuration Parameter Reference

The table below itemizes every configuration parameter utilized by QuizVerse:

| Variable Name | Type | Default Value | Recommended Production Setting | Description & Security Impact |
| :--- | :--- | :--- | :--- | :--- |
| `FLASK_ENV` | String | `development` | `production` | Dictates application execution mode. When set to `production`, debug mode is permanently disabled and strict security startup assertions are enforced. |
| `FLASK_SECRET_KEY` | String (Hex) | Insecure placeholder | 64-character random hex string | Cryptographic secret used for signing session cookies and generating CSRF tokens. **Mandatory in production.** Application halts on boot if default key is detected. |
| `ALLOW_DEMO_LOGINS` | Boolean | `true` (in dev) | `false` | Enables/disables 1-click fast-pass development login buttons on the login page. **Must be false in production** to prevent unauthorized account access. |
| `GEMINI_API_KEY` | String | Empty string (`""`) | Institutional Google AI API Key | API key for Google Gemini Generative AI models. Optional: if omitted or exhausted, automatic circuit breaker engages local algorithmic question synthesis. |
| `FLASK_HOST` | String | `127.0.0.1` | `127.0.0.1` | Network interface binding. Must bind to localhost when running behind an Nginx reverse proxy. |
| `FLASK_PORT` | Integer | `5000` | `5000` | Port for the WSGI application server (Gunicorn / Waitress). |
| `DATABASE_PATH` | Path | `quiz.db` | `/opt/quizverse/quiz.db` | Absolute or relative filesystem path to the primary SQLite database file. |
| `SESSION_COOKIE_SECURE` | Boolean | Inferred from env | `True` | Directs browsers to transmit session cookies exclusively over encrypted HTTPS connections. Automatically enabled when `FLASK_ENV=production`. |
| `SESSION_COOKIE_HTTPONLY`| Boolean | `True` | `True` | Prevents client-side JavaScript from accessing session cookies via `document.cookie`, mitigating XSS session theft. |
| `SESSION_COOKIE_SAMESITE`| String | `Lax` | `Lax` | Restricts cookie transmission on cross-site requests, mitigating Cross-Site Request Forgery (CSRF). |
| `PERMANENT_SESSION_LIFETIME`| Integer (Sec) | `28800` (8 Hours) | `28800` | Controls session duration before automatic timeout, preventing indefinite login persistence on shared campus lab terminals. |

---

## 3. Production Startup Sanity Guard

To prevent catastrophic security misconfigurations, `app.py` enforces fail-secure startup validations:

```python
# Production Startup Security Verification in app.py
if os.environ.get("FLASK_ENV") == "production":
    secret = os.environ.get("FLASK_SECRET_KEY", "").strip()
    insecure_defaults = [
        "",
        "dev-secret-key-change-in-production",
        "quizverse-insecure-secret-key-change-in-production",
        "change-me",
        "secret",
        "123456"
    ]
    if not secret or secret in insecure_defaults or len(secret) < 32:
        raise RuntimeError(
            "FATAL: Production mode active, but FLASK_SECRET_KEY is missing, "
            "too short (<32 chars), or set to an insecure default placeholder! "
            "Application startup halted to prevent security compromise."
        )
```

**Operational Impact:** If an administrator attempts to launch QuizVerse in production without provisioning a high-entropy secret, the process immediately crashes with exit code 1, preventing vulnerable operation.

---

## 4. Cryptographic Secret Generation

Never use dictionary words, passwords, or reused strings as secrets. Generate a high-entropy 256-bit (32-byte) cryptographic key via Python's `secrets` module:

```bash
python3 -c "import secrets; print(secrets.token_hex(32))"
```

*Example Output:*
```text
c84a7e93f120d58b29f041289c44e97a31d9b3a0429f45e7d56e1892c5a089bf
```

---

## 5. Production `.env` Template

Create `/opt/quizverse/.env` with file mode `0600` owned by `quizverse:quizverse`:

```ini
# =============================================================================
# QUIZVERSE INSTITUTIONAL PRODUCTION CONFIGURATION
# =============================================================================

# Execution environment: MUST be 'production'
FLASK_ENV=production

# 64-character high-entropy cryptographic secret for session signing
FLASK_SECRET_KEY=c84a7e93f120d58b29f041289c44e97a31d9b3a0429f45e7d56e1892c5a089bf

# Google Gemini API Key for dynamic synthesis, viva voce, and AI tutoring
# Leave blank to operate entirely in autonomous offline algorithmic fallback mode
GEMINI_API_KEY=AIzaSyYourInstitutionalKeyHere

# Disable all development fast-pass login shortcuts
ALLOW_DEMO_LOGINS=false

# Binding configuration (loopback interface behind Nginx)
FLASK_HOST=127.0.0.1
FLASK_PORT=5000

# Explicit Database Path
DATABASE_PATH=/opt/quizverse/quiz.db
```

---

## 6. Systemd Environment Configuration

Rather than relying on `.env` files on disk, enterprise Linux systems can inject environment parameters directly into the systemd service unit via an override file:

Execute:
```bash
sudo systemctl edit quizverse.service
```
Insert the following overrides:
```ini
[Service]
Environment="FLASK_ENV=production"
Environment="FLASK_SECRET_KEY=c84a7e93f120d58b29f041289c44e97a31d9b3a0429f45e7d56e1892c5a089bf"
Environment="GEMINI_API_KEY=AIzaSyYourInstitutionalKeyHere"
Environment="ALLOW_DEMO_LOGINS=false"
Environment="FLASK_HOST=127.0.0.1"
Environment="FLASK_PORT=5000"
```
Reload and restart the service:
```bash
sudo systemctl daemon-reload
sudo systemctl restart quizverse
```

---

## 7. Secret Rotation Protocol

1. **Scheduling:** Plan secret rotation during designated maintenance windows (e.g. Sunday 03:00 AM) or between academic terms.
2. **Impact:** Rotating `FLASK_SECRET_KEY` invalidates all currently active student browser sessions. Active students will be prompted to log in again.
3. **Execution Steps:**
   - Generate a new 64-character key.
   - Update the configuration in systemd or `.env`.
   - Execute graceful reload: `sudo systemctl reload quizverse`.
   - Verify health status: `curl -I http://127.0.0.1:5000/health`.

