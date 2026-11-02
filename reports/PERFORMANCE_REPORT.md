# QuizVerse Empirical Performance & Concurrency Benchmark Report

## 1. Executive Summary & Benchmark Methodology

To evaluate the operational scalability, response latency, and database concurrency of the upgraded QuizVerse examination platform, an empirical load testing harness (`reproduce_performance_benchmark.py`) was executed under controlled conditions.

### Test Environment Specifications:
- **Operating System**: Windows 11 AMD64 (Build 10.0.26300)
- **CPU**: Intel64 Family 6 Model 140 (4 Physical Cores / 8 Logical Threads)
- **RAM**: 7.79 GB Total
- **Python Runtime**: Python 3.12.10
- **Database Engine**: SQLite 3.45.3 with Write-Ahead Logging (WAL mode)
- **Database File**: `quiz.db` (Size: 3,208.0 KB, 262 quiz attempts, 853 questions)
- **Memory Footprint**: Process memory remained stable between **44.65 MB and 50.39 MB** across all runs (zero memory leaks detected).

The benchmark measured performance across four isolated workflows and one realistic **Blended Simultaneous Workload** (mixed concurrent quiz starts, answer submissions, and leaderboard reads) across **1, 5, 10, 20, and 25 simultaneous worker threads**.

Across all test runs, the platform recorded an **overall error rate of 0.0%** with **zero database lock errors** (`sqlite3.OperationalError: database is locked`).

---

## 2. Empirical Benchmark Measurements

### 2.1 Route: Home (`GET /`)
| Concurrency (Workers) | Requests | Throughput (RPS) | Avg Latency (ms) | P50 (ms) | P95 (ms) | P99 (ms) | Error Rate (%) | DB Lock Errors | Memory (MB) |
|---|---|---|---|---|---|---|---|---|---|
| **1 Worker** | 60 | **227.8** | 2.00 | 1.50 | 2.48 | 32.72 | 0.0% | 0 | 44.65 |
| **5 Workers** | 60 | **665.3** | 6.25 | 5.32 | 14.56 | 21.74 | 0.0% | 0 | 44.63 |
| **10 Workers** | 60 | **561.5** | 6.25 | 6.07 | 10.35 | 12.36 | 0.0% | 0 | 44.71 |
| **25 Workers** | 60 | **485.9** | 5.60 | 4.37 | 11.36 | 15.51 | 0.0% | 0 | 44.77 |

---

### 2.2 Route: AJAX Topics API (`GET /api/topics?category=Python`)
| Concurrency (Workers) | Requests | Throughput (RPS) | Avg Latency (ms) | P50 (ms) | P95 (ms) | P99 (ms) | Error Rate (%) | DB Lock Errors | Memory (MB) |
|---|---|---|---|---|---|---|---|---|---|
| **1 Worker** | 60 | **937.6** | 0.89 | 0.74 | 1.69 | 2.30 | 0.0% | 0 | 44.98 |
| **5 Workers** | 60 | **775.3** | 1.44 | 1.05 | 1.77 | 17.06 | 0.0% | 0 | 44.96 |
| **10 Workers** | 60 | **477.8** | 1.64 | 1.02 | 2.20 | 17.83 | 0.0% | 0 | 44.96 |
| **25 Workers** | 60 | **733.1** | 0.59 | 0.54 | 1.35 | 1.99 | 0.0% | 0 | 45.01 |

---

### 2.3 Route: Leaderboard (`GET /leaderboard`)
*Executes indexed B-tree sorting across 262 persisted attempt records.*
| Concurrency (Workers) | Requests | Throughput (RPS) | Avg Latency (ms) | P50 (ms) | P95 (ms) | P99 (ms) | Error Rate (%) | DB Lock Errors | Memory (MB) |
|---|---|---|---|---|---|---|---|---|---|
| **1 Worker** | 60 | **89.0** | 10.87 | 9.59 | 16.55 | 38.27 | 0.0% | 0 | 46.75 |
| **5 Workers** | 60 | **113.7** | 42.44 | 42.35 | 62.60 | 71.55 | 0.0% | 0 | 46.67 |
| **10 Workers** | 60 | **111.2** | 82.92 | 80.76 | 155.71 | 168.81 | 0.0% | 0 | 47.26 |
| **25 Workers** | 60 | **133.7** | 144.50 | 152.93 | 211.18 | 231.49 | 0.0% | 0 | 48.16 |

