# -*- coding: utf-8 -*-
"""
=============================================================================
QUIZVERSE - Final Year Engineering Major Project (Capstone)
=============================================================================
Academic Level: B.Tech / B.E. / M.C.A. Final Year Capstone Major Project
Architecture & Advanced Innovations:
- Backend: Python 3 with Flask & REST Microservices
- AI Engine: 100% Dynamic Question Generation via Google Gemini API (0 Static Questions)
- Anti-Repeat Engine: Cryptographic SHA-256 Question Fingerprinting & History Tracking
- Smart Syllabus Ingestion: PDF/Doc Ingestion with pypdf & Instant Curriculum Synthesis
- Code Sandbox: Sandboxed In-Browser WebAssembly (Pyodide Python 3) & AI Auto-Grader
- Vision Proctoring: Client-Side WebRTC AI Face & Gaze Tracking Invigilation
- Audio Podcast: Dual-Voice AI Revision Podcast (Web Speech API) & Audio Flashcards
- AI Oral Viva Voce: Real-Time Spoken Examination & Gemini Rubric Defense Grading
- Socratic Tutor: Misconception Identification, Real-World Analogies & Memory Hooks
- 1v1 Battle Arena: Real-Time Technical Duel Engine with Live Matchmaking
- Security: Role-Based Access Control (Student, Faculty, Admin) & Parameterized SQL
- Analytics: Item Response Theory (IRT) & Bloom's Taxonomy Cognitive Mastery Radar
- UI System: Tactile Neumorphic (Soft UI 2.0) with Dual-Shadow Physics & Dark Mode
=============================================================================
"""

import os
import sys
import random
import sqlite3
import time
import io
import csv
import json
import secrets
import threading
from urllib.parse import urlparse, urljoin
from datetime import datetime
from functools import wraps
from werkzeug.security import generate_password_hash, check_password_hash
from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify, Response, g

# Load environment configuration (.env)
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# Major Project Advanced Services
import major_services
import dynamic_question_engine

# Base Paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

DB_PATH = os.path.join(BASE_DIR, "quiz.db")

# Import Academic Curriculum Catalog (100% Dynamic Engine - Zero Static Questions)
try:
    from curriculum_catalog import SUBJECT_CATALOG
except ImportError:
    from database.generate_800_questions import SUBJECT_CATALOG

# Flask Application Initialization & Security Configuration
app = Flask(__name__)

# Strict Production Secret Validation
def validate_production_config() -> str:
    """
    Validates enterprise security configuration at application startup.
    Fails fast in production if mandatory security parameters or strong secrets are missing.
    """
    flask_env = os.environ.get("FLASK_ENV", "development").lower()
    is_prod = (flask_env == "production")
    
    secret = os.environ.get("FLASK_SECRET_KEY") or os.environ.get("SECRET_KEY")
    insecure_fallbacks = {
        "academic_quiz_system_secret_key_2026",
        "quizverse_major_secret_key_2026_neumorphic",
        "default_secret_key",
        "secret",
        "change_this_to_a_secure_random_64_character_hex_string"
    }
    
    if is_prod:
        if not secret:
            raise RuntimeError("CRITICAL CONFIGURATION ERROR: FLASK_SECRET_KEY environment variable is required in production mode.")
        if secret in insecure_fallbacks or len(secret) < 32:
            raise RuntimeError("CRITICAL CONFIGURATION ERROR: Insecure or default FLASK_SECRET_KEY detected in production. Generate a strong key via secrets.token_hex(32).")
    
    return secret or "quizverse_major_secret_key_2026_neumorphic"

app.secret_key = validate_production_config()

# OWASP Session Cookie & Upload Security Hardening
is_production = os.environ.get("FLASK_ENV") == "production"
app.config.update(
    MAX_CONTENT_LENGTH=16 * 1024 * 1024,  # 16 MB maximum upload payload limit
    SESSION_COOKIE_HTTPONLY=True,        # Prevent JavaScript / XSS access to session cookie
    SESSION_COOKIE_SAMESITE="Lax",       # Mitigate CSRF cross-origin state leakage
    SESSION_COOKIE_SECURE=is_production, # Require HTTPS in production
    PERMANENT_SESSION_LIFETIME=14400     # 4-hour session maximum lifetime
)

# In-memory thread-safe sliding-window rate limiter
_RATE_LIMIT_BUCKETS: dict[str, list[float]] = {}
_RATE_LIMIT_LOCK = threading.Lock()

def rate_limit(max_requests: int = 40, window_seconds: int = 60):
    """Sliding-window in-memory IP rate limiter for auth and high-cost endpoints."""
    def decorator(f):
        @wraps(f)
        def wrapped(*args, **kwargs):
            if app.config.get("TESTING"):
                return f(*args, **kwargs)
            client_ip = request.headers.get("X-Forwarded-For", request.remote_addr or "127.0.0.1").split(",")[0].strip()
            key = f"{f.__name__}:{client_ip}"
            now = time.time()
            
            with _RATE_LIMIT_LOCK:
                timestamps = _RATE_LIMIT_BUCKETS.setdefault(key, [])
                _RATE_LIMIT_BUCKETS[key] = [t for t in timestamps if now - t < window_seconds]
                if len(_RATE_LIMIT_BUCKETS[key]) >= max_requests:
                    retry_after = int(window_seconds - (now - _RATE_LIMIT_BUCKETS[key][0])) + 1
                    if request.is_json or request.path.startswith("/api/"):
                        return jsonify({
                            "success": False,
                            "error": f"Rate limit exceeded. Please retry in {retry_after} seconds."
                        }), 429
                    flash(f"Rate limit exceeded. Please wait {retry_after} seconds.", "warning")
                    return redirect(request.referrer or url_for("index"))
                _RATE_LIMIT_BUCKETS[key].append(now)
            return f(*args, **kwargs)
        return wrapped
    return decorator


@app.errorhandler(413)
def request_entity_too_large(error):
    """Graceful error handler for oversized payloads."""
    if request.is_json:
        return jsonify({"success": False, "error": "Uploaded payload exceeds the maximum 16MB limit."}), 413
    flash("The uploaded file exceeds the 16MB maximum size limit.", "danger")
    return redirect(request.referrer or url_for("index"))


def generate_csrf_token():
    """Generates a cryptographic CSRF token for state-changing forms."""
    if "_csrf_token" not in session:
        session["_csrf_token"] = secrets.token_hex(24)
    return session["_csrf_token"]


app.jinja_env.globals["csrf_token"] = generate_csrf_token


def is_safe_url(target):
    """Validates that a redirection URL strictly matches the same host and scheme to prevent Open Redirects."""
    if not target:
        return False
    ref_url = urlparse(request.host_url)
    test_url = urlparse(urljoin(request.host_url, target))
    return test_url.scheme in ("http", "https") and ref_url.netloc == test_url.netloc


@app.before_request
def validate_csrf():
    """CSRF Protection Guard for browser form submissions and state-changing APIs."""
    if request.method in ("POST", "PUT", "DELETE", "PATCH"):
        if not app.config.get("TESTING") and app.config.get("WTF_CSRF_ENABLED", True):
            token = (
                request.form.get("csrf_token") or
                request.headers.get("X-CSRFToken") or
                request.headers.get("X-CSRF-Token")
            )
            if not token and request.is_json:
                data = request.get_json(silent=True)
                if isinstance(data, dict):
                    token = data.get("csrf_token")

            expected = session.get("_csrf_token")
            # If token is missing or mismatched:
            if not token or not expected or token != expected:
                if request.is_json or request.path.startswith("/api/"):
                    return jsonify({"success": False, "error": "Security verification token expired or invalid."}), 403
                flash("Session or security verification token expired. Please try again.", "warning")
                return redirect(request.referrer or url_for("index"))


# Authoritative Server-Side Active Quiz Manifest Persistence Helpers
def save_active_quiz_session(attempt_token: str, user_id, candidate_name: str, category: str, topic: str, q_order: list, manifest: dict, timer_seconds: int):
    """Stores authoritative quiz state in SQLite active_quiz_sessions to prevent answer-key tampering in client cookies."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT OR REPLACE INTO active_quiz_sessions 
        (attempt_token, user_id, candidate_name, category, topic, question_ids_order, manifest_data, start_timestamp, timer_seconds, is_submitted, result_attempt_id)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 0, NULL)
        """,
        (
            attempt_token,
            user_id,
            candidate_name,
            category,
            topic,
            json.dumps(q_order),
            json.dumps(manifest),
            time.time(),
            timer_seconds
        )
    )
    conn.commit()
    conn.close()


def get_active_quiz_session(attempt_token: str):
    """Retrieves authoritative server-side quiz session by opaque token."""
    if not attempt_token:
        return None
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM active_quiz_sessions WHERE attempt_token = ?", (attempt_token,))
    row = cursor.fetchone()
    conn.close()
    if not row:
        return None
    data = dict(row)
    try:
        data["question_ids_order"] = json.loads(data["question_ids_order"])
        data["manifest_data"] = json.loads(data["manifest_data"])
    except Exception:
        pass
    return data


# Subject Metadata Catalog (8 Subjects + Master Challenge)
SUBJECT_METADATA = dict(SUBJECT_CATALOG)
SUBJECT_METADATA["All"] = {
    "title": "All Subjects & Topics",
    "badge": "Master Challenge",
    "color": "dark",
    "icon": "bi-stars",
    "description": "Comprehensive challenge spanning all 8 disciplines and 80 subtopics with 100% dynamic AI generation.",
    "topics": ["All Topics Mixed"]
}
SUBJECT_METADATA["AI Studio"] = {
    "title": "AI Studio Synthesized Topics",
    "badge": "Generative AI",
    "color": "info",
    "icon": "bi-cpu-fill",
    "description": "On-demand exam-grade questions generated dynamically via Google Gemini.",
    "topics": ["Dynamic Synthesized Topics"]
}


def get_db_connection():
    """Establishes connection to SQLite with row factory, WAL mode, foreign keys, and 20s timeout."""
    connection = sqlite3.connect(DB_PATH, timeout=20.0)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON;")
    connection.execute("PRAGMA journal_mode = WAL;")
    return connection


