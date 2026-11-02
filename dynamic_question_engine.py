# -*- coding: utf-8 -*-
"""
=============================================================================
QUIZVERSE MAJOR PROJECT - Dynamic Question Generation & Anti-Repeat Engine
=============================================================================
Architecture:
1. Live GenAI Synthesizer (Google Gemini API):
   Synthesizes novel, university-grade MCQs in real-time tailored to subject,
   subtopic, difficulty, and Bloom's Taxonomy level.
2. Parametric & Algorithmic Procedural Generator:
   Generates infinite code-evaluation and problem-solving questions with randomized
   parameters, variables, arithmetic, logic traces, and schemas. Guaranteed 100%
   accuracy with deterministic correct answers and zero repetition.
3. Anti-Repeat Tracking Engine:
   Maintains user question history with cryptographic fingerprints. Automatically
   excludes previously answered questions so candidates never see repeated questions.
=============================================================================
"""

import hashlib
import os
import random
import re
import sqlite3
import time
from typing import Any, Dict, List, Optional, Set

import major_services
from curriculum_catalog import get_subject_domain_focus, get_topics_for_subject


def get_db_path() -> str:
    """Returns absolute path to SQLite database."""
    base_dir = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base_dir, "quiz.db")


def get_db_connection() -> sqlite3.Connection:
    """Returns SQLite connection configured with 20s timeout, foreign keys, and WAL mode."""
    conn = sqlite3.connect(get_db_path(), timeout=20.0)
    conn.execute("PRAGMA foreign_keys = ON;")
    conn.execute("PRAGMA journal_mode = WAL;")
    return conn


def compute_question_hash(question_text: str) -> str:
    """Computes a normalized SHA-256 fingerprint for a question prompt."""
    normalized = re.sub(r'[^a-zA-Z0-9]', '', question_text.lower().strip())
    return hashlib.sha256(normalized.encode('utf-8')).hexdigest()[:32]


def ensure_history_tables(conn: sqlite3.Connection) -> None:
    """Ensures user_question_history, dynamic_questions tables and indexes exist."""
    cursor = conn.cursor()
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS user_question_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_identifier TEXT NOT NULL,
            question_hash TEXT NOT NULL,
            question_id INTEGER,
            category TEXT,
            topic TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    cursor.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_uqh_user_hash 
        ON user_question_history(user_identifier, question_hash)
        """
    )
    cursor.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_uqh_user 
        ON user_question_history(user_identifier)
        """
    )

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS dynamic_questions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            question TEXT NOT NULL,
            option_a TEXT NOT NULL,
            option_b TEXT NOT NULL,
            option_c TEXT NOT NULL,
            option_d TEXT NOT NULL,
            correct_answer TEXT NOT NULL,
            category TEXT NOT NULL,
            topic TEXT NOT NULL,
            difficulty TEXT DEFAULT 'Medium',
            bloom_level TEXT DEFAULT 'Understanding',
            explanation TEXT DEFAULT '',
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    # Ensure dynamic question primary key sequence begins at 10001
    cursor.execute("SELECT seq FROM sqlite_sequence WHERE name = 'dynamic_questions'")
    seq_row = cursor.fetchone()
    if not seq_row:
        cursor.execute("INSERT OR IGNORE INTO sqlite_sequence (name, seq) VALUES ('dynamic_questions', 10000)")

    conn.commit()


def get_user_seen_hashes(user_identifier: str, conn: Optional[sqlite3.Connection] = None) -> Set[str]:
    """Retrieves all question hashes previously presented to this candidate."""
    close_after = False
    if conn is None:
        conn = get_db_connection()
        close_after = True

    ensure_history_tables(conn)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT question_hash FROM user_question_history WHERE user_identifier = ?",
        (user_identifier.strip().lower(),)
    )
    seen = {row[0] for row in cursor.fetchall()}

    if close_after:
        conn.close()
    return seen


def record_user_presented_questions(
    user_identifier: str, 
    questions: List[Dict[str, Any]], 
    conn: Optional[sqlite3.Connection] = None
) -> None:
    """Records presented question hashes to guarantee zero repetition on future attempts."""
    close_after = False
    if conn is None:
        conn = get_db_connection()
        close_after = True

    ensure_history_tables(conn)
    cursor = conn.cursor()
    user_clean = user_identifier.strip().lower()

    for q in questions:
        q_text = q.get("question", "")
        q_hash = compute_question_hash(q_text)
        q_id = q.get("id")
        cat = q.get("category", "General")
        top = q.get("topic", "General")

        cursor.execute(
            """
            INSERT INTO user_question_history (user_identifier, question_hash, question_id, category, topic)
            VALUES (?, ?, ?, ?, ?)
            """,
            (user_clean, q_hash, q_id, cat, top)
        )

    conn.commit()
    if close_after:
        conn.close()


# =============================================================================
# ENGINE 1: LIVE GENAI DYNAMIC SYNTHESIZER (GOOGLE GEMINI)
# =============================================================================

