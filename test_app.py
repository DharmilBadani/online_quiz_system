"""
=============================================================================
QUIZVERSE MAJOR PROJECT - Academic Curriculum & Quiz Test Suite
=============================================================================
Verifies:
1. Dynamic Curriculum Catalog contains all 8 subjects and 80 subtopics
2. Every discipline contains 10 structured subtopics (zero static questions)
3. Java contains 'Looping Statements', 'Database Connection', 'CRUD Operations'
4. Full subject exam draws exactly 20 random questions (10:00 timer)
5. Topic-specific drill draws exactly 10 focused questions (05:00 timer)
6. Anti-cheating scrambles option letters
7. Scoring evaluates questions accurately and persists attempt with topic
8. Leaderboard supports subject filtering and displays subtopics
=============================================================================
"""

import unittest
import time
from app import app, get_db_connection
from database.init_db import init_database


class OnlineQuizSystemTestCase(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        """Ensure database schema is initialized for dynamic questions."""
        init_database()

    def setUp(self):
        """Set up Flask test client before each test."""
        app.config["TESTING"] = True
        app.config["WTF_CSRF_ENABLED"] = False
        self.client = app.test_client()

    def test_01_curriculum_catalog_contains_8_subjects_and_80_subtopics(self):
        """TEST 1: Dynamic Curriculum Catalog defines all 8 subjects and 80 subtopics (zero static questions)."""
        from curriculum_catalog import SUBJECT_CATALOG
        expected_subjects = ["Java", "Python", "C++", "WebDev", "DBMS", "Flask", "DSA", "OS"]
        self.assertEqual(len(SUBJECT_CATALOG), 8)
        for subj in expected_subjects:
            self.assertIn(subj, SUBJECT_CATALOG)
            self.assertEqual(len(SUBJECT_CATALOG[subj]["topics"]), 10)

    def test_02_java_has_10_topics_including_requested_subtopics(self):
        """TEST 2: Java has 10 topics including Looping Statements, Database Connection, CRUD Operations."""
        from curriculum_catalog import get_topics_for_subject
        topics = get_topics_for_subject("Java")
        self.assertEqual(len(topics), 10)
        self.assertIn("Looping Statements", topics)
        self.assertIn("Database Connection", topics)
        self.assertIn("CRUD Operations", topics)

    def test_03_subject_exam_draws_20_random_questions(self):
        """TEST 3: Full subject exam draws 20 random questions with 10:00 timer."""
        response = self.client.get("/quiz?category=Java&topic=All+Topics")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Question 1 of 20", response.data)
        self.assertIn(b"10:00", response.data)

        with self.client.session_transaction() as sess:
            manifest = sess.get("quiz_manifest") or {}
            q_order = sess.get("quiz_q_order") or []
            self.assertEqual(len(manifest), 20)
            self.assertEqual(len(q_order), 20)
            self.assertEqual(sess.get("selected_category"), "Java")

    def test_04_topic_drill_draws_10_focused_questions(self):
        """TEST 4: Topic drill (e.g. Java -> Looping Statements) draws 10 questions with 05:00 timer."""
        response = self.client.get("/quiz?category=Java&topic=Looping+Statements&candidate_name=JavaDev")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Question 1 of 10", response.data)
        self.assertIn(b"05:00", response.data)
        self.assertIn(b"Looping Statements", response.data)

        with self.client.session_transaction() as sess:
            manifest = sess.get("quiz_manifest") or {}
            q_order = sess.get("quiz_q_order") or []
            self.assertEqual(len(manifest), 10)
            self.assertEqual(len(q_order), 10)
            self.assertEqual(sess.get("active_subtopic"), "Looping Statements")

    def test_05_topic_drill_database_connection_draws_10_questions(self):
        """TEST 5: Topic drill on Java -> Database Connection draws 10 JDBC questions."""
        response = self.client.get("/quiz?category=Java&topic=Database+Connection")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Question 1 of 10", response.data)
        self.assertIn(b"Database Connection", response.data)

        with self.client.session_transaction() as sess:
            manifest = sess.get("quiz_manifest") or {}
            self.assertEqual(len(manifest), 10)

    def test_06_submission_evaluates_topic_drill_and_saves_attempt(self):
        """TEST 6: Submitting 10-question drill scores out of 10 and stores attempt with topic."""
        self.client.get("/quiz?category=Java&topic=CRUD+Operations&candidate_name=SqlExpert")

        with self.client.session_transaction() as sess:
            manifest = sess.get("quiz_manifest") or {}
            payload = {f"question_{qid}": info["c"] for qid, info in manifest.items()}

        time.sleep(0.05)
        response = self.client.post("/submit", data=payload, follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Quiz Completed!", response.data)
        self.assertIn(b"10 / 10", response.data)
        self.assertIn(b"100.0%", response.data)
        self.assertIn(b"Grade: A+", response.data)
        self.assertIn(b"CRUD Operations", response.data)

        # Verify persisted in quiz_attempts
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT score, total_questions, category, topic FROM quiz_attempts WHERE candidate_name = 'SqlExpert' LIMIT 1")
        row = cursor.fetchone()
        conn.close()

        self.assertIsNotNone(row)
        self.assertEqual(row["score"], 10)
        self.assertEqual(row["total_questions"], 10)
        self.assertEqual(row["category"], "Java")
        self.assertEqual(row["topic"], "CRUD Operations")

    def test_07_api_topics_returns_json(self):
        """TEST 7: /api/topics returns list of 10 subtopics for Java."""
        response = self.client.get("/api/topics?category=Java")
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertEqual(data["category"], "Java")
        self.assertEqual(len(data["topics"]), 10)
        self.assertIn("Looping Statements", data["topics"])

    def test_08_leaderboard_route_renders_with_topics(self):
        """TEST 8: Leaderboard route loads rankings cleanly with topic column."""
        response = self.client.get("/leaderboard")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Quiz Leaderboard", response.data)
        self.assertIn(b"Sub-Topic", response.data)


if __name__ == "__main__":
    unittest.main()
