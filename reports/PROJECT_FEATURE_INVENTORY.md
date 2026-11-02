# PROJECT_FEATURE_INVENTORY.md
# QuizVerse — Enterprise Quality Assurance & Engineering Audit

**Audit Date:** November 01, 2026  
**Auditor:** Software Quality Assurance and Engineering Audit Team  
**Scope:** Complete End-to-End Application Feature Inventory  

---

## 1. Feature Inventory Summary

| ID | Feature Name | Primary Endpoint | Roles Supported | Status Baseline |
|---|---|---|---|---|
| F-01 | User Authentication (Sign-in) | `POST /login` | Guest, Student, Faculty, Admin | Partially Passed (Next URL dropped by form) |
| F-02 | User Registration | `POST /register` | Guest, Student, Faculty | Inspected & Tested |
| F-03 | 1-Click Role Fast-Pass Demo Login | `GET /demo-login/<role>` | Student, Faculty, Admin | Tested & Passed |
| F-04 | User Session & Sign-out | `GET /logout` | All authenticated | Tested & Passed |
| F-05 | Gateway Landing vs Examination Hub | `GET /` & `GET /landing` | All | Tested & Passed |
| F-06 | 100% Dynamic Question Engine (Gemini) | Internal Service | System | Broken (Model 404 in major_services.py) |
| F-07 | Parametric Procedural Generator | Internal Service | System | Broken (WebDev=1, DSA=3, Flask=4 Qs) |
| F-08 | Cryptographic SHA-256 Anti-Repeat | Internal Service | System | Tested & Passed |
| F-09 | Full Subject Exam (20 Qs, 10:00) | `GET/POST /quiz` | All | Tested & Passed |
| F-10 | Focused Topic Drill (10 Qs, 05:00) | `GET/POST /quiz` | All | Tested & Passed |
| F-11 | Master Challenge (20 Qs, All Subjects) | `GET/POST /quiz` | All | Tested & Passed |
| F-12 | Anti-Cheating Option Shuffling | `GET /quiz` | All | Tested & Passed |
| F-13 | Client-Side Autosave & Safe Resume | `GET /quiz` | All | Tested & Passed |
| F-14 | WebRTC AI Vision Proctoring & Gaze | `GET /quiz?proctor=1` | All | Tested & Passed |
| F-15 | Duplicate Submission Prevention | `POST /submit` | All | Tested & Passed |
| F-16 | Server-Authoritative Timer & Grace Period | `POST /submit` | All | Tested & Passed |
| F-17 | Scoring & Speed Pace Analytics | `POST /submit` | All | Tested & Passed |
| F-18 | Attempt Persistence & Proctor Telemetry | `POST /submit` | All | Tested & Passed |
| F-19 | Result Screen & Animated Gauge | `GET /result` | All | Tested & Passed |
| F-20 | Socratic AI Doubt Tutor | `POST /api/ai-tutor` | All | Broken (Gemini 404 fallback only) |
| F-21 | AI Revision Podcast Studio | `POST /api/podcast/generate` | All | Partially Broken (Quote syntax error in flashcard onclick) |
| F-22 | Adaptive Mistake Practice Mode | `GET /quiz/review-mistakes` | All | Broken (Shuffled option mismatch on resubmit) |
| F-23 | Official Printable Certificate | `GET /result` | All | Tested & Passed |
| F-24 | Verified Attempt JSON Export | `GET /api/quiz/export-result/<id>` | All | Tested & Passed |
| F-25 | Ranked Leaderboard & Podium | `GET /leaderboard` | All | Tested & Passed |
| F-26 | 1v1 Real-Time Battle Arena | `GET /arena` | All | Tested & Passed |
| F-27 | AI Oral Viva Voce & Speech Examiner | `GET /viva`, `POST /api/viva/*` | All | Broken (Gemini 404 fallback only) |
| F-28 | GenAI Question & Syllabus Studio | `GET/POST /ai-generator` | Student, Faculty, Admin | Broken (start_quiz launches 20 unrelated Qs) |
| F-29 | Smart Syllabus & Note Ingestion | `GET/POST /syllabus-ingest` | All | Broken (Launch Quiz unpersisted) |
| F-30 | Live Code Sandbox & Pyodide WASM | `GET /sandbox`, `POST /api/sandbox/*` | All | Tested & Passed |
| F-31 | Cognitive Mastery Analytics (IRT) | `GET /analytics` | All | Tested & Passed |
| F-32 | Student Profile & History Telemetry | `GET /profile` | Student, Faculty, Admin | Partially Broken (Student Export Data links to Faculty Studio) |
| F-33 | Faculty Studio & Question CRUD | `GET/POST /faculty/studio`, `/faculty/question/*` | Faculty, Admin | Tested & Passed |
| F-34 | Institutional CSV Audit Export | `GET /faculty/export-csv` | Faculty, Admin | Tested & Passed |
| F-35 | Admin Console & User Governance | `GET /admin`, `POST /admin/user/*` | Admin | Partially Broken (Admin can demote self) |
| F-36 | Admin Proctor Telemetry Purge | `POST /admin/proctor/clear` | Admin | Tested & Passed |
| F-37 | Soft UI 2.0 Neumorphic Design & Dark Mode | Base layout & style.css | All | Tested & Passed |
| F-38 | Web Audio API FX Synthesizer | `static/js` / `base.html` | All | Tested & Passed |

