"""
=============================================================================
QUIZVERSE MAJOR PROJECT - Security, Architecture & Hardening Test Suite
=============================================================================
Verifies:
1. Open Redirect defense (mitigates malicious continuation URLs)
2. Server-authoritative RBAC enforcement on live database role modification
3. Referential integrity on user deletion (preserves quiz attempts with user_id NULL)
4. Duplicate submission prevention (blocks duplicate records on browser back/reload)
5. Server-authoritative timer policy (flags submissions exceeding timer limit)
6. CSV Formula Injection sanitization (=, +, -, @)
7. Downloadable quiz result export endpoint (/api/quiz/export-result/<id>)
8. Adaptive mistake revision practice mode (/quiz/review-mistakes)
9. Non-destructive database migrations & composite performance indexes
10. CSRF token generation and validation guard
=============================================================================
"""

import unittest
import time
import json
import sqlite3
from urllib.parse import urlparse
from app import app, get_db_connection, DB_PATH
from database.init_db import init_database


class SecurityAndHardeningTestCase(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        init_database()

    def setUp(self):
        app.config["TESTING"] = True
        app.config["WTF_CSRF_ENABLED"] = False
        self.client = app.test_client()

    def test_01_open_redirect_mitigation(self):
        """TEST 1: Malicious continuation URLs are rejected; only safe local paths allowed."""
        # Malicious external redirect attempt
        res_evil = self.client.post("/login?next=https://attacker.com/phishing", data={
            "username": "student",
            "password": "student123"
        }, follow_redirects=False)
        self.assertEqual(res_evil.status_code, 302)
        # Location header must point to internal '/' or '/landing', never external attacker domain
        location = res_evil.headers.get("Location", "")
        parsed = urlparse(location)
        self.assertNotIn("attacker.com", parsed.netloc)
        self.assertIn(parsed.path, ["/", "/landing"])

        self.client.get("/logout")

        # Legitimate internal redirect attempt
        res_safe = self.client.post("/login?next=/leaderboard", data={
            "username": "student",
            "password": "student123"
        }, follow_redirects=False)
        self.assertEqual(res_safe.status_code, 302)
        self.assertIn("/leaderboard", res_safe.headers.get("Location", ""))

        self.client.get("/logout")

    def test_02_server_authoritative_role_verification(self):
        """TEST 2: Role change in database immediately blocks unauthorized access on next request."""
        # 1. Login with faculty credentials
        self.client.post("/login", data={"username": "faculty", "password": "faculty123"}, follow_redirects=True)
        res_ok = self.client.get("/faculty/studio")
        self.assertEqual(res_ok.status_code, 200)

        # 2. Simulate administrator demoting faculty user in database to student
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("UPDATE users SET role = 'student' WHERE username = 'faculty'")
        conn.commit()
        conn.close()

        # 3. Next request to faculty studio must be immediately blocked by server-authoritative check
        res_blocked = self.client.get("/faculty/studio", follow_redirects=True)
        self.assertIn(b"Access restricted to faculty, admin accounts", res_blocked.data)

        # 4. Restore faculty role
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("UPDATE users SET role = 'faculty' WHERE username = 'faculty'")
        conn.commit()
        conn.close()

        self.client.get("/logout")

    def test_03_user_deletion_referential_integrity(self):
        """TEST 3: Deleting a user account sets quiz_attempts.user_id to NULL, preserving student history."""
        conn = get_db_connection()
        cursor = conn.cursor()
        # Create temporary user
        cursor.execute(
            "INSERT INTO users (username, email, password_hash, role) VALUES ('temp_student', 'temp@uni.edu', 'hash', 'student')"
        )
        temp_id = cursor.lastrowid
        # Create an attempt linked to this user
        cursor.execute(
            """
            INSERT INTO quiz_attempts (candidate_name, category, topic, score, total_questions, percentage, grade, time_taken_seconds, user_id)
            VALUES ('temp_student', 'Python', 'Core Logic', 10, 10, 100.0, 'A+', 120, ?)
            """,
            (temp_id,)
        )
        attempt_id = cursor.lastrowid
        conn.commit()
        conn.close()

        # Login as admin to delete temp user
        self.client.post("/login", data={"username": "admin", "password": "admin123"}, follow_redirects=True)
        res_del = self.client.post(f"/admin/user/{temp_id}/delete", follow_redirects=True)
        self.assertEqual(res_del.status_code, 200)

        # Verify attempt still exists but user_id is now NULL
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id, user_id FROM quiz_attempts WHERE id = ?", (attempt_id,))
        row = cursor.fetchone()
        self.assertIsNotNone(row)
        self.assertIsNone(row["user_id"])

        # Clean up temporary test attempt
        cursor.execute("DELETE FROM quiz_attempts WHERE id = ?", (attempt_id,))
        conn.commit()
        conn.close()

        self.client.get("/logout")

    def test_04_duplicate_submission_prevention(self):
        """TEST 4: Submitting the same quiz twice is blocked; browser back button cannot re-submit."""
        # 1. Start a quiz
        self.client.get("/quiz?category=Python&topic=Looping+Statements&candidate_name=DupTester")

        with self.client.session_transaction() as sess:
            manifest = sess.get("quiz_manifest") or {}
            payload = {f"question_{qid}": info["c"] for qid, info in manifest.items()}

        # 2. First submission succeeds
        res_first = self.client.post("/submit", data=payload, follow_redirects=True)
        self.assertEqual(res_first.status_code, 200)
        self.assertIn(b"Quiz Completed!", res_first.data)

        # 3. Second immediate submission attempt is intercepted by duplicate guard
        res_second = self.client.post("/submit", data=payload, follow_redirects=True)
        self.assertEqual(res_second.status_code, 200)
        self.assertTrue(
            b"already been submitted" in res_second.data or b"already submitted" in res_second.data
        )

    def test_05_server_authoritative_timer(self):
        """TEST 5: Submissions taking longer than timer duration + grace period are flagged as Over Time Limit."""
        self.client.get("/quiz?category=Python&topic=Variables&candidate_name=TimerTester")

        with self.client.session_transaction() as sess:
            manifest = sess.get("quiz_manifest") or {}
            payload = {f"question_{qid}": info["c"] for qid, info in manifest.items()}
            # Simulate quiz started 20 minutes ago (well past 5-minute / 300-second timer)
            sess["quiz_start_timestamp"] = time.time() - 1200
            sess["quiz_timer_seconds"] = 300

        res = self.client.post("/submit", data=payload, follow_redirects=True)
        self.assertEqual(res.status_code, 200)
        self.assertIn(b"Over Time Limit", res.data)

    def test_06_csv_formula_injection_sanitization(self):
        """TEST 6: Cells starting with =, +, -, @ are sanitized with leading single-quote in CSV export."""
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO quiz_attempts (candidate_name, category, topic, score, total_questions, percentage, grade, time_taken_seconds)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            ("=cmd|'/C calc'!A0", "C++", "Pointers", 8, 10, 80.0, "A", 150)
        )
        conn.commit()
        conn.close()

        # Login as faculty to download CSV
        self.client.post("/login", data={"username": "faculty", "password": "faculty123"}, follow_redirects=True)
        res_csv = self.client.get("/faculty/export-csv")
        self.assertEqual(res_csv.status_code, 200)

        # In CSV content, the malicious formula must be safely prefixed with single quote
        self.assertIn(b"'=cmd|'/C calc'!A0", res_csv.data)

        self.client.get("/logout")

    def test_07_export_quiz_result_json(self):
        """TEST 7: /api/quiz/export-result/<id> returns verified JSON assessment payload."""
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM quiz_attempts ORDER BY id DESC LIMIT 1")
        row = cursor.fetchone()
        conn.close()
        self.assertIsNotNone(row)
        attempt_id = row["id"]

        res = self.client.get(f"/api/quiz/export-result/{attempt_id}")
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(data["success"])
        report = data["quizverse_assessment_report"]
        self.assertEqual(report["attempt_id"], attempt_id)
        self.assertIn("score", report)
        self.assertIn("grade", report)
        self.assertIn("percentage", report)

    def test_08_review_mistakes_practice_mode(self):
        """TEST 8: /quiz/review-mistakes generates an adaptive practice session from missed questions."""
        # Take a quiz and intentionally answer some incorrectly
        self.client.get("/quiz?category=Python&topic=Functions&candidate_name=MistakeTester")

        with self.client.session_transaction() as sess:
            manifest = sess.get("quiz_manifest") or {}
            # Answer with an incorrect choice for the first question
            payload = {}
            for idx, (qid, info) in enumerate(manifest.items()):
                if idx == 0:
                    payload[f"question_{qid}"] = "Z"  # Incorrect
                else:
                    payload[f"question_{qid}"] = info["c"]

        res_submit = self.client.post("/submit", data=payload, follow_redirects=True)
        self.assertEqual(res_submit.status_code, 200)

        # Launch mistake review drill
        res_review = self.client.get("/quiz/review-mistakes")
        self.assertEqual(res_review.status_code, 200)
        self.assertIn(b"Mistake Revision", res_review.data)
        with self.client.session_transaction() as sess:
            self.assertEqual(sess.get("active_subtopic"), "Mistake Revision Mode")

    def test_09_database_migration_preserves_records_and_indexes(self):
        """TEST 9: init_database() runs idempotently, never drops data, and creates all composite indexes."""
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM quiz_attempts")
        before_count = cursor.fetchone()[0]
        conn.close()

        # Run init_database again
        init_database()

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM quiz_attempts")
        after_count = cursor.fetchone()[0]

        # Count must never decrease
        self.assertEqual(before_count, after_count)

        # Verify composite indexes exist
        cursor.execute("SELECT name FROM sqlite_master WHERE type = 'index'")
        indexes = {r[0] for r in cursor.fetchall()}
        expected_indexes = [
            "idx_qa_leaderboard",
            "idx_qa_user",
            "idx_qa_timestamp",
            "idx_dq_cat_topic",
            "idx_pl_attempt",
            "idx_pl_candidate",
            "idx_uqh_user_hash"
        ]
        for idx in expected_indexes:
            self.assertIn(idx, indexes)

        conn.close()

    def test_10_csrf_protection_validation(self):
        """TEST 10: State-changing form submissions require valid CSRF token when enabled."""
        app.config["TESTING"] = False
        app.config["WTF_CSRF_ENABLED"] = True

        try:
            # 1. POST without CSRF token should be rejected
            res_no_csrf = self.client.post("/login", data={
                "username": "student",
                "password": "student123"
            }, follow_redirects=True)
            self.assertIn(b"Session or security verification token expired", res_no_csrf.data)

            # 2. Extract CSRF token from page session
            with self.client.session_transaction() as sess:
                sess["_csrf_token"] = "valid_secure_csrf_token_12345"

            res_with_csrf = self.client.post("/login", data={
                "username": "student",
                "password": "student123",
                "csrf_token": "valid_secure_csrf_token_12345"
            }, follow_redirects=True)
            self.assertIn(b"Welcome back", res_with_csrf.data)

            self.client.get("/logout")
        finally:
            app.config["TESTING"] = True
            app.config["WTF_CSRF_ENABLED"] = False


if __name__ == "__main__":
    unittest.main()