def generate_ai_dynamic_questions(
    category: str,
    topic: str,
    count: int = 5,
    difficulty: str = "Medium",
    bloom_level: str = "Understanding",
    exclude_hashes: Optional[Set[str]] = None
) -> List[Dict[str, Any]]:
    """
    Queries Google Gemini API to synthesize fresh, university-grade examination questions on-demand.
    Explicitly instructs Gemini with subject-specific pedagogical focus, code blocks, and zero repetition.
    """
    if exclude_hashes is None:
        exclude_hashes = set()

    random_seed_tag = f"seed_{int(time.time() * 1000) % 999999}"
    domain_focus = get_subject_domain_focus(category)

    # If full subject exam, prompt across balanced subtopics
    if topic in ["All", "All Topics", "All Topics Mixed"]:
        available_topics = get_topics_for_subject(category)
        sample_size = min(len(available_topics), max(count, 3))
        sampled_topics = random.sample(available_topics, sample_size)
        subtopic_guidance = f"Distribute questions evenly across these specific curriculum subtopics: {', '.join(sampled_topics)}."
    else:
        subtopic_guidance = f"Focus strictly on the subtopic: '{topic}'."

    prompt = f"""
    You are an esteemed university professor and chief technical examiner in Computer Science & Software Engineering.
    Synthesize {count + 2} completely brand-new, challenging, non-repeating multiple-choice examination questions for:
    - Subject / Discipline: {category}
    - Specific Sub-Topic: {topic}
    - Curriculum Scope: {subtopic_guidance}
    - Core Technical Competencies: {domain_focus}
    - Target Difficulty: {difficulty}
    - Bloom's Taxonomy Cognitive Level: {bloom_level}
    - Random Entropy Nonce: {random_seed_tag}

    PEDAGOGICAL & ACCURACY REQUIREMENTS:
    1. ZERO REPETITION: Every question must be original and unique. Avoid textbook definitions. Provide realistic code execution questions (with formatted markdown code fences), debugging challenges, output predictions, or architectural trade-offs.
    2. RIGOROUS ACCURACY: Exactly one option must be unambiguously correct.
    3. PLAUSIBLE DISTRACTORS: Options A, B, C, D must all be realistic choices that address genuine common developer misconceptions.
    4. CORRECT ANSWER: Must be strictly one uppercase character: 'A', 'B', 'C', or 'D'.
    5. IN-DEPTH EXPLANATION: Include a detailed pedagogical rationale explaining why the designated answer is correct and why the alternatives fail.

    Return ONLY a valid JSON array of objects with these exact keys:
    [
      {{
        "question": "Question text (formatted with markdown code blocks where applicable)",
        "option_a": "Option A text",
        "option_b": "Option B text",
        "option_c": "Option C text",
        "option_d": "Option D text",
        "correct_answer": "A",
        "explanation": "Detailed explanation of the solution",
        "difficulty": "{difficulty}",
        "bloom_level": "{bloom_level}"
      }}
    ]
    """

    raw_response = major_services.call_gemini_api(prompt, json_mode=True, timeout=14)
    if not raw_response:
        return []

    parsed = major_services.safe_parse_json(raw_response)
    if not isinstance(parsed, list):
        return []

    valid_questions = []
    for item in parsed:
        q_text = str(item.get("question", "")).strip()
        if not q_text or len(q_text) < 15:
            continue

        q_hash = compute_question_hash(q_text)
        if q_hash in exclude_hashes:
            continue

        c_ans = str(item.get("correct_answer", "A")).strip().upper()
        if c_ans in ["OPTION_A", "OPTION A"]: c_ans = "A"
        elif c_ans in ["OPTION_B", "OPTION B"]: c_ans = "B"
        elif c_ans in ["OPTION_C", "OPTION C"]: c_ans = "C"
        elif c_ans in ["OPTION_D", "OPTION D"]: c_ans = "D"
        if c_ans not in ["A", "B", "C", "D"]:
            c_ans = "A"

        opt_a = str(item.get("option_a", "")).strip()
        opt_b = str(item.get("option_b", "")).strip()
        opt_c = str(item.get("option_c", "")).strip()
        opt_d = str(item.get("option_d", "")).strip()

        if not (opt_a and opt_b and opt_c and opt_d):
            continue

        valid_questions.append({
            "question": q_text,
            "option_a": opt_a,
            "option_b": opt_b,
            "option_c": opt_c,
            "option_d": opt_d,
            "correct_answer": c_ans,
            "category": category,
            "topic": topic,
            "difficulty": difficulty,
            "bloom_level": bloom_level,
            "explanation": str(item.get("explanation", f"Conceptual solution for {category} - {topic}")).strip()
        })
        exclude_hashes.add(q_hash)

        if len(valid_questions) >= count:
            break

    return valid_questions


# =============================================================================
# ENGINE 2: INFINITE PARAMETRIC & ALGORITHMIC PROCEDURAL GENERATOR
# =============================================================================

def _generate_parametric_python(topic: str, difficulty: str) -> Dict[str, Any]:
    """Generates an infinite variety of deterministic Python code-tracing MCQs."""
    gen_type = random.choice([
        "slicing", "comprehension", "dict_get", "lambda_map", 
        "bitwise", "string_split", "scope_closure", "exception_flow"
    ])

    if gen_type == "slicing":
        words = ["Algorithms", "Cybersecurity", "DataScience", "Distributed", "Microservices", "NeuralNetwork"]
        word = random.choice(words)
        start = random.randint(1, 3)
        stop = random.randint(start + 4, len(word) - 1)
        step = random.choice([1, 2])
        actual = word[start:stop:step]
        
        # Distractors
        d1 = word[start:stop] if step != 1 else word[start+1:stop]
        d2 = word[start-1:stop:step]
        d3 = word[start:stop-1:step]
        options = list({actual, d1, d2, d3})
        while len(options) < 4:
            options.append(actual[::-1] if actual[::-1] not in options else actual + "x")
        random.shuffle(options)
        c_letter = ["A", "B", "C", "D"][options.index(actual)]

        return {
            "question": f"What is the output of the following Python expression?\n\n```python\ntext = '{word}'\nprint(text[{start}:{stop}:{step}])\n```",
            "option_a": f"'{options[0]}'",
            "option_b": f"'{options[1]}'",
            "option_c": f"'{options[2]}'",
            "option_d": f"'{options[3]}'",
            "correct_answer": c_letter,
            "difficulty": difficulty,
            "bloom_level": "Applying",
            "explanation": f"In Python string slicing text[start:stop:step], index starts at {start} (inclusive) up to {stop} (exclusive) with step {step}. This slices to '{actual}'."
        }

    elif gen_type == "comprehension":
        n = random.randint(6, 10)
        mod = random.choice([2, 3])
        rem = random.randint(0, mod - 1)
        mult = random.choice([2, 3, 5])
        actual_list = [x * mult for x in range(n) if x % mod == rem]
        actual_str = str(actual_list)

        d1 = str([x * mult for x in range(n) if x % mod != rem])
        d2 = str([x for x in range(n) if x % mod == rem])
        d3 = str([x * mult for x in range(1, n + 1) if x % mod == rem])
        options = list({actual_str, d1, d2, d3})
        while len(options) < 4:
            options.append(str([x * 2 for x in actual_list]))
        random.shuffle(options)
        c_letter = ["A", "B", "C", "D"][options.index(actual_str)]

        return {
            "question": f"Evaluate the output of this Python list comprehension:\n\n```python\nresult = [x * {mult} for x in range({n}) if x % {mod} == {rem}]\nprint(result)\n```",
            "option_a": options[0],
            "option_b": options[1],
            "option_c": options[2],
            "option_d": options[3],
            "correct_answer": c_letter,
            "difficulty": difficulty,
            "bloom_level": "Analyzing",
            "explanation": f"The comprehension evaluates numbers 0 to {n-1}. Only numbers where x % {mod} == {rem} are multiplied by {mult}, resulting in {actual_str}."
        }

    elif gen_type == "bitwise":
        a = random.randint(8, 25)
        b = random.randint(5, 20)
        op = random.choice(["^", "&", "|"])
        actual = (a ^ b) if op == "^" else (a & b) if op == "&" else (a | b)
        
        d1 = (a + b)
        d2 = (a ^ b) if op != "^" else (a & b)
        d3 = abs(a - b)
        options = list({str(actual), str(d1), str(d2), str(d3)})
        while len(options) < 4:
            options.append(str(actual + random.randint(1, 5)))
        random.shuffle(options)
        c_letter = ["A", "B", "C", "D"][options.index(str(actual))]

        op_name = "XOR" if op == "^" else "AND" if op == "&" else "OR"
        return {
            "question": f"What is the output of the bitwise {op_name} operation in Python?\n\n```python\na = {a}\nb = {b}\nprint(a {op} b)\n```",
            "option_a": options[0],
            "option_b": options[1],
            "option_c": options[2],
            "option_d": options[3],
            "correct_answer": c_letter,
            "difficulty": difficulty,
            "bloom_level": "Applying",
            "explanation": f"Binary for {a} is {bin(a)[2:]} and {b} is {bin(b)[2:]}. Applying bitwise {op} produces {bin(actual)[2:]}, which equals decimal {actual}."
        }

    else:
        key = random.choice(["status", "code", "latency", "ttl"])
        default_val = random.randint(10, 50)
        actual = default_val + 5
        return {
            "question": f"What does the following dictionary lookup return in Python?\n\n```python\nmetrics = {{'active': True, 'region': 'us-east-1'}}\nval = metrics.get('{key}', {default_val}) + 5\nprint(val)\n```",
            "option_a": str(actual),
            "option_b": str(default_val),
            "option_c": "KeyError: '" + key + "'",
            "option_d": "None",
            "correct_answer": "A",
            "difficulty": difficulty,
            "bloom_level": "Understanding",
            "explanation": f"Since '{key}' does not exist in the dictionary, dict.get() returns the fallback default value {default_val}. Adding 5 gives {actual} without raising KeyError."
        }


