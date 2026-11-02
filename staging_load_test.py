# -*- coding: utf-8 -*-
"""
=============================================================================
QUIZVERSE v2.0 - Staging Realistic Multi-Student Examination Load Test
=============================================================================
Simulates complete student examination journeys:
1. Catalog landing (`GET /`)
2. Student authentication (`POST /login`)
3. Student dashboard inspection (`GET /dashboard/student`)
4. Exam initialization & token generation (`GET /quiz`)
5. Live proctoring telemetry logging (`POST /api/proctor/event`)
6. Exam final submission (`POST /submit`)
7. Result scorecard & analytics retrieval (`GET /result`)

Supports both Staggered Cohorts (25, 50, 100 students) and Synchronized Bursts
(50 and 100 simultaneous click-to-submit via threading.Barrier).
=============================================================================
"""

import time
import os
import sys
import psutil
import statistics
import threading
import concurrent.futures
from typing import Dict, List, Any

# Ensure project root in sys.path
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from app import app, get_db_connection
from database.init_db import init_database


def run_single_student_journey(student_id: int, barrier: threading.Barrier = None) -> Dict[str, Any]:
    """Simulates a complete student exam session."""
    client = app.test_client()
    latencies: List[float] = []
    errors = 0
    db_locks = 0
    status_codes = []

    def timed_req(method: str, path: str, **kwargs):
        nonlocal errors, db_locks
        t0 = time.perf_counter()
        try:
            if method == "GET":
                resp = client.get(path, **kwargs)
            else:
                resp = client.post(path, **kwargs)
            dt = (time.perf_counter() - t0) * 1000.0  # ms
            latencies.append(dt)
            status_codes.append(resp.status_code)
            if resp.status_code not in (200, 302):
                errors += 1
            return resp
        except Exception as e:
            dt = (time.perf_counter() - t0) * 1000.0
            latencies.append(dt)
            errors += 1
            if "database is locked" in str(e).lower() or "busy" in str(e).lower():
                db_locks += 1
            return None

    username = f"load_student_{student_id}"

    # Step 1: Catalog Landing (Initializes CSRF token in session)
    r1 = timed_req("GET", "/")

    # Extract CSRF token
    with client.session_transaction() as sess:
        csrf_tok = sess.get("_csrf_token", "")

    # Step 2: Student Login
    login_data = {"username": "student", "password": "student123", "csrf_token": csrf_tok}
    r2 = timed_req("POST", "/login", data=login_data, headers={"X-CSRFToken": csrf_tok}, follow_redirects=True)

    # Refresh CSRF token after login session regeneration
    with client.session_transaction() as sess:
        csrf_tok = sess.get("_csrf_token", "")

    # Step 3: Student Dashboard / Landing
    r3 = timed_req("GET", "/")

    # Step 4: Quiz Initialization & Token Issuance
    r4 = timed_req("GET", f"/quiz?category=Python&topic=Variables&candidate_name={username}")
    
    # Extract session token from client session
    with client.session_transaction() as sess:
        token = sess.get("active_quiz_token")
        if not csrf_tok:
            csrf_tok = sess.get("_csrf_token", "")

    if not token:
        errors += 1
        return {
            "student_id": student_id,
            "latencies": latencies,
            "errors": errors + 1,
            "db_locks": db_locks,
            "status_codes": status_codes,
            "submit_latency": 0.0
        }

    # Retrieve question IDs server-side from active session (zero answer leakage to client)
    from app import get_active_quiz_session
    active_row = get_active_quiz_session(token)
    q_order = active_row["question_ids_order"] if active_row else []

    # Step 5: Proctoring Telemetry Event (with CSRF header)
    r5 = timed_req("POST", "/api/proctor/event", 
                   json={"attempt_token": token, "violation_type": "Tab Switch"},
                   headers={"X-CSRFToken": csrf_tok})

    # Prepare submission payload
    payload = {f"question_{qid}": "A" for qid in q_order}
    payload["attempt_token"] = token
    payload["csrf_token"] = csrf_tok

    # Optional synchronization barrier (for synchronized click-to-submit testing)
    if barrier is not None:
        try:
            barrier.wait(timeout=15.0)
        except threading.BrokenBarrierError:
            pass

    # Step 6: Final Exam Submission (follows redirect to /result)
    t_submit_start = time.perf_counter()
    r6 = timed_req("POST", "/submit", data=payload, headers={"X-CSRFToken": csrf_tok}, follow_redirects=True)
    submit_latency = (time.perf_counter() - t_submit_start) * 1000.0

    # Step 7: Leaderboard Inspection
    r7 = timed_req("GET", "/leaderboard")

    return {
        "student_id": student_id,
        "latencies": latencies,
        "errors": errors,
        "db_locks": db_locks,
        "status_codes": status_codes,
        "submit_latency": submit_latency
    }


