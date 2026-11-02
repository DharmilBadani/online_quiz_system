# QUIZVERSE API REFERENCE

## 1. Authentication & System Endpoints

### `GET /api/admin/health`
- **Description:** System health diagnostics reporting database connectivity, WAL mode, and circuit breaker status.
- **Response:**
  ```json
  {
    "status": "healthy",
    "database": { "connected": true, "journal_mode": "wal" },
    "ai_circuit_breaker": { "state": "CLOSED", "failure_count": 0 }
  }
  ```

---

## 2. Examination & Question Endpoints

### `GET /api/quiz/topics`
- **Description:** Returns JSON array of available curriculum categories and subtopics.
- **Parameters:** `category` (optional)

### `POST /api/quiz/dynamic-generate`
- **Description:** Synthesizes unique parameterized questions for a candidate with a zero-repetition guarantee.
- **Request Body:**
  ```json
  {
    "category": "Python",
    "topic": "Core Logic",
    "count": 5,
    "candidate_name": "student_01"
  }
  ```

### `POST /api/proctor/event`
- **Description:** Ingests live proctoring events during an active examination.
- **Headers:** `X-CSRFToken`
- **Request Body:**
  ```json
  {
    "attempt_token": "a1b2c3d4...",
    "event": "tab_switch",
    "timestamp": 1710000000
  }
  ```

### `GET /api/export-result/<int:attempt_id>`
- **Description:** Exports JSON scorecard for an examination attempt.
- **Security:** Requires authentication and attempt ownership (or admin role).

---

## 3. Pedagogical & AI Endpoints

### `POST /api/ai-tutor`
- **Description:** Socratic AI tutor providing hints for incorrect choices.
- **Request Body:**
  ```json
  {
    "question": "What is encapsulation?",
    "options": {"A": "Data hiding", "B": "Looping", "C": "Compilation", "D": "Garbage collection"},
    "student_choice": "B",
    "correct_choice": "A",
    "explanation": "Encapsulation binds data and code together.",
    "topic": "OOP",
    "user_query": "Why is B wrong?"
  }
  ```

### `POST /api/viva/generate-question` & `POST /api/viva/evaluate`
- **Description:** AI Oral Viva Voce speech examiner question generation and student verbal transcript evaluation.