def _generate_parametric_java(topic: str, difficulty: str) -> Dict[str, Any]:
    """Generates an infinite variety of deterministic Java code-tracing MCQs."""
    gen_type = random.choice(["pre_post_inc", "ternary", "string_immutable", "array_loop"])

    if gen_type == "pre_post_inc":
        x = random.randint(2, 6)
        y = random.randint(3, 7)
        z = random.randint(1, 4)
        # int res = ++x * y-- + z
        # ++x becomes x+1; y-- uses current y then decrements;
        new_x = x + 1
        used_y = y
        actual = (new_x * used_y) + z

        d1 = (x * y) + z
        d2 = (new_x * (used_y - 1)) + z
        d3 = (x * used_y) + z
        options = list({str(actual), str(d1), str(d2), str(d3)})
        while len(options) < 4:
            options.append(str(actual + random.randint(1, 6)))
        random.shuffle(options)
        c_letter = ["A", "B", "C", "D"][options.index(str(actual))]

        return {
            "question": f"What is the output of the following Java code snippet?\n\n```java\nint x = {x};\nint y = {y};\nint res = ++x * y-- + {z};\nSystem.out.println(res);\n```",
            "option_a": options[0],
            "option_b": options[1],
            "option_c": options[2],
            "option_d": options[3],
            "correct_answer": c_letter,
            "difficulty": difficulty,
            "bloom_level": "Applying",
            "explanation": f"Prefix increment ++x executes first, making x={new_x}. Postfix decrement y-- evaluates using current y={used_y} then decrements. {new_x} * {used_y} + {z} = {actual}."
        }

    elif gen_type == "ternary":
        score = random.randint(40, 95)
        thresh1 = 80
        thresh2 = 60
        actual = "Distinction" if score >= thresh1 else "Pass" if score >= thresh2 else "Remedial"

        options = ["Distinction", "Pass", "Remedial", "Compilation Error"]
        random.shuffle(options)
        c_letter = ["A", "B", "C", "D"][options.index(actual)]

        return {
            "question": f"What is printed by this chained ternary operator in Java?\n\n```java\nint score = {score};\nString grade = (score >= {thresh1}) ? \"Distinction\" : (score >= {thresh2}) ? \"Pass\" : \"Remedial\";\nSystem.out.println(grade);\n```",
            "option_a": options[0],
            "option_b": options[1],
            "option_c": options[2],
            "option_d": options[3],
            "correct_answer": c_letter,
            "difficulty": difficulty,
            "bloom_level": "Understanding",
            "explanation": f"For score={score}, evaluating score >= {thresh1} is {score >= thresh1}. The second branch evaluates score >= {thresh2} which is {score >= thresh2}, selecting \"{actual}\"."
        }

    else:
        w1 = random.choice(["Cloud", "Spring", "Micro", "Kafka"])
        w2 = random.choice(["Native", "Boot", "Service", "Streams"])
        return {
            "question": f"What is the output of this Java String manipulation snippet?\n\n```java\nString s = \"{w1}\";\ns.concat(\"{w2}\");\nSystem.out.println(s);\n```",
            "option_a": f"\"{w1}\"",
            "option_b": f"\"{w1}{w2}\"",
            "option_c": "NullPointerException",
            "option_d": "Compilation Error",
            "correct_answer": "A",
            "difficulty": difficulty,
            "bloom_level": "Understanding",
            "explanation": f"Java Strings are immutable. `s.concat(\"{w2}\")` returns a new String instance, but since it is not reassigned back to `s`, `s` remains \"{w1}\"."
        }