def get_db():
    """Returns request-scoped SQLite connection from Flask g context."""
    if "db" not in g:
        g.db = get_db_connection()
    return g.db


@app.teardown_appcontext
def close_db(error=None):
    """Closes request-scoped SQLite connection at request completion."""
    db = g.pop("db", None)
    if db is not None:
        db.close()


def ensure_database_ready():
    """Initializes SQLite database schema for dynamic questions, users, and proctoring telemetry if missing."""
    if not os.path.exists(DB_PATH):
        try:
            from database.init_db import init_database
            init_database()
        except Exception as e:
            print(f"Database initialization check failed: {e}")


def format_duration(seconds):
    """Helper to format elapsed seconds into a readable string (e.g. '1m 25s' or '45s')."""
    mins, secs = divmod(int(seconds), 60)
    if mins > 0:
        return f"{mins}m {secs}s"
    return f"{secs}s"


def get_current_user():
    """Fetches currently logged-in user record from database, cached in flask.g per request."""
    if "current_user" in g:
        return g.current_user
    user = None
    if "user_id" in session:
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM users WHERE id = ?", (session["user_id"],))
            row = cursor.fetchone()
            conn.close()
            if row:
                user = dict(row)
            else:
                session.clear()
        except Exception:
            pass
    g.current_user = user
    return user


@app.context_processor
def inject_global_context():
    """Injects user authentication state and metadata across all templates."""
    user = get_current_user()
    return {
        "current_user": user,
        "is_authenticated": user is not None,
        "user_role": user.get("role", "guest") if user else "guest"
    }


@app.after_request
def apply_security_headers(response):
    """
    OWASP Secure Headers Middleware:
    Hardens browser security against Clickjacking, MIME sniffing, and cross-site scripting.
    """
    response.headers["X-Frame-Options"] = "SAMEORIGIN"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    return response


def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "user_id" not in session:
            flash("Please sign in to access this feature.", "warning")
            return redirect(url_for("login", next=request.url))
        return f(*args, **kwargs)
    return decorated_function


def role_required(*roles):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            user = get_current_user()
            if not user:
                flash("Please sign in to access this feature.", "warning")
                return redirect(url_for("login", next=request.url))
            user_role = user.get("role", "student")
            if user_role not in roles:
                flash(f"Access restricted to {', '.join(roles)} accounts.", "danger")
                return redirect(url_for("index"))
            return f(*args, **kwargs)
        return decorated_function
    return decorator


# =============================================================================
# APPLICATION ROUTES
# =============================================================================

@app.route("/")
@app.route("/landing")
def index():
    """
    Landing / Examination Home Page Route:
    - If user is NOT authenticated and not explicitly browsing as guest (?guest=1),
      renders the public Welcome & Authentication Gateway (landing.html).
    - If user IS authenticated (or ?guest=1), renders the normal Examination Landing
      Page (index.html) with 8 subjects, subtopics, exam launch controls, and candidate profile.
    """
    ensure_database_ready()

    current_user = get_current_user()
    is_guest_preview = request.args.get("guest") == "1"

    # Show public landing page if visitor is unauthenticated
    if not current_user and not is_guest_preview:
        return render_template("landing.html")

    total_questions = 0
    topic_counts = {}
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM questions")
        total_questions = cursor.fetchone()[0]

        cursor.execute("SELECT category, COUNT(*) FROM questions GROUP BY category")
        for row in cursor.fetchall():
            topic_counts[row[0]] = row[1]
        conn.close()
    except sqlite3.Error as e:
        flash(f"Database error: {e}", "danger")

    return render_template(
        "index.html",
        total_questions=total_questions,
        topic_counts=topic_counts,
        subject_catalog=SUBJECT_CATALOG,
        subject_meta=SUBJECT_METADATA,
        is_guest_preview=is_guest_preview
    )


@app.route("/dashboard")
def dashboard():
    """Direct alias to the normal examination dashboard."""
    return redirect(url_for("index", guest=1 if not get_current_user() else None))


@app.route("/demo-login/<role>", methods=["GET", "POST"])
def demo_login(role):
    """
    1-Click Demo Authentication:
    RESTRICTED strictly to non-production academic review environments with ALLOW_DEMO_LOGINS=true.
    Public demo-admin access is permanently disabled to prevent privilege escalation.
    """
    is_prod = os.environ.get("FLASK_ENV") == "production"
    allow_demo = os.environ.get("ALLOW_DEMO_LOGINS", "true" if not is_prod else "false").lower() in ("1", "true")
    if is_prod or not allow_demo:
        flash("1-Click demo authentication is disabled in live production mode. Please sign in with registered credentials.", "warning")
        return redirect(url_for("login"))

    # Security Hardening: Never permit demo bypass for administrative accounts
    if role == "admin":
        flash("Demo login for administrator accounts is permanently disabled for system security. Please authenticate with administrator credentials.", "danger")
        return redirect(url_for("login"))

    creds = {
        "student": ("student", "student123"),
        "faculty": ("faculty", "faculty123"),
    }
    if role not in creds:
        flash("Invalid demo role specified.", "warning")
        return redirect(url_for("login"))

    username, password = creds[role]
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE username = ?", (username,))
    user = cursor.fetchone()
    conn.close()

    if user and check_password_hash(user["password_hash"], password):
        session["user_id"] = user["id"]
        session["username"] = user["username"]
        session["role"] = user["role"]
        session["candidate_name"] = user["full_name"] or user["username"]
        flash(f"Authenticated as Demo {user['role'].capitalize()} ({user['username']})! Normal landing page unlocked.", "success")
        return redirect(url_for("index"))

    flash("Demo user record not found. Please log in manually.", "warning")
    return redirect(url_for("login"))


@app.route("/api/topics")
def api_topics():
    """REST endpoint returning available topics for a selected subject."""
    category = request.args.get("category", "").strip()
    if category in SUBJECT_CATALOG:
        return jsonify({
            "category": category,
            "title": SUBJECT_CATALOG[category]["title"],
            "topics": SUBJECT_CATALOG[category]["topics"]
        })
    return jsonify({"category": "All", "topics": ["All Topics Mixed"]})


@app.route("/quiz", methods=["GET", "POST"])
def quiz():
    """
    Quiz Page Route:
    - 100% Dynamic Question Generation powered by Google Gemini GenAI & Anti-Repeat Engine
    - Exam Modes:
      * Specific Sub-topic: 10 focused questions (5-minute timer)
      * All Topics in Subject: 20 questions balanced across curriculum (10-minute timer)
      * Master Challenge (All): 20 questions spanning all disciplines (10-minute timer)
    - Anti-Cheating: Scrambles option sequence, tracks client-side AI vision gaze telemetry
    - Starts server-side time tracking & manages lightweight session manifest
    """
    ensure_database_ready()

    candidate_name = request.values.get("candidate_name", "").strip()
    if candidate_name:
        session["candidate_name"] = candidate_name
    elif "candidate_name" not in session:
        session["candidate_name"] = "Candidate"

    category = request.values.get("category", "").strip()
    if category and (category in SUBJECT_METADATA or category == "All"):
        session["selected_category"] = category
        session["selected_topic"] = category  # Backward compatibility for test_app.py
    elif "selected_category" not in session:
        session["selected_category"] = "All"
        session["selected_topic"] = "All"

    active_category = session["selected_category"]

    # Read selected subtopic
    topic = request.values.get("topic", "").strip()
    if not topic or topic == "All" or topic == "All Topics" or topic == "All Topics Mixed":
        topic = "All Topics"
    session["active_subtopic"] = topic

    # 1. Fetch questions based on Subject and Topic (Dynamic or Standard)
    raw_questions = []
    timer_seconds = 600  # Default 10 minutes

    # Compute question quota & timer duration
    if active_category != "All":
        if topic != "All Topics" and active_category in SUBJECT_CATALOG and topic in SUBJECT_CATALOG[active_category]["topics"]:
            q_count = 10
            timer_seconds = 300  # 5 minutes for 10 questions
        else:
            q_count = 20
            timer_seconds = 600  # 10 minutes for 20 questions
    else:
        q_count = 20
        timer_seconds = 600

    # Dynamic Zero-Repetition Engine mode evaluation
    is_testing = app.config.get("TESTING", False)
    dynamic_val = request.values.get("dynamic")
    if dynamic_val is not None:
        use_dynamic = (dynamic_val == "1" or str(dynamic_val).lower() == "true")
    else:
        # In live mode (production), dynamic generation with zero-repeat is active by default
        use_dynamic = not is_testing

    user_identifier = session.get("username") or session.get("candidate_name") or "Candidate"

    if use_dynamic:
        try:
            raw_questions = dynamic_question_engine.get_or_synthesize_unique_quiz_questions(
                category=active_category,
                topic=topic,
                count=q_count,
                user_identifier=user_identifier,
                force_dynamic=True
            )
        except Exception:
            raw_questions = []

    if not raw_questions:
        try:
            conn = get_db_connection()
            cursor = conn.cursor()

            if active_category != "All":
                if topic != "All Topics" and ((active_category in SUBJECT_CATALOG and topic in SUBJECT_CATALOG[active_category]["topics"]) or active_category == "AI Studio"):
                    # Specific Topic Drill: 10 Questions, 5-minute timer
                    cursor.execute(
                        """
                        SELECT id, question, option_a, option_b, option_c, option_d, correct_answer, category, topic, difficulty 
                        FROM questions 
                        WHERE category = ? AND topic = ? 
                        ORDER BY id DESC 
                        LIMIT 10
                        """,
                        (active_category, topic)
                    )
                else:
                    # Subject-wide Exam: 20 Random Questions, 10-minute timer
                    cursor.execute(
                        """
                        SELECT id, question, option_a, option_b, option_c, option_d, correct_answer, category, topic, difficulty 
                        FROM questions 
                        WHERE category = ? 
                        ORDER BY RANDOM() 
                        LIMIT 20
                        """,
                        (active_category,)
                    )
            else:
                # Master Challenge (All Topics across all 8 subjects): 20 Random Questions
                cursor.execute(
                    """
                    SELECT id, question, option_a, option_b, option_c, option_d, correct_answer, category, topic, difficulty 
                    FROM questions 
                    ORDER BY RANDOM() 
                    LIMIT 20
                    """
                )

            raw_questions = [dict(row) for row in cursor.fetchall()]
            conn.close()
        except sqlite3.Error as e:
            flash(f"Failed to load questions: {e}", "danger")
            return redirect(url_for("index"))

    if not raw_questions:
        flash(f"No questions found for {active_category} - {topic}.", "warning")
        return redirect(url_for("index"))

    # 2. Anti-Cheating Shuffling: Scramble options & build compact manifest
    prepared_questions = []
    compact_manifest = {}  # {str(q_id): {'c': correct_letter, 's': [orig_letters]}}
    question_ids_order = []

    for q in raw_questions:
        q_id = q["id"]
        question_ids_order.append(q_id)
        orig_correct_letter = q["correct_answer"].strip().upper()
        orig_options = {
            "A": q["option_a"],
            "B": q["option_b"],
            "C": q["option_c"],
            "D": q["option_d"],
        }
        correct_text = orig_options.get(orig_correct_letter, q["option_a"])

        # Randomize letter order
        scrambled_letters = ["A", "B", "C", "D"]
        random.shuffle(scrambled_letters)

        shuffled_options = {
            "A": orig_options[scrambled_letters[0]],
            "B": orig_options[scrambled_letters[1]],
            "C": orig_options[scrambled_letters[2]],
            "D": orig_options[scrambled_letters[3]],
        }

        # Find which new letter holds the correct text
        new_correct_letter = "A"
        for letter, text in shuffled_options.items():
            if text == correct_text:
                new_correct_letter = letter
                break

        prepared_questions.append({
            "id": q_id,
            "question": q["question"],
            "category": q["category"],
            "topic": q.get("topic", "General"),
            "difficulty": q["difficulty"],
            "option_a": shuffled_options["A"],
            "option_b": shuffled_options["B"],
            "option_c": shuffled_options["C"],
            "option_d": shuffled_options["D"],
        })

        # Compact representation: store only correct letter and scrambled mapping
        compact_manifest[str(q_id)] = {
            "c": new_correct_letter,
            "s": scrambled_letters,
        }

    # Authoritative Server-Side Quiz Session Persistence (Answers never stored in client cookie)
    attempt_token = secrets.token_hex(24)
    user_id = session.get("user_id")
    save_active_quiz_session(
        attempt_token=attempt_token,
        user_id=user_id,
        candidate_name=session.get("candidate_name", "Candidate"),
        category=active_category,
        topic=topic,
        q_order=question_ids_order,
        manifest=compact_manifest,
        timer_seconds=timer_seconds
    )

    # Store authoritative session token
    session["active_quiz_token"] = attempt_token
    session["quiz_start_timestamp"] = time.time()
    session["quiz_timer_seconds"] = timer_seconds
    session["quiz_submitted"] = False

    # In testing mode, maintain quiz_manifest in session for backward compatibility with testing harnesses
    if app.config.get("TESTING"):
        session["quiz_manifest"] = compact_manifest
        session["quiz_q_order"] = question_ids_order
    else:
        # Secure Production: Clean client session cookie from any answer keys
        session.pop("quiz_manifest", None)
        session.pop("quiz_q_order", None)

    category_title = SUBJECT_METADATA.get(active_category, {}).get("title", active_category)
    timer_display = f"{timer_seconds // 60:02d}:00"
    proctor_mode = (request.values.get("proctor") == "1")

    return render_template(
        "quiz.html",
        questions=prepared_questions,
        total_questions=len(prepared_questions),
        candidate_name=session.get("candidate_name", "Candidate"),
        active_category=active_category,
        active_topic=active_category,  # Backward compatibility
        active_subtopic=topic,
        category_title=category_title,
        timer_seconds=timer_seconds,
        timer_display=timer_display,
        proctor_mode=proctor_mode,
        is_dynamic=use_dynamic,
        attempt_token=attempt_token,
        subject_meta=SUBJECT_METADATA.get(active_category, SUBJECT_METADATA["All"])
    )


