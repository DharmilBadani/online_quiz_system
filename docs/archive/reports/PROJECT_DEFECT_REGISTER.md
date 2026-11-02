# Project Defect Register & Vulnerability Ledger

This document maintains the official, enterprise-grade ledger of all defects, architectural anti-patterns, logic bugs, security exposures, and runtime bottlenecks identified during the comprehensive audit of the Online Examination & Adaptive Learning System.

**Audit Protocol:** ISO/IEC 25010 & IEEE 829 Compliant  
**Audit Date:** November 2026  
**Auditing Team:** Independent Software Quality Assurance & Engineering Audit Team  
**Status Lifecycle:** `DETECTED` $\rightarrow$ `REPRODUCED` $\rightarrow$ `REPAIRED` $\rightarrow$ `REGRESSION_VERIFIED`

---

## 1. Defect Summary Dashboard

| Severity | Total Discovered | Confirmed / Reproduced | Repaired | Regression Passed |
|:---|:---:|:---:|:---:|:---:|
| **Critical** | 2 | 2 | 2 | 2 |
| **High** | 2 | 2 | 2 | 2 |
| **Medium** | 4 | 4 | 4 | 4 |
| **Low** | 2 | 2 | 2 | 2 |
| **Total** | **10** | **10** | **10** | **10** |

---

## 2. Detailed Defect Inventory

### Defect ID: D-01
- **Module:** `dynamic_question_engine.py` (`_generate_parametric_webdev`, `_generate_parametric_dsa`, `_generate_parametric_flask`)
- **Severity:** `Critical`
- **Detection Phase:** Phase 5 (White Box) & Phase 8 (Automated Suite — `test_01_parametric_generator_all_categories_generate_full_quota`)
- **Description:** Parametric generators for `WebDev`, `DSA`, and `Flask` suffered from quota starvation when generating dynamic non-repeating exams.
  - `WebDev`: Generated exactly 1 static question (`typeof null === 'object'`). Variables `val1` and `val2` were computed but unused.
  - `DSA`: Had only 3 hash variations (`factor = random.choice([2, 3, 4])`), causing deduplication filters to drop subsequent items.
  - `Flask`: Had only 4 converter rules (`int`, `float`, `path`, `uuid`), stalling when 5, 10, or 20 questions were requested.
- **Root Cause:** Narrow domain models in procedural generator functions; missing loop permutations and procedural templates.
- **Impact:** System failure to generate full 10-question or 20-question quizzes for Web Development, Data Structures, and Flask subjects in dynamic mode, triggering an infinite loop or premature termination.
- **Reproduction:** `dynamic_question_engine.generate_parametric_dynamic_questions('WebDev', 'General', count=10)` returned length 1.
- **Remediation:** Expand procedural generators with 20+ distinct algorithmic variations per subject covering DOM, CSS, JS coercion, asymptotic complexity, BST traversals, stack/queue operations, routing, Jinja2 filters, and HTTP methods.
- **Status:** `REPAIRED` & `REGRESSION_VERIFIED`

---

### Defect ID: D-02
- **Module:** `major_services.py` (`call_gemini_api`)
- **Severity:** `Critical`
- **Detection Phase:** Phase 6 (API Integration Testing) & Phase 8 (`test_02_gemini_model_cascade_contains_active_models`)
- **Description:** Google Gemini API client hardcoded deprecated model strings: `gemini-2.0-flash` and `gemini-1.5-flash`.
- **Root Cause:** Upstream deprecation of legacy preview endpoints by Google Generative AI API returning HTTP 404 (`models/gemini-2.0-flash is not found`).
- **Impact:** Complete failure of all upstream GenAI features (Socratic Tutor, Syllabus Synthesizer, Audio Podcast generator, Code Doctor) across live environments, forcing fallback to offline templates.
- **Reproduction:** Direct REST call to `https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent` returned HTTP 404.
- **Remediation:** Update the model cascade order to active production models: `["gemini-3.5-flash-lite", "gemini-3.5-flash", "gemini-3.8-flash"]`.
- **Status:** `REPAIRED` & `REGRESSION_VERIFIED`

---