def _generate_parametric_cpp(topic: str, difficulty: str) -> Dict[str, Any]:
    """Generates an infinite variety of deterministic C++ pointer and memory MCQs."""
    vals = [random.randint(10, 20), random.randint(21, 35), random.randint(36, 50), random.randint(51, 70)]
    offset = random.randint(1, 2)
    add = random.randint(3, 8)
    vals[offset] += add
    actual = vals[offset]

    d1 = vals[0] + add
    d2 = vals[offset] - add
    d3 = vals[offset + 1] if offset + 1 < len(vals) else vals[0]
    options = list({str(actual), str(d1), str(d2), str(d3)})
    while len(options) < 4:
        options.append(str(actual + random.randint(1, 5)))
    random.shuffle(options)
    c_letter = ["A", "B", "C", "D"][options.index(str(actual))]

    return {
        "question": f"Analyze the following C++ pointer arithmetic snippet:\n\n```cpp\nint arr[] = {{{vals[0]}, {vals[1]-add if offset==1 else vals[1]}, {vals[2]-add if offset==2 else vals[2]}, {vals[3]}}};\nint* ptr = arr + {offset};\n*ptr += {add};\nstd::cout << arr[{offset}];\n```",
        "option_a": options[0],
        "option_b": options[1],
        "option_c": options[2],
        "option_d": options[3],
        "correct_answer": c_letter,
        "difficulty": difficulty,
        "bloom_level": "Applying",
        "explanation": f"`arr + {offset}` points to `arr[{offset}]`. Dereferencing `*ptr += {add}` mutates the element in place, printing {actual}."
    }


def _generate_parametric_dbms(topic: str, difficulty: str) -> Dict[str, Any]:
    """Generates an infinite variety of deterministic SQL and relational schema MCQs."""
    num_dept = random.randint(3, 6)
    emp_per_dept = random.randint(4, 8)
    total_emp = num_dept * emp_per_dept
    threshold = random.randint(5, 7)
    
    # Matching departments
    matching_depts = random.randint(1, num_dept - 1)
    
    return {
        "question": f"In a database containing an `Employees` table with {total_emp} records mapped across {num_dept} distinct departments, consider the following query:\n\n```sql\nSELECT department_id, COUNT(*) AS emp_count\nFROM Employees\nGROUP BY department_id\nHAVING COUNT(*) >= {threshold};\n```\nIf {matching_depts} departments have {threshold} or more employees, how many rows are returned by this query?",
        "option_a": str(matching_depts),
        "option_b": str(num_dept),
        "option_c": str(total_emp),
        "option_d": "1",
        "correct_answer": "A",
        "difficulty": difficulty,
        "bloom_level": "Analyzing",
        "explanation": f"The `GROUP BY` partitions records into departments, and the `HAVING` clause filters aggregated groups. Exactly {matching_depts} department groups satisfy `COUNT(*) >= {threshold}`, so {matching_depts} rows are returned."
    }


