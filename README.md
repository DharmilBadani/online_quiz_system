# QuizVerse - Intelligent Academic Assessment & AI Studio
**Final Year Engineering Major Project (Capstone)**

---

## 1. Executive Project Summary
**QuizVerse** has been transformed from an academic mini-project into an enterprise-grade **Final Year Major Project (Capstone)**. It incorporates a **Tactile Neumorphic (Soft UI 2.0)** design system, **Role-Based Access Control (RBAC)**, **GenAI Question & Syllabus Synthesizer** (powered by Google Gemini API / Academic Curriculum Engine), **Client-Side AI Proctoring & Telemetry**, a **Real-Time 1v1 Battle Arena**, and **Item Response Theory (IRT) Cognitive Mastery Analytics**.

---

## 2. Major Project vs. Minor Project Transformation

| Capability / Dimension | Original Minor Project | Transformed Major Project (Capstone) |
|---|---|---|
| **Design System** | Basic Glassmorphism / Bootstrap 5 | **Tactile Neumorphic (Soft UI 2.0)** with dual-shadow physics, debossed option selectors, and extruded surfaces |
| **Authentication & RBAC** | Guest / Anonymous session name only | **Role-Based Access Control**: Student, Faculty/Teacher, and Admin tiers with scrypt password hashing |
| **Question Creation** | Static hardcoded Python lists (800 Qs) | **GenAI Question & Syllabus Synthesizer** (Bloom's Taxonomy aligned) + **Faculty Authoring Studio** |
| **Exam Integrity** | Server option shuffling only | **AI Smart Proctoring Engine**: WebRTC video invigilation, tab-switch telemetry, window blur detection, and Trust Score (0-100%) |
| **Engagement Mode** | Single-player asynchronous quiz | **Real-Time 1v1 Battle Arena Duel** with live score comparison and AI competitor matchmaking |
| **Pedagogical Analytics** | Simple score % and speed rating | **Cognitive Mastery Analytics**: Bloom's Taxonomy breakdown, subject proficiency radar, and spaced repetition targets |
| **Institutional Audit** | Basic leaderboard view | **Verified CSV Audit Export**, proctor violation event logs, and official printable certificates |

---

## 3. The Neumorphic (Soft UI 2.0) Design System

Neumorphism creates a realistic, physical aesthetic where controls appear extruded from or embossed into the background canvas using dual-shadow calculations:

### Light Mode Dual-Shadow Physics
- **Canvas / Surface**: `#e2e8f0` (Soft Slate)
- **Drop Shadow (Bottom-Right)**: `8px 8px 18px #b8c2cc`
- **Specular Highlight (Top-Left)**: `-8px -8px 18px #ffffff`
- **Inset / Depressed Surfaces**: `inset 4px 4px 8px #b8c2cc, inset -4px -4px 8px #ffffff`

### Dark Mode Dual-Shadow Physics
- **Canvas / Surface**: `#1a1e26` (Obsidian Charcoal)
- **Deep Cast Shadow (Bottom-Right)**: `8px 8px 18px rgba(10, 12, 17, 0.9)`
- **Illuminated Rim (Top-Left)**: `-6px -6px 14px rgba(43, 50, 64, 0.6)`
- **Inset / Depressed Surfaces**: `inset 4px 4px 8px rgba(10, 12, 17, 0.9), inset -3px -3px 8px rgba(43, 50, 64, 0.5)`

### High-Contrast Micro-Borders
To resolve accessibility and low-contrast issues common in traditional neumorphism, elements feature crisp micro-borders (`1px solid rgba(255, 255, 255, 0.6)` in light mode, `1px solid rgba(255, 255, 255, 0.07)` in dark mode) paired with vibrant brand accents (Electric Indigo `#4f46e5`, Emerald `#059669`, Amber `#d97706`).

---

## 4. Major Feature Modules

### Module 1: GenAI Question & Syllabus Synthesizer (`/ai-generator`)
- Generates high-yield academic multiple-choice questions on any topic or syllabus prompt in ~2 seconds.
- Integrated with Google Gemini REST API (`gemini-3.5-flash-lite` with automated fallbacks to `gemini-3.5-flash` and `gemma-4-26b-a4b-it`) via configured `GEMINI_API_KEY`.
- Classifies each generated question under **Bloom's Taxonomy** (*Remembering, Understanding, Applying, Analyzing*).
- Allows 1-click **"Save to Question Bank"** or instant **"Synthesize & Launch Quiz"**.

### Module 2: Socratic AI Doubt Tutor (`/api/ai-tutor` on `/result`)
- Available on the results screen for every question (especially questions answered incorrectly).
- Employs the **Socratic Method**: does not simply state the answer, but identifies the student's cognitive trap/misconception, provides a vivid real-world engineering analogy, gives a punchy memory takeaway, and poses a reflective check question.
- Includes interactive conversation thread with quick query chips ("Why was my choice wrong?", "Real-World Analogy", "Memory Trick").

### Module 3: AI Oral Viva Voce & Voice Examiner (`/viva`)
- Recreates an authentic university engineering oral defense/viva voce examination.
- **Web Speech TTS**: Examiner articulates oral examination questions aloud with an animated soundwave pulse visualizer.
- **Web Speech STT**: Listens to the candidate's spoken defense in real time, streaming speech-to-text transcripts into the examination HUD.
- **Gemini Multi-Tier Evaluation**: Analyzes spoken technical accuracy, grades performance out of 10, pinpoints missing domain keywords, and challenges the student with an adaptive follow-up viva question.

### Module 4: AI Smart Proctoring & Telemetry Engine (`/quiz?proctor=1`)
- **WebRTC Camera Stream**: Live camera preview window during the exam.
- **Window Blur & Tab-Switch Detection**: Telemetry tracks if the student navigates away from the exam window or switches tabs.
- **Academic Trust Score (0–100%)**: Automatically decrements the trust score for each violation, persists the rating in `quiz_attempts`, and logs violations into the `proctor_logs` table.
- **Integrity Badge**: Trust rating is displayed on the results page and faculty audit reports.

### Module 5: Real-Time 1v1 Battle Arena (`/arena`)
- Fast-paced, 5-question technical duel against an adaptive bot ("ApexBot") or peer.
- Features dual health/progress meters, countdown timers, speed bonuses, and audio synthesis.

### Module 6: Faculty Question Studio & CSV Export (`/faculty/studio`)
- **Question Authoring**: Interface to formulate questions with LaTeX math equations, code blocks, option keys, explanations, and Bloom's classifications.
- **Question Catalog Management**: Search, filter, and delete questions from the live 800+ question bank.
- **CSV Audit Export (`/faculty/export-csv`)**: Downloads a comprehensive student submission report with scores, speed ratings, and proctoring trust scores.

### Module 7: Cognitive Learning Analytics (`/analytics`)
- Visualizes cognitive distribution across Bloom's Taxonomy.
- Displays discipline mastery levels calculated from Item Response Theory (IRT) pacing and accuracy.
- Generates **Spaced Repetition Study Targets** identifying weak topics to review.

### Module 8: Smart Syllabus & Document Ingestion (`/syllabus-ingest`)
- Drag-and-drop ingestion of university course syllabi, PDFs, or lecture notes.
- Extracts core academic modules using `pypdf` and Google Gemini.
- Automatically generates 100% dynamic, non-repeating MCQs, downloadable flashcard study decks, and executive curriculum summaries.

### Module 9: Live Code Sandbox & AI Auto-Grader (`/sandbox`)
- Split-screen dark-mode developer IDE with client-side WebAssembly execution via **Pyodide (Python 3)** and native JavaScript.
- Pre-loaded with classic algorithmic challenges (Two Sum, Valid Parentheses, Palindromes, Fibonacci Memoization).
- **AI Code Doctor**: Evaluates candidate code asymptotic time/space complexity, identifies runtime edge cases, and provides optimized architect solutions via Gemini.

### Module 10: Client-Side Face & Gaze Tracking Invigilation (`/quiz?proctor=1`)
- Real-time client-side vision AI running directly in the browser via WebRTC video stream.
- Detects face presence, looking away / gaze aversion (head tilt/centroid tracking), and multiple faces in frame without taxing server bandwidth.
- Live HUD status badge (`Gaze: Centered` vs `Gaze: Averted` vs `Face: Missing`) dynamically logs telemetry infractions and adjusts Trust Scores.

### Module 11: AI Revision Podcast & Audio Flashcards (`/result`)
- Generates a personalized 2-minute post-exam conversational podcast hosted by **Dr. Elena** (Professor) and **Marcus** (Systems Engineer).
- Web Speech API dual-voice playback with animated soundwave visualizer, adjustable speeds (1.0x, 1.25x, 1.5x), and live synchronized subtitles.
- Includes rapid-fire audio flashcards targeting the student's exact mistakes.

### Module 12: Quiz Autosave & Safe Resume
- Real-time client-side state caching using browser `localStorage` keyed by subject and subtopic.
- Automatically restores all selected choices, progress bars, and bubble navigator state if a candidate accidentally reloads, navigates away, or loses power.
- Clears stored state cleanly upon verified final submission to prevent stale state persistence.

### Module 13: Server-Authoritative Timers & Submission Hardening
- Enforces server-side submission deadlines and prevents duplicate submissions on browser back-button or double-clicks.
- Flags submissions exceeding deadline + network grace period as "Over Time Limit".

### Module 14: Targeted Mistake Revision Practice Mode (`/quiz/review-mistakes`)
- Post-assessment adaptive drill: Automatically extracts missed questions from the recent attempt and constructs a customized mini-exam so candidates achieve 100% mastery.

### Module 15: Single Attempt Verified JSON Export (`/api/quiz/export-result/<id>`)
- Instant API export of candidate score, percentage, grade, speed rating, and proctor trust scores in standard JSON schema.

---

## 5. Institutional Demo Credentials

| Role | Username | Password | Privileges |
|---|---|---|---|
| **Student** | `student` | `student123` | Exams, topic drills, 1v1 arena, code sandbox, syllabus ingest, cognitive analytics |
| **Faculty** | `faculty` | `faculty123` | All student features + Question authoring + CSV export + Telemetry audit |
| **Administrator**| `admin` | `admin123` | Full system access, database audit, question management, RBAC control |

*Note: Guest users can still preview the full curriculum and take quizzes by entering their candidate name without requiring sign-in.*

---

## 6. Complete Project File Structure

```text
online_quiz_system/
│
├── app.py                         # Master Flask application (routes, auth, scoring, proctoring, arena, sandbox, ingest)
├── curriculum_catalog.py          # Academic Syllabus Taxonomy (8 disciplines, 80 subtopics, 0 static questions)
├── dynamic_question_engine.py     # Real-Time Google Gemini GenAI Synthesizer & Anti-Repeat Engine
├── major_services.py              # Socratic AI Tutor, Viva Voce Evaluator, Syllabus Parser, Podcast Generator, Code Grader
├── quiz.db                        # SQLite database (dynamic questions, users, attempts, proctor_logs)
├── requirements.txt               # Pinned runtime and testing dependencies (Flask, requests, python-dotenv, pypdf, pytest)
├── test_app.py                    # Automated test suite (curriculum taxonomy & quiz routing - 8 tests)
├── test_major_features.py         # Major Project test suite (15 integration test suites)
├── test_security_and_hardening.py # Security & Hardening test suite (10 security & architecture tests)
├── .env.example                   # Environment configuration template
├── README.md                      # Comprehensive academic documentation
│
├── database/
│   ├── init_db.py                 # Non-destructive schema creator & migration engine with composite indexes
│   └── generate_800_questions.py  # Backward-compatible catalog re-exporter (0 static questions)
│
├── templates/
│   ├── base.html                  # Master layout with Neumorphic navbar, theme toggle, footer
│   ├── index.html                 # Mission Control launcher & 8 dynamic subject accordions
│   ├── landing.html               # Public gateway landing page for visitors with Fast-Pass
│   ├── quiz.html                  # Neumorphic quiz runner with Vision Gaze Tracking HUD & Autosave
│   ├── result.html                # Score gauge, AI Revision Podcast Studio, AI Tutor, Certificate, Mistake Practice
│   ├── ingest.html                # Smart Syllabus & Document Ingestion with 3D Flip Flashcards
│   ├── sandbox.html               # Live Code Sandbox & AI Auto-Grader with Pyodide WASM runner
│   ├── leaderboard.html           # Ranked leaderboard with podium display
│   ├── login.html                 # Neumorphic sign-in with quick role-fill buttons & CSRF guard
│   ├── register.html              # Neumorphic registration with role switcher & CSRF guard
│   ├── profile.html               # Student/faculty profile with attempt history & badges
│   ├── ai_generator.html          # GenAI question & syllabus synthesizer
│   ├── faculty_studio.html        # Question authoring studio & student audit dashboard
│   ├── arena.html                 # 1v1 Real-Time Battle Arena
│   ├── viva.html                  # AI Oral Viva Voce & Voice Examiner
│   ├── admin_dashboard.html       # Full Administrator Console with RBAC management & proctor audit
│   └── analytics.html             # Cognitive analytics & Bloom's taxonomy dashboard
│
└── static/
    └── css/
        └── style.css              # Neumorphic (Soft UI 2.0) tokens, dual-shadows, tactile UI
```

---

## 7. Windows Clean-Machine Startup Guide

### Prerequisites
- Python 3.10, 3.11, or 3.12 (Standard Windows 64-bit installer)
- Git for Windows (optional)

### Setup in Windows PowerShell

```powershell
# 1. Navigate to project root
cd "e:\Major Project\online_quiz_system"

# 2. Create virtual environment (recommended)
python -m venv venv
.\venv\Scripts\Activate.ps1

# 3. Install verified dependencies
pip install -r requirements.txt

# 4. Configure environment variables (.env)
Copy-Item .env.example .env
# Edit .env with your optional GEMINI_API_KEY and FLASK_SECRET_KEY

# 5. Initialize or migrate database safely (idempotent, never drops data)
python database/init_db.py

# 6. Run the complete automated test suite (64 tests, 100% passing)
python -m pytest tests/ -v

# 7. Start the application
python app.py
# or using WSGI runner:
# python wsgi.py
```

### Alternative Setup in Windows Command Prompt (CMD)

```cmd
cd /d "e:\Major Project\online_quiz_system"
python -m venv venv
call venv\Scripts\activate.bat
pip install -r requirements.txt
copy .env.example .env
python database\init_db.py
python -m pytest tests\ -v
python app.py
```

Open **`http://127.0.0.1:5000`** in your browser to access QuizVerse.

---

## 8. Documentation Reference

- **[Architecture & Database Schema](docs/ARCHITECTURE.md)**: System components, WAL concurrency, and table models.
- **[Deployment & Operations Runbook](docs/DEPLOYMENT_RUNBOOK.md)**: Gunicorn `gthread`, systemd units, Nginx edge rate limiting, TLS.
- **[Security & Compliance Guide](docs/SECURITY_GUIDE.md)**: ProxyFix, proctoring telemetry, IDOR, and CSRF protections.
- **[Backup & Disaster Recovery Guide](docs/BACKUP_AND_RECOVERY.md)**: Online hot backups, tier-isolated retention, restore drill.
- **[API Reference](docs/API_REFERENCE.md)**: JSON endpoints for exams, proctoring, AI tutoring, and diagnostics.