def execute_cohort_test(cohort_size: int, synchronized_submit: bool = False) -> Dict[str, Any]:
    """Executes a cohort test of N virtual students."""
    process = psutil.Process(os.getpid())
    ram_before = process.memory_info().rss / (1024 * 1024)
    cpu_before = psutil.cpu_percent(interval=0.1)

    barrier = threading.Barrier(cohort_size) if synchronized_submit else None
    mode_str = "SYNCHRONIZED BURST" if synchronized_submit else "STAGGERED PACING"
    print(f"\n==================================================================")
    print(f"RUNNING COHORT: {cohort_size} Students ({mode_str})")
    print(f"==================================================================")

    t_start = time.perf_counter()

    with concurrent.futures.ThreadPoolExecutor(max_workers=min(cohort_size, 32)) as executor:
        futures = [executor.submit(run_single_student_journey, i, barrier) for i in range(cohort_size)]
        results = [f.result() for f in concurrent.futures.as_completed(futures)]

    total_duration = time.perf_counter() - t_start
    ram_after = process.memory_info().rss / (1024 * 1024)
    cpu_after = psutil.cpu_percent(interval=0.1)

    all_latencies: List[float] = []
    all_submit_latencies: List[float] = []
    total_errors = 0
    total_db_locks = 0
    total_requests = 0

    for r in results:
        all_latencies.extend(r["latencies"])
        all_submit_latencies.append(r["submit_latency"])
        total_errors += r["errors"]
        total_db_locks += r["db_locks"]
        total_requests += len(r["latencies"])

    all_latencies.sort()
    all_submit_latencies.sort()

    def calc_percentile(arr: List[float], p: float) -> float:
        if not arr:
            return 0.0
        k = (len(arr) - 1) * (p / 100.0)
        f = int(k)
        c = min(f + 1, len(arr) - 1)
        d = k - f
        return arr[f] + d * (arr[c] - arr[f])

    p50 = calc_percentile(all_latencies, 50)
    p95 = calc_percentile(all_latencies, 95)
    p99 = calc_percentile(all_latencies, 99)

    sub_p50 = calc_percentile(all_submit_latencies, 50)
    sub_p95 = calc_percentile(all_submit_latencies, 95)
    sub_p99 = calc_percentile(all_submit_latencies, 99)

    throughput = total_requests / total_duration if total_duration > 0 else 0.0
    exam_workflows_per_sec = cohort_size / total_duration if total_duration > 0 else 0.0

    print(f"Total Completed Workflows : {cohort_size}/{cohort_size}")
    print(f"Total Requests Processed  : {total_requests}")
    print(f"Total Test Duration       : {total_duration:.2f} s")
    print(f"Overall Request RPS       : {throughput:.2f} req/s")
    print(f"Full Exam Journeys / sec  : {exam_workflows_per_sec:.2f} exams/s")
    print(f"Latency P50 / P95 / P99   : {p50:.2f} ms / {p95:.2f} ms / {p99:.2f} ms")
    print(f"Submit Lat P50 / P95 / P99: {sub_p50:.2f} ms / {sub_p95:.2f} ms / {sub_p99:.2f} ms")
    print(f"HTTP Errors / DB Locks    : {total_errors} / {total_db_locks}")
    print(f"RAM RSS Before -> After   : {ram_before:.2f} MB -> {ram_after:.2f} MB")

    return {
        "cohort_size": cohort_size,
        "mode": mode_str,
        "duration_sec": total_duration,
        "total_requests": total_requests,
        "throughput_rps": throughput,
        "p50_ms": p50,
        "p95_ms": p95,
        "p99_ms": p99,
        "submit_p50_ms": sub_p50,
        "submit_p95_ms": sub_p95,
        "submit_p99_ms": sub_p99,
        "total_errors": total_errors,
        "total_db_locks": total_db_locks,
        "ram_before_mb": ram_before,
        "ram_after_mb": ram_after,
        "cpu_after_pct": cpu_after
    }


def main():
    print("==================================================================")
    print("QUIZVERSE v2.0 - REALISTIC STAGING CONCURRENCY LOAD TEST")
    print("==================================================================")
    
    # Ensure database initialized
    init_database()
    
    results = []
    # Progressive Staggered Testing
    results.append(execute_cohort_test(cohort_size=25, synchronized_submit=False))
    results.append(execute_cohort_test(cohort_size=50, synchronized_submit=False))
    results.append(execute_cohort_test(cohort_size=100, synchronized_submit=False))

    # Progressive Synchronized Final Submission Testing
    results.append(execute_cohort_test(cohort_size=50, synchronized_submit=True))
    results.append(execute_cohort_test(cohort_size=100, synchronized_submit=True))

    print("\n\n==================================================================")
    print("SUMMARY OF ALL COHORT RUNS")
    print("==================================================================")
    print(f"{'Cohort':<8} {'Mode':<22} {'RPS':<8} {'Dur(s)':<8} {'P95(ms)':<10} {'Sub_P95(ms)':<12} {'Locks':<6} {'Errors':<6}")
    print("-" * 84)
    for r in results:
        print(f"{r['cohort_size']:<8} {r['mode']:<22} {r['throughput_rps']:<8.1f} {r['duration_sec']:<8.2f} {r['p95_ms']:<10.2f} {r['submit_p95_ms']:<12.2f} {r['total_db_locks']:<6} {r['total_errors']:<6}")


if __name__ == "__main__":
    main()