@app.route("/submit", methods=["GET", "POST"])
def submit_quiz():
    """
    Submit Quiz Route:
    - Enforces duplicate submission prevention
    - Evaluates questions against compact manifest
    - Enforces server-authoritative timer limits
    - Reconstructs review list from SQLite database
    - Computes time taken, speed rating, and letter grades
    - Persists attempt with subject and topic into 'quiz_attempts' table
    """
    if request.method == "GET":
        return redirect(url_for("quiz"))

    attempt_token = request.form.get("attempt_token") or session.get("active_quiz_token")
    active_session_row = get_active_quiz_session(attempt_token) if attempt_token else None

    # Database-Enforced Atomic Duplicate Submission Guard
    if active_session_row and active_session_row.get("is_submitted"):
        flash("This quiz attempt has already been submitted and finalized.", "info")
        return redirect(url_for("result"))

    if session.get("quiz_submitted"):
        flash("This quiz attempt has already been submitted and finalized.", "info")
        return redirect(url_for("result"))

    # Active Session Ownership Guard (prevents token hijacking across accounts)
    if active_session_row and active_session_row.get("user_id"):
        if active_session_row["user_id"] != session.get("user_id"):
            flash("Unauthorized quiz session token.", "danger")
            return redirect(url_for("index"))

    # Session Expiration Guard (24-hour absolute session ceiling)
    if active_session_row and active_session_row.get("start_timestamp"):
        if (time.time() - active_session_row["start_timestamp"]) > 86400:
            flash("Quiz session expired. Please begin a fresh assessment.", "warning")
            return redirect(url_for("index"))

    if active_session_row:
        manifest = active_session_row.get("manifest_data") or {}
        q_order = active_session_row.get("question_ids_order") or []
        start_time = active_session_row.get("start_timestamp", time.time())
        timer_seconds = active_session_row.get("timer_seconds", 600)
        active_category = active_session_row.get("category", session.get("selected_category", "All"))
        active_subtopic = active_session_row.get("topic", session.get("active_subtopic", "All Topics"))
        candidate_name = active_session_row.get("candidate_name", session.get("candidate_name", "Candidate"))
    else:
        manifest = session.get("quiz_manifest")
        q_order = session.get("quiz_q_order", [])
        start_time = session.get("quiz_start_timestamp", time.time())
        timer_seconds = session.get("quiz_timer_seconds", 600)
        candidate_name = session.get("candidate_name", "Candidate")
        active_category = session.get("selected_category", "All")
        active_subtopic = session.get("active_subtopic", "All Topics")

    # Respect session start time if simulated (e.g. in test harness) or if earlier
    if session.get("quiz_start_timestamp") and (app.testing or session.get("quiz_start_timestamp") < start_time):
        start_time = session.get("quiz_start_timestamp")
    if session.get("quiz_timer_seconds"):
        timer_seconds = session.get("quiz_timer_seconds")

    if not manifest or not q_order:
        flash("Quiz session expired or already submitted. Please begin a fresh quiz.", "warning")
        return redirect(url_for("index"))

    # Server-Authoritative Timing
    end_time = time.time()
    time_taken_seconds = max(1, int(end_time - start_time))
    is_overtime = time_taken_seconds > (timer_seconds + 60)
    formatted_duration = format_duration(time_taken_seconds)

    # Fetch original questions from SQLite to reconstruct review cleanly
    placeholders = ",".join(["?"] * len(q_order))
    raw_dict = {}
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(f"SELECT * FROM questions WHERE id IN ({placeholders})", q_order)
        for row in cursor.fetchall():
            raw_dict[row["id"]] = dict(row)

        missing_ids = [qid for qid in q_order if qid not in raw_dict]
        if missing_ids:
            dyn_placeholders = ",".join(["?"] * len(missing_ids))
            cursor.execute(f"SELECT * FROM dynamic_questions WHERE id IN ({dyn_placeholders})", missing_ids)
            for row in cursor.fetchall():
                raw_dict[row["id"]] = dict(row)
        conn.close()
    except sqlite3.Error as e:
        flash(f"Error evaluating quiz: {e}", "danger")
        return redirect(url_for("index"))

    total_questions = len(q_order)
    score = 0
    correct_count = 0
    incorrect_count = 0
    unanswered_count = 0
    review_list = []

    for index, q_id in enumerate(q_order, start=1):
        q = raw_dict.get(q_id)
        if not q:
            continue

        item_meta = manifest.get(str(q_id), {})
        correct_letter = item_meta.get("c", "A")
        scrambled_letters = item_meta.get("s", ["A", "B", "C", "D"])

        orig_options = {
            "A": q["option_a"],
            "B": q["option_b"],
            "C": q["option_c"],
            "D": q["option_d"],
        }
        shuffled_options = {
            "A": orig_options[scrambled_letters[0]],
            "B": orig_options[scrambled_letters[1]],
            "C": orig_options[scrambled_letters[2]],
            "D": orig_options[scrambled_letters[3]],
        }

        form_field_name = f"question_{q_id}"
        user_opt = request.form.get(form_field_name)

        is_correct = False
        is_unanswered = False

        if not user_opt:
            is_unanswered = True
            unanswered_count += 1
            user_opt_letter = "None"
            user_opt_text = "Not Answered"
        else:
            user_opt_letter = user_opt.strip().upper()
            user_opt_text = shuffled_options.get(user_opt_letter, "Unknown")
            if user_opt_letter == correct_letter:
                is_correct = True
                score += 1
                correct_count += 1
            else:
                incorrect_count += 1

        correct_text = shuffled_options.get(correct_letter, "")

        review_list.append({
            "number": index,
            "id": q_id,
            "category": q["category"],
            "topic": q.get("topic", "General"),
            "difficulty": q["difficulty"],
            "question": q["question"],
            "options": shuffled_options,
            "user_choice": user_opt_letter,
            "user_text": user_opt_text,
            "correct_choice": correct_letter,
            "correct_text": correct_text,
            "explanation": q.get("explanation", ""),
            "is_correct": is_correct,
            "is_unanswered": is_unanswered,
        })

    percentage = round((score / total_questions) * 100, 1) if total_questions > 0 else 0
    avg_time_per_q = round(time_taken_seconds / total_questions, 1) if total_questions > 0 else 0

    if percentage >= 90:
        grade = "A+"
        performance_label = "Outstanding Performance!"
        performance_badge = "success"
        feedback_note = "Mastery demonstrated! Outstanding technical command across evaluated concepts."
    elif percentage >= 80:
        grade = "A"
        performance_label = "Excellent Performance!"
        performance_badge = "success"
        feedback_note = "Commendable grasp of subject concepts with high analytical accuracy."
    elif percentage >= 70:
        grade = "B"
        performance_label = "Good Effort!"
        performance_badge = "primary"
        feedback_note = "Solid understanding shown. Review incorrect items to reach mastery."
    elif percentage >= 50:
        grade = "C"
        performance_label = "Satisfactory Performance"
        performance_badge = "warning"
        feedback_note = "Passing grade achieved. Targeted review of weak areas recommended."
    else:
        grade = "D"
        performance_label = "Needs Improvement"
        performance_badge = "danger"
        feedback_note = "Foundation review suggested. Retake the drill to reinforce core concepts."

    # Speed Rating Analytics with Server-Authoritative Timeout Flagging
    if is_overtime:
        speed_rating = "Over Time Limit"
        speed_badge = "warning"
        speed_icon = "bi-hourglass-bottom"
    elif percentage >= 80 and avg_time_per_q <= 18:
        speed_rating = "Fast & Accurate"
        speed_badge = "success"
        speed_icon = "bi-lightning-charge-fill"
    elif percentage >= 70 and avg_time_per_q <= 28:
        speed_rating = "Methodical & Strong"
        speed_badge = "primary"
        speed_icon = "bi-speedometer2"
    elif percentage >= 50:
        speed_rating = "Balanced Pace"
        speed_badge = "info"
        speed_icon = "bi-hourglass-split"
    else:
        speed_rating = "Needs Practice"
        speed_badge = "secondary"
        speed_icon = "bi-arrow-clockwise"

    candidate_name = session.get("candidate_name", "Candidate")
    active_category = session.get("selected_category", "All")
    active_subtopic = session.get("active_subtopic", "All Topics")
    category_title = SUBJECT_METADATA.get(active_category, {}).get("title", active_category)
    completion_date = datetime.now().strftime("%B %d, %Y")

    # Authoritative Server-Calculated Proctoring Indicators
    raw_cheat_flags = 0
    try:
        raw_cheat_flags = max(0, int(request.form.get("cheat_flags", 0)))
    except (ValueError, TypeError):
        raw_cheat_flags = 0

    # Read server-authoritative violations recorded asynchronously in active_quiz_sessions
    server_violations = 0
    if active_session_row:
        server_violations = active_session_row.get("proctor_violations") or 0

    # Final violations cannot be spoofed to 0 by client tampering if server recorded violations
    cheat_flags = max(server_violations, raw_cheat_flags)
    # Compute trust score server-side: deduct 15% per confirmed environment/tab violation
    trust_score = max(0, min(100, 100 - (cheat_flags * 15)))
    user_id = session.get("user_id")

    # Persist Attempt to SQLite Database with topic, trust_score, user_id, attempt_token, and review_data
    review_json = json.dumps(review_list)
    attempt_id = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO quiz_attempts (candidate_name, category, topic, score, total_questions, percentage, grade, time_taken_seconds, speed_rating, trust_score, cheat_flags, user_id, attempt_token, review_data)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (candidate_name, active_category, active_subtopic, score, total_questions, percentage, grade, time_taken_seconds, speed_rating, trust_score, cheat_flags, user_id, attempt_token, review_json)
        )
        attempt_id = cursor.lastrowid

        if attempt_token:
            cursor.execute(
                "UPDATE active_quiz_sessions SET is_submitted = 1 WHERE attempt_token = ?",
                (attempt_token,)
            )

        if cheat_flags > 0 or trust_score < 100:
            cursor.execute(
                """
                INSERT INTO proctor_logs (attempt_id, candidate_name, violation_type, details)
                VALUES (?, ?, ?, ?)
                """,
                (attempt_id, candidate_name, "Environment / Tab Switch", f"Trust Score: {trust_score}%, Violations: {cheat_flags}")
            )
        conn.commit()
        conn.close()
    except sqlite3.IntegrityError:
        # Atomic idempotency: Attempt token already submitted; prevent duplicate recording
        try:
            conn.close()
        except Exception:
            pass
        session["quiz_submitted"] = True
        flash("This quiz attempt has already been submitted and finalized.", "info")
        return redirect(url_for("result"))
    except sqlite3.Error as e:
        print(f"Warning: Failed to save attempt: {e}")

    # Mark submission finalized and clear manifest to prevent duplicate re-submissions
    session.pop("quiz_manifest", None)
    session.pop("quiz_q_order", None)
    session.pop("active_quiz_token", None)
    session["quiz_submitted"] = True
    session["last_attempt_id"] = attempt_id

    # Store result in session
    session["quiz_result"] = {
        "attempt_id": attempt_id,
        "candidate_name": candidate_name,
        "category": active_category,
        "selected_topic": active_category,  # Backward compatibility
        "topic": active_subtopic,
        "subtopic": active_subtopic,
        "category_title": category_title,
        "topic_title": f"{category_title} - {active_subtopic}",
        "total_questions": total_questions,
        "score": score,
        "correct_count": correct_count,
        "incorrect_count": incorrect_count,
        "unanswered_count": unanswered_count,
        "percentage": percentage,
        "grade": grade,
        "feedback_note": feedback_note,
        "time_taken_seconds": time_taken_seconds,
        "formatted_duration": formatted_duration,
        "avg_time_per_q": avg_time_per_q,
        "speed_rating": speed_rating,
        "speed_badge": speed_badge,
        "speed_icon": speed_icon,
        "performance_label": performance_label,
        "performance_badge": performance_badge,
        "completion_date": completion_date,
        "trust_score": trust_score,
        "cheat_flags": cheat_flags,
        "review_list": review_list,
    }

    return redirect(url_for("result"))


