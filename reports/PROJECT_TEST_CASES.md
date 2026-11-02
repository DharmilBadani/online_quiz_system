# PROJECT_TEST_CASES.md
# Comprehensive Test Case Specification Matrix
**Project:** QuizVerse — Intelligent Academic Assessment & AI Studio  
**Audit Team:** SQA Engineering Audit Team  
**Date:** November 01, 2026  

---

## 1. Authentication & Role-Based Access Control (RBAC)

| Case ID | Test Name | Objective | Preconditions | Inputs / Action | Expected Result | Status Baseline |
|---|---|---|---|---|---|---|
| TC-AUTH-01 | Student Authentication | Verify standard student credentials login | User exists (`student`) | POST `/login` with `student`/`student123` | 302 redirect, session populated with student role | Passed |
| TC-AUTH-02 | Faculty Authentication | Verify faculty credentials login | User exists (`faculty`) | POST `/login` with `faculty`/`faculty123` | 302 redirect, session populated with faculty role | Passed |
| TC-AUTH-03 | Admin Authentication | Verify administrator login | User exists (`admin`) | POST `/login` with `admin`/`admin123` | 302 redirect, session populated with admin role | Passed |
| TC-AUTH-04 | Invalid Credentials Rejection | Reject invalid password | System ready | POST `/login` with `student`/`wrong_pass` | 200 re-render with danger flash alert | Passed |
| TC-AUTH-05 | Login Continuation Redirection | Redirect to `next` URL after sign-in | User unauthenticated | Access `/login?next=/leaderboard` then submit form | Redirects to `/leaderboard` | Failed (Next param dropped by form action) |
| TC-AUTH-06 | Open Redirect Protection | Reject external malicious URLs | System ready | POST `/login?next=https://attacker.com` | Redirects to internal `/` or `/landing`, not attacker | Passed |
| TC-AUTH-07 | Institutional Registration | Create valid student account | New username | POST `/register` with valid credentials | 302 redirect, user created in `users` table | Passed |
| TC-AUTH-08 | Duplicate Username Handling | Prevent duplicate account creation | Existing user | POST `/register` with `student` | Rejects with warning flash, preserves DB | Passed |
| TC-AUTH-09 | Password Length Constraint | Enforce minimum 6 characters | System ready | POST `/register` with password `123` | Rejects with warning flash | Passed |
| TC-AUTH-10 | Sign-out Session Clearance | Invalidate session upon logout | User logged in | GET `/logout` | Session keys cleared, redirect to index | Passed |

---

## 2. Dynamic Question Generation & Anti-Repeat Engine

| Case ID | Test Name | Objective | Preconditions | Inputs / Action | Expected Result | Status Baseline |
|---|---|---|---|---|---|---|
| TC-DYN-01 | Cryptographic SHA-256 Fingerprinting | Verify normalization & hashing of question text | None | `compute_question_hash("Sample Q?")` | Deterministic 32-char hex string | Passed |
| TC-DYN-02 | User History Recording | Record presented question hashes in database | DB ready | Call `record_user_presented_questions` | Hashes persisted in `user_question_history` | Passed |
| TC-DYN-03 | Anti-Repeat Exclusion | Guarantee previously seen questions are excluded | User has seen Q | Query questions with `seen_hashes` | Previously seen question is never returned | Passed |
| TC-DYN-04 | Gemini Live Model Cascade | Verify Gemini API model cascade | API Key set | Call `call_gemini_api` | Returns live AI completion | Failed (Hardcoded models 404) |
| TC-DYN-05 | Python Parametric Variety | Generate 10 distinct Python questions | Offline mode | Call `generate_parametric_dynamic_questions('Python', 10)` | Returns 10 unique deterministic questions | Passed |
| TC-DYN-06 | Java Parametric Variety | Generate 10 distinct Java questions | Offline mode | Call `generate_parametric_dynamic_questions('Java', 10)` | Returns 10 unique deterministic questions | Passed |
| TC-DYN-07 | C++ Parametric Variety | Generate 10 distinct C++ questions | Offline mode | Call `generate_parametric_dynamic_questions('C++', 10)` | Returns 10 unique deterministic questions | Passed |
| TC-DYN-08 | DBMS Parametric Variety | Generate 10 distinct SQL questions | Offline mode | Call `generate_parametric_dynamic_questions('DBMS', 10)` | Returns 10 unique deterministic questions | Passed |
| TC-DYN-09 | OS Parametric Variety | Generate 10 distinct OS questions | Offline mode | Call `generate_parametric_dynamic_questions('OS', 10)` | Returns 10 unique deterministic questions | Passed |
| TC-DYN-10 | DSA Parametric Variety | Generate 10 distinct DSA questions | Offline mode | Call `generate_parametric_dynamic_questions('DSA', 10)` | Returns 10 unique questions | Failed (Returns only 3 questions) |
| TC-DYN-11 | WebDev Parametric Variety | Generate 10 distinct WebDev questions | Offline mode | Call `generate_parametric_dynamic_questions('WebDev', 10)` | Returns 10 unique questions | Failed (Returns only 1 question) |
| TC-DYN-12 | Flask Parametric Variety | Generate 10 distinct Flask questions | Offline mode | Call `generate_parametric_dynamic_questions('Flask', 10)` | Returns 10 unique questions | Failed (Returns only 4 questions) |