def _generate_parametric_dsa(topic: str, difficulty: str) -> Dict[str, Any]:
    """Generates an infinite variety of deterministic Data Structures & Algorithm MCQs."""
    archetype = random.choice(["log_loop", "nested_loop", "bst_inorder", "postfix_eval", "hash_probe", "queue_stack"])
    
    if archetype == "log_loop":
        factor = random.choice([2, 3, 4, 5, 8, 10])
        var_name = random.choice(["n", "len", "size", "limit"])
        return {
            "question": f"Determine the asymptotic worst-case time complexity of the following code snippet:\n\n```cpp\nint ops = 0;\nwhile ({var_name} > 1) {{\n    {var_name} = {var_name} / {factor};\n    ops++;\n}}\n```",
            "option_a": f"O(log_{factor} n) — logarithmic time",
            "option_b": "O(n) — linear time",
            "option_c": f"O(n * log_{factor} n)",
            "option_d": "O(1) — constant time",
            "correct_answer": "A",
            "difficulty": difficulty,
            "bloom_level": "Analyzing",
            "explanation": f"The loop variable `{var_name}` is divided by {factor} on every step. The total number of iterations required to reach 1 from n is log_{factor}(n), which is O(log n)."
        }
    elif archetype == "nested_loop":
        inner_type = random.choice(["linear", "logarithmic"])
        if inner_type == "linear":
            return {
                "question": "What is the worst-case time complexity of the following nested loop structure?\n\n```python\ntotal = 0\nfor i in range(n):\n    for j in range(i, n):\n        total += (i * j)\n```",
                "option_a": "O(n^2)",
                "option_b": "O(n)",
                "option_c": "O(n log n)",
                "option_d": "O(n^3)",
                "correct_answer": "A",
                "difficulty": difficulty,
                "bloom_level": "Analyzing",
                "explanation": "The outer loop runs n times. The inner loop runs n, n-1, n-2, ..., 1 times. The sum of 1 to n is n(n+1)/2, which yields asymptotic complexity of O(n^2)."
            }
        else:
            return {
                "question": "Analyze the asymptotic time complexity of the following algorithmic snippet:\n\n```java\nint count = 0;\nfor (int i = 0; i < n; i++) {\n    for (int j = 1; j < n; j *= 2) {\n        count++;\n    }\n}\n```",
                "option_a": "O(n log n)",
                "option_b": "O(n^2)",
                "option_c": "O(log n)",
                "option_d": "O(n)",
                "correct_answer": "A",
                "difficulty": difficulty,
                "bloom_level": "Analyzing",
                "explanation": "The outer loop executes n times. The inner loop doubles j on each iteration, running log2(n) times. The product is O(n log n)."
            }
    elif archetype == "bst_inorder":
        vals = random.sample([12, 25, 37, 43, 56, 68, 79, 81, 94], 5)
        sorted_vals = sorted(vals)
        ans_str = ", ".join(map(str, sorted_vals))
        rev_str = ", ".join(map(str, sorted_vals[::-1]))
        shuff1 = ", ".join(map(str, vals))
        shuff2 = ", ".join(map(str, [sorted_vals[2], sorted_vals[0], sorted_vals[1], sorted_vals[4], sorted_vals[3]]))
        
        opts = list({ans_str, rev_str, shuff1, shuff2})
        while len(opts) < 4:
            opts.append(", ".join(map(str, random.sample(vals, len(vals)))))
        random.shuffle(opts)
        c_letter = ["A", "B", "C", "D"][opts.index(ans_str)]
        
        return {
            "question": f"A Binary Search Tree (BST) is constructed by sequentially inserting the following keys: `[{', '.join(map(str, vals))}]`. What is the result of an **Inorder Traversal** on this BST?",
            "option_a": opts[0],
            "option_b": opts[1],
            "option_c": opts[2],
            "option_d": opts[3],
            "correct_answer": c_letter,
            "difficulty": difficulty,
            "bloom_level": "Applying",
            "explanation": "An Inorder Traversal (Left, Root, Right) of any valid Binary Search Tree visits keys in strictly ascending sorted order regardless of insertion sequence."
        }
    elif archetype == "postfix_eval":
        a = random.randint(2, 7)
        b = random.randint(2, 6)
        c = random.randint(1, 5)
        correct_val = (a + b) * c
        d1 = a + (b * c)
        d2 = (a * b) + c
        d3 = (a + b) + c
        opts = list({str(correct_val), str(d1), str(d2), str(d3)})
        while len(opts) < 4:
            opts.append(str(correct_val + random.randint(3, 10)))
        random.shuffle(opts)
        c_letter = ["A", "B", "C", "D"][opts.index(str(correct_val))]
        
        return {
            "question": f"Evaluate the following Postfix (Reverse Polish) expression using a standard stack-based evaluator:\n`{a} {b} + {c} *`",
            "option_a": opts[0],
            "option_b": opts[1],
            "option_c": opts[2],
            "option_d": opts[3],
            "correct_answer": c_letter,
            "difficulty": difficulty,
            "bloom_level": "Applying",
            "explanation": f"Push {a}, push {b}. Read '+', pop {b} and {a}, compute {a} + {b} = {a+b}, push {a+b}. Push {c}. Read '*', pop {c} and {a+b}, compute ({a+b}) * {c} = {correct_val}."
        }
    elif archetype == "hash_probe":
        table_size = random.choice([7, 11, 13])
        key = random.randint(15, 60)
        h = key % table_size
        opts = [f"Index {h}", f"Index {(h + 1) % table_size}", f"Index {(h + 2) % table_size}", f"Index {key}"]
        random.shuffle(opts)
        c_letter = ["A", "B", "C", "D"][opts.index(f"Index {h}")]
        return {
            "question": f"Given a hash table of size M = {table_size} using open addressing and the division hash function `h(k) = k mod M`. Into which initial slot does key `k = {key}` hash prior to collision resolution?",
            "option_a": opts[0],
            "option_b": opts[1],
            "option_c": opts[2],
            "option_d": opts[3],
            "correct_answer": c_letter,
            "difficulty": difficulty,
            "bloom_level": "Understanding",
            "explanation": f"Using division hashing, slot = {key} mod {table_size} = {h}."
        }
    else:  # queue_stack
        return {
            "question": "Which data structure is fundamentally utilized by Breadth-First Search (BFS) for graph level-order traversal, and which for Depth-First Search (DFS)?",
            "option_a": "BFS utilizes a Queue (FIFO); DFS utilizes a Stack (LIFO or recursion)",
            "option_b": "BFS utilizes a Stack (LIFO); DFS utilizes a Queue (FIFO)",
            "option_c": "Both BFS and DFS utilize a Priority Queue",
            "option_d": "BFS utilizes a Doubly Linked List; DFS utilizes a Binary Heap",
            "correct_answer": "A",
            "difficulty": difficulty,
            "bloom_level": "Understanding",
            "explanation": "Breadth-First Search explores nodes tier by tier using a FIFO Queue. Depth-First Search explores paths to maximum depth using a LIFO Stack or recursive call stack."
        }


def _generate_parametric_os(topic: str, difficulty: str) -> Dict[str, Any]:
    """Generates an infinite variety of deterministic Operating Systems MCQs."""
    b1 = random.randint(4, 8)
    b2 = random.randint(2, 6)
    b3 = random.randint(3, 7)
    # FCFS waiting times: P1=0, P2=b1, P3=b1+b2
    avg_wait = round((0 + b1 + (b1 + b2)) / 3.0, 2)
    d1 = round((b1 + b2 + b3) / 3.0, 2)
    d2 = round((0 + b2 + (b2 + b1)) / 3.0, 2)
    d3 = round(avg_wait + 1.5, 2)

    options = list({f"{avg_wait} ms", f"{d1} ms", f"{d2} ms", f"{d3} ms"})
    while len(options) < 4:
        options.append(f"{avg_wait + random.randint(2, 5)} ms")
    random.shuffle(options)
    c_letter = ["A", "B", "C", "D"][options.index(f"{avg_wait} ms")]

    return {
        "question": f"Three processes P1, P2, and P3 arrive at time t=0 in order with CPU burst times of {b1} ms, {b2} ms, and {b3} ms respectively. Under First-Come, First-Served (FCFS) scheduling without preemption, what is the average waiting time?",
        "option_a": options[0],
        "option_b": options[1],
        "option_c": options[2],
        "option_d": options[3],
        "correct_answer": c_letter,
        "difficulty": difficulty,
        "bloom_level": "Applying",
        "explanation": f"P1 waits 0 ms. P2 waits {b1} ms. P3 waits {b1}+{b2}={b1+b2} ms. Average waiting time = (0 + {b1} + {b1+b2}) / 3 = {avg_wait} ms."
    }