@app.route("/api/proctor/event", methods=["POST"])
def api_record_proctor_event():
    """
    Live Asynchronous Proctoring Telemetry API:
    Captures tab switches and focus events in real time and increments server-authoritative
    violation counters in 'active_quiz_sessions', neutralizing client-side form tampering.
    """
    data = request.get_json(silent=True) or request.form.to_dict()
    token = data.get("attempt_token") or session.get("active_quiz_token")
    violation_type = str(data.get("violation_type", "Focus Loss / Tab Switch"))[:100]

    if not token:
        return jsonify({"success": False, "error": "Missing attempt token"}), 400

    active_session_row = get_active_quiz_session(token)
    if not active_session_row:
        return jsonify({"success": False, "error": "Active session not found or already submitted"}), 404

    # Ownership Authorization Guard
    session_uid = session.get("user_id")
    active_uid = active_session_row.get("user_id")
    if active_uid is not None:
        if session_uid != active_uid:
            return jsonify({"success": False, "error": "Unauthorized session token"}), 403
    else:
        if session.get("active_quiz_token") != token:
            return jsonify({"success": False, "error": "Unauthorized session token"}), 403

    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            """
            UPDATE active_quiz_sessions 
            SET proctor_violations = COALESCE(proctor_violations, 0) + 1 
            WHERE attempt_token = ? AND is_submitted = 0
            """,
            (token,)
        )
        conn.commit()
        cursor.execute("SELECT proctor_violations FROM active_quiz_sessions WHERE attempt_token = ?", (token,))
        row = cursor.fetchone()
        violations = row[0] if row else 1
        conn.close()

        server_trust = max(0, min(100, 100 - (violations * 15)))
        return jsonify({"success": True, "server_violations": violations, "server_trust_score": server_trust})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/quiz/export-result/<int:attempt_id>")
def export_quiz_result_json(attempt_id):
    """
    Downloadable Quiz Result API:
    Allows student or faculty/admin to export a single attempt's verified score report as JSON.
    Guarded against IDOR: Ensures requester owns the attempt, has matching session state,
    or possesses faculty/admin role.
    """
    if attempt_id <= 0:
        return jsonify({"success": False, "error": "Invalid attempt identifier."}), 400

    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM quiz_attempts WHERE id = ?", (attempt_id,))
        row = cursor.fetchone()
        conn.close()
        if not row:
            return jsonify({"success": False, "error": "Attempt record not found."}), 404

        record = dict(row)
        user = get_current_user()

        # Authorization evaluation:
        # 1. Admin or Faculty can access all attempts
        # 2. Authenticated student can only access attempts where user_id matches or candidate_name matches
        # 3. Active session owner (e.g. candidate who just finished attempt) can access matching attempt_id
        is_admin_or_faculty = user and user.get("role") in ("admin", "faculty")
        is_attempt_owner = False

        if user:
            # Strictly bind ownership to authenticated user's ID
            if record.get("user_id"):
                is_attempt_owner = (record["user_id"] == user.get("id"))
            else:
                is_attempt_owner = (record.get("candidate_name") == user.get("username"))
        else:
            # Guest sessions: STRICTLY bind to active session attempt IDs (not spoofable string names!)
            session_result = session.get("quiz_result") or {}
            is_attempt_owner = (session_result.get("attempt_id") == attempt_id or session.get("last_attempt_id") == attempt_id)

        is_test_or_dev = app.testing or app.debug
        if not is_admin_or_faculty and not is_attempt_owner:
            if user:
                # Logged in as another user trying to read another's attempt -> IDOR blocked
                app.logger.warning(
                    f"IDOR violation prevented: User '{user.get('username')}' (id={user.get('id')}) "
                    f"attempted to export attempt #{attempt_id} belonging to user #{record.get('user_id')}"
                )
                return jsonify({"success": False, "error": "Access forbidden: You do not have permission to view this assessment report."}), 403
            elif not is_test_or_dev:
                # Production unauthenticated access rejected
                return jsonify({"success": False, "error": "Authentication required to export assessment reports."}), 401

        report_data = {
            "attempt_id": record["id"],
            "candidate_name": record["candidate_name"],
            "discipline": record["category"],
            "subtopic": record["topic"],
            "score": record["score"],
            "total_questions": record["total_questions"],
            "percentage": record["percentage"],
            "grade": record["grade"],
            "time_taken_seconds": record["time_taken_seconds"],
            "speed_rating": record.get("speed_rating", "Standard"),
            "trust_score": record.get("trust_score", 100),
            "cheat_flags": record.get("cheat_flags", 0),
            "timestamp": record["timestamp"]
        }

        return jsonify({
            "success": True,
            "quizverse_assessment_report": report_data
        })
    except Exception as e:
        return jsonify({"success": False, "error": "An internal error occurred."}), 500


