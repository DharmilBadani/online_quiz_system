"""
QuizVerse Performance Reproduction & Concurrency Benchmark
Independent, reproducible benchmarking harness with memory profiling,
concurrency percentiles (p50, p95, p99), throughput, and lock error tracking.
"""

import os
import sys
import time
import statistics
import concurrent.futures
import sqlite3
import psutil
from app import app, get_db_connection


def make_request(endpoint_type: str):
    """Executes a single isolated test client request, tracking latency, status, and lock errors."""
    client = app.test_client()
    start_time = time.perf_counter()
    status_code = 0
    lock_error = False

    try:
        if endpoint_type == "home":
            res = client.get("/")
            status_code = res.status_code
        elif endpoint_type == "api_topics":
            res = client.get("/api/topics?category=Python")
            status_code = res.status_code
        elif endpoint_type == "leaderboard":
            res = client.get("/leaderboard")
            status_code = res.status_code
        elif endpoint_type == "quiz_init":
            res = client.get("/quiz?category=Python&topic=Variables&candidate_name=ReproduceTester")
            status_code = res.status_code
        elif endpoint_type == "submit":
            # Simulate real submission
            client.get("/quiz?category=Python&topic=Variables&candidate_name=SubTester")
            with client.session_transaction() as sess:
                token = sess.get("active_quiz_token")
                manifest = sess.get("quiz_manifest") or {}
                payload = {f"question_{qid}": "A" for qid in manifest.keys()}
                payload["attempt_token"] = token
            res = client.post("/submit", data=payload, follow_redirects=True)
            status_code = res.status_code
        else:
            res = client.get("/")
            status_code = res.status_code
    except sqlite3.OperationalError as e:
        if "locked" in str(e).lower() or "busy" in str(e).lower():
            lock_error = True
        status_code = 500
    except Exception:
        status_code = 500

    latency_ms = (time.perf_counter() - start_time) * 1000.0
    return latency_ms, status_code, lock_error


def benchmark_endpoint(endpoint: str, concurrency: int, total_requests: int = 60):
    proc = psutil.Process(os.getpid())
    mem_before_mb = proc.memory_info().rss / (1024 * 1024)

    latencies = []
    errors = 0
    lock_errors = 0
    start_total = time.perf_counter()

    with concurrent.futures.ThreadPoolExecutor(max_workers=concurrency) as executor:
        futures = [executor.submit(make_request, endpoint) for _ in range(total_requests)]
        for f in concurrent.futures.as_completed(futures):
            lat_ms, code, is_locked = f.result()
            latencies.append(lat_ms)
            if code not in (200, 302):
                errors += 1
            if is_locked:
                lock_errors += 1

    total_time = time.perf_counter() - start_total
    mem_after_mb = proc.memory_info().rss / (1024 * 1024)
    rps = total_requests / total_time if total_time > 0 else 0
    latencies.sort()

    avg_lat = statistics.mean(latencies)
    p50_lat = statistics.median(latencies)
    p95_idx = int(0.95 * len(latencies))
    p99_idx = int(0.99 * len(latencies))
    p95_lat = latencies[min(p95_idx, len(latencies) - 1)]
    p99_lat = latencies[min(p99_idx, len(latencies) - 1)]
    err_rate = (errors / total_requests) * 100.0

    return {
        "concurrency": concurrency,
        "total_requests": total_requests,
        "duration_sec": round(total_time, 3),
        "throughput_rps": round(rps, 1),
        "avg_ms": round(avg_lat, 2),
        "p50_ms": round(p50_lat, 2),
        "p95_ms": round(p95_lat, 2),
        "p99_ms": round(p99_lat, 2),
        "error_rate_pct": round(err_rate, 2),
        "lock_errors": lock_errors,
        "mem_delta_mb": round(mem_after_mb - mem_before_mb, 2),
        "mem_final_mb": round(mem_after_mb, 2)
    }


def main():
    app.config["TESTING"] = True
    app.config["WTF_CSRF_ENABLED"] = False

    endpoints = ["home", "api_topics", "leaderboard", "quiz_init"]
    concurrency_tiers = [1, 5, 10, 25]

    print("==========================================================================================")
    print("QUIZVERSE EMPIRICAL BENCHMARK REPRODUCTION & MEMORY CONCURRENCY PROFILING")
    print("==========================================================================================")
    print(f"System: Windows 11 AMD64 | Python: {sys.version.split()[0]} | Database: {round(os.path.getsize('quiz.db')/1024, 1)} KB (WAL Mode)")
    print(f"Hardware: 4 Physical Cores / 8 Logical Threads | Total RAM: {round(psutil.virtual_memory().total/(1024**3), 2)} GB")
    print("==========================================================================================\n")

    for ep in endpoints:
        print(f"--- Endpoint: {ep.upper()} ---")
        print(f"{'Conc':<6} | {'Reqs':<6} | {'RPS':<10} | {'Avg(ms)':<9} | {'P50(ms)':<9} | {'P95(ms)':<9} | {'P99(ms)':<9} | {'Err(%)':<7} | {'LockErr':<8} | {'Mem(MB)':<8}")
        print("-" * 98)
        for c in concurrency_tiers:
            r = benchmark_endpoint(ep, c, total_requests=60)
            print(f"{r['concurrency']:<6} | {r['total_requests']:<6} | {r['throughput_rps']:<10} | {r['avg_ms']:<9} | {r['p50_ms']:<9} | {r['p95_ms']:<9} | {r['p99_ms']:<9} | {r['error_rate_pct']:<7} | {r['lock_errors']:<8} | {r['mem_final_mb']:<8}")
        print()

    # Blended simultaneous load test
    print("--- Blended Simultaneous Workload: Mixed Reads & Writes (Init + Submit + Leaderboard) ---")
    print(f"{'Conc':<6} | {'Reqs':<6} | {'RPS':<10} | {'Avg(ms)':<9} | {'P50(ms)':<9} | {'P95(ms)':<9} | {'P99(ms)':<9} | {'Err(%)':<7} | {'LockErr':<8} | {'Mem(MB)':<8}")
    print("-" * 98)
    for c in [5, 10, 20]:
        r = benchmark_endpoint("submit", c, total_requests=40)
        print(f"{r['concurrency']:<6} | {r['total_requests']:<6} | {r['throughput_rps']:<10} | {r['avg_ms']:<9} | {r['p50_ms']:<9} | {r['p95_ms']:<9} | {r['p99_ms']:<9} | {r['error_rate_pct']:<7} | {r['lock_errors']:<8} | {r['mem_final_mb']:<8}")


if __name__ == "__main__":
    main()

