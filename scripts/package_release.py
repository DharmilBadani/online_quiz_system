"""
QuizVerse Release Packaging Tool
Packages the clean production distribution artifact adhering to institutional release guidelines.
"""

import os
import sys
import zipfile
import hashlib

def should_exclude(rel_path):
    parts = os.path.normpath(rel_path).split(os.sep)
    # Exclude internal directories
    if any(p in ('.git', '__pycache__', '.pytest_cache', 'backups', 'dist', '.vscode') for p in parts):
        return True
    # Exclude archived documentation
    if len(parts) >= 2 and parts[0] == 'docs' and parts[1] == 'archive':
        return True
    filename = parts[-1]
    # Exclude active secrets and databases
    if filename in ('.env', 'quiz.db', 'quiz.db-shm', 'quiz.db-wal'):
        return True
    # Exclude compiled or temporary extensions
    if any(filename.endswith(ext) for ext in ('.pyc', '.pyo', '.db', '.db-shm', '.db-wal', '.log', '.zip')):
        return True
    return False

def build_package(zip_name="QuizVerse_v2.0.0_Clean_Release.zip"):
    root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    dist_dir = os.path.join(root_dir, "dist")
    os.makedirs(dist_dir, exist_ok=True)
    zip_path = os.path.join(dist_dir, zip_name)

    packaged_files = []
    total_uncompressed = 0

    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for root, dirs, files in os.walk(root_dir):
            rel_root = os.path.relpath(root, root_dir)
            if rel_root == ".":
                rel_root = ""
            
            # Prune excluded directories in-place for fast traversal
            dirs[:] = [
                d for d in dirs 
                if not should_exclude(os.path.join(rel_root, d))
            ]

            for file in sorted(files):
                rel_path = os.path.normpath(os.path.join(rel_root, file))
                if should_exclude(rel_path):
                    continue

                abs_path = os.path.join(root, file)
                zf.write(abs_path, rel_path)
                packaged_files.append(rel_path)
                total_uncompressed += os.path.getsize(abs_path)

    # Compute SHA-256
    with open(zip_path, "rb") as f:
        sha256_hash = hashlib.sha256(f.read()).hexdigest()

    compressed_size = os.path.getsize(zip_path)

    print("=" * 60)
    print(f"QuizVerse Production Package Built: {zip_name}")
    print("=" * 60)
    print(f"Destination:          {zip_path}")
    print(f"Total Files:          {len(packaged_files)}")
    print(f"Uncompressed Size:    {total_uncompressed:,} bytes ({total_uncompressed / 1024:.2f} KB)")
    print(f"Compressed Size:      {compressed_size:,} bytes ({compressed_size / 1024:.2f} KB)")
    print(f"SHA-256 Checksum:     {sha256_hash}")
    print("=" * 60)

    return {
        "zip_path": zip_path,
        "file_count": len(packaged_files),
        "uncompressed_bytes": total_uncompressed,
        "compressed_bytes": compressed_size,
        "sha256": sha256_hash,
        "files": packaged_files
    }

if __name__ == "__main__":
    pkg_name = sys.argv[1] if len(sys.argv) > 1 else "QuizVerse_v2.0.0_Clean_Release.zip"
    build_package(pkg_name)
