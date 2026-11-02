# -*- coding: utf-8 -*-
"""
=============================================================================
QUIZVERSE MAJOR PROJECT - Academic Curriculum Re-Export
=============================================================================
Re-exports SUBJECT_CATALOG from curriculum_catalog.py.
Static questions have been completely deprecated in favor of 100% dynamic
real-time question generation powered by Google Gemini GenAI.
=============================================================================
"""

import os
import sys

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from curriculum_catalog import SUBJECT_CATALOG, get_all_subjects, get_topics_for_subject, get_subject_domain_focus


def get_all_800_questions():
    """
    Deprecated: Static hardcoded questions have been eliminated.
    All questions are now generated dynamically via dynamic_question_engine.py.
    """
    return []


if __name__ == "__main__":
    print(f"Active subjects in curriculum: {list(SUBJECT_CATALOG.keys())}")
    print("100% Dynamic Question Generation Mode Active.")