### Defect ID: D-03
- **Module:** `app.py` (`syllabus_ingest`), `templates/ingest.html`
- **Severity:** `High`
- **Detection Phase:** Phase 3 (Functionality & E2E Flow Audit)
- **Description:** Document/Syllabus Ingestion synthesized questions were returned to the frontend but never persisted into the SQLite database. Clicking "Launch Quiz" (`/quiz?category=AI+Studio&topic=Custom+Syllabus`) redirected to general fallback questions or failed with 0 questions.
- **Root Cause:** Disconnect between API response and the quiz runner data store.
- **Impact:** Students who uploaded course syllabi or lecture slides were unable to take practice exams on their specific synthesized questions.
- **Reproduction:** Upload syllabus at `/syllabus-ingest`, then click "Launch Quiz". The resulting quiz contained random unrelated questions.
- **Remediation:** Persist ingested questions into `questions` table under `category='AI Studio'` and `topic='Custom Syllabus'`, or pass them into the active quiz session.
- **Status:** `REPAIRED` & `REGRESSION_VERIFIED`

---

### Defect ID: D-04
- **Module:** `app.py` (`review_mistakes_quiz`), `templates/result.html`
- **Severity:** `High`
- **Detection Phase:** Phase 4 (Logic & Data Flow Audit)
- **Description:** Mistake Review Mode passed already-scrambled option dictionaries into `prepared_questions` while assigning `compact_manifest[str(qid)]['s'] = ['A', 'B', 'C', 'D']`.
- **Root Cause:** When submitted to `/submit`, the backend fetched original options from database and indexed them using `s`, causing mismatched option text in review lists and scoring discrepancies.
- **Impact:** Candidates re-taking mistake review drills saw misaligned answers and incorrect feedback upon submission.
- **Reproduction:** Take a quiz, fail a question, click "Drill Incorrect Questions", and submit answers; review shows shuffled option text mapped to mismatched database options.
- **Remediation:** In `review_mistakes_quiz`, query original questions from SQLite, execute standard shuffling, and record consistent permutation indices in `session["quiz_manifest"]`.
- **Status:** `REPAIRED` & `REGRESSION_VERIFIED`

---

### Defect ID: D-05
- **Module:** `templates/login.html`, `app.py` (`login`)
- **Severity:** `Medium`
- **Detection Phase:** Phase 6 (Black Box User Journey & UI Testing)
- **Description:** When an unauthenticated user accesses a protected route (e.g. `/profile`), the `next` query parameter was lost upon form submission.
- **Root Cause:** `<form action="{{ url_for('login') }}">` omitted the `next` query parameter, and the backend did not inspect `request.form.get("next")`.
- **Impact:** Users were consistently redirected to `/` (home) after login instead of their intended destination.
- **Reproduction:** Navigate to `/profile` while logged out $\rightarrow$ redirected to `/login?next=%2Fprofile` $\rightarrow$ submit credentials $\rightarrow$ redirected to `/` instead of `/profile`.
- **Remediation:** Preserve `next` in form action: `action="{{ url_for('login', next=request.args.get('next', '')) }}"`, add hidden input `<input type="hidden" name="next" value="{{ request.args.get('next', '') }}">`, and check `request.args.get("next") or request.form.get("next")`.
- **Status:** `REPAIRED` & `REGRESSION_VERIFIED`

---

### Defect ID: D-06
- **Module:** `app.py` (`admin_update_user_role`)
- **Severity:** `Medium`
- **Detection Phase:** Phase 14 (Security & RBAC Audit) & Phase 8 (`test_06_admin_self_demotion_is_prevented`)
- **Description:** An authenticated administrator could change their own role to `student` or `faculty`.
- **Root Cause:** Missing guard check comparing target `user_id` against `session.get("user_id")`.
- **Impact:** Irreversible accidental self-lockout of the primary administrator account, requiring direct manual database surgery.
- **Reproduction:** Admin visits `/admin`, changes own role to "student" $\rightarrow$ role updated $\rightarrow$ admin privileges immediately lost.
- **Remediation:** Add validation rejecting self-demotion if `user_id == session.get("user_id")` and `new_role != "admin"`, flashing a danger warning.
- **Status:** `REPAIRED` & `REGRESSION_VERIFIED`

---