---

## 3. Quiz Delivery, Timers, Option Shuffling & Proctoring

| Case ID | Test Name | Objective | Preconditions | Inputs / Action | Expected Result | Status Baseline |
|---|---|---|---|---|---|---|
| TC-QUIZ-01 | 20-Question Subject Exam | Full exam draws exactly 20 questions | DB ready | GET `/quiz?category=Java&topic=All+Topics` | Renders 20 questions, 10:00 timer | Passed |
| TC-QUIZ-02 | 10-Question Sub-topic Drill | Drill draws exactly 10 questions | DB ready | GET `/quiz?category=Java&topic=Looping+Statements` | Renders 10 questions, 05:00 timer | Passed |
| TC-QUIZ-03 | Master Challenge Combined Exam | Draw 20 questions across all 8 subjects | DB ready | GET `/quiz?category=All&topic=All+Topics` | Renders 20 mixed questions, 10:00 timer | Passed |
| TC-QUIZ-04 | Anti-Cheat Option Shuffling | Randomize options sequence per candidate | DB ready | Generate quiz session | Option letters scrambled, manifest records mapping | Passed |
| TC-QUIZ-05 | Autosave Answer Cache | Cache selected choices in localStorage | Active quiz | Select radio inputs | State stored under subtopic key | Passed |
| TC-QUIZ-06 | Autosave State Recovery | Restore choices on accidental page reload | Cached state | Reload `/quiz` | Pre-selects choices, restores progress bar | Passed |
| TC-QUIZ-07 | Proctoring HUD Visibility | Enable camera & gaze invigilation | `proctor=1` | GET `/quiz?category=Python&proctor=1` | Proctor HUD visible, WebRTC camera init | Passed |
| TC-QUIZ-08 | Tab Switch Telemetry Flag | Decrement trust score on tab change | Proctored quiz | Trigger `visibilitychange` event | Trust score decrements, violation logged | Passed |
| TC-QUIZ-09 | Window Blur Telemetry Flag | Decrement trust score on focus loss | Proctored quiz | Trigger `window.blur` event | Trust score decrements, violation logged | Passed |

---

## 4. Submission, Scoring, Overtime & Persistence

| Case ID | Test Name | Objective | Preconditions | Inputs / Action | Expected Result | Status Baseline |
|---|---|---|---|---|---|---|
| TC-SUB-01 | Quiz Answer Evaluation | Grade submitted choices accurately | Active manifest | POST `/submit` with all correct answers | 100% score, Grade A+, 302 to `/result` | Passed |
| TC-SUB-02 | Partial Scoring & Letter Grade | Calculate accurate partial percentages | Active manifest | POST `/submit` with 7/10 correct | 70.0% score, Grade B | Passed |
| TC-SUB-03 | Unanswered Question Handling | Gracefully evaluate unselected items | Active manifest | POST `/submit` with empty payload | 0% score, Grade D, 0 answered | Passed |
| TC-SUB-04 | Duplicate Submission Prevention | Prevent re-submission via back button | Quiz submitted | POST `/submit` second time | Intercepted, redirects with info flash | Passed |
| TC-SUB-05 | Server-Authoritative Timer | Flag submissions exceeding duration | Active quiz | POST `/submit` with elapsed > limit + 60s | Speed rating = "Over Time Limit" | Passed |
| TC-SUB-06 | Speed Pace Calculation | Compute average time per question | Fast completion | POST `/submit` with fast elapsed time | Correct average seconds, speed badge assigned | Passed |
| TC-SUB-07 | Database Attempt Persistence | Store record in `quiz_attempts` | Quiz submitted | Complete quiz submission | Row created with candidate, score, trust, topic | Passed |
| TC-SUB-08 | Proctor Violation Log Persistence | Store telemetry in `proctor_logs` | Infractions > 0 | Submit with `cheat_flags=2`, `trust_score=70` | Proctor log row created linking attempt | Passed |

---

## 5. Result Analytics, Mistake Practice & AI Modules

