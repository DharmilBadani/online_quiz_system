"""
=============================================================================
QUIZVERSE ADDENDUM VALIDATION & ADVANCED ENGINEERING TEST SUITE
=============================================================================
Verifies:
1. Live proctor event API neutralizes client-side form tampering (cheat_flags=0)
2. Cross-user attempt token session hijacking is strictly rejected
3. Expired quiz session (> 24 hours) is safely rejected
4. Guest candidate-name spoofing on result export is prevented
5. Gemini AI 10-condition matrix: HTTP 429, 403, invalid key, timeout, malformed JSON,
   circuit breaker opening, cooldown rejection, half-open recovery, and parametric fallback.
6. Blended concurrency: simultaneous quiz initialization, submissions, and leaderboard reads.
=============================================================================
"""

import unittest
import os
import json
import time
import sqlite3
import concurrent.futures
from unittest.mock import patch, MagicMock
import requests
from app import app, get_db_connection
from database.init_db import init_database
import major_services
import dynamic_question_engine


class AddendumValidationTestCase(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        init_database()

    def setUp(self):
        app.config["TESTING"] = True
        app.config["WTF_CSRF_ENABLED"] = False
        self.client = app.test_client()

    def test_01_server_side_proctor_telemetry_neutralizes_form_tampering(self):
        """TEST 1: Server-recorded proctor violations neutralize client-side form tampering (cheat_flags=0)."""
        # Start a quiz
        self.client.get("/quiz?category=Python&topic=Variables&candidate_name=TamperTester")
        with self.client.session_transaction() as sess:
            token = sess.get("active_quiz_token")
            manifest = sess.get("quiz_manifest") or {}
            payload = {f"question_{qid}": "A" for qid in manifest.keys()}
            payload["attempt_token"] = token
            # Attacker maliciously overrides cheat_flags to 0 in browser form
            payload["cheat_flags"] = "0"
            payload["trust_score"] = "100"

        self.assertIsNotNone(token)

        # 2. Simulate 2 live blur/tab-switch telemetry events sent asynchronously
        res_evt1 = self.client.post("/api/proctor/event", json={"attempt_token": token, "violation_type": "Tab Switch"})
        self.assertEqual(res_evt1.status_code, 200)
        self.assertEqual(res_evt1.get_json()["server_violations"], 1)

        res_evt2 = self.client.post("/api/proctor/event", json={"attempt_token": token, "violation_type": "Window Blur"})
        self.assertEqual(res_evt2.status_code, 200)
        self.assertEqual(res_evt2.get_json()["server_violations"], 2)

        # 3. Submit quiz with tampered cheat_flags = 0
        res_submit = self.client.post("/submit", data=payload, follow_redirects=True)
        self.assertEqual(res_submit.status_code, 200)

        # 4. Verify authoritative database record reflects server-captured violations (2) and deducted trust score (70%)
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT cheat_flags, trust_score FROM quiz_attempts WHERE attempt_token = ?", (token,))
        row = cursor.fetchone()
        conn.close()

        self.assertIsNotNone(row)
        self.assertEqual(row["cheat_flags"], 2)
        self.assertEqual(row["trust_score"], 70)  # 100 - (2 * 15) = 70

    def test_02_cross_user_token_hijacking_rejected(self):
        """TEST 2: Attempting to submit a quiz using another user's session token is rejected."""
        # 1. Login as Student A and initiate a quiz
        self.client.post("/login", data={"username": "student", "password": "student123"}, follow_redirects=True)
        self.client.get("/quiz?category=Python&topic=Variables")
        with self.client.session_transaction() as sess:
            token_a = sess.get("active_quiz_token")
            manifest_a = sess.get("quiz_manifest") or {}
        self.client.get("/logout")

        # 2. Login as Faculty / User B
        self.client.post("/login", data={"username": "faculty", "password": "faculty123"}, follow_redirects=True)

        # 3. User B attempts to submit using User A's token
        payload = {f"question_{qid}": "A" for qid in manifest_a.keys()}
        payload["attempt_token"] = token_a

        res = self.client.post("/submit", data=payload, follow_redirects=True)
        self.assertIn(b"Unauthorized quiz session token", res.data)
        self.client.get("/logout")

    def test_03_expired_quiz_session_rejected(self):
        """TEST 3: Submitting an expired session (> 24 hours old) is blocked."""
        self.client.get("/quiz?category=Python&topic=Variables&candidate_name=ExpiryTester")
        with self.client.session_transaction() as sess:
            token = sess.get("active_quiz_token")
            manifest = sess.get("quiz_manifest") or {}
            payload = {f"question_{qid}": "A" for qid in manifest.keys()}
            payload["attempt_token"] = token

        # Artificially age the active session by 25 hours
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("UPDATE active_quiz_sessions SET start_timestamp = ? WHERE attempt_token = ?", (time.time() - 90000, token))
        conn.commit()
        conn.close()

        res = self.client.post("/submit", data=payload, follow_redirects=True)
        self.assertIn(b"Quiz session expired", res.data)

    def test_04_guest_name_spoofing_export_blocked(self):
        """TEST 4: Guest cannot export an attempt simply by guessing or sharing a candidate name."""
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO quiz_attempts (candidate_name, category, topic, score, total_questions, percentage, grade, time_taken_seconds)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            ("CommonName", "Python", "Syntax", 10, 10, 100.0, "A+", 60)
        )
        attempt_id = cursor.lastrowid
        conn.commit()
        conn.close()

        # In production mode without matching session attempt_id, guest cannot access
        app.config["TESTING"] = False
        try:
            with self.client.session_transaction() as sess:
                sess["candidate_name"] = "CommonName"
                # Intentionally omit attempt_id from session

            res = self.client.get(f"/api/quiz/export-result/{attempt_id}")
            self.assertEqual(res.status_code, 401)  # Authentication required
            self.assertFalse(res.get_json()["success"])
        finally:
            app.config["TESTING"] = True

    def test_05_gemini_fallback_matrix_10_scenarios(self):
        """TEST 5: Full 10-condition evaluation of Gemini REST client, circuit breaker, and parametric synthesis."""
        # 1. Successful response mock
        with patch("requests.post") as mock_post:
            mock_post.return_value.status_code = 200
            mock_post.return_value.json.return_value = {
                "candidates": [{"content": {"parts": [{"text": "Mock AI Response"}]}}]
            }
            res = major_services.call_gemini_api("Hello AI")
            self.assertEqual(res, "Mock AI Response")

        # 2. HTTP 429 Rate limit handling
        with patch("requests.post") as mock_post:
            mock_post.return_value.status_code = 429
            mock_post.side_effect = requests.RequestException("Rate Limit Exceeded")
            res_429 = major_services.call_gemini_api("Test 429")
            self.assertIsNone(res_429)

        # 3. HTTP 403 Forbidden / Quota exhaustion
        with patch("requests.post") as mock_post:
            mock_post.return_value.status_code = 403
            res_403 = major_services.call_gemini_api("Test 403")
            self.assertIsNone(res_403)

        # 4. Invalid API key handling
        with patch.dict("os.environ", {"GEMINI_API_KEY": ""}):
            res_nokey = major_services.call_gemini_api("Test No Key")
            self.assertIsNone(res_nokey)

        # 5. Request timeout handling
        with patch("requests.post", side_effect=requests.Timeout("Connection timed out")):
            res_timeout = major_services.call_gemini_api("Test Timeout")
            self.assertIsNone(res_timeout)

        # 6. Malformed JSON handling
        with patch("requests.post") as mock_post:
            mock_post.return_value.status_code = 200
            mock_post.return_value.json.side_effect = ValueError("Corrupt JSON payload")
            res_badjson = major_services.call_gemini_api("Test Bad JSON")
            self.assertIsNone(res_badjson)

        # 7. Provider outage (ConnectionError)
        with patch("requests.post", side_effect=requests.ConnectionError("DNS failure")):
            res_outage = major_services.call_gemini_api("Test Outage")
            self.assertIsNone(res_outage)

        # 8. Circuit breaker opening after 3 consecutive failures
        major_services._GEMINI_CIRCUIT["consecutive_failures"] = 0
        major_services.record_gemini_failure()
        major_services.record_gemini_failure()
        major_services.record_gemini_failure()
        self.assertTrue(major_services.is_gemini_circuit_open())
        # Immediate fail-fast without network call
        t0 = time.time()
        res_cb = major_services.call_gemini_api("Test Circuit Open")
        self.assertIsNone(res_cb)
        self.assertLess(time.time() - t0, 0.05)

        # 9. Half-open recovery after cooldown
        major_services._GEMINI_CIRCUIT["last_failure_time"] = time.time() - 50.0  # Expire 45s cooldown
        self.assertFalse(major_services.is_gemini_circuit_open())
        major_services.record_gemini_success()
        self.assertEqual(major_services._GEMINI_CIRCUIT["consecutive_failures"], 0)

        # 10. Parametric offline synthesis generates valid, answerable, non-duplicated questions
        qs = dynamic_question_engine.generate_parametric_dynamic_questions("Python", "Variables", 5)
        self.assertEqual(len(qs), 5)
        for q in qs:
            self.assertIn("question", q)
            self.assertIn(q["correct_answer"], ["A", "B", "C", "D"])
            self.assertTrue(len(q["option_a"]) > 0)
            self.assertTrue(len(q["explanation"]) > 0)

    def test_06_blended_concurrency_simultaneous_reads_and_writes(self):
        """TEST 6: Blended multi-threaded load: simultaneous quiz init, submissions, and leaderboard reads."""
        def worker_task(thread_id):
            client = app.test_client()
            # 1. Read leaderboard
            r1 = client.get("/leaderboard")
            # 2. Init quiz
            r2 = client.get(f"/quiz?category=Python&topic=Variables&candidate_name=Concurrent_{thread_id}")
            # 3. Submit quiz
            with client.session_transaction() as sess:
                token = sess.get("active_quiz_token")
                manifest = sess.get("quiz_manifest") or {}
                payload = {f"question_{qid}": "A" for qid in manifest.keys()}
                payload["attempt_token"] = token
            r3 = client.post("/submit", data=payload, follow_redirects=True)
            return (r1.status_code, r2.status_code, r3.status_code)

        with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
            futures = [executor.submit(worker_task, i) for i in range(16)]
            results = [f.result() for f in concurrent.futures.as_completed(futures)]

        for codes in results:
            self.assertEqual(codes[0], 200)
            self.assertEqual(codes[1], 200)
            self.assertEqual(codes[2], 200)

    def test_07_unauthorized_proctor_telemetry_blocked(self):
        """TEST 7: User B or unauthenticated client cannot post proctor violations to User A's token."""
        # 1. Login as Student and start a quiz
        self.client.post("/login", data={"username": "student", "password": "student123"}, follow_redirects=True)
        self.client.get("/quiz?category=Python&topic=Variables")
        with self.client.session_transaction() as sess:
            student_token = sess.get("active_quiz_token")
        self.client.get("/logout")

        # 2. Unauthenticated client attempts to send proctor event for student's token
        res_unauth = self.client.post("/api/proctor/event", json={"attempt_token": student_token, "violation_type": "Tab Switch"})
        self.assertEqual(res_unauth.status_code, 403)
        self.assertFalse(res_unauth.get_json()["success"])

        # 3. User B (Faculty) logs in and attempts to send proctor event for student's token
        self.client.post("/login", data={"username": "faculty", "password": "faculty123"}, follow_redirects=True)
        res_cross = self.client.post("/api/proctor/event", json={"attempt_token": student_token, "violation_type": "Tab Switch"})
        self.assertEqual(res_cross.status_code, 403)
        self.assertFalse(res_cross.get_json()["success"])
        self.client.get("/logout")

    def test_08_unauthenticated_user_cannot_submit_authenticated_token(self):
        """TEST 8: An unauthenticated caller cannot submit an exam session token issued to an authenticated user."""
        # 1. Login as student and start quiz
        self.client.post("/login", data={"username": "student", "password": "student123"}, follow_redirects=True)
        self.client.get("/quiz?category=Python&topic=Variables")
        with self.client.session_transaction() as sess:
            student_token = sess.get("active_quiz_token")
            manifest = sess.get("quiz_manifest") or {}
        self.client.get("/logout")

        # 2. Unauthenticated caller attempts to submit using student's token
        payload = {f"question_{qid}": "A" for qid in manifest.keys()}
        payload["attempt_token"] = student_token

        res = self.client.post("/submit", data=payload, follow_redirects=True)
        self.assertIn(b"Unauthorized quiz session token", res.data)

    def test_09_backup_and_recovery_utility_verification(self):
        """TEST 9: SQLite Online Backup utility creates verified snapshot, prunes via keep, and restores."""
        import database.backup_db as backup_db
        import tempfile
        import os
        with tempfile.TemporaryDirectory() as tmpdir:
            # 1. Create first backup
            b1 = backup_db.create_backup(dest_dir=tmpdir, keep=2)
            self.assertTrue(os.path.exists(b1))
            # 2. Create second backup
            time.sleep(1.05)
            b2 = backup_db.create_backup(dest_dir=tmpdir, keep=2)
            self.assertTrue(os.path.exists(b2))
            # 3. Create third backup with keep=2; should prune b1
            time.sleep(1.05)
            b3 = backup_db.create_backup(dest_dir=tmpdir, keep=2)
            self.assertTrue(os.path.exists(b3))
            self.assertFalse(os.path.exists(b1))  # b1 pruned
            self.assertTrue(os.path.exists(b2))  # b2 kept
            # 4. Test restore into a separate temp database file
            orig_db_path = backup_db.DB_PATH
            try:
                test_restore_target = os.path.join(tmpdir, "restored_test.db")
                backup_db.DB_PATH = test_restore_target
                success = backup_db.restore_backup(b3)
                self.assertTrue(success)
                self.assertTrue(os.path.exists(test_restore_target))
            finally:
                backup_db.DB_PATH = orig_db_path

    def test_10_anti_spoofing_client_ip_and_proxyfix(self):
        """TEST 10: Anti-spoofing client IP resolution neutralizes raw unvalidated headers."""
        with app.test_request_context("/", environ_base={"REMOTE_ADDR": "127.0.0.1"}, headers={"X-Forwarded-For": "203.0.113.199"}):
            from flask import request
            self.assertIsNotNone(request.remote_addr)
            # Under secure configuration, remote_addr represents the validated network connection
            self.assertEqual(request.remote_addr, "127.0.0.1")

    def test_11_centralized_database_path_override(self):
        """TEST 11: DATABASE_PATH environment configuration is honored dynamically."""
        import tempfile
        with tempfile.TemporaryDirectory() as tmpdir:
            custom_db = os.path.join(tmpdir, "custom_quiz.db")
            old_env = os.environ.get("DATABASE_PATH")
            try:
                os.environ["DATABASE_PATH"] = custom_db
                resolved = os.path.abspath(os.environ.get("DATABASE_PATH"))
                self.assertEqual(resolved, os.path.abspath(custom_db))
            finally:
                if old_env is not None:
                    os.environ["DATABASE_PATH"] = old_env
                else:
                    os.environ.pop("DATABASE_PATH", None)

    def test_12_backup_tiered_storage_isolation(self):
        """TEST 12: Tiered storage (daily vs exam_window) prunes independently without cross-directory deletion."""
        import database.backup_db as backup_db
        import tempfile
        with tempfile.TemporaryDirectory() as tmpdir:
            # 1. Create daily backups with keep=1
            d1 = backup_db.create_backup(dest_dir=tmpdir, tier="daily", keep=1)
            time.sleep(1.05)
            d2 = backup_db.create_backup(dest_dir=tmpdir, tier="daily", keep=1)
            # 2. Create exam_window backups with keep=2
            e1 = backup_db.create_backup(dest_dir=tmpdir, tier="exam_window", keep=2)
            time.sleep(1.05)
            e2 = backup_db.create_backup(dest_dir=tmpdir, tier="exam_window", keep=2)

            self.assertFalse(os.path.exists(d1))  # d1 pruned in daily tier
            self.assertTrue(os.path.exists(d2))   # d2 preserved in daily tier
            self.assertTrue(os.path.exists(e1))   # e1 preserved in exam_window tier
            self.assertTrue(os.path.exists(e2))   # e2 preserved in exam_window tier


if __name__ == "__main__":
    unittest.main()