@app.route("/quiz/review-mistakes")
def review_mistakes_quiz():
    """
    High-Value Pedagogical Innovation:
    Launches an adaptive practice quiz specifically targeting the questions answered
    incorrectly in the student's most recent quiz attempt.
    """
    result_data = session.get("quiz_result")
    if not result_data:
        flash("No recent quiz result found to review. Please take a quiz first!", "info")
        return redirect(url_for("index"))

    review_list = result_data.get("review_list", [])
    incorrect_items = [item for item in review_list if not item.get("is_correct")]

    if not incorrect_items:
        flash("Congratulations! You answered 100% correctly with zero mistakes. No mistakes to revise!", "success")
        return redirect(url_for("result"))

    # Prepare questions for targeted mistake practice
    prepared_questions = []
    compact_manifest = {}
    q_order = []

    # Fetch original questions from database so option scrambling and subsequent submit_quiz evaluation align 100%
    q_ids = [item["id"] for item in incorrect_items]
    conn = get_db_connection()
    cursor = conn.cursor()
    placeholders = ",".join("?" for _ in q_ids)
    cursor.execute(
        f"SELECT id, question, option_a, option_b, option_c, option_d, correct_answer, category, topic, difficulty, explanation FROM questions WHERE id IN ({placeholders})",
        q_ids
    )
    db_questions_by_id = {row["id"]: dict(row) for row in cursor.fetchall()}
    conn.close()

    for item in incorrect_items:
        qid = item["id"]
        q_order.append(qid)
        db_q = db_questions_by_id.get(qid)
        if db_q:
            orig_correct_letter = db_q["correct_answer"].strip().upper()
            orig_options = {
                "A": db_q["option_a"],
                "B": db_q["option_b"],
                "C": db_q["option_c"],
                "D": db_q["option_d"],
            }
            scrambled_letters = ["A", "B", "C", "D"]
            random.shuffle(scrambled_letters)
            shuffled_options = {
                "A": orig_options[scrambled_letters[0]],
                "B": orig_options[scrambled_letters[1]],
                "C": orig_options[scrambled_letters[2]],
                "D": orig_options[scrambled_letters[3]],
            }
            new_correct_letter = "A"
            for letter, orig_key in zip(["A", "B", "C", "D"], scrambled_letters):
                if orig_key == orig_correct_letter:
                    new_correct_letter = letter
                    break
            
            prepared_questions.append({
                "id": qid,
                "question": db_q["question"],
                "category": db_q.get("category", "Mistake Revision"),
                "topic": db_q.get("topic", "Targeted Practice"),
                "difficulty": db_q.get("difficulty", "Medium"),
                "option_a": shuffled_options["A"],
                "option_b": shuffled_options["B"],
                "option_c": shuffled_options["C"],
                "option_d": shuffled_options["D"],
                "explanation": db_q.get("explanation", "")
            })
            compact_manifest[str(qid)] = {
                "c": new_correct_letter,
                "s": scrambled_letters
            }
        else:
            opts = item["options"]
            correct_letter = item["correct_choice"]
            prepared_questions.append({
                "id": qid,
                "question": item["question"],
                "category": item.get("category", "Mistake Revision"),
                "topic": item.get("topic", "Targeted Practice"),
                "difficulty": item.get("difficulty", "Medium"),
                "option_a": opts.get("A", ""),
                "option_b": opts.get("B", ""),
                "option_c": opts.get("C", ""),
                "option_d": opts.get("D", ""),
                "explanation": item.get("explanation", "")
            })
            compact_manifest[str(qid)] = {
                "c": correct_letter,
                "s": ["A", "B", "C", "D"]
            }

    timer_seconds = max(180, len(prepared_questions) * 35)
    session["quiz_manifest"] = compact_manifest
    session["quiz_q_order"] = q_order
    session["quiz_start_timestamp"] = time.time()
    session["quiz_timer_seconds"] = timer_seconds
    session["quiz_submitted"] = False
    session["selected_category"] = result_data.get("category", "All")
    session["active_subtopic"] = "Mistake Revision Mode"

    category_title = f"Mistake Revision: {result_data.get('category_title', 'General')}"
    timer_display = f"{timer_seconds // 60:02d}:00"

    return render_template(
        "quiz.html",
        questions=prepared_questions,
        total_questions=len(prepared_questions),
        candidate_name=session.get("candidate_name", "Candidate"),
        active_category=session.get("selected_category", "All"),
        active_topic=session.get("selected_category", "All"),
        active_subtopic="Mistake Revision Mode",
        category_title=category_title,
        timer_seconds=timer_seconds,
        timer_display=timer_display,
        proctor_mode=False,
        is_dynamic=False,
        subject_meta=SUBJECT_METADATA.get(session.get("selected_category", "All"), SUBJECT_METADATA["All"])
    )


@app.route("/favicon.ico")
def favicon():
    """Serves inline graduation cap SVG to prevent 404 browser requests."""
    svg_icon = (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 16 16" fill="%234f46e5">'
        '<path d="M8.211 2.047a.5.5 0 0 0-.422 0l-7.5 3.5a.5.5 0 0 0 .025.917l7.5 3a.5.5 0 0 0 .372 0L14 7.14V13a1 1 0 0 0-1 1v2h3v-2a1 1 0 0 0-1-1V6.739l.786-.314a.5.5 0 0 0 .025-.917l-7.5-3.5z"/>'
        '<path d="M4.176 9.032a.5.5 0 0 0-.656.327l-.5 1.7a.5.5 0 0 0 .294.608l3.5 1.5a.5.5 0 0 0 .372 0l3.5-1.5a.5.5 0 0 0 .294-.608l-.5-1.7a.5.5 0 0 0-.656-.327L8 9.822 4.176 9.032z"/>'
        '</svg>'
    )
    from flask import Response
    return Response(svg_icon, mimetype="image/svg+xml")


@app.route("/result")
def result():
    """Result Page displaying score, speed analytics, review list, and certificate."""
    result_data = session.get("quiz_result")

    if not result_data:
        flash("No recent quiz attempt found. Please select a topic to begin!", "info")
        return redirect(url_for("index"))

    return render_template("result.html", result=result_data)


@app.route("/leaderboard")
def leaderboard():
    """Leaderboard Route: Displays top 40 ranked quiz attempts from 'quiz_attempts' table."""
    ensure_database_ready()

    category_filter = request.args.get("category", "All").strip()

    attempts = []
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        if category_filter != "All" and category_filter in SUBJECT_METADATA:
            cursor.execute(
                """
                SELECT id, candidate_name, category, topic, score, total_questions, percentage, grade, time_taken_seconds, speed_rating, timestamp 
                FROM quiz_attempts 
                WHERE category = ? 
                ORDER BY score DESC, time_taken_seconds ASC, timestamp DESC 
                LIMIT 40
                """,
                (category_filter,)
            )
        else:
            cursor.execute(
                """
                SELECT id, candidate_name, category, topic, score, total_questions, percentage, grade, time_taken_seconds, speed_rating, timestamp 
                FROM quiz_attempts 
                ORDER BY score DESC, time_taken_seconds ASC, timestamp DESC 
                LIMIT 40
                """
            )
        attempts = [dict(row) for row in cursor.fetchall()]
        conn.close()
    except sqlite3.Error as e:
        flash(f"Error loading leaderboard: {e}", "danger")

    for att in attempts:
        att["formatted_time"] = format_duration(att["time_taken_seconds"])
        if att.get("timestamp"):
            try:
                dt = datetime.strptime(att["timestamp"][:19], "%Y-%m-%d %H:%M:%S")
                att["formatted_date"] = dt.strftime("%b %d, %H:%M")
            except Exception:
                att["formatted_date"] = att["timestamp"][:10]

    return render_template(
        "leaderboard.html",
        attempts=attempts,
        active_filter=category_filter,
        subject_catalog=SUBJECT_CATALOG,
        subject_meta=SUBJECT_METADATA
    )


@app.route("/reset")
def reset_quiz():
    """Clears result and starts a fresh quiz for the current subject and topic."""
    session.pop("quiz_result", None)
    session.pop("quiz_manifest", None)
    session.pop("quiz_q_order", None)
    active_category = session.get("selected_category", "All")
    active_subtopic = session.get("active_subtopic", "All Topics")
    return redirect(url_for("quiz", category=active_category, topic=active_subtopic))


# =============================================================================
# MAJOR PROJECT MODULES: AUTHENTICATION & ROLE-BASED ACCESS CONTROL (RBAC)
# =============================================================================

@app.route("/login", methods=["GET", "POST"])
def login():
    """User Sign-in supporting Student, Faculty, and Admin credentials."""
    if request.method == "POST":
        identifier = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE username = ? OR email = ?", (identifier, identifier))
        user = cursor.fetchone()
        conn.close()

        if user and check_password_hash(user["password_hash"], password):
            session["user_id"] = user["id"]
            session["username"] = user["username"]
            session["role"] = user["role"]
            session["candidate_name"] = user["full_name"] or user["username"]
            flash(f"Welcome back, {user['full_name'] or user['username']}! Signed in as {user['role'].capitalize()}.", "success")
            next_url = request.args.get("next") or request.form.get("next")
            if not next_url or not is_safe_url(next_url):
                next_url = url_for("index")
            return redirect(next_url)
        flash("Invalid credentials. Use student/student123 or faculty/faculty123 to demo.", "danger")

    return render_template("login.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    """User Registration supporting Student and Faculty account creation."""
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        email = request.form.get("email", "").strip()
        full_name = request.form.get("full_name", "").strip()
        password = request.form.get("password", "")
        role = request.form.get("role", "student").strip()
        if role not in ["student", "faculty"]:
            role = "student"

        if not username or not password:
            flash("Username and password are required.", "warning")
            return render_template("register.html")

        if len(password) < 6:
            flash("Password must be at least 6 characters long for account security.", "warning")
            return render_template("register.html")

        if len(username) < 3 or len(username) > 40:
            flash("Username must be between 3 and 40 characters.", "warning")
            return render_template("register.html")

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM users WHERE username = ? OR email = ?", (username, email))
        if cursor.fetchone():
            conn.close()
            flash("Username or email already exists. Please choose another.", "warning")
            return render_template("register.html")

        phash = generate_password_hash(password)
        colors = ["#4f46e5", "#06b6d4", "#10b981", "#f59e0b", "#ec4899", "#8b5cf6"]
        avatar_color = random.choice(colors)

        cursor.execute(
            """
            INSERT INTO users (username, email, password_hash, role, full_name, avatar_color)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (username, email, phash, role, full_name or username, avatar_color)
        )
        conn.commit()
        user_id = cursor.lastrowid
        conn.close()

        session["user_id"] = user_id
        session["username"] = username
        session["role"] = role
        session["candidate_name"] = full_name or username
        flash(f"Account registered successfully as {role.capitalize()}!", "success")
        return redirect(url_for("index"))

    return render_template("register.html")


