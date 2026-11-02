# -*- coding: utf-8 -*-
"""
=============================================================================
QUIZVERSE MAJOR PROJECT - Dynamic Curriculum & Academic Catalog
=============================================================================
Defines the academic syllabus structure (8 Core Subjects, 10 Topics each = 80 Topics).
Contains ZERO hardcoded questions — all examination questions are generated
dynamically on-the-fly via Google Gemini GenAI with zero repetition.
=============================================================================
"""

from typing import Dict, List, Any

# Subject Metadata and Academic Syllabus Structure
SUBJECT_CATALOG: Dict[str, Dict[str, Any]] = {
    "Java": {
        "title": "Java Programming",
        "badge": "Core Enterprise Language",
        "color": "danger",
        "icon": "bi-cup-hot-fill",
        "description": "OOP, loops, collections, exceptions, JDBC database connections, and CRUD operations.",
        "topics": [
            "Data Types & Variables",
            "Operators & Expressions",
            "Looping Statements",
            "Object-Oriented Programming",
            "Inheritance & Polymorphism",
            "Exception Handling",
            "Collections Framework",
            "File I/O & Streams",
            "Database Connection",
            "CRUD Operations"
        ],
        "domain_focus": "Java 17/21 LTS, JVM memory model, OOP design patterns, inheritance, polymorphism, Collections Framework, multithreading, JDBC connectivity, and CRUD."
    },
    "Python": {
        "title": "Python Programming",
        "badge": "Core Programming",
        "color": "primary",
        "icon": "bi-filetype-py",
        "description": "Syntax, loops, functions, comprehensions, OOP, file handling, SQLite connections & CRUD.",
        "topics": [
            "Syntax & Core Data Types",
            "Looping Statements",
            "Functions & Lambda Expressions",
            "Lists, Dictionaries, Tuples & Sets",
            "List Comprehensions & Iterators",
            "Object-Oriented Python",
            "File Handling & I/O",
            "Exception Handling",
            "SQLite Database Connection",
            "CRUD Operations"
        ],
        "domain_focus": "Python 3.12, memory management, data structures, generators, list/dict comprehensions, decorators, OOP, exceptions, and SQLite CRUD."
    },
    "C++": {
        "title": "C++ Programming",
        "badge": "Systems & Performance",
        "color": "info",
        "icon": "bi-file-earmark-code-fill",
        "description": "Pointers, dynamic memory, loops, function overloading, OOP, templates, and STL containers.",
        "topics": [
            "Basic Syntax & Variables",
            "Looping Statements & Branches",
            "Functions & Function Overloading",
            "Pointers & References",
            "Dynamic Memory Allocation",
            "Classes, Objects & Constructors",
            "Inheritance & Access Specifiers",
            "Polymorphism & Virtual Functions",
            "Standard Template Library (STL)",
            "File Streams & File I/O"
        ],
        "domain_focus": "Modern C++ (C++17/20), pointers, references, dynamic memory, RAII, copy/move semantics, templates, STL algorithms, and memory layout."
    },
    "WebDev": {
        "title": "Web Development",
        "badge": "Frontend & Interactive",
        "color": "success",
        "icon": "bi-globe2",
        "description": "HTML5 semantic structure, forms, CSS box model, Flexbox, Grid, animations, and JS DOM.",
        "topics": [
            "HTML5 Structure & Semantic Tags",
            "HTML Forms & Validation",
            "CSS3 Selectors & Specificity",
            "CSS Box Model",
            "CSS Flexbox Layout",
            "CSS Grid System",
            "CSS Transitions & Animations",
            "Responsive Design & Media Queries",
            "JavaScript DOM Manipulation",
            "JavaScript Event Handling"
        ],
        "domain_focus": "Modern Web Technologies, HTML5 semantic structure, CSS3 Flexbox/Grid, responsive layout, JavaScript ES6+, DOM manipulation, and browser events."
    },
    "DBMS": {
        "title": "Database Management (SQL)",
        "badge": "Data Architecture",
        "color": "secondary",
        "icon": "bi-database-fill-gear",
        "description": "Relational models, SQL DDL, CRUD operations, joins, grouping, normalization, and ACID transactions.",
        "topics": [
            "DBMS Concepts & Architecture",
            "Relational Data Model & Keys",
            "SQL DDL Commands",
            "SQL DML & CRUD Operations",
            "Filtering & Operators",
            "Aggregate Functions & GROUP BY",
            "SQL Joins",
            "Constraints & Foreign Keys",
            "Database Normalization",
            "Transactions & ACID Properties"
        ],
        "domain_focus": "Relational Database Management Systems, SQL (DDL/DML/DQL), relational algebra, normal forms (1NF-BCNF), indexing, joins, and ACID transactions."
    },
    "Flask": {
        "title": "Flask Web Framework",
        "badge": "Backend Web Engineering",
        "color": "dark",
        "icon": "bi-diagram-3-fill",
        "description": "Microframework setup, dynamic routing, Jinja2 templating, sessions, SQLite integration, and errors.",
        "topics": [
            "Flask Setup & Architecture",
            "Routing & URL Converters",
            "HTTP Methods (GET, POST)",
            "Request Object & Form Handling",
            "Jinja2 Templating Engine",
            "Static Assets & CSS",
            "Session Management & Cookies",
            "Flash Messaging & Alerts",
            "SQLite Database Connection",
            "Error Handlers & HTTP Codes"
        ],
        "domain_focus": "Python Flask microframework, WSGI, routing, Jinja2 templating, sessions, request dispatching, error handlers, and REST API design."
    },
    "DSA": {
        "title": "Data Structures & Algorithms",
        "badge": "Computer Science Core",
        "color": "warning",
        "icon": "bi-bezier2",
        "description": "Arrays, linked lists, stacks, queues, trees, BST, searching, sorting, and graph algorithms.",
        "topics": [
            "Arrays & Memory Allocation",
            "Singly & Doubly Linked Lists",
            "Stacks & LIFO Applications",
            "Queues & Circular Queues",
            "Recursion & Divide-and-Conquer",
            "Binary Trees & Traversals",
            "Binary Search Trees (BST)",
            "Searching Algorithms",
            "Sorting Algorithms",
            "Graph Traversal (BFS & DFS)"
        ],
        "domain_focus": "Data Structures and Algorithms, asymptotic Big-O complexity analysis, trees (BST, AVL), graphs (BFS/DFS), heaps, and sorting trade-offs."
    },
    "OS": {
        "title": "Operating Systems",
        "badge": "System Software & Concurrency",
        "color": "primary",
        "icon": "bi-cpu-fill",
        "description": "Kernels, process states, CPU scheduling, IPC, synchronization, semaphores, deadlocks, and paging.",
        "topics": [
            "OS Architecture & System Calls",
            "Process States & PCB",
            "CPU Scheduling",
            "Inter-Process Communication",
            "Process Synchronization & Critical Section",
            "Semaphores & Mutex Locks",
            "Deadlocks & Banker's Algorithm",
            "Memory Management & Paging",
            "Virtual Memory & Page Replacement",
            "File Systems & Disk Scheduling"
        ],
        "domain_focus": "Operating Systems, kernel vs user space, process management, CPU scheduling, synchronization, semaphores, deadlocks (Banker's), and virtual memory paging."
    }
}


def get_all_subjects() -> List[str]:
    """Returns list of all available subjects."""
    return list(SUBJECT_CATALOG.keys())


def get_topics_for_subject(subject: str) -> List[str]:
    """Returns list of topics for a specific subject."""
    if subject in SUBJECT_CATALOG:
        return SUBJECT_CATALOG[subject]["topics"]
    return ["General Concepts"]


def get_subject_domain_focus(subject: str) -> str:
    """Returns academic pedagogical focus instructions for GenAI prompt engineering."""
    if subject in SUBJECT_CATALOG:
        return SUBJECT_CATALOG[subject].get("domain_focus", "University-level Computer Science principles.")
    return "University-level Computer Science principles and application engineering."
