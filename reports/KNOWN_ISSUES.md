# QuizVerse Known Operational Constraints & Advanced Engineering Roadmap

## 1. Known Operational Constraints & Engineering Boundaries

### 1.1 WebRTC / Camera Access Requires Secure Context (HTTPS or Localhost)
- **Constraint**: The W3C Secure Context specification blocks access to `navigator.mediaDevices.getUserMedia()` on insecure `http://` network origins (except `localhost` and `127.0.0.1`).
- **Application Behavior**: When deployed over plain HTTP on LAN or IP addresses, the proctoring HUD in [`templates/quiz.html`](file:///e:/Major%20Project/online_quiz_system/templates/quiz.html) detects permission denial and gracefully presents a simulated fallback indicator without throwing unhandled exceptions or disrupting exam flow.
- **Production Requirement**: Production deployments must be fronted by Nginx with TLS 1.3 enabled via Let's Encrypt or institutional SSL certificates as specified in [`reports/DEPLOYMENT_GUIDE.md`](file:///e:/Major%20Project/online_quiz_system/reports/DEPLOYMENT_GUIDE.md).

---

### 1.2 SQLite Write Concurrency Scale Ceilings
- **Constraint**: SQLite operates with a single-writer file-locking model. While Write-Ahead Logging (WAL mode) and our 5,000 ms busy lock timeout eliminate contention between concurrent readers and writers, concurrent write operations are serialized.
- **Empirical Measurement**: In our empirical benchmark, SQLite handled **30.7 mixed write RPS** without lock errors. Because active test-takers submit only once every 10–20 minutes, this supports active pools of 300–500 students under normal staggered conditions.
- **Ceiling**: If $\ge 500$ students execute synchronized submissions at the exact same second, queue wait times can spike to 5–15 seconds.
- **Migration Trigger**: When concurrent sustained write requirements exceed 35 writes/sec or peak P95 write latency exceeds 1,500 ms, the storage layer should be migrated to PostgreSQL with PgBouncer.

---

### 1.3 Google Gemini API Quota & Rate Limits
- **Constraint**: Google AI Studio free-tier API keys enforce a limit of 15 Requests Per Minute (RPM) and 1,500 Requests Per Day.
- **System Defense**: The Gemini Circuit Breaker in [`major_services.py`](file:///e:/Major%20Project/online_quiz_system/major_services.py) trips upon 3 consecutive 429/403 errors, entering a 45-second cooldown and engaging instant (<0.1 ms) offline parametric synthesis.
- **Production Recommendation**: High-throughput institutional examination sessions require a paid Google Cloud Project API key with billing enabled.

---

### 1.4 Code Sandbox Polyglot Execution Scope
- **Constraint**: The live code sandbox auto-grader in [`major_services.py`](file:///e:/Major%20Project/online_quiz_system/major_services.py) runs Python code within an in-process restricted environment. C++ and Java evaluations currently operate via semantic parsing and LLM AST verification.
- **Production Recommendation**: To compile and execute raw untrusted student C++ or Java binaries on the server, integrate an isolated containerized execution runner (e.g. Judge0 or gVisor sandbox).

---

## 2. Advanced Feature Roadmap Evaluation (Future Engineering)

The following six advanced architectural enhancements have been evaluated for future development. In accordance with strict engineering standards, they are documented below with their architectural specifications and are **not** claimed as currently implemented:

---

### Roadmap Item 1: Redis-Based Distributed Quiz Session Management
- **Business Justification**: Enables multi-node horizontal scaling across multiple Gunicorn/Uvicorn worker servers behind an Nginx load balancer without tying sessions to a single SQLite file.
- **Technical Architecture**: Replace the SQLite `active_quiz_sessions` table with a Redis cluster storing JSON manifests with cryptographic keys (`quiz:session:<attempt_token>`) and automatic TTL expiration (`EXPIRE 86400`).
- **Dependencies**: Redis 7.0+, `redis-py` library.
- **Security Implications**: Redis cluster must use TLS and AUTH passwords; manifests in Redis must be encrypted at rest if sensitive questions are stored.
- **Development Complexity**: Medium (2–3 engineering days).
- **Expected Benefit**: Linear horizontal scalability to thousands of concurrent exam-takers across multiple application servers.
- **Testing Strategy**: Multi-process integration tests asserting session retrieval across independent worker processes.

---

### Roadmap Item 2: Faculty Live Proctoring through WebRTC
- **Business Justification**: Permits human invigilators in the Faculty Studio to inspect live camera feeds, detect unauthorized secondary devices, and conduct remote examinations with high integrity.
- **Technical Architecture**: Establish peer-to-peer WebRTC mesh or Selective Forwarding Unit (SFU) connections between candidate browser video elements and a multi-view grid in [`templates/faculty_studio.html`](file:///e:/Major%20Project/online_quiz_system/templates/faculty_studio.html).
- **Dependencies**: STUN/TURN servers (e.g. coturn), WebRTC SFU (e.g. mediasoup or LiveKit).
- **Security Implications**: End-to-end media encryption; candidate consent prompts; strict role gating preventing unauthorized viewing of student camera feeds.
- **Development Complexity**: High (2–3 engineering weeks).
- **Expected Benefit**: Real-time human oversight complementing automated tab-switch heuristics.
- **Testing Strategy**: Automated browser headless WebRTC connection handshakes and packet loss resilience testing.

---

### Roadmap Item 3: Learning Management System (LMS) Integration via LTI 1.3
- **Business Justification**: Eliminates manual grade exports by allowing institutional LMS platforms (Canvas, Moodle, Blackboard) to launch QuizVerse exams as seamless external tool assignments with automatic grade passback.
- **Technical Architecture**: Implement IMS Global LTI 1.3 Advantage standard using OAuth2, OpenID Connect (OIDC) third-party launch flows, and Assignment and Grade Services (AGS) REST endpoints.
- **Dependencies**: `pylti1p3`, `cryptography` (for RSA JWKS key management).
- **Security Implications**: State-parameter validation to prevent CSRF in OIDC launch; private key storage for tool JWT signing.
- **Development Complexity**: High (3–4 engineering weeks).
- **Expected Benefit**: Turnkey adoption by universities and schools without independent user account management.
- **Testing Strategy**: Mock LTI 1.3 platform test harnesses validating OIDC launch tokens and grade synchronization.

---

### Roadmap Item 4: Properly Calibrated Item Response Theory (IRT)
- **Business Justification**: Replaces coarse 3-tier difficulty (Easy, Medium, Hard) with continuous mathematical ability estimation, accurately assessing student latent proficiency ($\theta$).
- **Technical Architecture**: Implement the 2-Parameter Logistic (2PL) or 3-Parameter Logistic (3PL) IRT model:
  $$P_i(\theta) = c_i + \frac{1 - c_i}{1 + e^{-a_i(\theta - b_i)}}$$
  where $a_i$ is item discrimination, $b_i$ is item difficulty, and $c_i$ is pseudo-guessing probability. Update candidate proficiency $\theta$ after each response via Maximum Likelihood Estimation (MLE) or Expected A Posteriori (EAP).
- **Dependencies**: `scipy`, `numpy`.
- **Security Implications**: Low; purely internal algorithmic computation.
- **Development Complexity**: High (3 engineering weeks for parameter calibration algorithms and convergence safeguards).
- **Expected Benefit**: Significantly shorter tests with higher psychometric measurement precision.
- **Testing Strategy**: Synthetic student response Monte Carlo simulation verifying $\theta$ convergence across diverse skill distributions.

---

### Roadmap Item 5: Enhanced Adaptive Question Selection
- **Business Justification**: Dynamically selects the next question that maximizes Fisher Information at the candidate's current estimated ability level, eliminating unchallenging or excessively difficult items.
- **Technical Architecture**: Integrates with the IRT engine to compute Item Information Functions (IIF) across remaining candidate pool items, selecting $q^* = \arg\max_i I_i(\hat{\theta})$ with exposure control heuristics (Sympson-Hetter algorithm) to prevent item over-exposure.
- **Dependencies**: IRT module, item bank parameter tables.
- **Security Implications**: Exposure control ensures question bank security and prevents test collusion.
- **Development Complexity**: Medium-High (2 engineering weeks).
- **Expected Benefit**: Adaptive 10-question tests providing equivalent diagnostic reliability to traditional 50-question linear exams.
- **Testing Strategy**: Automated test suites evaluating item exposure distributions and standard error of measurement (SEM) reduction.

---

### Roadmap Item 6: Advanced Learning Analytics & Bayesian Knowledge Tracing (BKT)
- **Business Justification**: Models student knowledge acquisition dynamically over time rather than computing static percentage averages, forecasting when knowledge decay requires spaced repetition.
- **Technical Architecture**: Implement Bayesian Knowledge Tracing (BKT) tracking four parameters per subtopic: initial knowledge $P(L_0)$, transition probability $P(T)$, slip probability $P(S)$, and guess probability $P(G)$. Update posterior mastery probability $P(L_t | \text{obs})$ in real time.
- **Dependencies**: `numpy`, integration with student attempt logs.
- **Security Implications**: Student diagnostic profile privacy; strictly bound to authenticated student account.
- **Development Complexity**: Medium (2 engineering weeks).
- **Expected Benefit**: Predictive study schedules informing students exactly when to review specific concepts before forgetting occurs.
- **Testing Strategy**: Unit tests asserting correct Bayesian posterior updates given correct/incorrect observation sequences.