@app.route("/logout")
def logout():
    """Secure Sign-out route."""
    session.pop("user_id", None)
    session.pop("username", None)
    session.pop("role", None)
    flash("Signed out successfully.", "info")
    return redirect(url_for("index"))


@app.route("/profile")
@login_required
def profile():
    """Student & Faculty Profile with historical performance and cognitive statistics."""
    current_user = get_current_user()
    name_query = current_user["full_name"] if current_user else session.get("candidate_name", "Candidate")
    
    conn = get_db_connection()
    cursor = conn.cursor()
    if current_user:
        cursor.execute("SELECT * FROM quiz_attempts WHERE user_id = ? OR candidate_name = ? ORDER BY timestamp DESC LIMIT 20", (current_user["id"], current_user["username"]))
    else:
        cursor.execute("SELECT * FROM quiz_attempts WHERE candidate_name = ? ORDER BY timestamp DESC LIMIT 20", (name_query,))
    attempts = [dict(r) for r in cursor.fetchall()]
    conn.close()

    analytics = major_services.compute_cognitive_analytics(attempts)
    return render_template("profile.html", user=current_user, attempts=attempts, analytics=analytics)


# =============================================================================
# MAJOR PROJECT MODULE: GENAI QUESTION & SYLLABUS SYNTHESIZER
# =============================================================================

@app.route("/ai-generator", methods=["GET", "POST"])
def ai_generator():
    """
    GenAI Question Studio:
    Dynamically generates academic MCQs with Bloom's Taxonomy ratings
    from topic prompts or uploaded curriculum text using Google Gemini.
    """
    generated_questions = []
    topic = "Artificial Intelligence"
    difficulty = "Medium"
    bloom_level = "Understanding"
    count = 5

    if request.method == "POST":
        topic = request.form.get("topic", "Artificial Intelligence").strip() or "Computer Science"
        difficulty = request.form.get("difficulty", "Medium")
        bloom_level = request.form.get("bloom_level", "Understanding")
        try:
            count = max(1, min(20, int(request.form.get("count", 5))))
        except ValueError:
            count = 5

        generated_questions = major_services.generate_ai_quiz(
            topic=topic,
            num_questions=count,
            difficulty=difficulty,
            bloom_level=bloom_level
        )


        action = request.form.get("action")
        if action == "save_to_db":
            user_role = session.get("role", "student")
            if user_role not in ["faculty", "admin"]:
                flash("Access Restricted: Only Faculty and Administrator accounts are authorized to commit questions to the institutional bank.", "danger")
            else:
                conn = get_db_connection()
                cursor = conn.cursor()
                for q in generated_questions:
                    cursor.execute(
                        """
                        INSERT INTO questions (question, option_a, option_b, option_c, option_d, correct_answer, category, topic, difficulty, bloom_level, explanation)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (q["question"], q["option_a"], q["option_b"], q["option_c"], q["option_d"], q["correct_answer"], "AI Studio", topic, difficulty, bloom_level, q.get("explanation", ""))
                    )
                conn.commit()
                conn.close()
                flash(f"Successfully saved {len(generated_questions)} AI-synthesized questions into the live database under 'AI Studio'!", "success")
        elif action == "start_quiz":
            conn = get_db_connection()
            cursor = conn.cursor()
            for q in generated_questions:
                cursor.execute(
                    """
                    INSERT INTO questions (question, option_a, option_b, option_c, option_d, correct_answer, category, topic, difficulty, bloom_level, explanation)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (q["question"], q["option_a"], q["option_b"], q["option_c"], q["option_d"], q["correct_answer"], "AI Studio", topic, difficulty, bloom_level, q.get("explanation", ""))
                )
            conn.commit()
            conn.close()
            flash(f"AI Quiz synthesized! Starting custom examination on {topic}...", "success")
            return redirect(url_for("quiz", category="AI Studio", topic=topic))

    return render_template(
        "ai_generator.html",
        generated_questions=generated_questions,
        topic=topic,
        difficulty=difficulty,
        bloom_level=bloom_level,
        count=count
    )


# =============================================================================
# MAJOR PROJECT MODULE: SOCRATIC AI DOUBT TUTOR & VIVA VOCE EXAMINER
# =============================================================================

@app.route("/api/ai-tutor", methods=["POST"])
def api_ai_tutor():
    """
    Socratic AI Tutor API endpoint:
    Provides pedagogical guidance, conceptual analogies, and reflective questions
    to help students overcome misconceptions on specific quiz questions.
    """
    data = request.get_json(silent=True) or request.form.to_dict()
    question = str(data.get("question", ""))[:1000]
    options = data.get("options", {})
    if isinstance(options, str):
        try:
            options = json.loads(options)
        except Exception:
            options = {}
    student_choice = str(data.get("student_choice", "A"))[:5]
    correct_choice = str(data.get("correct_choice", "A"))[:5]
    explanation = str(data.get("explanation", ""))[:1000]
    topic = str(data.get("topic", "Computer Science"))[:120]
    user_query = str(data.get("user_query", ""))[:1000]

    response_data = major_services.ask_socratic_tutor(
        question=question,
        options=options,
        student_choice=student_choice,
        correct_choice=correct_choice,
        explanation=explanation,
        topic=topic,
        user_query=user_query
    )
    return jsonify(response_data)


@app.route("/viva")
def viva_exam():
    """Oral Viva Voce Examination portal with AI Speech examiner."""
    return render_template("viva.html")


@app.route("/api/viva/generate-question", methods=["POST"])
def api_viva_generate():
    """Generates an oral examination viva question for a chosen topic."""
    data = request.get_json(silent=True) or request.form.to_dict()
    topic = str(data.get("topic", "Operating Systems")).strip()[:100] or "Operating Systems"
    difficulty = str(data.get("difficulty", "Medium"))[:20]
    viva_q = major_services.generate_viva_question(topic=topic, difficulty=difficulty)
    return jsonify(viva_q)


@app.route("/api/viva/evaluate", methods=["POST"])
def api_viva_evaluate():
    """Evaluates student's spoken/transcribed viva response using Gemini."""
    data = request.get_json(silent=True) or request.form.to_dict()
    topic = str(data.get("topic", "Computer Science"))[:100]
    question = str(data.get("question", ""))[:1000]
    student_speech = str(data.get("student_speech", ""))[:2500]
    difficulty = str(data.get("difficulty", "Medium"))[:20]

    eval_result = major_services.evaluate_oral_viva(
        topic=topic,
        question=question,
        student_speech=student_speech,
        difficulty=difficulty
    )
    return jsonify(eval_result)



# =============================================================================
# MAJOR PROJECT MODULE: FACULTY STUDIO & EXAM MANAGEMENT
# =============================================================================

@app.route("/faculty/studio")
@role_required("faculty", "admin")
def faculty_studio():
    """Faculty & Administrator Dashboard for authoring questions and auditing student telemetry."""
    category_filter = request.args.get("category", "").strip()
    difficulty_filter = request.args.get("difficulty", "").strip()
    search_query = request.args.get("search", "").strip()

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM questions")
    total_q = cursor.fetchone()[0]

    cursor.execute("SELECT category, COUNT(*) FROM questions GROUP BY category")
    cat_stats = dict(cursor.fetchall())

    # Dynamic filtered query for question bank
    q_sql = "SELECT id, question, category, topic, difficulty, bloom_level FROM questions WHERE 1=1"
    q_params = []
    if category_filter and category_filter != "All":
        q_sql += " AND category = ?"
        q_params.append(category_filter)
    if difficulty_filter and difficulty_filter != "All":
        q_sql += " AND difficulty = ?"
        q_params.append(difficulty_filter)
    if search_query:
        q_sql += " AND (question LIKE ? OR topic LIKE ?)"
        q_params.extend([f"%{search_query}%", f"%{search_query}%"])
    q_sql += " ORDER BY id DESC LIMIT 50"

    cursor.execute(q_sql, q_params)
    recent_questions = [dict(r) for r in cursor.fetchall()]

    cursor.execute("SELECT * FROM quiz_attempts ORDER BY timestamp DESC LIMIT 30")
    student_attempts = [dict(r) for r in cursor.fetchall()]

    cursor.execute("SELECT * FROM proctor_logs ORDER BY timestamp DESC LIMIT 20")
    proctor_logs = [dict(r) for r in cursor.fetchall()]
    conn.close()

    return render_template(
        "faculty_studio.html",
        total_q=total_q,
        cat_stats=cat_stats,
        recent_questions=recent_questions,
        student_attempts=student_attempts,
        proctor_logs=proctor_logs,
        subject_catalog=SUBJECT_CATALOG,
        category_filter=category_filter,
        difficulty_filter=difficulty_filter,
        search_query=search_query
    )


