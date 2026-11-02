# REMAINING RISKS & FUTURE ACTIONS ROADMAP — QUIZVERSE v2.0.0
**Project:** QuizVerse — Institutional Online Examination & Assessment Platform  
**Target Release:** v2.0.0 Institutional Production Release Candidate  
**Inspection Date:** November 2, 2026  
**Auditing Role:** Principal Software Architect & Site Reliability Engineer  

---

## 1. Residual Risk Register & Operational Mitigations

While all critical security vulnerabilities and architectural defects have been resolved in the v2.0.0 release candidate, the following operational risks and environmental constraints remain relevant for institutional operations:

| Risk ID | Risk Description | Severity | Operational Context | Implemented Mitigation & Protocol |
| :--- | :--- | :--- | :--- | :--- |
| **RISK-01** | Administrator Non-Compliance on Secret Rotation | Medium | If an administrator deploys the template `.env` without generating a fresh secret key, session forgery could occur. | `app.py` validates `FLASK_SECRET_KEY` on startup when `FLASK_ENV=production`. If a known default placeholder is detected, the process aborts immediately. |
| **RISK-02** | Examination Cohort Exceeding 500 Concurrent Examinees | Medium | SQLite allows concurrent readers but serializes writers. If > 500 examinees click submit simultaneously, disk I/O queues may increase. | The deployment runbook specifies exam window scheduling or batching for large departments. For cohorts > 500, migration to PostgreSQL 16 is recommended. |
| **RISK-03** | Upstream Gemini API Quota Exhaustion or Regional Outage | Low | High-frequency oral viva or question synthesis requests could encounter HTTP 429 quota limits. | The 3-state `CircuitBreaker` and deterministic parametric offline generators guarantee 100% platform availability even under complete AI disconnectivity. |
| **RISK-04** | Transient Student Wi-Fi Disconnections | Low | A student sitting for an exam may experience intermittent campus Wi-Fi drops during a question. | The client exam UI caches state locally, and active attempt tokens remain valid in server-side session memory for 24 hours, permitting seamless resume. |
| **RISK-05** | Host Server Hardware Failure | Low | Single-node server hardware outage could interrupt active exams. | High-frequency exam-window backups run every 15 minutes to isolated disk tiers. Offsite replication via `rsync` or S3 ensures RPO < 15 minutes and RTO < 5 minutes. |

---

## 2. Engineering Roadmap (v2.1 & v3.0)

### 2.1 Enterprise Institutional Authentication (v2.1)
- **SAML 2.0 / Shibboleth / OAuth2 / LDAP:** Enable native integration with institutional identity providers (e.g., Azure AD, Google Workspace for Education, Canvas LMS LTI) to eliminate local credential management entirely.
- **Role Synchronization:** Automatically map student and faculty organizational units (OUs) to QuizVerse permissions.

### 2.2 Relational Database Abstraction (v2.2)
- **PostgreSQL 16 Multi-Master Backend:** Introduce an optional database adapter layer allowing large universities to switch from SQLite to PostgreSQL with connection pooling (PgBouncer).
- **Horizontal Scaling:** Decouple session storage to Redis, enabling multi-node Gunicorn clusters behind an AWS ALB or HAProxy load balancer.

### 2.3 Automated WebRTC Video Proctoring (v3.0)
- **Edge Vision AI:** Implement client-side lightweight TensorFlow.js face tracking to detect second persons or absence without streaming heavy video feeds to the server, preserving bandwidth in low-connectivity college campuses.
- **Encrypted Audit Replays:** Capture periodic timestamped frame snapshots attached directly to proctoring telemetry audit logs.

### 2.4 Asynchronous Task Processing (v3.0)
- **Celery / Redis Worker Pool:** Offload intensive batch AI syllabus processing, multi-speaker podcast synthesis, and bulk PDF report generation to asynchronous background workers.