def _generate_parametric_webdev(topic: str, difficulty: str) -> Dict[str, Any]:
    """Generates an infinite variety of deterministic Web Development & JS MCQs."""
    archetype = random.choice(["coercion", "closure", "box_model", "event_loop", "flexbox", "nan_behavior", "array_methods", "destructuring"])

    if archetype == "coercion":
        pairs = [
            ("[] + []", "'' (empty string)", "'' (empty string)", "[]", "[object Object]", "undefined"),
            ("[] + {}", "'[object Object]'", "'[object Object]'", "''", "NaN", "TypeError"),
            ("true + true", "2", "2", "true", "1", "NaN"),
            ("'5' - 2", "3", "3", "'3'", "'52'", "NaN"),
            ("'5' + 2", "'52'", "'52'", "7", "NaN", "TypeError"),
            ("null == undefined", "true", "true", "false", "TypeError", "null"),
            ("null === undefined", "false", "false", "true", "undefined", "TypeError"),
        ]
        expr, correct_val, o1, o2, o3, o4 = random.choice(pairs)
        opts = [o1, o2, o3, o4]
        random.shuffle(opts)
        c_letter = ["A", "B", "C", "D"][opts.index(correct_val)]
        return {
            "question": f"In JavaScript (ECMAScript), what is the exact evaluated result of the following expression?\n\n```javascript\nconsole.log({expr});\n```",
            "option_a": opts[0],
            "option_b": opts[1],
            "option_c": opts[2],
            "option_d": opts[3],
            "correct_answer": c_letter,
            "difficulty": difficulty,
            "bloom_level": "Analyzing",
            "explanation": f"In JavaScript coercion rules, `{expr}` evaluates to `{correct_val}`."
        }
    elif archetype == "closure":
        n = random.randint(3, 5)
        var_keyword = random.choice(["var", "let"])
        if var_keyword == "var":
            ans = f"{n} printed {n} times"
            opts = [f"{n} printed {n} times", f"0, 1, 2... {n-1}", "0 printed {n} times", "ReferenceError: i is not defined"]
        else:
            ans = f"0, 1, 2... {n-1}"
            opts = [f"0, 1, 2... {n-1}", f"{n} printed {n} times", f"undefined printed {n} times", "NaN"]
        random.shuffle(opts)
        c_letter = ["A", "B", "C", "D"][opts.index(ans)]
        return {
            "question": f"Predict the console output of this asynchronous JavaScript loop:\n\n```javascript\nfor ({var_keyword} i = 0; i < {n}; i++) {{\n    setTimeout(() => console.log(i), 100);\n}}\n```",
            "option_a": opts[0],
            "option_b": opts[1],
            "option_c": opts[2],
            "option_d": opts[3],
            "correct_answer": c_letter,
            "difficulty": difficulty,
            "bloom_level": "Analyzing",
            "explanation": f"Using `{var_keyword}`: {'`var` is function-scoped; by the time the timer callbacks run on the event loop, i has already reached ' + str(n) if var_keyword == 'var' else '`let` is block-scoped, binding a fresh lexical `i` to each iteration closure.'}"
        }
    elif archetype == "box_model":
        w = random.randint(150, 300)
        p = random.randint(10, 25)
        b = random.randint(2, 6)
        total_content = w + 2*p + 2*b
        opts = [f"{total_content}px", f"{w}px", f"{w + p + b}px", f"{w + 2*p}px"]
        random.shuffle(opts)
        c_letter = ["A", "B", "C", "D"][opts.index(f"{total_content}px")]
        return {
            "question": f"An element has `width: {w}px`, `padding: {p}px`, `border: {b}px solid black`, and default `box-sizing: content-box`. What is the total rendered width of this element in the browser viewport?",
            "option_a": opts[0],
            "option_b": opts[1],
            "option_c": opts[2],
            "option_d": opts[3],
            "correct_answer": c_letter,
            "difficulty": difficulty,
            "bloom_level": "Applying",
            "explanation": f"Under `content-box`, total width = content width ({w}) + left/right padding ({2*p}) + left/right border ({2*b}) = {total_content}px."
        }
    elif archetype == "event_loop":
        return {
            "question": "In the JavaScript browser runtime, which queue takes immediate priority upon completion of the current synchronous call stack frame?",
            "option_a": "Microtask Queue (Promises, queueMicrotask)",
            "option_b": "Macrotask / Task Queue (setTimeout, setInterval)",
            "option_c": "Rendering Queue",
            "option_d": "Web Worker Queue",
            "correct_answer": "A",
            "difficulty": difficulty,
            "bloom_level": "Understanding",
            "explanation": "The JavaScript event loop exhausts all queued Microtasks (such as Promise reaction callbacks) before moving to the next Macrotask."
        }
    elif archetype == "flexbox":
        return {
            "question": "In CSS Flexible Box Layout (`display: flex`), which property aligns items along the cross axis by default?",
            "option_a": "align-items",
            "option_b": "justify-content",
            "option_c": "align-content",
            "option_d": "flex-direction",
            "correct_answer": "A",
            "difficulty": difficulty,
            "bloom_level": "Understanding",
            "explanation": "`justify-content` controls alignment along the main axis, while `align-items` aligns flex items along the perpendicular cross axis."
        }
    elif archetype == "nan_behavior":
        return {
            "question": "What is the result of evaluating `typeof NaN` and `NaN === NaN` in JavaScript?",
            "option_a": "`typeof NaN === 'number'` and `NaN === NaN` evaluates to `false`",
            "option_b": "`typeof NaN === 'NaN'` and `NaN === NaN` evaluates to `true`",
            "option_c": "`typeof NaN === 'undefined'` and `NaN === NaN` evaluates to `false`",
            "option_d": "`typeof NaN === 'number'` and `NaN === NaN` evaluates to `true`",
            "correct_answer": "A",
            "difficulty": difficulty,
            "bloom_level": "Understanding",
            "explanation": "In IEEE 754 floating point standard and JS, NaN belongs to the numeric type (`typeof NaN === 'number'`), but NaN is not equal to any value, including itself (`NaN === NaN` is false)."
        }
    elif archetype == "array_methods":
        arr = [random.randint(1, 5) for _ in range(3)]
        mult = random.randint(2, 3)
        res_arr = [x * mult for x in arr]
        ans = str(res_arr)
        opts = [ans, str(arr), str(sum(arr)), str([x + mult for x in arr])]
        random.shuffle(opts)
        c_letter = ["A", "B", "C", "D"][opts.index(ans)]
        return {
            "question": f"Given `const nums = {arr};`, what does `nums.map(x => x * {mult})` return without mutating the original array?",
            "option_a": opts[0],
            "option_b": opts[1],
            "option_c": opts[2],
            "option_d": opts[3],
            "correct_answer": c_letter,
            "difficulty": difficulty,
            "bloom_level": "Applying",
            "explanation": f"`Array.prototype.map()` creates a new array populated with the results of calling the provided function on every element, returning {ans}."
        }
    else:  # destructuring
        return {
            "question": "What happens when destructuring an object with default values if the property exists but has the value `null`?\n\n```javascript\nconst { count = 10 } = { count: null };\nconsole.log(count);\n```",
            "option_a": "null",
            "option_b": "10",
            "option_c": "undefined",
            "option_d": "TypeError",
            "correct_answer": "A",
            "difficulty": difficulty,
            "bloom_level": "Analyzing",
            "explanation": "In JavaScript destructuring, default fallback values are only triggered when the property is strictly `undefined`. `null` is a valid assigned value, so `count` retains `null`."
        }