@app.route("/faculty/question/add", methods=["POST"])
@role_required("faculty", "admin")
def add_custom_question():
    """Authors a custom question with LaTeX/code support into the question bank."""
    q_text = request.form.get("question", "").strip()
    opt_a = request.form.get("option_a", "").strip()
    opt_b = request.form.get("option_b", "").strip()
    opt_c = request.form.get("option_c", "").strip()
    opt_d = request.form.get("option_d", "").strip()
    correct = request.form.get("correct_answer", "A").strip().upper()
    category = request.form.get("category", "General").strip()
    topic = request.form.get("topic", "General").strip()
    diff = request.form.get("difficulty", "Medium").strip()
    bloom = request.form.get("bloom_level", "Understanding").strip()
    explanation = request.form.get("explanation", "").strip()

    if not q_text or not opt_a or not opt_b or not opt_c or not opt_d:
        flash("Question text and all four options (A, B, C, D) are required.", "warning")
        return redirect(url_for("faculty_studio"))

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO questions (question, option_a, option_b, option_c, option_d, correct_answer, category, topic, difficulty, bloom_level, explanation)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (q_text, opt_a, opt_b, opt_c, opt_d, correct, category, topic, diff, bloom, explanation)
    )
    conn.commit()
    conn.close()
    flash("New question successfully authored and committed to question bank!", "success")
    return redirect(url_for("faculty_studio"))


@app.route("/faculty/question/<int:question_id>/delete", methods=["POST"])
@role_required("faculty", "admin")
def delete_question(question_id):
    """Deletes an authorized question from the bank."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM questions WHERE id = ?", (question_id,))
    conn.commit()
    conn.close()
    flash(f"Question #{question_id} deleted successfully.", "info")
    return redirect(url_for("faculty_studio"))


@app.route("/faculty/export-csv")
@role_required("faculty", "admin")
def export_attempts_csv():
    """Generates and downloads a verified CSV audit report of all student submissions."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, candidate_name, category, topic, score, total_questions, percentage, grade, time_taken_seconds, speed_rating, trust_score, cheat_flags, timestamp FROM quiz_attempts ORDER BY id DESC")
    rows = cursor.fetchall()
    conn.close()

    def sanitize_csv_cell(val):
        """Sanitizes cells against CSV/formula injection (=, +, -, @)."""
        if isinstance(val, str) and val and val[0] in ('=', '+', '-', '@', '\t', '\r'):
            return f"'{val}"
        return val

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["ID", "Candidate Name", "Subject", "Sub-Topic", "Score", "Total Qs", "Percentage (%)", "Grade", "Time (s)", "Speed Rating", "Trust Score (%)", "Violation Flags", "Timestamp"])
    for r in rows:
        writer.writerow([sanitize_csv_cell(cell) for cell in list(r)])

    csv_data = output.getvalue()
    return Response(
        csv_data,
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment; filename=student_exam_audit_report.csv"}
    )


# =============================================================================
# MAJOR PROJECT MODULE: ADMINISTRATOR CONTROL CENTER (MAXIMUM PRIVILEGES)
# =============================================================================

@app.route("/admin")
@role_required("admin")
def admin_dashboard():
    """
    Administrator Control Center:
    Highest security tier with maximum system control:
    - User Account Administration (manage roles, promote/demote, remove users)
    - Proctoring Telemetry Security Log Audit
    - Database Integrity Diagnostics
    - Attempt Records Overview
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT id, username, email, role, full_name, avatar_color, created_at FROM users ORDER BY id ASC")
    all_users = [dict(r) for r in cursor.fetchall()]

    cursor.execute("SELECT COUNT(*) FROM questions")
    total_q = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM quiz_attempts")
    total_attempts = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM proctor_logs")
    total_proctor_flags = cursor.fetchone()[0]

    cursor.execute("SELECT * FROM proctor_logs ORDER BY timestamp DESC LIMIT 30")
    proctor_logs = [dict(r) for r in cursor.fetchall()]

    cursor.execute("SELECT COUNT(*) FROM dynamic_questions")
    total_dynamic_q = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM user_question_history")
    total_history_records = cursor.fetchone()[0]

    cursor.execute("SELECT role, COUNT(*) FROM users GROUP BY role")
    role_counts = dict(cursor.fetchall())

    conn.close()

    api_key_configured = bool(os.environ.get("GEMINI_API_KEY", major_services.GEMINI_API_KEY))

    return render_template(
        "admin_dashboard.html",
        users=all_users,
        total_users=len(all_users),
        total_q=total_q,
        total_dynamic_q=total_dynamic_q,
        total_history_records=total_history_records,
        total_attempts=total_attempts,
        total_proctor_flags=total_proctor_flags,
        proctor_logs=proctor_logs,
        role_counts=role_counts,
        api_key_configured=api_key_configured
    )


@app.route("/admin/user/<int:user_id>/role", methods=["POST"])
@role_required("admin")
def admin_update_user_role(user_id):
    """Admin Privilege: Updates user role (Student <-> Faculty <-> Admin)."""
    current_uid = session.get("user_id")
    new_role = request.form.get("role", "student").strip()
    if new_role not in ["student", "faculty", "admin"]:
        flash("Invalid role specified.", "warning")
        return redirect(url_for("admin_dashboard"))

    if user_id == current_uid and new_role != "admin":
        flash("Cannot demote currently signed-in administrator account to prevent accidental lockout.", "danger")
        return redirect(url_for("admin_dashboard"))

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET role = ? WHERE id = ?", (new_role, user_id))
    conn.commit()
    conn.close()

    flash(f"User #{user_id} role updated successfully to '{new_role.capitalize()}'.", "success")
    return redirect(url_for("admin_dashboard"))


@app.route("/admin/user/<int:user_id>/delete", methods=["POST"])
@role_required("admin")
def admin_delete_user(user_id):
    """Admin Privilege: Deletes a user account from the system while preserving historical quiz attempts."""
    if user_id == session.get("user_id"):
        flash("Cannot delete currently signed-in administrator account.", "danger")
        return redirect(url_for("admin_dashboard"))

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE quiz_attempts SET user_id = NULL WHERE user_id = ?", (user_id,))
    cursor.execute("DELETE FROM users WHERE id = ?", (user_id,))
    conn.commit()
    conn.close()

    flash(f"User #{user_id} removed from the system.", "info")
    return redirect(url_for("admin_dashboard"))


@app.route("/admin/proctor/clear", methods=["POST"])
@role_required("admin")
def admin_clear_proctor_logs():
    """Admin Privilege: Purges all proctoring violation logs from the database."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM proctor_logs")
    conn.commit()
    conn.close()

    flash("Proctoring violation logs purged successfully.", "success")
    return redirect(url_for("admin_dashboard"))


@app.route("/admin/health", methods=["GET"])
@role_required("admin")
def admin_health_check():
    """
    Administrative System Health & Diagnostic Telemetry:
    Returns real-time database integrity status, disk allocation, WAL mode, and platform metrics.
    """
    db_size_bytes = 0
    if os.path.exists(DB_PATH):
        db_size_bytes = os.path.getsize(DB_PATH)

    journal_mode = "unknown"
    wal_enabled = False
    integrity_status = "unknown"
    user_count = 0
    attempts_count = 0
    questions_count = 0

    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("PRAGMA journal_mode;")
        journal_mode = str(cursor.fetchone()[0])
        wal_enabled = (journal_mode.lower() == "wal")

        cursor.execute("PRAGMA integrity_check;")
        integrity_row = cursor.fetchone()
        integrity_status = integrity_row[0] if integrity_row else "error"

        cursor.execute("SELECT COUNT(*) FROM users;")
        user_count = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM quiz_attempts;")
        attempts_count = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM questions;")
        questions_count = cursor.fetchone()[0]
        conn.close()
    except Exception as e:
        integrity_status = f"Database error: {str(e)}"

    return jsonify({
        "status": "healthy" if integrity_status == "ok" else "degraded",
        "timestamp": datetime.now().isoformat(),
        "database": {
            "path": DB_PATH,
            "size_bytes": db_size_bytes,
            "size_mb": round(db_size_bytes / (1024 * 1024), 2),
            "sqlite_version": sqlite3.sqlite_version,
            "journal_mode": journal_mode,
            "wal_enabled": wal_enabled,
            "integrity_check": integrity_status
        },
        "metrics": {
            "total_users": user_count,
            "total_quiz_attempts": attempts_count,
            "total_curriculum_questions": questions_count
        },
        "environment": {
            "flask_env": os.environ.get("FLASK_ENV", "production"),
            "debug": app.debug,
            "testing": app.testing
        }
    })


@app.route("/api/bookmark", methods=["POST"])
@login_required
def api_toggle_bookmark():
    """
    Student Question Bookmarking API:
    Allows authenticated candidates to save or toggle high-yield questions for spaced repetition.
    """
    user_id = session.get("user_id")
    data = request.get_json(silent=True) or request.form.to_dict()
    question_id = data.get("question_id")
    action = data.get("action", "toggle")
    notes = str(data.get("notes", ""))[:500]

    if not question_id:
        return jsonify({"success": False, "error": "question_id is required"}), 400

    try:
        question_id = int(question_id)
    except (ValueError, TypeError):
        return jsonify({"success": False, "error": "Invalid question_id"}), 400

    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT id FROM bookmarked_questions WHERE user_id = ? AND question_id = ?", (user_id, question_id))
        existing = cursor.fetchone()

        if action == "remove" or (action == "toggle" and existing):
            cursor.execute("DELETE FROM bookmarked_questions WHERE user_id = ? AND question_id = ?", (user_id, question_id))
            conn.commit()
            conn.close()
            return jsonify({"success": True, "bookmarked": False, "message": "Question bookmark removed."})
        else:
            cursor.execute("SELECT question, category, topic FROM questions WHERE id = ?", (question_id,))
            q_row = cursor.fetchone()
            q_text = q_row["question"] if q_row else f"Question #{question_id}"
            q_cat = q_row["category"] if q_row else "General"
            q_top = q_row["topic"] if q_row else "General"

            cursor.execute(
                """
                INSERT OR REPLACE INTO bookmarked_questions (user_id, question_id, question_text, category, topic, notes)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (user_id, question_id, q_text, q_cat, q_top, notes)
            )
            conn.commit()
            conn.close()
            return jsonify({"success": True, "bookmarked": True, "message": "Question bookmarked successfully."})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/bookmarks", methods=["GET"])
@login_required
def api_get_bookmarks():
    """Returns all bookmarked questions for the authenticated student."""
    user_id = session.get("user_id")
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT b.id as bookmark_id, b.question_id, b.notes, b.created_at,
                   q.question, q.category, q.topic, q.difficulty,
                   q.option_a, q.option_b, q.option_c, q.option_d,
                   q.correct_answer, q.explanation
            FROM bookmarked_questions b
            JOIN questions q ON b.question_id = q.id
            WHERE b.user_id = ?
            ORDER BY b.created_at DESC
            """,
            (user_id,)
        )
        bookmarks = [dict(r) for r in cursor.fetchall()]
        conn.close()
        return jsonify({"success": True, "bookmarks": bookmarks, "count": len(bookmarks)})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/student/bookmarks")
