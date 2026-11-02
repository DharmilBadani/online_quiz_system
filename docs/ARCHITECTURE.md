# QUIZVERSE SYSTEM ARCHITECTURE

## 1. Overview
QuizVerse is a full-stack online examination and assessment platform built with Python, Flask, SQLite3, Jinja2, and Vanilla JavaScript. The platform supports proctored examinations, dynamic algorithmic question synthesis with zero question repetition, interactive AI tutoring, AI oral viva voce examinations, code sandboxing, and administrative telemetry analytics.

---

## 2. Component Structure

```
QuizVerse/
├── app.py                      # Flask WSGI application controller, routing, RBAC, middleware
├── major_services.py           # Gemini AI cascade, 3-state circuit breaker, Socratic tutor, Viva Voce
├── dynamic_question_engine.py  # Algorithmic question parameterization, candidate anti-repeat hash tracking
├── curriculum_catalog.py       # Static master taxonomy (8 core subjects, 80 granular subtopics)
├── wsgi.py                     # WSGI server entry point (Gunicorn / uWSGI)
├── database/                   # Database lifecycle & migrations
│   ├── init_db.py              # DDL schema initialization, WAL mode, composite indexes, 800-question seed
│   ├── backup_db.py            # SQLite online backup API with tiered retention isolation
│   └── generate_800_questions.py # Question seeding utility
├── templates/                  # 16 Jinja2 server-rendered HTML templates
├── static/                     # Static CSS styling and client assets
├── tests/                      # Automated QA regression and security test suites
├── scripts/                    # Concurrency load testing and operational benchmarks
├── docs/                       # System documentation and manuals
│   └── archive/                # Historical audit reports and logs
├── requirements.txt            # Production runtime dependencies
├── requirements-dev.txt        # Development and testing dependencies
├── .env.example                # Safe environment variable configuration template
└── README.md                   # Quickstart and overview
```

---

## 3. Database Schema & Concurrency Model

### Persistence Layer
- **Engine:** SQLite3
- **Journal Mode:** Write-Ahead Logging (`PRAGMA journal_mode=WAL;`)
- **Disk Synchronization:** `PRAGMA synchronous=NORMAL;`
- **Busy Timeout:** `PRAGMA busy_timeout=5000;` (5,000ms client lock retry interval)
- **Foreign Keys:** `PRAGMA foreign_keys=ON;`
- **Centralized Configuration:** All modules resolve database location dynamically via `os.environ.get("DATABASE_PATH", "quiz.db")`.

### Core Tables
1. `users`: User credentials, roles (`student`, `faculty`, `admin`), PBKDF2 password hashes.
2. `questions`: Curriculum master question bank (800+ seeded questions across 8 domains).
3. `quiz_attempts`: Submitted examination attempts, scores, durations, cheat violation counts.
4. `active_quiz_sessions`: Server-authoritative in-flight exam sessions and tamper-resistant answer rosters.
5. `dynamic_questions`: Algorithmic question cache keyed by unique question hash.
6. `user_question_history`: Candidate anti-collision registry ensuring zero question repetition across attempts.
7. `proctor_logs`: Timestamped audit events (`tab_switch`, `fullscreen_exit`, `blur`).
8. `bookmarked_questions`: Student Study Vault saved questions for targeted review.
9. `viva_evaluations`: AI Oral Viva Voce speech examination transcripts and cognitive scoring.
10. `coding_challenges` & `coding_submissions`: Live code sandbox problems and automated test runner outputs.

---

## 4. Security Architecture

1. **Anti-Spoofing Client IP Resolution:** WSGI application wrapped with `werkzeug.middleware.proxy_fix.ProxyFix`. Rate limiter inspects `request.remote_addr`, neutralizing forged `X-Forwarded-For` headers.
2. **Authoritative Server-Side Sessions:** Active quiz attempts issue a cryptographically random token (`secrets.token_hex(24)`). Cheating flags and tab switches submitted by client forms are ignored; the server counts events authoritatively.
3. **Insecure Direct Object Reference (IDOR) Mitigation:** Result exports enforce strict ownership checks (`attempt.user_id == session.user_id` or admin role).
4. **CSRF Protection:** State-modifying requests require valid `_csrf_token` in form data or `X-CSRFToken` in AJAX headers.
5. **CSV Formula Injection Sanitization:** Spreadsheet formula characters (`=`, `+`, `-`, `@`) are prepended with single quotes `'` during exports.