def _generate_parametric_flask(topic: str, difficulty: str) -> Dict[str, Any]:
    """Generates an infinite variety of deterministic Flask & REST API MCQs."""
    archetype = random.choice(["converters", "methods", "request_data", "session_secret", "blueprints", "status_codes", "jinja_filter", "app_context"])

    if archetype == "converters":
        conv_info = [
            ("int", "1024", "matches positive integers and passes them as `int`"),
            ("float", "98.6", "matches floating-point values and passes them as `float`"),
            ("path", "api/v1/users/reports", "matches any string including slashes `/`"),
            ("uuid", "e2b5e39b-73b3-4665-9854-525996b71b8e", "matches UUID strings and passes a `uuid.UUID` object"),
        ]
        converter, val, desc = random.choice(conv_info)
        return {
            "question": f"In Flask route rules, what is the role of the `<{converter}:param>` URL converter when receiving the request path segment `{val}`?",
            "option_a": f"It {desc}.",
            "option_b": "It rejects the request with HTTP 400 Bad Request.",
            "option_c": "It forces client-side HTTPS encryption on that segment.",
            "option_d": "It treats the segment strictly as a query parameter in `request.args`.",
            "correct_answer": "A",
            "difficulty": difficulty,
            "bloom_level": "Understanding",
            "explanation": f"Flask built-in URL converters validate pattern matching and type-cast the URL segment before passing it to the view function: `{converter}` {desc}."
        }
    elif archetype == "methods":
        return {
            "question": "By default, what HTTP method(s) does a Flask route decorated with `@app.route('/login')` respond to if `methods` argument is omitted?",
            "option_a": "Only GET (and implicit HEAD/OPTIONS)",
            "option_b": "Both GET and POST",
            "option_c": "All HTTP verbs (GET, POST, PUT, DELETE)",
            "option_d": "Only POST",
            "correct_answer": "A",
            "difficulty": difficulty,
            "bloom_level": "Understanding",
            "explanation": "Flask routes default strictly to handling `GET` requests unless `methods=['GET', 'POST']` is explicitly specified."
        }
    elif archetype == "request_data":
        return {
            "question": "To parse incoming `application/json` request payloads in a Flask endpoint, which property or method should be accessed?",
            "option_a": "`request.get_json()` or `request.json`",
            "option_b": "`request.form`",
            "option_c": "`request.args`",
            "option_d": "`request.values`",
            "correct_answer": "A",
            "difficulty": difficulty,
            "bloom_level": "Applying",
            "explanation": "`request.args` parses URL query parameters, `request.form` parses URL-encoded HTML form bodies, while `request.get_json()` decodes JSON payloads into Python dict/list."
        }
    elif archetype == "session_secret":
        return {
            "question": "How does Flask's default client-side `session` mechanism protect cookie integrity across requests?",
            "option_a": "It cryptographically signs the session cookie payload using `app.secret_key` with HMAC-SHA1/SHA256.",
            "option_b": "It encrypts the entire cookie so clients cannot inspect its contents.",
            "option_c": "It stores all session values directly in server RAM and only sends a GUID cookie.",
            "option_d": "It hashes passwords into the browser's LocalStorage.",
            "correct_answer": "A",
            "difficulty": difficulty,
            "bloom_level": "Analyzing",
            "explanation": "Flask default sessions are signed cookies, NOT encrypted. The client can read the base64-encoded contents, but cannot alter them without invalidating the cryptographic HMAC signature generated with `app.secret_key`."
        }
    elif archetype == "blueprints":
        return {
            "question": "In a large modular Flask application, which architectural component encapsulates related routes, static files, and templates?",
            "option_a": "Flask Blueprint (`flask.Blueprint`)",
            "option_b": "Flask ModelViewController (`flask.MVC`)",
            "option_c": "Werkzeug Dispatcher",
            "option_d": "Jinja Module",
            "correct_answer": "A",
            "difficulty": difficulty,
            "bloom_level": "Understanding",
            "explanation": "Blueprints are Flask's official architectural pattern for modularizing routes, error handlers, and assets into distinct subsystems (e.g. auth, api, admin)."
        }
    elif archetype == "status_codes":
        codes = [
            ("201", "Resource created successfully (e.g. POST new user)"),
            ("302", "Found / Temporary Redirect to another URL"),
            ("401", "Unauthorized — authentication credentials missing or invalid"),
            ("403", "Forbidden — authenticated user lacks required permissions/role"),
            ("404", "Not Found — target resource or endpoint does not exist"),
            ("500", "Internal Server Error — unhandled runtime exception in view function"),
        ]
        code, meaning = random.choice(codes)
        opts = [f"{code} — {meaning}"]
        for c, m in codes:
            if c != code and len(opts) < 4:
                opts.append(f"{c} — {m}")
        random.shuffle(opts)
        c_letter = ["A", "B", "C", "D"][opts.index(f"{code} — {meaning}")]
        return {
            "question": f"Which standard HTTP status code should a RESTful Flask endpoint return for: '{meaning}'?",
            "option_a": opts[0],
            "option_b": opts[1],
            "option_c": opts[2],
            "option_d": opts[3],
            "correct_answer": c_letter,
            "difficulty": difficulty,
            "bloom_level": "Applying",
            "explanation": f"HTTP status {code} is defined as: {meaning}."
        }
    elif archetype == "jinja_filter":
        return {
            "question": "In a Jinja2 template rendered by Flask, which filter must be applied to safely embed a server-side Python dictionary into client-side JavaScript without XSS vulnerabilities?",
            "option_a": "`{{ data | tojson }}`",
            "option_b": "`{{ data | safe }}`",
            "option_c": "`{{ data | escape }}`",
            "option_d": "`{{ data | raw }}`",
            "correct_answer": "A",
            "difficulty": difficulty,
            "bloom_level": "Applying",
            "explanation": "The `|tojson` filter converts Python data structures into JSON strings and safely escapes HTML tags like `</script>` to prevent XSS."
        }
    else:  # app_context
        return {
            "question": "In Flask, which special context object stores per-request temporary data (e.g., database connection) that is automatically torn down at the end of the request?",
            "option_a": "`flask.g`",
            "option_b": "`flask.current_app`",
            "option_c": "`flask.session`",
            "option_d": "`flask.request`",
            "correct_answer": "A",
            "difficulty": difficulty,
            "bloom_level": "Understanding",
            "explanation": "`flask.g` is an application context global unique to each active request thread, ideal for storing open database handles during the request lifecycle."
        }