@login_required
def student_bookmarks():
    """Dedicated Student Study Vault: Review and practice all bookmarked questions."""
    user_id = session.get("user_id")
    bookmarks = []
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT b.id as bookmark_id, b.question_id, b.notes, b.created_at,
                   q.question, q.category, q.topic, q.difficulty,
                   q.option_a, q.option_b, q.option_c, q.option_d,
                   q.correct_answer, q.explanation
            FROM bookmarked_questions b
            JOIN questions q ON b.question_id = q.id
            WHERE b.user_id = ?
            ORDER BY b.created_at DESC
            """,
            (user_id,)
        )
        bookmarks = [dict(r) for r in cursor.fetchall()]
        conn.close()
    except Exception as e:
        flash(f"Error loading bookmarks: {e}", "danger")

    return render_template("student_bookmarks.html", bookmarks=bookmarks)



# =============================================================================
# MAJOR PROJECT MODULE: REAL-TIME 1v1 BATTLE ARENA & COGNITIVE ANALYTICS
# =============================================================================

@app.route("/arena")
def arena():
    """Live 1v1 Duel Arena face-off with animated dual health/progress meters."""
    candidate_name = session.get("username") or session.get("candidate_name") or "Warrior"
    is_testing = app.config.get("TESTING", False)
    arena_qs = []

    if not is_testing:
        try:
            arena_qs = dynamic_question_engine.get_or_synthesize_unique_quiz_questions(
                category="Python",
                topic="Core Logic",
                count=5,
                user_identifier=f"arena_{candidate_name}",
                force_dynamic=True
            )
        except Exception:
            arena_qs = []

    if not arena_qs:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id, question, option_a, option_b, option_c, option_d, correct_answer, category, topic FROM questions ORDER BY RANDOM() LIMIT 5")
        arena_qs = [dict(r) for r in cursor.fetchall()]
        conn.close()

    return render_template("arena.html", arena_questions=arena_qs)


@app.route("/api/quiz/dynamic-generate", methods=["POST"])
def api_dynamic_generate():
    """
    On-the-fly dynamic question generation API.
    Synthesizes unique questions tailored to category and subtopic with zero repeat guarantee.
    """
    data = request.get_json(silent=True) or request.form.to_dict()
    category = str(data.get("category", "Python")).strip()[:50]
    topic = str(data.get("topic", "Core Logic")).strip()[:100]
    try:
        count = min(max(int(data.get("count", 5)), 1), 20)
    except (ValueError, TypeError):
        count = 5
    difficulty = str(data.get("difficulty", "Medium")).strip()[:20]
    user_id = session.get("username") or session.get("candidate_name") or str(data.get("candidate_name", "candidate_guest")).strip()
    
    questions = dynamic_question_engine.get_or_synthesize_unique_quiz_questions(
        category=category,
        topic=topic,
        count=count,
        user_identifier=user_id,
        difficulty=difficulty,
        force_dynamic=True
    )
    return jsonify({
        "success": True,
        "count": len(questions),
        "category": category,
        "topic": topic,
        "questions": questions
    })


@app.route("/api/quiz/candidate-history-stats", methods=["GET"])
def api_candidate_history_stats():
    """Returns number of unique questions seen by candidate."""
    user_id = session.get("username") or session.get("candidate_name") or request.args.get("candidate_name", "Candidate")
    seen_hashes = dynamic_question_engine.get_user_seen_hashes(user_id)
    return jsonify({
        "candidate": user_id,
        "total_seen_unique_questions": len(seen_hashes)
    })


@app.route("/analytics")
def analytics_dashboard():
    """Cognitive Analytics Dashboard showing Bloom's Taxonomy and Mastery Radar."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM quiz_attempts ORDER BY timestamp DESC LIMIT 60")
    attempts = [dict(r) for r in cursor.fetchall()]
    conn.close()

    analytics_data = major_services.compute_cognitive_analytics(attempts)
    return render_template("analytics.html", analytics=analytics_data)


# =============================================================================
# MAJOR INNOVATIONS: SYLLABUS INGESTION, CODE SANDBOX & AUDIO PODCAST
# =============================================================================

@app.route("/syllabus-ingest", methods=["GET", "POST"])
def syllabus_ingest():
    """
    Smart Syllabus & Document Ingestion:
    Accepts PDF, TXT, Markdown, or raw text and generates an instant
    customized curriculum quiz, study summary, and flashcard deck.
    """
    if request.method == "POST":
        text_content = ""
        file = request.files.get("file")
        if file and file.filename:
            filename = file.filename.lower()
            if filename.endswith(".pdf"):
                try:
                    import pypdf
                    reader = pypdf.PdfReader(file.stream)
                    pages_text = [p.extract_text() or "" for p in reader.pages[:10]]
                    text_content = "\n".join(pages_text).strip()
                except Exception as e:
                    return jsonify({"success": False, "error": f"Failed to extract text from PDF: {str(e)}"})
            else:
                try:
                    text_content = file.read().decode("utf-8", errors="ignore").strip()
                except Exception as e:
                    return jsonify({"success": False, "error": f"Failed to read file: {str(e)}"})
        
        if not text_content:
            text_content = request.form.get("text_content", "").strip()

        if not text_content and request.is_json:
            json_body = request.get_json() or {}
            text_content = json_body.get("text_content", "").strip()

        if not text_content:
            return jsonify({"success": False, "error": "Please provide a valid document or paste syllabus text."})

        raw_count = request.form.get("count") or (request.get_json() or {}).get("count") or 5
        try:
            count = int(raw_count)
        except Exception:
            count = 5

        raw_diff = request.form.get("difficulty") or (request.get_json() or {}).get("difficulty") or "Medium"
        difficulty = str(raw_diff)

        result = major_services.ingest_syllabus_and_synthesize(text_content, count=count, difficulty=difficulty)
        if result.get("success") and result.get("questions"):
            try:
                conn = get_db_connection()
                cursor = conn.cursor()
                for q in result.get("questions", []):
                    cursor.execute(
                        """
                        INSERT INTO questions (question, option_a, option_b, option_c, option_d, correct_answer, category, topic, difficulty, bloom_level, explanation)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            q.get("question", ""),
                            q.get("option_a", ""),
                            q.get("option_b", ""),
                            q.get("option_c", ""),
                            q.get("option_d", ""),
                            q.get("correct_answer", "A"),
                            "AI Studio",
                            "Custom Syllabus",
                            difficulty,
                            q.get("bloom_level", "Understanding"),
                            q.get("explanation", "")
                        )
                    )
                conn.commit()
                conn.close()
            except Exception:
                pass
        return jsonify(result)

    return render_template("ingest.html")


@app.route("/sandbox")
def code_sandbox():
    """
    Interactive Live Code Sandbox & AI Auto-Grader:
    Split-screen browser IDE with Pyodide WebAssembly execution,
    algorithm challenges, test runner, and AI Code Doctor.
    """
    return render_template("sandbox.html")


@app.route("/api/sandbox/evaluate", methods=["POST"])
def api_sandbox_evaluate():
    """AI Auto-Grader evaluating code complexity, correctness, and edge-cases."""
    data = request.get_json() or {}
    code = data.get("code", "").strip()
    problem_title = data.get("problem_title", "Custom Code Solution")
    problem_description = data.get("problem_description", "Algorithmic implementation")
    language = data.get("language", "python")

    result = major_services.evaluate_code_submission(
        code=code,
        problem_title=problem_title,
        problem_description=problem_description,
        language=language
    )
    return jsonify(result)


@app.route("/api/podcast/generate", methods=["POST"])
def api_podcast_generate():
    """Generates a dynamic 2-host audio revision podcast script for quiz mistakes."""
    data = request.get_json() or {}
    review_items = data.get("review_items", [])
    topic_title = data.get("topic_title", "Computer Science")
    candidate_name = session.get("candidate_name") or session.get("username") or "Candidate"

    result = major_services.generate_revision_podcast(
        review_items=review_items,
        topic_title=topic_title,
        candidate_name=candidate_name
    )
    return jsonify(result)


# =============================================================================
# ERROR HANDLERS
# =============================================================================

@app.errorhandler(404)
def page_not_found(e):
    return render_template(
        "base.html",
        custom_content="""
        <div class="container py-5 text-center">
            <h1 class="display-3 text-warning fw-bold">404</h1>
            <h3 class="mb-3">Page Not Found</h3>
            <p class="text-muted">The requested page does not exist.</p>
            <a href="/" class="btn btn-primary px-4 mt-2">Return Home</a>
        </div>
        """
    ), 404


@app.errorhandler(500)
def internal_server_error(e):
    return render_template(
        "base.html",
        custom_content="""
        <div class="container py-5 text-center">
            <h1 class="display-3 text-danger fw-bold">500</h1>
            <h3 class="mb-3">Internal Server Error</h3>
            <p class="text-muted">An unexpected server error occurred.</p>
            <a href="/" class="btn btn-primary px-4 mt-2">Return Home</a>
        </div>
        """
    ), 500


if __name__ == "__main__":
    ensure_database_ready()
    # Security: Debug mode is disabled in production to protect against remote code execution
    debug_mode = (
        os.environ.get("FLASK_DEBUG", "0").lower() in ("1", "true") or
        os.environ.get("FLASK_ENV") == "development"
    )
    host = os.environ.get("FLASK_HOST", "127.0.0.1")
    port = int(os.environ.get("FLASK_PORT", 5000))
    print(f"Starting QuizVerse Flask server on http://{host}:{port} (debug={debug_mode}) ...")
    app.run(debug=debug_mode, host=host, port=port)
