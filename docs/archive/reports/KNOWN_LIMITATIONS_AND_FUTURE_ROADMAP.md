# QuizVerse v2.0 - Known Limitations & Future Engineering Roadmap

**Document ID:** QZ-RD-2026-011  
**Author:** Principal Software Architect & Product Engineering  
**Application Target:** QuizVerse Institutional Examination System  
**Effective Date:** November 1, 2026  
**Status:** ARCHITECTURAL SPECIFICATION & PLANNING  

---

## 1. Executive Summary

This document provides a candid, evidence-based technical evaluation of the current architectural boundaries and physical constraints of QuizVerse v2.0, along with a structured 6-phase engineering roadmap designed to scale the platform from a mid-sized institutional application (up to 500 concurrent examinees) to a multi-campus, high-concurrency enterprise system (10,000+ concurrent examinees).

---

## 2. Current Architectural Boundaries & Operational Constraints

### 2.1 SQLite Single-Writer Concurrency Ceiling
- **Current Architecture:** SQLite 3.45.3 operating in Write-Ahead Logging (WAL) mode with a 5,000 ms busy timeout.
- **Strength:** Extremely fast reads (up to 937 RPS) with zero memory bloat (50 MB footprint) and zero external database daemon dependencies.
- **Constraint:** SQLite serializes all database write operations through a single operating system file lock. While WAL mode allows simultaneous readers during a write transaction, concurrent write transactions must queue sequentially.
- **Operational Boundary:** Under empirical testing, the sustained write capacity peaks at **30.7 to 35.0 mixed write RPS**. If a synchronized batch of $> 500$ students clicks "Submit Final Exam" at the exact same millisecond, tail requests will queue up to 5–8 seconds.
- **Current Mitigation:** The client countdown timer incorporates 0–3 second randomized submission jitter to distribute final write spikes.

### 2.2 Client-Side Browser WebAssembly Footprint
- **Current Architecture:** The Live Code Sandbox executes candidate Python 3 scripts in-browser via Pyodide WebAssembly (v0.25.0).
- **Strength:** Complete server insulation against Remote Code Execution (RCE) attacks; the server never executes untrusted student code.
- **Constraint:** Pyodide requires downloading ~15 MB of WebAssembly binaries and standard library components on the candidate's initial page visit.
- **Current Mitigation:** Assets are cached aggressively in the client browser (`Cache-Control: max-age=2592000`) and CDN, meaning subsequent loads are instantaneous.

### 2.3 Process-Local In-Memory Rate Limiting
- **Current Architecture:** A Python sliding-window rate limiter using thread locks (`threading.Lock()`).
- **Constraint:** In a multi-process WSGI topology (e.g. Gunicorn with 4 separate worker processes), each worker process maintains an isolated in-memory dictionary. While adequate for single-node deployments using multi-threaded workers (`gthread`), an attacker could theoretically rotate requests across processes.
- **Current Mitigation:** Gunicorn configured with `worker-class = gthread` running multiple threads within bounded processes, combined with Nginx edge rate limiting (`limit_req_zone`).

### 2.4 Browser-Level Proctoring Boundaries
- **Current Architecture:** JavaScript client telemetry monitoring HTML5 Fullscreen API, Page Visibility API (`document.visibilityState`), window blur events, and local WebRTC camera streams.
- **Constraint:** Web browser security models prevent web applications from capturing OS-level hotkeys (e.g., Windows Key, Alt-Tab on some Linux window managers) or detecting secondary physical monitors without explicit user permission. Furthermore, WebRTC camera access requires a W3C Secure Context (HTTPS or localhost).
- **Current Mitigation:** Real-time violation ingestion via `POST /api/proctor/event` logs every window blur and tab switch, giving exam proctors a tamper-proof timestamped audit trail.

### 2.5 Multi-Language Code Compilation Constraints
- **Current Architecture:** Interactive execution is available for Python via Pyodide WebAssembly. For compiled languages (C++, Java), the AI Code Doctor performs static algorithmic analysis and complexity feedback, but does not compile native binaries on the host OS.
- **Design Rationale:** Spawning uncontained `g++` or `javac` subprocesses directly on the host server creates severe security risks (fork bombs, privilege escalation, server compromise).

---

## 3. Six-Phase Engineering Roadmap

