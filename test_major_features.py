"""
=============================================================================
QUIZVERSE MAJOR PROJECT - Comprehensive Automated Test Suite
=============================================================================
Verifies:
1. User Authentication (Login, Register, Session context, Logout)
2. GenAI Question & Syllabus Synthesizer endpoint (/ai-generator)
3. Faculty Authoring Studio & CSV Audit Export (/faculty/studio, /faculty/export-csv)
4. Real-Time 1v1 Battle Arena endpoint (/arena)
5. Cognitive Analytics & Bloom's Taxonomy engine (/analytics)
6. AI Proctoring Telemetry persistence (trust_score, cheat_flags, proctor_logs)
=============================================================================
"""

import unittest
import time
from app import app, get_db_connection
from database.init_db import init_database
import dynamic_question_engine


class MajorProjectTestCase(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        init_database()

    def setUp(self):
        app.config["TESTING"] = True
        app.config["WTF_CSRF_ENABLED"] = False
        self.client = app.test_client()

    def test_01_user_login_student_and_faculty(self):
        """TEST 1: User can authenticate with student and faculty credentials."""
        # 1. Login with student
        res = self.client.post("/login", data={"username": "student", "password": "student123"}, follow_redirects=True)
        self.assertEqual(res.status_code, 200)
        with self.client.session_transaction() as sess:
            self.assertEqual(sess.get("username"), "student")
            self.assertEqual(sess.get("role"), "student")

        # 2. Logout
        res = self.client.get("/logout", follow_redirects=True)
        self.assertEqual(res.status_code, 200)
        with self.client.session_transaction() as sess:
            self.assertIsNone(sess.get("user_id"))

        # 3. Login with faculty
        res = self.client.post("/login", data={"username": "faculty", "password": "faculty123"}, follow_redirects=True)
        self.assertEqual(res.status_code, 200)
        with self.client.session_transaction() as sess:
            self.assertEqual(sess.get("username"), "faculty")
            self.assertEqual(sess.get("role"), "faculty")

    def test_02_user_registration(self):
        """TEST 2: New candidate can register an institutional student account."""
        unique_user = f"scholar_{int(time.time())}"
        res = self.client.post("/register", data={
            "username": unique_user,
            "email": f"{unique_user}@university.edu",
            "full_name": "Test Scholar",
            "password": "pass1234Secure",
            "role": "student"
        }, follow_redirects=True)
        self.assertEqual(res.status_code, 200)

        with self.client.session_transaction() as sess:
            self.assertEqual(sess.get("username"), unique_user)
            self.assertEqual(sess.get("role"), "student")

    def test_03_ai_generator_endpoint(self):
        """TEST 3: GenAI Question Synthesizer generates questions with Bloom's taxonomy."""
        res = self.client.post("/ai-generator", data={
            "topic": "Neural Networks",
            "difficulty": "Hard",
            "bloom_level": "Analyzing",
            "count": "3"
        })
        self.assertEqual(res.status_code, 200)
        self.assertIn(b"Neural Networks", res.data)
        self.assertIn(b"Pedagogical Rationale", res.data)

    def test_04_faculty_studio_and_csv_export(self):
        """TEST 4: Faculty Studio loads catalog, authoring form, and exports CSV with faculty credentials."""
        # 1. Unauthenticated access blocked
        res_unauth = self.client.get("/faculty/studio")
        self.assertEqual(res_unauth.status_code, 302)

        # 2. Authenticate as faculty
        self.client.post("/login", data={"username": "faculty", "password": "faculty123"}, follow_redirects=True)

        # 3. Faculty access granted
        res = self.client.get("/faculty/studio")
        self.assertEqual(res.status_code, 200)
        self.assertIn(b"FACULTY PORTAL", res.data)
        self.assertIn(b"Author New Examination Question", res.data)

        # 4. CSV Export endpoint
        res_csv = self.client.get("/faculty/export-csv")
        self.assertEqual(res_csv.status_code, 200)
        self.assertEqual(res_csv.content_type, "text/csv; charset=utf-8")
        self.assertIn(b"Candidate Name", res_csv.data)
        self.assertIn(b"Trust Score (%)", res_csv.data)

        self.client.get("/logout")

    def test_05_arena_endpoint(self):
        """TEST 5: 1v1 Battle Arena loads 5 duel questions."""
        res = self.client.get("/arena")
        self.assertEqual(res.status_code, 200)
        self.assertIn(b"1v1 Real-Time Speed Duel", res.data)
        self.assertIn(b"ApexBot", res.data)

    def test_06_analytics_endpoint(self):
        """TEST 6: Cognitive Analytics Dashboard renders Bloom's Taxonomy & Mastery tiers."""
        res = self.client.get("/analytics")
        self.assertEqual(res.status_code, 200)
        self.assertIn(b"Bloom's Taxonomy Cognitive Mastery", res.data)
        self.assertIn(b"Discipline Mastery Index", res.data)

    def test_07_proctoring_telemetry_submission(self):
        """TEST 7: Proctoring telemetry (trust score & violations) is persisted with attempt."""
        # Start a quiz
        self.client.get("/quiz?category=Python&topic=Looping+Statements&candidate_name=ProctorTester")

        with self.client.session_transaction() as sess:
            manifest = sess.get("quiz_manifest") or {}
            payload = {f"question_{qid}": info["c"] for qid, info in manifest.items()}

        # Attach telemetry
        payload["trust_score"] = "85"
        payload["cheat_flags"] = "1"

        res = self.client.post("/submit", data=payload, follow_redirects=True)
        self.assertEqual(res.status_code, 200)
        self.assertIn(b"Trust: 85%", res.data)

        # Verify persisted in quiz_attempts & proctor_logs
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT trust_score, cheat_flags FROM quiz_attempts WHERE candidate_name = 'ProctorTester' ORDER BY id DESC LIMIT 1")
        row = cursor.fetchone()
        self.assertIsNotNone(row)
        self.assertEqual(row["trust_score"], 85)
        self.assertEqual(row["cheat_flags"], 1)

        cursor.execute("SELECT violation_type FROM proctor_logs WHERE candidate_name = 'ProctorTester' ORDER BY id DESC LIMIT 1")
        log_row = cursor.fetchone()
        self.assertIsNotNone(log_row)
        conn.close()

    def test_08_socratic_ai_tutor_api(self):
        """TEST 8: Socratic AI Tutor returns pedagogical explanation & takeaway."""
        res = self.client.post("/api/ai-tutor", json={
            "question": "What is the time complexity of binary search?",
            "options": {"A": "O(1)", "B": "O(log n)", "C": "O(n)", "D": "O(n^2)"},
            "student_choice": "C",
            "correct_choice": "B",
            "explanation": "Binary search divides the search interval in half at each step.",
            "topic": "Algorithms",
            "user_query": "Why is it not O(n)?"
        })
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertIn("reply", data)
        self.assertTrue(len(data["reply"]) > 10)

    def test_09_viva_voce_workflow(self):
        """TEST 9: AI Oral Viva Voce generates viva question and evaluates speech defense."""
        res_page = self.client.get("/viva")
        self.assertEqual(res_page.status_code, 200)
        self.assertIn(b"AI Oral Viva Voce", res_page.data)

        res_q = self.client.post("/api/viva/generate-question", json={
            "topic": "Operating Systems",
            "difficulty": "Medium"
        })
        self.assertEqual(res_q.status_code, 200)
        data_q = res_q.get_json()
        self.assertIn("question", data_q)

        res_eval = self.client.post("/api/viva/evaluate", json={
            "topic": "Operating Systems",
            "question": data_q["question"],
            "student_speech": "A process is a program in execution containing program counter, stack, and data segment. A thread is a lightweight unit of execution sharing the process address space.",
            "difficulty": "Medium"
        })
        self.assertEqual(res_eval.status_code, 200)
        data_eval = res_eval.get_json()
        self.assertIn("score", data_eval)
        self.assertIn("feedback", data_eval)
        self.assertTrue(0 <= data_eval["score"] <= 10)

    def test_10_role_based_access_control_and_admin(self):
        """TEST 10: Strict RBAC enforcement - student blocked from faculty/admin, admin has maximum privileges."""
        # 1. Student login
        self.client.post("/login", data={"username": "student", "password": "student123"}, follow_redirects=True)

        # 2. Student CANNOT access faculty studio (access denied flash)
        res_faculty_blocked = self.client.get("/faculty/studio", follow_redirects=True)
        self.assertIn(b"Access restricted to faculty, admin accounts", res_faculty_blocked.data)

        # 3. Student CANNOT access admin console
        res_admin_blocked = self.client.get("/admin", follow_redirects=True)
        self.assertIn(b"Access restricted to admin accounts", res_admin_blocked.data)

        # 4. Student CANNOT export CSV audit report
        res_csv_blocked = self.client.get("/faculty/export-csv", follow_redirects=True)
        self.assertIn(b"Access restricted to faculty, admin accounts", res_csv_blocked.data)

        # 5. Logout student
        self.client.get("/logout")

        # 6. Faculty login
        self.client.post("/login", data={"username": "faculty", "password": "faculty123"}, follow_redirects=True)

        # 7. Faculty CAN access faculty studio & CSV export
        res_faculty_ok = self.client.get("/faculty/studio")
        self.assertEqual(res_faculty_ok.status_code, 200)

        # 8. Faculty CANNOT access admin console (restricted to admin)
        res_faculty_admin_blocked = self.client.get("/admin", follow_redirects=True)
        self.assertIn(b"Access restricted to admin accounts", res_faculty_admin_blocked.data)

        self.client.get("/logout")

        # 9. Admin login (MAXIMUM RIGHTS)
        self.client.post("/login", data={"username": "admin", "password": "admin123"}, follow_redirects=True)

        # 10. Admin CAN access admin console
        res_admin = self.client.get("/admin")
        self.assertEqual(res_admin.status_code, 200)
        self.assertIn(b"ADMINISTRATOR CONSOLE", res_admin.data)
        self.assertIn(b"Registered Accounts", res_admin.data)

        # 11. Admin CAN access faculty studio
        res_admin_faculty = self.client.get("/faculty/studio")
        self.assertEqual(res_admin_faculty.status_code, 200)

        # 12. Admin CAN access CSV export
        res_admin_csv = self.client.get("/faculty/export-csv")
        self.assertEqual(res_admin_csv.status_code, 200)

        # 13. Admin CAN update user roles
        res_role_update = self.client.post("/admin/user/1/role", data={"role": "student"}, follow_redirects=True)
        self.assertEqual(res_role_update.status_code, 200)
        self.assertIn(b"role updated successfully", res_role_update.data)

        self.client.get("/logout")

    def test_11_gateway_landing_and_post_login_landing_page(self):
        """TEST 11: Public gateway landing page for unauthenticated visitors & normal landing page after login."""
        # 1. Unauthenticated visitor at / sees the public gateway landing page
        res_gateway = self.client.get("/")
        self.assertEqual(res_gateway.status_code, 200)
        self.assertIn(b"Sign In to Access Portal", res_gateway.data)
        self.assertIn(b"1-Click Fast Pass", res_gateway.data)
        self.assertIn(b"Major Project Super-Features", res_gateway.data)

        # 2. Guest preview query (?guest=1) displays normal landing page with preview notice
        res_guest = self.client.get("/?guest=1")
        self.assertEqual(res_guest.status_code, 200)
        self.assertIn(b"Guest Preview Mode", res_guest.data)
        self.assertIn(b"Candidate Profile Name", res_guest.data)

        # 3. Authenticate with student credentials
        res_login = self.client.post("/login", data={"username": "student", "password": "student123"}, follow_redirects=True)
        self.assertEqual(res_login.status_code, 200)

        # 4. Authenticated user at / sees the NORMAL landing page with their identity
        res_auth_home = self.client.get("/")
        self.assertEqual(res_auth_home.status_code, 200)
        self.assertIn(b"Candidate Profile Name", res_auth_home.data)
        self.assertIn(b"Authenticated:", res_auth_home.data)
        self.assertIn(b"student", res_auth_home.data)

        # 5. Sign out reverts / back to public gateway landing page
        res_logout = self.client.get("/logout", follow_redirects=True)
        self.assertEqual(res_logout.status_code, 200)
        self.assertIn(b"Sign In to Access Portal", res_logout.data)

        # 6. 1-Click Fast Pass for Demo Faculty logs in and unlocks normal landing page
        res_demo_faculty = self.client.get("/demo-login/faculty", follow_redirects=True)
        self.assertEqual(res_demo_faculty.status_code, 200)
        with self.client.session_transaction() as sess:
            self.assertEqual(sess.get("role"), "faculty")
        self.assertIn(b"Candidate Profile Name", res_demo_faculty.data)

        self.client.get("/logout")

    def test_12_dynamic_questions_zero_repeat_guarantee(self):
        """TEST 12: Dynamic Question Synthesizer guarantees ZERO repetition across multiple sessions."""
        candidate = f"candidate_zero_repeat_{int(time.time())}"

        # 1. Synthesize first batch of 5 questions
        batch_1 = dynamic_question_engine.get_or_synthesize_unique_quiz_questions(
            category="Python",
            topic="Core Logic",
            count=5,
            user_identifier=candidate,
            force_dynamic=True
        )
        self.assertEqual(len(batch_1), 5)
        batch_1_ids = [q["id"] for q in batch_1]
        batch_1_hashes = [dynamic_question_engine.compute_question_hash(q["question"]) for q in batch_1]
        self.assertEqual(len(set(batch_1_hashes)), 5)  # All distinct within batch

        # Verify IDs are in dynamic range (>= 10001)
        for q_id in batch_1_ids:
            self.assertGreaterEqual(q_id, 10001)

        # 2. Synthesize second batch of 5 questions for the same candidate and topic
        batch_2 = dynamic_question_engine.get_or_synthesize_unique_quiz_questions(
            category="Python",
            topic="Core Logic",
            count=5,
            user_identifier=candidate,
            force_dynamic=True
        )
        self.assertEqual(len(batch_2), 5)
        batch_2_hashes = [dynamic_question_engine.compute_question_hash(q["question"]) for q in batch_2]

        # GUARANTEE: Zero overlap between batch 1 and batch 2
        overlap = set(batch_1_hashes).intersection(set(batch_2_hashes))
        self.assertEqual(len(overlap), 0, f"Found repeated question hashes: {overlap}")

        # 3. Check anti-repeat tracking database
        seen_hashes = dynamic_question_engine.get_user_seen_hashes(candidate)
        self.assertGreaterEqual(len(seen_hashes), 10)

        # 4. Test Candidate History Stats API endpoint
        res_stats = self.client.get(f"/api/quiz/candidate-history-stats?candidate_name={candidate}")
        self.assertEqual(res_stats.status_code, 200)
        data_stats = res_stats.get_json()
        self.assertEqual(data_stats["candidate"], candidate)
        self.assertGreaterEqual(data_stats["total_seen_unique_questions"], 10)

        # 5. Test Dynamic Generation API endpoint
        res_gen = self.client.post("/api/quiz/dynamic-generate", json={
            "category": "DBMS",
            "topic": "SQL Joins",
            "count": 3,
            "candidate_name": candidate
        })
        self.assertEqual(res_gen.status_code, 200)
        gen_data = res_gen.get_json()
        self.assertTrue(gen_data["success"])
        self.assertEqual(len(gen_data["questions"]), 3)

        # 6. Test taking dynamic quiz through Flask route with dynamic=1
        res_quiz = self.client.get(f"/quiz?category=Python&topic=Variables&candidate_name={candidate}&dynamic=1")
        self.assertEqual(res_quiz.status_code, 200)
        self.assertIn(b"Dynamic (0 Repeats)", res_quiz.data)

        # Submit the dynamic quiz
        with self.client.session_transaction() as sess:
            manifest = sess.get("quiz_manifest") or {}
            q_order = sess.get("quiz_q_order") or []

        form_data = {}
        for qid in q_order:
            form_data[f"question_{qid}"] = "A"

        res_submit = self.client.post("/submit", data=form_data, follow_redirects=True)
        self.assertEqual(res_submit.status_code, 200)
        self.assertIn(b"Quiz Completed!", res_submit.data)
        self.assertIn(b"Detailed Question Review", res_submit.data)

    def test_13_syllabus_ingest_and_synthesis(self):
        """TEST 13: Smart Syllabus Ingestion parses uploaded text and synthesizes questions & flashcards."""
        # 1. GET page renders correctly
        res_page = self.client.get("/syllabus-ingest")
        self.assertEqual(res_page.status_code, 200)
        self.assertIn(b"Smart Syllabus", res_page.data)

        # 2. POST with sample curriculum notes
        sample_notes = """
        Course: Distributed Cloud Systems
        Module 1: Consensus Algorithms (Paxos, Raft leader election, split vote resolution)
        Module 2: Replication & CAP Theorem (Eventual Consistency vs Linearizability)
        Module 3: Fault Tolerance & Heartbeat Mechanisms
        """
        res_ingest = self.client.post("/syllabus-ingest", json={
            "text_content": sample_notes,
            "count": 3,
            "difficulty": "Medium"
        })
        self.assertEqual(res_ingest.status_code, 200)
        data = res_ingest.get_json()
        self.assertTrue(data["success"])
        self.assertTrue(len(data["questions"]) >= 1)
        self.assertTrue(len(data.get("flashcards", [])) >= 1)

    def test_14_live_code_sandbox_and_auto_grader(self):
        """TEST 14: Code Sandbox renders IDE and AI Auto-Grader evaluates candidate code."""
        # 1. GET /sandbox renders IDE layout
        res_page = self.client.get("/sandbox")
        self.assertEqual(res_page.status_code, 200)
        self.assertIn(b"Live Code Sandbox", res_page.data)
        self.assertIn(b"AI Code Doctor", res_page.data)

        # 2. POST to Auto-Grader endpoint
        sample_code = """
def two_sum(nums, target):
    seen = {}
    for i, n in enumerate(nums):
        diff = target - n
        if diff in seen:
            return [seen[diff], i]
        seen[n] = i
    return []
"""
        res_eval = self.client.post("/api/sandbox/evaluate", json={
            "code": sample_code,
            "problem_title": "Two Sum",
            "problem_description": "Return indices of two numbers that add up to target.",
            "language": "python"
        })
        self.assertEqual(res_eval.status_code, 200)
        data = res_eval.get_json()
        self.assertTrue(data["success"])
        self.assertIn("verdict", data)
        self.assertIn("time_complexity", data)

    def test_15_ai_podcast_generator(self):
        """TEST 15: AI Revision Podcast synthesizes conversational 2-host audio script & flashcards."""
        sample_review = [
            {
                "question": "What is the primary difference between a process and a thread?",
                "correct_text": "Threads share memory within the same address space; processes have isolated memory.",
                "user_text": "Processes share memory; threads are strictly isolated.",
                "is_correct": False
            }
        ]
        res_pod = self.client.post("/api/podcast/generate", json={
            "review_items": sample_review,
            "topic_title": "Operating Systems Threads"
        })
        self.assertEqual(res_pod.status_code, 200)
        data = res_pod.get_json()
        self.assertTrue(data["success"])
        self.assertIn("dialogue", data)
        self.assertTrue(len(data["dialogue"]) >= 2)
        self.assertTrue(len(data.get("audio_flashcards", [])) >= 1)


if __name__ == "__main__":
    unittest.main()



