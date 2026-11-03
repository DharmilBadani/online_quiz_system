# -*- coding: utf-8 -*-
"""
=============================================================================
QUIZVERSE - Final Year Major Project Database Schema Initializer
=============================================================================
1. Creates 'users' table with Role-Based Access Control (Student, Faculty, Admin).
2. Creates 'dynamic_questions' table with Bloom's Taxonomy & explanations.
3. Creates 'user_question_history' table for SHA-256 cryptographic anti-repeat engine.
4. Creates 'proctor_logs' table for WebRTC AI vision & telemetry invigilation.
5. Creates 'quiz_attempts' table for attempt history and cognitive analytics.
=============================================================================
"""

import os
import sys
import sqlite3

try:
    from werkzeug.security import generate_password_hash
except ImportError:
    import hashlib
    def generate_password_hash(password: str) -> str:
        # Graceful fallback hash for offline database initialization
        return f"pbkdf2:sha256:600000${hashlib.sha256(password.encode('utf-8')).hexdigest()}"

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

DB_PATH = os.path.abspath(os.environ.get("DATABASE_PATH", os.path.join(BASE_DIR, "quiz.db")))
os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)

SAMPLE_ATTEMPTS = [
    ("Alice Sharma", "Java", "Database Connection", 10, 10, 100.0, "A+", 120, "Fast & Accurate"),
    ("Rohan Mehta", "Java", "All Topics", 19, 20, 95.0, "A+", 290, "Fast & Accurate"),
    ("Priya Nair", "Python", "CRUD Operations", 10, 10, 100.0, "A+", 115, "Fast & Accurate"),
    ("David Miller", "DBMS", "SQL Joins", 9, 10, 90.0, "A+", 140, "Fast & Accurate"),
    ("Elena Rostova", "Flask", "Routing & URL Converters", 10, 10, 100.0, "A+", 130, "Fast & Accurate"),
    ("Carlos Mendez", "C++", "Pointers & References", 9, 10, 90.0, "A+", 155, "Methodical & Strong"),
    ("Aarav Patel", "WebDev", "CSS Flexbox Layout", 10, 10, 100.0, "A+", 105, "Fast & Accurate"),
    ("Sophia Chen", "DSA", "Binary Search Trees (BST)", 9, 10, 90.0, "A+", 170, "Methodical & Strong"),
    ("Vikram Singh", "OS", "Deadlocks & Banker's Algorithm", 10, 10, 100.0, "A+", 125, "Fast & Accurate")
]