```
+-----------------------------------------------------------------------------------+
|                           QUIZVERSE EVOLUTION ROADMAP                             |
+-----------------------------------------------------------------------------------+
| Phase 1: PostgreSQL Enterprise Database Migration                                  |
|   - Eliminate single-writer bottlenecks; support 5,000+ simultaneous writes       |
+-----------------------------------------------------------------------------------+
| Phase 2: Centralized Redis Layer (Sessions, Cache & Distributed Rate Limiting)    |
|   - Multi-node shared session store & global IP rate limiting                    |
+-----------------------------------------------------------------------------------+
| Phase 3: Asynchronous Task Workers (Celery / Redis Queue)                         |
|   - Offload heavy AI synthesis, bulk syllabus ingestion & PDF generation          |
+-----------------------------------------------------------------------------------+
| Phase 4: Containerized Multi-Language Code Execution Sandbox (Judge0 / Docker)   |
|   - Native C++, Java, Rust, and Go compilation inside ephemeral gVisor sandboxes   |
+-----------------------------------------------------------------------------------+
| Phase 5: Continuous WebRTC Video Streaming & Computer Vision Proctoring           |
|   - Server-side multi-candidate live video stream wall for proctors               |
+-----------------------------------------------------------------------------------+
| Phase 6: LMS Interoperability (LTI 1.3 Advantage Standard)                        |
|   - Turnkey integration with Canvas, Blackboard, Moodle, and Brightspace          |
+-----------------------------------------------------------------------------------+
```

---

### Phase 1: PostgreSQL Enterprise Database Migration
- **Objective:** Support multi-server institutional clusters with $> 5,000$ concurrent submissions.
- **Technical Steps:**
  1. Introduce SQLAlchemy ORM / psycopg3 abstraction layer in `database/init_db.py`.
  2. Implement database connection pooling via PgBouncer (pool size: 50–100 connections).
  3. Partition `quiz_attempts` and `proctoring_logs` tables by academic year and semester.
  4. Enable continuous WAL streaming replication to an active-passive hot standby.

### Phase 2: Centralized Redis Cache & Distributed Rate Limiting
- **Objective:** Unify session state and rate limiting across load-balanced multi-server clusters.
- **Technical Steps:**
  1. Migrate Flask session storage from signed client cookies to Redis (`flask-session`).
  2. Implement Redis token-bucket rate limiter via `Flask-Limiter` with fallback to local memory if Redis disconnects.
  3. Cache frequently queried public leaderboards and topic taxonomies in Redis with a 60-second TTL.

### Phase 3: Asynchronous Task Workers (Celery / RQ)
- **Objective:** Eliminate WSGI worker blocking during heavy syllabus processing and batch exports.
- **Technical Steps:**
  1. Deploy Celery workers backed by Redis broker.
  2. Offload unstructured 50-page syllabus PDF parsing and dynamic question generation to background tasks.
  3. Generate institutional batch grade report PDFs asynchronously, notifying faculty via webhook or email upon completion.

### Phase 4: Containerized Multi-Language Sandbox (Judge0 / Piston)
- **Objective:** Provide full native execution, compilation, and unit-testing for C, C++, Java, Go, and Rust.
- **Technical Steps:**
  1. Integrate an isolated microservice container running Judge0 or Piston.
  2. Restrict container execution via Linux cgroups, seccomp filters, and gVisor sandboxing (0 network access, 2-second CPU timeout, 128 MB RAM limit).
  3. Connect QuizVerse Code Sandbox to execute multi-language candidate test cases securely.

### Phase 5: WebRTC Video Streaming & Automated CV Proctoring
- **Objective:** Live multi-stream proctoring wall for exam invigilators.
- **Technical Steps:**
  1. Implement lightweight WebRTC peer connection forwarding periodic video snapshots (1 frame every 5 seconds) to an SFU (Selective Forwarding Unit).
  2. Run background computer vision models (MediaPipe Face Mesh) to detect multiple faces, absence of candidate, or gaze diversion.
  3. Surface automated alerts to proctor dashboard in real time.

### Phase 6: LTI 1.3 Advantage Integration (Canvas / Moodle / Blackboard)
- **Objective:** Seamless institutional LMS single sign-on (SSO) and automated gradebook synchronization.
- **Technical Steps:**
  1. Implement LTI 1.3 Core, Assignment and Grade Services (AGS), and Names and Role Provisioning Services (NRPS).
  2. Allow university instructors to embed QuizVerse examinations directly into Canvas / Blackboard course modules.
  3. Automatically transmit final student grades, Bloom's cognitive breakdowns, and proctoring audit logs back into the institutional SIS gradebook.

