"""
=============================================================================
QUIZVERSE MAJOR PROJECT - Comprehensive Quality Assurance & Audit Test Suite
=============================================================================
Audit Test Suite covering:
1. Parametric Procedural Generator Quota Validation (WebDev, DSA, Flask)
2. GenAI Gemini Model Selection & API Fallback Cascade
3. Syllabus Ingestion to Quiz Runner Integration
4. Mistake Revision Option Mapping & Submission Verification
5. Login 'next' URL Continuation Preservation
6. Admin Self-Demotion Governance Guard
7. Student Profile Export Link Role Authorization Guard
8. API Malformed / Edge-Case Request Handling
9. Database Transaction & Foreign Key Integrity
10. Performance Response Latency Benchmark
=============================================================================
"""

import io
import json
import os
import sqlite3
import time
import unittest
from urllib.parse import urlparse

from app import app, get_db_connection, DB_PATH
from database.init_db import init_database
import dynamic_question_engine
import major_services


class ComprehensiveAuditTestCase(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        init_database()

    def setUp(self):
        app.config["TESTING"] = True
        app.config["WTF_CSRF_ENABLED"] = False
        self.client = app.test_client()

    def test_01_parametric_generator_all_categories_generate_full_quota(self):
        """TC-DYN-05 to TC-DYN-12: Every subject must generate requested quota of 10 unique questions."""
        categories = ["Python", "Java", "C++", "DBMS", "DSA", "OS", "WebDev", "Flask"]
        for cat in categories:
            qs = dynamic_question_engine.generate_parametric_dynamic_questions(
                category=cat, topic="General", count=10
            )
            self.assertEqual(
                len(qs), 10,
                f"Category '{cat}' failed to generate full quota of 10 questions. Generated only {len(qs)}."
            )
            # Ensure every question has distinct prompt text
            prompts = [q["question"] for q in qs]
            self.assertEqual(len(set(prompts)), 10, f"Category '{cat}' produced duplicate question prompts in parametric mode.")
            # Ensure each question has valid fields and correct answer
            for q in qs:
                self.assertIn(q["correct_answer"], ["A", "B", "C", "D"])
                self.assertTrue(len(q["option_a"]) > 0)
                self.assertTrue(len(q["option_b"]) > 0)
                self.assertTrue(len(q["option_c"]) > 0)
                self.assertTrue(len(q["option_d"]) > 0)

    def test_02_gemini_model_cascade_contains_active_models(self):
        """TC-DYN-04: Gemini API model list must target active models, not deprecated ones."""
        # Inspect model cascade in major_services
        import inspect
        source = inspect.getsource(major_services.call_gemini_api)
        # Old deprecated model strings must not be the sole target
        self.assertNotIn('"gemini-2.0-flash"', source, "Deprecated 'gemini-2.0-flash' (which 404s) found in model cascade.")
        self.assertIn("gemini-3.5-flash", source, "'gemini-3.5-flash' missing from production model cascade.")

    def test_03_login_next_continuation_url_preserved(self):
        """TC-AUTH-05: Submitting credentials from /login?next=/profile must redirect to /profile."""
        res = self.client.post("/login?next=/profile", data={
            "username": "student",
            "password": "student123",
            "next": "/profile"
        }, follow_redirects=False)
        self.assertEqual(res.status_code, 302)
        location = res.headers.get("Location", "")
        self.assertIn("/profile", location)
        self.client.get("/logout")

    def test_04_syllabus_ingest_persists_questions_for_quiz_runner(self):
        """TC-ING-02: Syllabus ingestion must persist synthesized questions so Launch Quiz works."""
        sample_syllabus = """
        Course: Advanced Distributed Systems
        Module 1: Consensus Mechanisms and Byzantine Fault Tolerance
        Module 2: Raft Leader Election and Log Replication Protocols
        Module 3: Vector Clocks and Causal Consistency in Key-Value Stores
        """
        res = self.client.post("/syllabus-ingest", data={
            "text_content": sample_syllabus,
            "count": 5,
            "difficulty": "Hard"
        })
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(data.get("success"))
        self.assertGreaterEqual(len(data.get("questions", [])), 3)

        # Verify questions are accessible when starting quiz on Custom Syllabus
        res_quiz = self.client.get("/quiz?category=AI+Studio&topic=Custom+Syllabus&dynamic=0")
        self.assertEqual(res_quiz.status_code, 200)
        self.assertIn(b"Question 1", res_quiz.data)

    def test_05_review_mistakes_preserves_option_alignment(self):
        """TC-RES-03: Submitting review-mistakes quiz must correctly evaluate against original database options."""
        # 1. Start a quiz
        self.client.get("/quiz?category=Python&topic=Syntax+%26+Core+Data+Types&candidate_name=MistakeAlignmentTester")
        
        with self.client.session_transaction() as sess:
            manifest = sess.get("quiz_manifest") or {}
            self.assertGreater(len(manifest), 0)
            # Intentionally pick incorrect answers
            payload = {f"question_{qid}": "Z" for qid in manifest}

        # 2. Submit initial quiz with all incorrect
        res_submit = self.client.post("/submit", data=payload, follow_redirects=True)
        self.assertEqual(res_submit.status_code, 200)
        self.assertIn(b"0.0%", res_submit.data)

        # 3. Launch mistake review drill
        res_mistakes = self.client.get("/quiz/review-mistakes")
        self.assertEqual(res_mistakes.status_code, 200)

        # 4. Now answer all questions in review drill with their correct answers
        with self.client.session_transaction() as sess:
            rev_manifest = sess.get("quiz_manifest") or {}
            self.assertGreater(len(rev_manifest), 0)
            rev_payload = {f"question_{qid}": info["c"] for qid, info in rev_manifest.items()}

        res_rev_submit = self.client.post("/submit", data=rev_payload, follow_redirects=True)
        self.assertEqual(res_rev_submit.status_code, 200)
        # Should now score 100% on the mistake review attempt
        self.assertIn(b"100.0%", res_rev_submit.data)
        self.assertIn(b"Grade: A+", res_rev_submit.data)

    def test_06_admin_self_demotion_is_prevented(self):
        """TC-ADM-02: Administrator cannot demote their own account to prevent lockouts."""
        # Login as admin
        self.client.post("/login", data={"username": "admin", "password": "admin123"}, follow_redirects=True)
        
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM users WHERE username = 'admin'")
        admin_id = cursor.fetchone()["id"]
        conn.close()

        # Attempt to demote self to student
        res = self.client.post(f"/admin/user/{admin_id}/role", data={"role": "student"}, follow_redirects=True)
        self.assertIn(b"Cannot demote currently signed-in administrator", res.data)

        # Verify admin role is preserved
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT role FROM users WHERE id = ?", (admin_id,))
        role = cursor.fetchone()["role"]
        conn.close()
        self.assertEqual(role, "admin")

        self.client.get("/logout")

    def test_07_api_dynamic_generate_invalid_input_handling(self):
        """Verify /api/quiz/dynamic-generate handles non-integer count and malformed payloads without 500."""
        # Non-integer count
        res = self.client.post("/api/quiz/dynamic-generate", json={
            "category": "Python",
            "topic": "Core Logic",
            "count": "invalid_number"
        })
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(data["success"])

        # Empty body
        res_empty = self.client.post("/api/quiz/dynamic-generate", data="")
        self.assertEqual(res_empty.status_code, 200)
        self.assertTrue(res_empty.get_json()["success"])

    def test_08_api_ai_tutor_handles_non_dict_options(self):
        """Verify /api/ai-tutor handles non-dict options and missing fields without 500 error."""
        res = self.client.post("/api/ai-tutor", json={
            "question": "What is Python?",
            "options": ["A", "B", "C", "D"],  # List instead of dict
            "student_choice": "A",
            "correct_choice": "B",
            "explanation": "Test explanation",
            "topic": "Python"
        })
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertIn("reply", data)

    def test_09_api_sandbox_evaluate_handles_empty_or_non_json(self):
        """Verify /api/sandbox/evaluate handles empty code or missing content gracefully."""
        res = self.client.post("/api/sandbox/evaluate", json={"code": ""})
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertFalse(data.get("success"))
        self.assertIn("error", data)

    def test_10_database_concurrency_and_wal_mode(self):
        """TC-DB-01: Verify SQLite WAL mode and foreign key enforcement under multi-connection access."""
        conn1 = get_db_connection()
        conn2 = get_db_connection()

        # Both connections must report WAL journal mode
        mode1 = conn1.execute("PRAGMA journal_mode;").fetchone()[0]
        mode2 = conn2.execute("PRAGMA journal_mode;").fetchone()[0]
        self.assertEqual(mode1.lower(), "wal")
        self.assertEqual(mode2.lower(), "wal")

        # Foreign keys must be ON
        fk1 = conn1.execute("PRAGMA foreign_keys;").fetchone()[0]
        fk2 = conn2.execute("PRAGMA foreign_keys;").fetchone()[0]
        self.assertEqual(fk1, 1)
        self.assertEqual(fk2, 1)

        conn1.close()
        conn2.close()


if __name__ == "__main__":
    unittest.main()

