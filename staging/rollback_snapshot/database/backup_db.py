# -*- coding: utf-8 -*-
"""
=============================================================================
QUIZVERSE - Enterprise Database Backup & Recovery Utility
=============================================================================
Safely creates hot SQLite online backups without blocking active read/write operations.
Supports timestamped rotating snapshots, retention pruning, and point-in-time recovery verification.
=============================================================================
"""

import os
import sys
import glob
import sqlite3
import shutil
import argparse
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, "quiz.db")
BACKUP_DIR = os.path.join(BASE_DIR, "backups")


def prune_old_backups(dest_dir: str, keep: int) -> int:
    """Retains the newest `keep` backups and removes older snapshots."""
    if keep <= 0:
        return 0
    pattern = os.path.join(dest_dir, "quiz_backup_*.db")
    backups = sorted(glob.glob(pattern), key=os.path.getmtime, reverse=True)
    pruned_count = 0
    if len(backups) > keep:
        for old_file in backups[keep:]:
            try:
                os.remove(old_file)
                pruned_count += 1
                print(f"[INFO] Pruned old backup archive: {old_file}")
            except OSError as err:
                print(f"[WARNING] Could not delete old backup {old_file}: {err}")
    return pruned_count


def create_backup(dest_dir: str = BACKUP_DIR, keep: int = None) -> str:
    """
    Creates an atomic, consistent hot backup of quiz.db using the SQLite Online Backup API.
    Does NOT require locking or taking the application offline.
    Optionally prunes old archives if `keep` is provided.
    """
    os.makedirs(dest_dir, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_filename = f"quiz_backup_{timestamp}.db"
    backup_path = os.path.join(dest_dir, backup_filename)

    if not os.path.exists(DB_PATH):
        raise FileNotFoundError(f"Source database not found at: {DB_PATH}")

    # Open connection to source database
    src_conn = sqlite3.connect(DB_PATH)
    dest_conn = sqlite3.connect(backup_path)

    try:
        with dest_conn:
            # Atomic online page-by-page copy
            src_conn.backup(dest_conn, pages=100)
        
        # Verify backup integrity
        dest_cursor = dest_conn.cursor()
        dest_cursor.execute("PRAGMA integrity_check;")
        status = dest_cursor.fetchone()[0]
        if status != "ok":
            raise RuntimeError(f"Backup integrity verification failed: {status}")

        print(f"[SUCCESS] Database backup created and verified: {backup_path}")

        if keep is not None and keep > 0:
            prune_old_backups(dest_dir, keep)

        return backup_path
    finally:
        dest_conn.close()
        src_conn.close()


def restore_backup(backup_path: str) -> bool:
    """Restores database from a verified backup file."""
    if not os.path.exists(backup_path):
        raise FileNotFoundError(f"Backup file not found: {backup_path}")

    # Verify candidate backup before restoring
    test_conn = sqlite3.connect(backup_path)
    try:
        test_cursor = test_conn.cursor()
        test_cursor.execute("PRAGMA integrity_check;")
        if test_cursor.fetchone()[0] != "ok":
            raise RuntimeError("Candidate backup corrupt; aborting restore.")
    finally:
        test_conn.close()

    # Create safety fallback of current state if exists
    if os.path.exists(DB_PATH):
        safety_path = f"{DB_PATH}.pre_restore_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        shutil.copy2(DB_PATH, safety_path)
        print(f"[INFO] Safety pre-restore snapshot saved: {safety_path}")

    # Perform restore via SQLite backup API
    src_conn = sqlite3.connect(backup_path)
    dest_conn = sqlite3.connect(DB_PATH)
    try:
        with dest_conn:
            src_conn.backup(dest_conn, pages=100)
        print(f"[SUCCESS] Database restored from: {backup_path}")
        return True
    finally:
        dest_conn.close()
        src_conn.close()


def main():
    parser = argparse.ArgumentParser(description="QuizVerse SQLite Enterprise Backup & Recovery Utility")
    parser.add_argument("action", nargs="?", default="backup", choices=["backup", "restore"], help="Action to perform (default: backup)")
    parser.add_argument("path", nargs="?", default=None, help="Path to backup file (required for restore)")
    parser.add_argument("--dest", default=BACKUP_DIR, help=f"Destination directory for backups (default: {BACKUP_DIR})")
    parser.add_argument("--keep", type=int, default=None, help="Number of rolling backup snapshots to retain")

    # Handle cases where user runs: python backup_db.py --keep 7
    args = parser.parse_args()

    if args.action == "backup":
        create_backup(dest_dir=args.dest, keep=args.keep)
    elif args.action == "restore":
        if not args.path:
            print("[ERROR] Please provide the path to the backup file to restore: python backup_db.py restore <backup_path>")
            sys.exit(1)
        restore_backup(args.path)


if __name__ == "__main__":
    main()