---

## 2. Feature Verification Matrix

| Feature | Frontend State | Backend Route | Database Operation | Observed Result | Status |
|---|---|---|---|---|---|
| **F-01 Login** | Working form | Connected (`/login`) | Read (`users`) | Works, but `next` redirect query param dropped by `<form action>` | Partially Passed |
| **F-02 Registration** | Working form | Connected (`/register`) | Write (`users`) | Inspected & Tested. Backend needs email uniqueness safety check | Passed |
| **F-03 Demo Login** | Working buttons | Connected (`/demo-login/<role>`) | Read (`users`) | 1-click authentication instant and verified | Passed |
| **F-04 Logout** | Working navbar link | Connected (`/logout`) | Session pop | Verified clean session clearance | Passed |
| **F-05 Gateway / Hub** | Working switcher | Connected (`/` & `/landing`) | Read (`questions`) | Unauthenticated redirects to landing; authenticated/guest to hub | Passed |
| **F-06 Gemini Synthesizer**| Working interface | Connected | External REST | Google API returns 404 due to deprecated model strings | Failed |
| **F-07 Procedural Generator**| Working engine | Connected | Procedural | WebDev returns 1, DSA returns 3, Flask returns 4 questions | Failed |
| **F-08 Anti-Repeat** | Silent engine | Connected | Read/Write (`user_question_history`) | Cryptographic SHA-256 fingerprinting prevents repeated questions | Passed |
| **F-09 20-Q Exam** | Working HUD | Connected (`/quiz`) | Read (`questions`) | Draws 20 questions, sets 10:00 timer, validates | Passed |
| **F-10 10-Q Drill** | Working HUD | Connected (`/quiz`) | Read (`questions`) | Draws 10 questions, sets 05:00 timer, validates | Passed |
| **F-11 Master Challenge**| Working HUD | Connected (`/quiz`) | Read (`questions`) | Draws 20 mixed questions across 8 subjects | Passed |
| **F-12 Option Shuffling**| Working tiles | Connected (`/quiz`) | Scrambles | Compact manifest stores scrambled letter mapping | Passed |
| **F-13 Autosave/Resume** | Working localStorage | Client-side | Client storage | Restores selections on reload; wiped on submission | Passed |
| **F-14 AI Vision Proctor**| Working WebRTC HUD | Client/Server | Write (`proctor_logs`) | Detects blur, tab-switch, aversion, logs to table | Passed |
| **F-15 Duplicate Guard** | Working button | Connected (`/submit`) | Session flag | Re-submission returns finalized alert, blocks double submit | Passed |
| **F-16 Timer Policy** | Working countdown | Connected (`/submit`) | Timestamp check | Flags overtime (> grace period) as "Over Time Limit" | Passed |
| **F-17 Scoring & Grades**| Working gauge | Connected (`/submit`) | Calculation | Computes score, percentage, grade, speed rating | Passed |
| **F-18 Persistence** | N/A | Connected (`/submit`) | Write (`quiz_attempts`) | Stores candidate name, category, topic, score, time, trust | Passed |
| **F-19 Result Screen** | Working charts | Connected (`/result`) | Read (`session`) | Gauge counts up, confetti fires, stats breakdown | Passed |
| **F-20 Socratic Tutor** | Working modal | Connected (`/api/ai-tutor`) | External AI | Functions via fallback; Gemini 404 prevents live Socratic tutor | Partially Passed |
| **F-21 Audio Podcast** | Working studio | Connected (`/api/podcast/generate`)| External AI + TTS | Dialogue audio plays, but flashcards with single quotes break JS | Partially Passed |
| **F-22 Mistake Practice**| Working CTA | Connected (`/quiz/review-mistakes`)| Read/Write | Shuffled options mismatched against database original text | Failed |
| **F-23 Certificate** | Working print | Client print | DOM formatting | Verified layout, seal, watermark, academic honors | Passed |
| **F-24 JSON Export** | Working link | Connected (`/api/quiz/export-result/<id>`)| Read (`quiz_attempts`) | Returns RFC-compliant verified assessment JSON | Passed |
| **F-25 Leaderboard** | Working podium | Connected (`/leaderboard`)| Read (`quiz_attempts`) | Displays top 40, podium top 3, subject filter | Passed |
| **F-26 1v1 Arena** | Working duel HUD | Connected (`/arena`) | Read (`questions`) | 5 rapid-fire questions against ApexBot with live progress | Passed |
| **F-27 Viva Voce** | Working STT/TTS | Connected (`/viva` & APIs) | External AI + Web Speech| Functions via fallback; live Gemini evaluation 404s | Partially Passed |
| **F-28 AI Generator** | Working studio | Connected (`/ai-generator`)| Write (`questions`)| Synthesizes Qs, but launch quiz runs 20 unrelated Qs | Partially Passed |
| **F-29 Syllabus Ingest** | Working dropzone | Connected (`/syllabus-ingest`)| In-memory / Gemini | Generates flashcards & MCQs, but Launch Quiz is not persisted | Partially Passed |
| **F-30 Code Sandbox** | Working IDE | Connected (`/sandbox` & API)| Pyodide WASM + Gemini | In-browser Python/JS WASM runner works; AI grader connected | Passed |
| **F-31 Analytics** | Working charts | Connected (`/analytics`) | Read (`quiz_attempts`) | Computes Bloom's distribution, IRT theta, spaced targets | Passed |
| **F-32 User Profile** | Working badges | Connected (`/profile`) | Read (`quiz_attempts`) | Displays attempts & radar; student Export Data link 302s | Partially Passed |
| **F-33 Faculty Studio** | Working table | Connected (`/faculty/studio`)| CRUD (`questions`)| Authoring form, live monitor, question delete | Passed |
| **F-34 CSV Export** | Working download | Connected (`/faculty/export-csv`)| Read (`quiz_attempts`) | Formula injection sanitized; downloads clean audit CSV | Passed |
| **F-35 Admin Console** | Working admin UI | Connected (`/admin`)| CRUD (`users`)| Role update & user deletion work; admin can self-demote | Partially Passed |
| **F-36 Proctor Purge** | Working purge | Connected (`/admin/proctor/clear`)| Delete (`proctor_logs`)| Purges logs cleanly with CSRF verification | Passed |
| **F-37 Neumorphism UI** | Dual-shadow CSS | Static | CSS tokens | High contrast micro-borders, tactile buttons, dark/light | Passed |
| **F-38 Sound Synthesizer**| Working Web Audio| Static | Web Audio API | Zero external audio asset dependencies, pleasant click/bell | Passed |