### Defect ID: D-07
- **Module:** `templates/profile.html` (Line 89)
- **Severity:** `Medium`
- **Detection Phase:** Phase 6 (Black Box UI Navigation Audit)
- **Description:** In the student profile page, the "Export Data" button linked directly to `/faculty/studio`.
- **Root Cause:** Copy-paste link from faculty template without permission guard.
- **Impact:** Students clicking "Export Data" experienced an unauthorized access redirect with a danger flash.
- **Reproduction:** Log in as student, navigate to `/profile`, click "Export Data" button $\rightarrow$ 302 redirected to `/index` with "Access denied: Faculty or Admin role required".
- **Remediation:** Condition the button on `user.role in ['faculty', 'admin']` or wire it to a valid student data export JSON endpoint.
- **Status:** `REPAIRED` & `REGRESSION_VERIFIED`

---

### Defect ID: D-08
- **Module:** `templates/result.html` (Line 893)
- **Severity:** `Medium`
- **Detection Phase:** Phase 6 (Frontend Console & Script Validation)
- **Description:** Flashcard audio player inline onclick handler used `speakFlashcard('${escapeHtml(f.q)}', '${escapeHtml(f.a)}')`.
- **Root Cause:** `escapeHtml` only escaped `<`, `>`, `&`, and `"`, but not `'` (single quotes).
- **Impact:** Any flashcard containing an apostrophe (e.g. `What's`, `Euler's`, `don't`) produced an unhandled JavaScript `Uncaught SyntaxError: Unexpected identifier` and broke audio playback.
- **Reproduction:** Generate podcast/flashcards with question containing apostrophes $\rightarrow$ click speaker icon $\rightarrow$ browser console shows syntax error.
- **Remediation:** Pass index into array `speakFlashcardByIndex(index)` or sanitize single quotes with `\'`.
- **Status:** `REPAIRED` & `REGRESSION_VERIFIED`

---

### Defect ID: D-09
- **Module:** `templates/index.html` (`renderSubtopics`)
- **Severity:** `Low`
- **Detection Phase:** Phase 6 (UI Interaction Audit)
- **Description:** Switching subject tabs dynamically updated the topic forms in the DOM but failed to propagate the proctoring toggle checkbox state.
- **Root Cause:** Topic cards re-rendered without reading the current `proctorCheck.checked` boolean.
- **Impact:** If a candidate toggled "Full AI Proctoring" and then switched subject tabs, proctoring mode silently reset to disabled.
- **Reproduction:** Enable Proctoring switch on home page $\rightarrow$ click "WebDev" tab $\rightarrow$ click a subtopic drill $\rightarrow$ quiz launched without proctoring.
- **Remediation:** Read `document.getElementById('proctorModeToggle').checked` dynamically inside `renderSubtopics()` and append `proctor=1` input when true.
- **Status:** `REPAIRED` & `REGRESSION_VERIFIED`

---

### Defect ID: D-10
- **Module:** `app.py` (`api_dynamic_generate`, `api_ai_tutor`) & `major_services.py`
- **Severity:** `Low`
- **Detection Phase:** Phase 8 (Automated Suite & Robustness Testing)
- **Description:** Unhandled exceptions when invalid types were submitted to API endpoints:
  - `api_dynamic_generate`: Non-integer `count` caused an unhandled `ValueError: invalid literal for int() with base 10`.
  - `api_ai_tutor`: Submitting a list for `options` caused `AttributeError: 'list' object has no attribute 'get'` in `ask_socratic_tutor`.
- **Root Cause:** Insufficient input sanitization and assumption of dictionary schema.
- **Impact:** Server responded with HTTP 500 internal server error instead of graceful degradation or HTTP 400.
- **Reproduction:** `POST /api/quiz/dynamic-generate` with `{"count": "invalid"}` returned HTTP 500.
- **Remediation:** Add `try...except ValueError` in `api_dynamic_generate` and defensive type conversion in `major_services.py`.
- **Status:** `REPAIRED` & `REGRESSION_VERIFIED`

---

## 3. Verification Sign-Off

All 10 defects have been cataloged with verifiable reproduction test cases in `test_comprehensive_audit.py`. The source code modifications and regression test results are logged in `reports/PROJECT_REPAIR_LOG.md`.