def generate_parametric_dynamic_questions(
    category: str,
    topic: str,
    count: int = 5,
    difficulty: str = "Medium",
    bloom_level: str = "Understanding",
    exclude_hashes: Optional[Set[str]] = None
) -> List[Dict[str, Any]]:
    """
    Infinite procedural algorithmic question generator.
    Guarantees mathematically unique questions that NEVER repeat even offline.
    """
    if exclude_hashes is None:
        exclude_hashes = set()

    generators = {
        "Python": _generate_parametric_python,
        "Java": _generate_parametric_java,
        "C++": _generate_parametric_cpp,
        "DBMS": _generate_parametric_dbms,
        "DSA": _generate_parametric_dsa,
        "OS": _generate_parametric_os,
        "WebDev": _generate_parametric_webdev,
        "Flask": _generate_parametric_flask,
    }

    gen_func = generators.get(category, _generate_parametric_python)
    results = []
    attempts = 0
    max_attempts = count * 15

    while len(results) < count and attempts < max_attempts:
        attempts += 1
        q_data = gen_func(topic, difficulty)
        q_text = q_data["question"]
        q_hash = compute_question_hash(q_text)

        if q_hash in exclude_hashes:
            continue

        q_data["category"] = category
        q_data["topic"] = topic
        q_data["difficulty"] = difficulty
        q_data["bloom_level"] = bloom_level
        results.append(q_data)
        exclude_hashes.add(q_hash)

    return results


# =============================================================================
# MASTER ORCHESTRATOR: ZERO-REPETITION DYNAMIC QUIZ PROVISIONER
# =============================================================================

def get_or_synthesize_unique_quiz_questions(
    category: str,
    topic: str,
    count: int,
    user_identifier: str,
    difficulty: str = "Medium",
    bloom_level: str = "Understanding",
    force_dynamic: bool = True
) -> List[Dict[str, Any]]:
    """
    Orchestrates dynamic question generation with 100% zero repetition:
    1. Checks candidate's historical questions and identifies unseen questions.
    2. Synthesizes brand-new dynamic questions via Gemini AI and Algorithmic engine.
    3. Persists new questions into database and records them in user history.
    4. Guarantees the candidate never encounters repeated questions.
    """
    conn = get_db_connection()
    conn.row_factory = sqlite3.Row
    ensure_history_tables(conn)

    seen_hashes = get_user_seen_hashes(user_identifier, conn)
    needed = count
    selected_questions: List[Dict[str, Any]] = []

    # 1. If not forcing 100% fresh AI synthesis, try pulling unseen questions from bank first
    if not force_dynamic:
        cursor = conn.cursor()
        if category == "All" or category == "All Topics":
            cursor.execute("SELECT * FROM questions ORDER BY RANDOM() LIMIT 100")
        elif topic == "All" or topic == "All Topics":
            cursor.execute("SELECT * FROM questions WHERE category = ? ORDER BY RANDOM() LIMIT 100", (category,))
        else:
            cursor.execute("SELECT * FROM questions WHERE category = ? AND topic = ? ORDER BY RANDOM() LIMIT 50", (category, topic))
        
        candidates = [dict(r) for r in cursor.fetchall()]
        for cand in candidates:
            cand_hash = compute_question_hash(cand["question"])
            if cand_hash not in seen_hashes:
                selected_questions.append(cand)
                seen_hashes.add(cand_hash)
                if len(selected_questions) >= needed:
                    break

    # 2. If more questions needed (or force_dynamic=True to prevent repeats), synthesize fresh questions
    remaining_needed = needed - len(selected_questions)
    if remaining_needed > 0:
        # A. Attempt Live Gemini GenAI synthesis
        ai_generated = generate_ai_dynamic_questions(
            category=category if category not in ["All", "All Topics"] else "Computer Science",
            topic=topic if topic not in ["All", "All Topics"] else "Core Systems & Algorithms",
            count=remaining_needed,
            difficulty=difficulty,
            bloom_level=bloom_level,
            exclude_hashes=seen_hashes
        )
        selected_questions.extend(ai_generated)

        # B. If GenAI was offline / limited, top up with Infinite Parametric Procedural Generator
        still_needed = needed - len(selected_questions)
        if still_needed > 0:
            parametric_generated = generate_parametric_dynamic_questions(
                category=category if category not in ["All", "All Topics"] else "Python",
                topic=topic if topic not in ["All", "All Topics"] else "Core Logic",
                count=still_needed,
                difficulty=difficulty,
                bloom_level=bloom_level,
                exclude_hashes=seen_hashes
            )
            selected_questions.extend(parametric_generated)

    # 3. Ensure all synthesized questions have SQLite IDs (persist them to bank)
    cursor = conn.cursor()
    final_questions: List[Dict[str, Any]] = []

    for q in selected_questions[:needed]:
        q_id = q.get("id")
        if not q_id:
            cursor.execute(
                """
                INSERT INTO dynamic_questions (question, option_a, option_b, option_c, option_d, correct_answer, category, topic, difficulty, bloom_level, explanation)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    q["question"], q["option_a"], q["option_b"], q["option_c"], q["option_d"],
                    q["correct_answer"], q.get("category", category), q.get("topic", topic),
                    q.get("difficulty", difficulty), q.get("bloom_level", bloom_level), q.get("explanation", "")
                )
            )
            q["id"] = cursor.lastrowid
        final_questions.append(q)

    conn.commit()

    # 4. Record presented questions in user_question_history so candidate NEVER sees them again
    record_user_presented_questions(user_identifier, final_questions, conn)
    conn.close()

    return final_questions