| Case ID | Test Name | Objective | Preconditions | Inputs / Action | Expected Result | Status Baseline |
|---|---|---|---|---|---|---|
| TC-RES-01 | Result Screen Gauge & Confetti | Render score gauge, stats, certificate | Quiz submitted | GET `/result` | Circular gauge displays, review list rendered | Passed |
| TC-RES-02 | Single Attempt JSON Export API | Export verified attempt JSON schema | Valid attempt ID | GET `/api/quiz/export-result/<id>` | 200 OK, JSON schema with grade & trust score | Passed |
| TC-RES-03 | Adaptive Mistake Revision Practice | Construct targeted drill from missed Qs | Attempt with errors | GET `/quiz/review-mistakes` | Custom drill prepared with missed items | Failed (Option text corrupted on re-submit) |
| TC-RES-04 | 100% Perfect Score Mistake Handler | Handle 0 errors gracefully | Attempt with 100% | GET `/quiz/review-mistakes` | Redirects to result with congratulations flash | Passed |
| TC-RES-05 | Socratic AI Tutor API | Provide misconception guidance & analogy | Question context | POST `/api/ai-tutor` | 200 OK with `reply`, `key_takeaway`, `concept_tag` | Partially Passed (Fallback only) |
| TC-RES-06 | AI Revision Podcast API | Generate 2-host conversational recap | Review items | POST `/api/podcast/generate` | 200 OK with `dialogue` and `audio_flashcards` | Partially Passed (Quote syntax error in flashcards) |
| TC-RES-07 | AI Oral Viva Generation | Generate spoken viva examination question | Domain topic | POST `/api/viva/generate-question` | 200 OK with `question`, `expected_concepts` | Partially Passed (Fallback only) |
| TC-RES-08 | AI Oral Viva Defense Scoring | Evaluate spoken candidate transcript | Transcript string | POST `/api/viva/evaluate` | 200 OK with `score`, `feedback`, `missing_points` | Partially Passed (Fallback only) |
| TC-RES-09 | 1v1 Battle Arena Duel | Load 5 questions against ApexBot | Arena active | GET `/arena` | Renders duel HUD with dual health bars | Passed |
| TC-RES-10 | Code Sandbox WASM Execution | Execute Python in browser via Pyodide | Sandbox page | Click 'Run Code' on Two Sum | Executes in WebAssembly without server latency | Passed |
| TC-RES-11 | AI Code Auto-Grader API | Evaluate code complexity & edge cases | Python code | POST `/api/sandbox/evaluate` | 200 OK with time/space complexity & feedback | Passed |
| TC-RES-12 | Syllabus Ingestion & Synthesis | Extract modules & generate MCQs from PDF | Syllabus PDF/Text | POST `/syllabus-ingest` | 200 OK with `modules`, `questions`, `flashcards` | Partially Passed (Quiz launch unpersisted) |

---

## 6. Faculty Studio, Admin Console & Security Hardening

| Case ID | Test Name | Objective | Preconditions | Inputs / Action | Expected Result | Status Baseline |
|---|---|---|---|---|---|---|
| TC-FAC-01 | Faculty Studio Access Control | Restrict studio to faculty/admin | Logged in as student | GET `/faculty/studio` | 302 redirect with danger flash | Passed |
| TC-FAC-02 | Custom Question Authoring | Commit authored question to bank | Faculty auth | POST `/faculty/question/add` | Inserted into `questions` table | Passed |
| TC-FAC-03 | Question Bank Deletion | Delete question by ID | Faculty auth | POST `/faculty/question/<id>/delete` | Deleted from table, flash notice | Passed |
| TC-FAC-04 | CSV Export Formula Sanitization | Sanitize malicious spreadsheet formulas | Attempt with `=cmd` | GET `/faculty/export-csv` | Cells with `=, +, -, @` prefixed with single quote | Passed |
| TC-ADM-01 | Admin Console Access Control | Restrict admin console strictly to admin | Logged in as faculty | GET `/admin` | 302 redirect with danger flash | Passed |
| TC-ADM-02 | User Role Modification | Change user role between student/faculty | Admin auth | POST `/admin/user/<id>/role` | `users.role` updated | Partially Passed (Admin can demote self) |
| TC-ADM-03 | User Deletion Referential Integrity | Preserve student attempts upon user delete | Admin auth | POST `/admin/user/<id>/delete` | User deleted; attempts preserved with `user_id = NULL` | Passed |
| TC-ADM-04 | Self-Deletion Guard | Block admin from deleting active account | Admin auth | POST `/admin/user/<current_id>/delete` | Blocked with danger flash | Passed |
| TC-ADM-05 | Proctor Log Purge | Purge all proctoring violation logs | Admin auth | POST `/admin/proctor/clear` | `proctor_logs` table truncated | Passed |
| TC-SEC-01 | CSRF Token Generation & Check | Block POST without valid token | `WTF_CSRF=True` | POST `/login` without CSRF token | 302 redirect with security warning flash | Passed |
| TC-SEC-02 | OWASP Session Cookie Flags | Prevent XSS access to session cookie | App config | Inspect session cookie headers | `HttpOnly=True`, `SameSite=Lax` | Passed |
| TC-SEC-03 | OWASP Security Response Headers | Prevent clickjacking and MIME sniffing | All responses | Inspect response headers | `X-Frame-Options: SAMEORIGIN`, `nosniff`, `XSS` | Passed |
| TC-SEC-04 | Parameterized SQL Injection Guard | Prevent SQL injection on user input | All inputs | Input `' OR '1'='1` in login/quiz/search | Safely handled via parameterized statements | Passed |
| TC-SEC-05 | Payload Upload Size Limit | Enforce 16MB maximum upload payload | Big payload | POST payload > 16MB | 413 Entity Too Large handler catches | Passed |