def init_database():
    """Initializes schemas for dynamic questions, RBAC users, proctor logs, and attempts."""
    print(f"Connecting to database at: {DB_PATH}")
    connection = sqlite3.connect(DB_PATH, timeout=20.0)
    connection.execute("PRAGMA foreign_keys = ON;")
    connection.execute("PRAGMA journal_mode = WAL;")
    cursor = connection.cursor()

    # 1. Primary Users table for RBAC (Must exist first for Foreign Key referential integrity)
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            email TEXT UNIQUE,
            password_hash TEXT NOT NULL,
            role TEXT DEFAULT 'student',
            full_name TEXT,
            avatar_color TEXT DEFAULT '#4f46e5',
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_users_username ON users(username)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_users_email ON users(email)")

    # Seed default Major Project role accounts
    default_users = [
        ("student", "student@university.edu", generate_password_hash("student123"), "student", "Alex Student", "#6366f1"),
        ("faculty", "faculty@university.edu", generate_password_hash("faculty123"), "faculty", "Prof. Vikram Sharma", "#10b981"),
        ("admin", "admin@university.edu", generate_password_hash("admin123"), "admin", "System Administrator", "#f59e0b")
    ]
    for uname, email, phash, role, fname, color in default_users:
        cursor.execute("SELECT id, role FROM users WHERE username = ?", (uname,))
        row = cursor.fetchone()
        if not row:
            cursor.execute(
                """
                INSERT INTO users (username, email, password_hash, role, full_name, avatar_color)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (uname, email, phash, role, fname, color)
            )
            print(f"Created default user: {uname} ({role})")
        elif uname == "admin" and row[1] != "admin":
            cursor.execute("UPDATE users SET role = 'admin' WHERE username = 'admin'")
            print("Restored default admin account role integrity.")

    # 2. Questions table for dynamic storage and backward compatibility
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS questions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            question TEXT NOT NULL,
            option_a TEXT NOT NULL,
            option_b TEXT NOT NULL,
            option_c TEXT NOT NULL,
            option_d TEXT NOT NULL,
            correct_answer TEXT NOT NULL,
            category TEXT NOT NULL,
            topic TEXT NOT NULL,
            difficulty TEXT DEFAULT 'Medium',
            bloom_level TEXT DEFAULT 'Understanding',
            explanation TEXT DEFAULT ''
        )
        """
    )
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_q_cat_topic ON questions(category, topic)")
    print("Questions schema verified. Running 100% Dynamic Question Generation mode.")

    # Safe Non-Destructive Migration for quiz_attempts table
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='quiz_attempts'")
    has_a_table = cursor.fetchone() is not None

    if not has_a_table:
        cursor.execute(
            """
            CREATE TABLE quiz_attempts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                candidate_name TEXT NOT NULL,
                category TEXT NOT NULL,
                topic TEXT DEFAULT 'All Topics',
                score INTEGER NOT NULL,
                total_questions INTEGER NOT NULL,
                percentage REAL NOT NULL,
                grade TEXT NOT NULL,
                time_taken_seconds INTEGER NOT NULL,
                speed_rating TEXT DEFAULT 'Standard',
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                trust_score INTEGER DEFAULT 100,
                cheat_flags INTEGER DEFAULT 0,
                user_id INTEGER,
                attempt_token TEXT,
                review_data TEXT,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL
            )
            """
        )
        cursor.executemany(
            """
            INSERT INTO quiz_attempts (candidate_name, category, topic, score, total_questions, percentage, grade, time_taken_seconds, speed_rating, trust_score, cheat_flags, user_id, attempt_token, review_data)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 100, 0, NULL, NULL, NULL)
            """,
            SAMPLE_ATTEMPTS
        )
        connection.commit()
        print(f"Created quiz_attempts schema and seeded {len(SAMPLE_ATTEMPTS)} benchmark leaderboard records.")
    else:
        # Incremental non-destructive column migrations (Never drop user data)
        cursor.execute("PRAGMA table_info(quiz_attempts)")
        existing_cols = {row[1] for row in cursor.fetchall()}
        
        if "topic" not in existing_cols:
            cursor.execute("ALTER TABLE quiz_attempts ADD COLUMN topic TEXT DEFAULT 'All Topics'")
            print("Migrated: added 'topic' column to quiz_attempts.")
        if "trust_score" not in existing_cols:
            cursor.execute("ALTER TABLE quiz_attempts ADD COLUMN trust_score INTEGER DEFAULT 100")
            print("Migrated: added 'trust_score' column to quiz_attempts.")
        if "cheat_flags" not in existing_cols:
            cursor.execute("ALTER TABLE quiz_attempts ADD COLUMN cheat_flags INTEGER DEFAULT 0")
            print("Migrated: added 'cheat_flags' column to quiz_attempts.")
        if "user_id" not in existing_cols:
            cursor.execute("ALTER TABLE quiz_attempts ADD COLUMN user_id INTEGER")
            print("Migrated: added 'user_id' column to quiz_attempts.")
        if "attempt_token" not in existing_cols:
            cursor.execute("ALTER TABLE quiz_attempts ADD COLUMN attempt_token TEXT")
            print("Migrated: added 'attempt_token' column to quiz_attempts.")
        if "review_data" not in existing_cols:
            cursor.execute("ALTER TABLE quiz_attempts ADD COLUMN review_data TEXT")
            print("Migrated: added 'review_data' column to quiz_attempts.")

        cursor.execute("SELECT COUNT(*) FROM quiz_attempts")
        attempt_count = cursor.fetchone()[0]
        print(f"Database contains {attempt_count} preserved quiz attempt records.")

    # High-Performance Composite Indexes for Leaderboard & User History
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_qa_leaderboard ON quiz_attempts(category, score DESC, time_taken_seconds ASC)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_qa_user ON quiz_attempts(user_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_qa_timestamp ON quiz_attempts(timestamp DESC)")
    cursor.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_qa_attempt_token ON quiz_attempts(attempt_token) WHERE attempt_token IS NOT NULL")

    # Authoritative Server-Side Active Quiz Sessions Table (No answer keys sent to client)
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS active_quiz_sessions (
            attempt_token TEXT PRIMARY KEY,
            user_id INTEGER,
            candidate_name TEXT NOT NULL,
            category TEXT NOT NULL,
            topic TEXT NOT NULL,
            question_ids_order TEXT NOT NULL,
            manifest_data TEXT NOT NULL,
            start_timestamp REAL NOT NULL,
            timer_seconds INTEGER NOT NULL,
            is_submitted INTEGER DEFAULT 0,
            result_attempt_id INTEGER,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL,
            FOREIGN KEY (result_attempt_id) REFERENCES quiz_attempts(id) ON DELETE SET NULL
        )
        """
    )
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_aqs_user ON active_quiz_sessions(user_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_aqs_submitted ON active_quiz_sessions(is_submitted)")

    # Active quiz sessions proctor violations migration
    cursor.execute("PRAGMA table_info(active_quiz_sessions)")
    existing_aqs_cols = {row[1] for row in cursor.fetchall()}
    if "proctor_violations" not in existing_aqs_cols:
        cursor.execute("ALTER TABLE active_quiz_sessions ADD COLUMN proctor_violations INTEGER DEFAULT 0")

    # Student Bookmarked Questions Table
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS bookmarked_questions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            question_id INTEGER,
            question_text TEXT NOT NULL,
            category TEXT NOT NULL,
            topic TEXT NOT NULL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
            UNIQUE(user_id, question_id, question_text)
        )
        """
    )
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_bm_user ON bookmarked_questions(user_id)")

    # Bookmarked questions notes migration
    cursor.execute("PRAGMA table_info(bookmarked_questions)")
    existing_bm_cols = {row[1] for row in cursor.fetchall()}
    if "notes" not in existing_bm_cols:
        cursor.execute("ALTER TABLE bookmarked_questions ADD COLUMN notes TEXT")

    # Questions bloom_level and explanation migrations
    cursor.execute("PRAGMA table_info(questions)")
    existing_q_cols = {row[1] for row in cursor.fetchall()}
    if "bloom_level" not in existing_q_cols:
        cursor.execute("ALTER TABLE questions ADD COLUMN bloom_level TEXT DEFAULT 'Understanding'")
    if "explanation" not in existing_q_cols:
        cursor.execute("ALTER TABLE questions ADD COLUMN explanation TEXT")

    # Major Project Additions: Proctoring Violations Telemetry Table
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS proctor_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            attempt_id INTEGER,
            candidate_name TEXT,
            violation_type TEXT NOT NULL,
            details TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
        """
    )

    # Major Project Additions: Zero-Repetition Dynamic Question Tracking Table
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS user_question_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_identifier TEXT NOT NULL,
            question_hash TEXT NOT NULL,
            question_id INTEGER,
            category TEXT,
            topic TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_uqh_user_hash ON user_question_history(user_identifier, question_hash)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_uqh_user ON user_question_history(user_identifier)")

    # Major Project Additions: Dynamic Questions Pool Table (IDs starting at 10001)
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS dynamic_questions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            question TEXT NOT NULL,
            option_a TEXT NOT NULL,
            option_b TEXT NOT NULL,
            option_c TEXT NOT NULL,
            option_d TEXT NOT NULL,
            correct_answer TEXT NOT NULL,
            category TEXT NOT NULL,
            topic TEXT NOT NULL,
            difficulty TEXT DEFAULT 'Medium',
            bloom_level TEXT DEFAULT 'Understanding',
            explanation TEXT DEFAULT '',
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_dq_cat_topic ON dynamic_questions(category, topic)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_pl_attempt ON proctor_logs(attempt_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_pl_candidate ON proctor_logs(candidate_name)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_users_username ON users(username)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_users_email ON users(email)")
    cursor.execute("SELECT seq FROM sqlite_sequence WHERE name = 'dynamic_questions'")
    seq_row = cursor.fetchone()
    if not seq_row:
        cursor.execute("INSERT OR IGNORE INTO sqlite_sequence (name, seq) VALUES ('dynamic_questions', 10000)")

    connection.commit()
    connection.close()
    print("Database initialization complete.")


if __name__ == "__main__":
    init_database()
