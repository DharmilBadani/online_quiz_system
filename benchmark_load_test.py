"""
Empirical Performance and Concurrency Benchmark Harness for QuizVerse
Measures throughput, latency percentiles (p50, p95, p99), error rates,
and SQLite WAL concurrency across levels: 1, 5, 10, 25.
"""

import time
import statistics
import concurrent.futures
from app import app, get_db_connection


def make_request(endpoint_type: str):
    """Executes a single test request with an isolated Flask test client."""
    client = app.test_client()
    start_time = time.perf_counter()
    status_code = 0
    try:
        if endpoint_type == "home":
            res = client.get("/")
            status_code = res.status_code
        elif endpoint_type == "leaderboard":
            res = client.get("/leaderboard")
            status_code = res.status_code
        elif endpoint_type == "api_topics":
            res = client.get("/api/topics?category=Python")
            status_code = res.status_code
        elif endpoint_type == "quiz_init":
            res = client.get("/quiz?category=Python&topic=Variables&candidate_name=Benchmarker")
            status_code = res.status_code
        else:
            res = client.get("/")
            status_code = res.status_code
    except Exception as e:
        status_code = 500

    latency_ms = (time.perf_counter() - start_time) * 1000.0
    return latency_ms, status_code


def benchmark_concurrency(endpoint: str, concurrency: int, total_requests: int = 50):
    latencies = []
    errors = 0
    start_total = time.perf_counter()

    with concurrent.futures.ThreadPoolExecutor(max_workers=concurrency) as executor:
        futures = [executor.submit(make_request, endpoint) for _ in range(total_requests)]
        for f in concurrent.futures.as_completed(futures):
            lat_ms, code = f.result()
            latencies.append(lat_ms)
            if code not in (200, 302):
                errors += 1

    total_time = time.perf_counter() - start_total
    rps = total_requests / total_time if total_time > 0 else 0
    latencies.sort()

    avg_lat = statistics.mean(latencies)
    p50_lat = statistics.median(latencies)
    p95_idx = int(0.95 * len(latencies))
    p99_idx = int(0.99 * len(latencies))
    p95_lat = latencies[p95_idx] if p95_idx < len(latencies) else latencies[-1]
    p99_lat = latencies[p99_idx] if p99_idx < len(latencies) else latencies[-1]
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
        "error_rate_pct": round(err_rate, 2)
    }


def main():
    app.config["TESTING"] = True
    app.config["WTF_CSRF_ENABLED"] = False

    endpoints = ["home", "leaderboard", "api_topics", "quiz_init"]
    concurrency_levels = [1, 5, 10, 25]

    print("================================================================================")
    print("QUIZVERSE EMPIRICAL PERFORMANCE & CONCURRENCY BENCHMARK")
    print("================================================================================")

    for ep in endpoints:
        print(f"\n--- Benchmarking Endpoint: {ep.upper()} ---")
        print(f"{'Concurrency':<12} | {'Requests':<10} | {'Throughput (rps)':<18} | {'Avg (ms)':<10} | {'P50 (ms)':<10} | {'P95 (ms)':<10} | {'P99 (ms)':<10} | {'Err (%)':<8}")
        print("-" * 100)
        for c in concurrency_levels:
            res = benchmark_concurrency(ep, c, total_requests=60)
            print(f"{res['concurrency']:<12} | {res['total_requests']:<10} | {res['throughput_rps']:<18} | {res['avg_ms']:<10} | {res['p50_ms']:<10} | {res['p95_ms']:<10} | {res['p99_ms']:<10} | {res['error_rate_pct']:<8}")

    print("\nBenchmark completed successfully.")


if __name__ == "__main__":
    main()

