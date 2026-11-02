# -*- coding: utf-8 -*-
"""
=============================================================================
QUIZVERSE - Enterprise Database Backup & Recovery Utility
=============================================================================
Safely creates hot SQLite online backups without blocking active read/write operations.
Supports centralized DATABASE_PATH, tiered storage (daily/exam_window),
retention pruning, and point-in-time recovery verification.
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
DB_PATH = os.path.abspath(os.environ.get("DATABASE_PATH", os.path.join(BASE_DIR, "quiz.db")))
BACKUP_DIR = os.path.abspath(os.environ.get("BACKUP_DIR", os.path.join(BASE_DIR, "backups")))


def prune_old_backups(dest_dir: str, keep: int) -> int:
    """Retains the newest `keep` backups in `dest_dir` and removes older snapshots."""
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


def create_backup(dest_dir: str = BACKUP_DIR, keep: int = None, tier: str = None) -> str:
    """
    Creates an atomic, consistent hot backup of quiz.db using the SQLite Online Backup API.
    Does NOT require locking or taking the application offline.
    Optionally organizes by storage tier (e.g. 'daily' or 'exam_window') and prunes via `keep`.
    """
    target_dir = os.path.join(dest_dir, tier) if tier else dest_dir
    os.makedirs(target_dir, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_filename = f"quiz_backup_{timestamp}.db"
    backup_path = os.path.join(target_dir, backup_filename)

    active_db = os.path.abspath(os.environ.get("DATABASE_PATH", DB_PATH))
    if not os.path.exists(active_db):
        raise FileNotFoundError(f"Source database not found at: {active_db}")

    # Open connection to source database
    src_conn = sqlite3.connect(active_db)
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
            prune_old_backups(target_dir, keep)

        return backup_path
    finally:
        dest_conn.close()
        src_conn.close()


def restore_backup(backup_path: str, target_db: str = None) -> bool:
    """Restores database from a verified backup file into target_db (default: DATABASE_PATH)."""
    if not os.path.exists(backup_path):
        raise FileNotFoundError(f"Backup file not found: {backup_path}")

    active_db = target_db or os.path.abspath(os.environ.get("DATABASE_PATH", DB_PATH))

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
    if os.path.exists(active_db):
        safety_path = f"{active_db}.pre_restore_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        shutil.copy2(active_db, safety_path)
        print(f"[INFO] Safety pre-restore snapshot saved: {safety_path}")

    # Ensure target directory exists
    os.makedirs(os.path.dirname(active_db), exist_ok=True)

    # Perform restore via SQLite backup API
    src_conn = sqlite3.connect(backup_path)
    dest_conn = sqlite3.connect(active_db)
    try:
        with dest_conn:
            src_conn.backup(dest_conn, pages=100)
        print(f"[SUCCESS] Database restored from: {backup_path} -> {active_db}")
        return True
    finally:
        dest_conn.close()
        src_conn.close()


def list_backups(dest_dir: str = BACKUP_DIR, tier: str = None):
    """Lists available database backups and verifies their integrity."""
    target_dir = os.path.join(dest_dir, tier) if tier else dest_dir
    if not os.path.exists(target_dir):
        print(f"[INFO] Backup directory does not exist: {target_dir}")
        return []

    pattern = os.path.join(target_dir, "**", "quiz_backup_*.db") if not tier else os.path.join(target_dir, "quiz_backup_*.db")
    backups = sorted(glob.glob(pattern, recursive=not tier), key=os.path.getmtime, reverse=True)
    if not backups:
        print(f"[INFO] No backups found in {target_dir}")
        return []

    print(f"\n{'Backup Snapshot File':<50} {'Size':<12} {'Created':<22} {'Integrity':<10}")
    print("-" * 95)
    for b in backups:
        sz = os.path.getsize(b) / 1024.0
        sz_str = f"{sz:.1f} KB" if sz < 1024 else f"{sz/1024.0:.2f} MB"
        mtime = datetime.fromtimestamp(os.path.getmtime(b)).strftime("%Y-%m-%d %H:%M:%S")
        status = "ok"
        try:
            conn = sqlite3.connect(b)
            status = conn.execute("PRAGMA integrity_check;").fetchone()[0]
            conn.close()
        except Exception as e:
            status = f"error: {e}"
        print(f"{os.path.basename(b):<50} {sz_str:<12} {mtime:<22} {status:<10}")
    print(f"Total backups found: {len(backups)}\n")
    return backups


def main():
    parser = argparse.ArgumentParser(description="QuizVerse SQLite Enterprise Backup & Recovery Utility")
    parser.add_argument("action", nargs="?", default="backup", choices=["backup", "restore", "list"], help="Action to perform (default: backup)")
    parser.add_argument("path", nargs="?", default=None, help="Path to backup file (required for restore)")
    parser.add_argument("--dest", default=BACKUP_DIR, help=f"Destination directory for backups (default: {BACKUP_DIR})")
    parser.add_argument("--tier", choices=["daily", "exam_window", "manual"], default=None, help="Backup storage tier (sub-directory under BACKUP_DIR)")
    parser.add_argument("--keep", type=int, default=None, help="Number of rolling backup snapshots to retain")

    args = parser.parse_args()

    if args.action == "backup":
        create_backup(dest_dir=args.dest, keep=args.keep, tier=args.tier)
    elif args.action == "restore":
        if not args.path:
            print("[ERROR] Please provide the path to the backup file to restore: python backup_db.py restore <backup_path>")
            sys.exit(1)
        restore_backup(args.path)
    elif args.action == "list":
        list_backups(dest_dir=args.dest, tier=args.tier)


if __name__ == "__main__":
    main()
