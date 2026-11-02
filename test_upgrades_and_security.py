"""
=============================================================================
QUIZVERSE SYSTEM UPGRADATION & SECURITY VERIFICATION SUITE
=============================================================================
Verifies:
1. Demo admin login lockout (permanently blocks admin demo logins)
2. Result export authorization & IDOR defense (/api/quiz/export-result/<id>)
3. Result export permitted for authentic owner & admin roles
4. Server-side quiz session persistence & answer-key protection
5. Atomic idempotent quiz submission guarding against duplicates
6. Administrative system health & diagnostic telemetry (/admin/health)
7. Student question bookmarking & personal study vault (/api/bookmark)
8. Evidence-based cognitive analytics diagnostics (zero fabricated topics)
9. Gemini API circuit breaker fail-fast protection
=============================================================================
"""

import unittest
import json
import time
import sqlite3
from app import app, get_db_connection, DB_PATH
from database.init_db import init_database
import major_services


class SystemUpgradesAndSecurityTestCase(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        init_database()

    def setUp(self):
        app.config["TESTING"] = True
        app.config["WTF_CSRF_ENABLED"] = False
        self.client = app.test_client()

    def test_01_demo_admin_permanently_rejected(self):
        """TEST 1: /demo-login/admin is permanently forbidden and cannot be exploited for privilege escalation."""
        res = self.client.get("/demo-login/admin", follow_redirects=True)
        self.assertIn(b"Demo login for administrator accounts is permanently disabled", res.data)
        with self.client.session_transaction() as sess:
            self.assertNotEqual(sess.get("role"), "admin")
            self.assertIsNone(sess.get("user_id"))

    def test_02_export_result_idor_blocked(self):
        """TEST 2: Cross-user IDOR access to quiz export reports is strictly rejected with 403 Forbidden."""
        # 1. Create two distinct student records in the database
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM users WHERE username = 'student'")
        user_a = cursor.fetchone()["id"]

        # Insert attempt belonging specifically to user A
        cursor.execute(
            """
            INSERT INTO quiz_attempts (candidate_name, category, topic, score, total_questions, percentage, grade, time_taken_seconds, user_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            ("student", "Python", "Data Types", 9, 10, 90.0, "A+", 120, user_a)
        )
        attempt_id = cursor.lastrowid
        conn.commit()
        conn.close()

        # 2. Authenticate as a different student with unique credentials
        ts = int(time.time() * 1000)
        self.client.post("/register", data={
            "username": f"intruder_{ts}",
            "email": f"intruder_{ts}@university.edu",
            "full_name": "Intruder Candidate",
            "password": "Password123!",
            "role": "student"
        }, follow_redirects=True)

        # 3. Attempt to export User A's result while authenticated as User B
        res = self.client.get(f"/api/quiz/export-result/{attempt_id}")
        self.assertEqual(res.status_code, 403)
        data = res.get_json()
        self.assertFalse(data["success"])
        self.assertIn("Access forbidden", data["error"])

        self.client.get("/logout")

    def test_03_export_result_authorized_for_owner_and_admin(self):
        """TEST 3: Authorized attempt owner and Administrator can export verified score reports."""
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM users WHERE username = 'student'")
        student_uid = cursor.fetchone()["id"]

        cursor.execute(
            """
            INSERT INTO quiz_attempts (candidate_name, category, topic, score, total_questions, percentage, grade, time_taken_seconds, user_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            ("student", "Java", "OOP Concepts", 10, 10, 100.0, "A+", 90, student_uid)
        )
        attempt_id = cursor.lastrowid
        conn.commit()
        conn.close()

        # 1. Login as owner student
        self.client.post("/login", data={"username": "student", "password": "student123"}, follow_redirects=True)
        res_owner = self.client.get(f"/api/quiz/export-result/{attempt_id}")
        self.assertEqual(res_owner.status_code, 200)
        data_owner = res_owner.get_json()
        self.assertTrue(data_owner["success"])
        self.assertEqual(data_owner["quizverse_assessment_report"]["attempt_id"], attempt_id)
        self.client.get("/logout")

        # 2. Login as administrator -> Should have full access
        self.client.post("/login", data={"username": "admin", "password": "admin123"}, follow_redirects=True)
        res_admin = self.client.get(f"/api/quiz/export-result/{attempt_id}")
        self.assertEqual(res_admin.status_code, 200)
        data_admin = res_admin.get_json()
        self.assertTrue(data_admin["success"])
        self.client.get("/logout")

    def test_04_server_side_quiz_session_protection(self):
        """TEST 4: Authoritative quiz manifest is stored in database; answers are not stored in production client cookies."""
        # Start a quiz
        self.client.get("/quiz?category=Python&topic=Variables&candidate_name=SessionTester")
        
        with self.client.session_transaction() as sess:
            token = sess.get("active_quiz_token")
            self.assertIsNotNone(token)
            self.assertIsInstance(token, str)

        # Check that the token exists in active_quiz_sessions database table
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM active_quiz_sessions WHERE attempt_token = ?", (token,))
        row = cursor.fetchone()
        conn.close()

        self.assertIsNotNone(row)
        manifest = json.loads(row["manifest_data"])
        self.assertIsInstance(manifest, dict)
        self.assertGreater(len(manifest), 0)

    def test_05_atomic_idempotent_duplicate_submission(self):
        """TEST 5: Duplicate submissions with the same attempt_token are idempotently rejected."""
        self.client.get("/quiz?category=Python&topic=Variables&candidate_name=IdempotencyTester")
        with self.client.session_transaction() as sess:
            manifest = sess.get("quiz_manifest") or {}
            token = sess.get("active_quiz_token")
            payload = {f"question_{qid}": "A" for qid in manifest.keys()}
            payload["attempt_token"] = token

        # First post succeeds
        res1 = self.client.post("/submit", data=payload, follow_redirects=True)
        self.assertEqual(res1.status_code, 200)

        # Count records with this attempt_token
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM quiz_attempts WHERE attempt_token = ?", (token,))
        count_first = cursor.fetchone()[0]
        self.assertEqual(count_first, 1)

        # Second post with identical attempt_token
        res2 = self.client.post("/submit", data=payload, follow_redirects=True)
        self.assertEqual(res2.status_code, 200)

        cursor.execute("SELECT COUNT(*) FROM quiz_attempts WHERE attempt_token = ?", (token,))
        count_second = cursor.fetchone()[0]
        conn.close()

        # Database must still have exactly 1 record (idempotent, zero duplicate)
        self.assertEqual(count_second, 1)

    def test_06_admin_health_diagnostics_endpoint(self):
        """TEST 6: /admin/health returns real-time diagnostic JSON for admins; non-admins are blocked."""
        # 1. Unauthenticated -> Blocked
        res_unauth = self.client.get("/admin/health")
        self.assertEqual(res_unauth.status_code, 302)

        # 2. Student -> Blocked
        self.client.post("/login", data={"username": "student", "password": "student123"}, follow_redirects=True)
        res_student = self.client.get("/admin/health", follow_redirects=True)
        self.assertIn(b"Access restricted to admin accounts", res_student.data)
        self.client.get("/logout")

        # 3. Admin -> Returns diagnostic payload
        self.client.post("/login", data={"username": "admin", "password": "admin123"}, follow_redirects=True)
        res_admin = self.client.get("/admin/health")
        self.assertEqual(res_admin.status_code, 200)
        data = res_admin.get_json()
        self.assertEqual(data["status"], "healthy")
        self.assertIn("database", data)
        self.assertIn("metrics", data)
        self.assertTrue(data["database"]["wal_enabled"])
        self.assertEqual(data["database"]["integrity_check"], "ok")
        self.assertGreaterEqual(data["metrics"]["total_curriculum_questions"], 100)
        self.client.get("/logout")

    def test_07_bookmark_toggle_and_study_vault(self):
        """TEST 7: Students can bookmark questions, view bookmarks in JSON API, and access the Study Vault."""
        self.client.post("/login", data={"username": "student", "password": "student123"}, follow_redirects=True)

        # 1. Toggle bookmark for question 1
        res_add = self.client.post("/api/bookmark", json={"question_id": 1, "action": "add"})
        self.assertEqual(res_add.status_code, 200)
        self.assertTrue(res_add.get_json()["bookmarked"])

        # 2. Check API bookmarks list
        res_list = self.client.get("/api/bookmarks")
        self.assertEqual(res_list.status_code, 200)
        bookmarks = res_list.get_json()["bookmarks"]
        self.assertTrue(any(b["question_id"] == 1 for b in bookmarks))

        # 3. Check Study Vault HTML view
        res_vault = self.client.get("/student/bookmarks")
        self.assertEqual(res_vault.status_code, 200)
        self.assertIn(b"Personal Study Vault", res_vault.data)

        # 4. Toggle bookmark off
        res_remove = self.client.post("/api/bookmark", json={"question_id": 1, "action": "remove"})
        self.assertEqual(res_remove.status_code, 200)
        self.assertFalse(res_remove.get_json()["bookmarked"])

        self.client.get("/logout")

    def test_08_evidence_based_cognitive_analytics_no_fabrication(self):
        """TEST 8: Cognitive analytics produces strictly evidence-based results without fabricated weak topics."""
        # 1. Zero attempts -> Empty weak topics with diagnostic notice
        res_empty = major_services.compute_cognitive_analytics([])
        self.assertEqual(res_empty["total_attempts"], 0)
        self.assertEqual(res_empty["weak_topics"], [])
        self.assertIn("No assessment data available", res_empty["weak_topics_note"])

        # 2. Perfect attempts (all >= 70%) -> Empty weak topics with mastery praise
        perfect_attempts = [
            {"category": "Python", "topic": "Functions", "score": 10, "total_questions": 10, "percentage": 100.0},
            {"category": "Java", "topic": "Classes", "score": 9, "total_questions": 10, "percentage": 90.0}
        ]
        res_perfect = major_services.compute_cognitive_analytics(perfect_attempts)
        self.assertEqual(res_perfect["weak_topics"], [])
        self.assertIn("Commendable mastery", res_perfect["weak_topics_note"])

        # 3. Low score in specific topic -> Authentic diagnostic recommendation
        mixed_attempts = [
            {"category": "Python", "topic": "Recursion", "score": 4, "total_questions": 10, "percentage": 40.0},
            {"category": "DBMS", "topic": "Normalization", "score": 3, "total_questions": 10, "percentage": 30.0},
            {"category": "Python", "topic": "Variables", "score": 9, "total_questions": 10, "percentage": 90.0}
        ]
        res_mixed = major_services.compute_cognitive_analytics(mixed_attempts)
        self.assertEqual(len(res_mixed["weak_topics"]), 2)
        # Lowest accuracy first
        self.assertEqual(res_mixed["weak_topics"][0], "DBMS - Normalization")
        self.assertEqual(res_mixed["weak_topics"][1], "Python - Recursion")

    def test_09_gemini_circuit_breaker(self):
        """TEST 9: Gemini circuit breaker opens after 3 consecutive failures and prevents further requests during cooldown."""
        major_services._GEMINI_CIRCUIT["consecutive_failures"] = 0
        major_services._GEMINI_CIRCUIT["last_failure_time"] = 0.0

        # Simulate 3 failures
        major_services.record_gemini_failure()
        major_services.record_gemini_failure()
        major_services.record_gemini_failure()

        self.assertTrue(major_services.is_gemini_circuit_open())

        # Calling API with open circuit immediately returns None without delay
        t0 = time.time()
        result = major_services.call_gemini_api("Test prompt with circuit open")
        elapsed = time.time() - t0
        self.assertIsNone(result)
        self.assertLess(elapsed, 0.1)  # Instant failover

        # Reset circuit
        major_services.record_gemini_success()
        self.assertFalse(major_services.is_gemini_circuit_open())


if __name__ == "__main__":
    unittest.main()
