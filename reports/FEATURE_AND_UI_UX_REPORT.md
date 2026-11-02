# QuizVerse Feature Enhancements & UI/UX Engineering Report

## 1. Overview of Pedagogical & Technical Innovations

In addition to deep security hardening, QuizVerse received multiple targeted feature enhancements and UI/UX refinements. Each addition adheres to the modern Neumorphic dark/light design system, improves student learning outcomes, and reinforces academic integrity without adding unnecessary bloat.

---

## 2. Detailed Feature Enhancements

### 2.1 Personal Study Vault & Question Bookmarking
- **Endpoints**:
  - `POST /api/bookmark` (AJAX toggle/add/remove with CSRF validation)
  - `GET /api/bookmarks` (JSON list of student's saved questions)
  - `GET /student/bookmarks` (Dedicated interactive study vault HTML view)
- **Pedagogical Objective**: During timed examinations or practice drills, candidates often encounter questions containing novel edge cases or challenging algorithmic concepts. The Study Vault allows students to instantly bookmark questions for spaced repetition.
- **UI/UX Implementation**:
  - In [`templates/quiz.html`](file:///e:/Major%20Project/online_quiz_system/templates/quiz.html), an unobtrusive `Bookmark` button is positioned alongside question marks.
  - Clicking triggers an asynchronous AJAX request that toggles the icon to `<i class="bi bi-bookmark-fill text-warning"></i>` without reloading the page or interrupting exam focus.
  - In [`templates/student_bookmarks.html`](file:///e:/Major%20Project/online_quiz_system/templates/student_bookmarks.html), questions are rendered with their 4 options, highlighted correct answers, difficulty badges, and pedagogical explanations.
  - Smooth removal animation (`opacity` and `translateY` CSS transitions) updates the list dynamically.
  - Linked directly in the main navigation user dropdown for authenticated students.

---

### 2.2 Administrative System Health & Telemetry Monitor
- **Endpoint**: `GET /admin/health` (Restricted to `admin` role)
- **Technical Objective**: Provides DevOps and administrators with instant programmatic visibility into database integrity, filesystem allocation, and platform operational metrics.
- **Payload Structure**:
  ```json
  {
    "status": "healthy",
    "timestamp": "2026-11-01T19:04:48.123456",
    "database": {
      "path": "E:\\Major Project\\online_quiz_system\\quiz.db",
      "size_bytes": 225280,
      "size_mb": 0.22,
      "sqlite_version": "3.45.3",
      "journal_mode": "wal",
      "wal_enabled": true,
      "integrity_check": "ok"
    },
    "metrics": {
      "total_users": 56,
      "total_quiz_attempts": 186,
      "total_curriculum_questions": 120
    },
    "environment": {
      "flask_env": "production",
      "debug": false,
      "testing": false
    }
  }
  ```
- **Security Boundary**: Requests from unauthenticated clients or students are blocked with `302 Redirect` to login or `Access restricted to admin accounts`.

---

### 2.3 Faculty Studio Question Bank Filtering & Audit
- **Endpoint**: `GET /faculty/studio`
- **Component**: [`templates/faculty_studio.html`](file:///e:/Major%20Project/online_quiz_system/templates/faculty_studio.html)
- **Faculty Workflow**: Faculty members manage large question repositories. Previously, the studio listed unfilterable submissions.
- **Enhancement**:
  - Integrated a Question Bank Repository table directly beneath the authoring form.
  - Built a dynamic multi-criteria filter toolbar:
    - **Subject Dropdown**: Filters by any of the 8 curriculum domains (e.g. Java, Python, C++, DBMS).
    - **Difficulty Dropdown**: Filters by Easy, Medium, or Hard.
    - **Search Input**: Full-text substring search across question text and sub-topics.
  - Displays question ID, curriculum subject, topic, difficulty badge, and a deletion trigger with confirmation dialog.

---

### 2.4 Evidence-Based Cognitive Analytics (Zero Fabrication)
- **Component**: [`major_services.py`](file:///e:/Major%20Project/online_quiz_system/major_services.py) &rarr; `compute_cognitive_analytics()`
- **Correction**: Legacy code returned arbitrary hardcoded strings (e.g. `"Java - Database Connection"`, `"DBMS - Transactions & ACID"`) even when a candidate had taken 0 quizzes or scored 100% on every test.
- **Remediation**:
  - When `total_attempts == 0`: `weak_topics` is an empty list with an explanatory message: *"No assessment data available yet. Complete a quiz to receive personalized topic diagnostics."*
  - When candidate has authentic attempts: Calculates real accuracy percentages per `(category, topic)`. Only topics where empirical accuracy is **< 70%** are classified as weak areas, sorted by lowest score first.
  - When all topics meet or exceed 70%: Celebrates student mastery with an emerald benchmark card: *"Commendable mastery! All evaluated topics meet or exceed 70% proficiency."*

---

### 2.5 Google Gemini API Circuit Breaker
- **Component**: [`major_services.py`](file:///e:/Major%20Project/online_quiz_system/major_services.py)
- **Resilience Objective**: When the external Gemini API is unreachable, has exhausted its rate limit, or network latency spikes, waiting through 3 sequential model timeouts blocked server threads for up to 30 seconds.
- **Implementation**:
  - Circuit Breaker state machine tracks consecutive API failures.
  - If **3 consecutive failures** occur, the circuit opens for a **45-second cooldown**.
  - During cooldown, calls to `call_gemini_api()` fail fast in `< 0.1 ms`, immediately activating the offline algorithmic question synthesizer.
  - After 45 seconds, the circuit half-opens. If the next API call succeeds, the circuit fully closes; otherwise, cooldown resets.

---

### 2.6 ApexBot Simulation Transparency in 1v1 Battle Arena
- **Component**: [`templates/arena.html`](file:///e:/Major%20Project/online_quiz_system/templates/arena.html)
- **UX Clarity**: Transparently communicates that ApexBot is an algorithmic benchmark opponent rather than a deceptive live human peer.
- **HUD Additions**:
  - Labeled with a distinct `AI SIMULATION` monospace badge.
  - Transparent notification banner: *"Transparency Notice: ApexBot is an algorithmic benchmark opponent (75% baseline accuracy with jittered reaction latency) designed for pacing drills."*

---

### 2.7 AI Proctoring Privacy Disclaimers & Ethical Telemetry
- **Component**: [`templates/quiz.html`](file:///e:/Major%20Project/online_quiz_system/templates/quiz.html)
- **Ethics & Privacy**: Academic invigilation can raise student privacy concerns regarding camera feeds and biometrics.
- **UX Additions**:
  - Embedded prominent privacy assurance beneath the live camera monitor:
    - *"Privacy Guarantee: Client-side focus tracking only. No video or biometric streams are saved or transmitted to external servers."*
  - Clearly explains that academic trust score adjustments are derived strictly from tab switches, window blur events, and local face orientation heuristics.