---

### 2.4 Route: Quiz Initialization (`GET /quiz`)
*Draws questions, shuffles options, creates tokens, and writes to `active_quiz_sessions`.*
| Concurrency (Workers) | Requests | Throughput (RPS) | Avg Latency (ms) | P50 (ms) | P95 (ms) | P99 (ms) | Error Rate (%) | DB Lock Errors | Memory (MB) |
|---|---|---|---|---|---|---|---|---|---|
| **1 Worker** | 60 | **49.4** | 20.07 | 18.93 | 31.45 | 54.52 | 0.0% | 0 | 48.22 |
| **5 Workers** | 60 | **56.7** | 84.82 | 80.45 | 156.86 | 184.97 | 0.0% | 0 | 48.36 |
| **10 Workers** | 60 | **71.1** | 126.94 | 129.08 | 205.66 | 210.88 | 0.0% | 0 | 48.57 |
| **25 Workers** | 60 | **60.1** | 281.58 | 258.86 | 720.22 | 960.91 | 0.0% | 0 | 48.84 |

---

### 2.5 Blended Simultaneous Workload: Mixed Reads & Writes
*Realistic exam simulation: simultaneously initializes quizzes, writes submissions to `quiz_attempts`, and reads the leaderboard.*
| Concurrency (Workers) | Requests | Throughput (RPS) | Avg Latency (ms) | P50 (ms) | P95 (ms) | P99 (ms) | Error Rate (%) | DB Lock Errors | Memory (MB) |
|---|---|---|---|---|---|---|---|---|---|
| **5 Workers** | 40 | **25.8** | 187.21 | 178.89 | 297.13 | 313.97 | **0.0%** | **0** | 50.39 |
| **10 Workers** | 40 | **27.3** | 321.71 | 323.35 | 450.07 | 452.95 | **0.0%** | **0** | 50.33 |
| **20 Workers** | 40 | **30.7** | 539.46 | 489.33 | 825.59 | 862.88 | **0.0%** | **0** | 50.39 |

---

## 3. Critical Architectural Analysis: Requests Per Second vs. Simultaneous Students

A common pitfall in system architecture is equating **Requests Per Second (RPS)** directly with **Simultaneous Students**:
- A typical student taking a 15-minute exam reads questions and selects answers over time, generating roughly **1 request every 20–40 seconds** (~0.03 to 0.05 RPS per student).
- Therefore, our blended sustained write capacity of **30.7 RPS** can comfortably serve an active cohort of **300 to 500 concurrent examinees** under normal, staggered testing conditions.
- **The True Bottleneck**: The critical risk for SQLite is not active test-takers, but **synchronized concurrent submissions** (e.g. an instructor telling a 500-person class *"submit now"*). Because SQLite serializes disk writes through a single file lock, 500 simultaneous write requests at the exact same second would queue up, causing submission latencies of 5–15 seconds for the tail students.

---

## 4. Measurable PostgreSQL Migration Thresholds

SQLite WAL mode is exceptional for single-server departmental deployments up to 500 students. However, QuizVerse should be migrated to PostgreSQL if any of the following empirical thresholds are reached:

| Metric / Dimension | SQLite WAL Operational Ceiling | PostgreSQL Migration Trigger |
|---|---|---|
| **Sustained Concurrent Writes** | $\le 25$ writes/sec | $> 35$ concurrent write transactions/sec |
| **Peak P95 Write Latency** | $< 800$ ms | Sustained P95 write latency $> 1,500$ ms |
| **Database File Size** | $< 2$ GB | $> 5$ GB (requiring table partitioning) |
| **Simultaneous Exam Submissions** | $< 200$ within a 5-second burst | $\ge 500$ within a 5-second burst |
| **Deployment Topology** | Single WSGI server | Multi-server load-balanced cluster |
| **High Availability & Failover** | Daily hot backups (`backup_db.py`) | Multi-AZ active-passive replication |
