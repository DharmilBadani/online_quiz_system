# QuizVerse Enterprise - Backup & Disaster Recovery Runbook

**Document ID:** QZ-BDR-2026-004  
**Author:** Database Reliability & Disaster Recovery Team  
**Scope:** Institutional Exam Data Protection, Hot Backup Automation, and Failover Recovery  
**Application:** QuizVerse v2.0  
**Effective Date:** November 1, 2026  

---

## 1. Objectives & Metrics

Institutional examination platforms require non-negotiable data integrity and immediate recovery capabilities to prevent exam loss or grade corruption.

| Metric | Target SLA | Operational Design |
| :--- | :--- | :--- |
| **RPO (Recovery Point Objective)** | < 15 Minutes during active exams / 24 Hours standard | Automated hourly snapshots during active testing windows; WAL checkpoints every 1000 pages. |
| **RTO (Recovery Time Objective)** | < 3 Minutes | Pre-verified backup images restorable via SQLite Online Backup API without server reboots. |
| **Integrity Verification** | 100% Automated | Pre- and post-backup integrity validation using `PRAGMA integrity_check;`. |

---

## 2. SQLite Online Backup Architecture

Because QuizVerse operates with SQLite Write-Ahead Logging (`PRAGMA journal_mode=WAL;`), standard file-copy commands (`cp quiz.db`) are dangerous and can capture an inconsistent intermediate state while the `-wal` log is open.

QuizVerse addresses this by utilizing the native **SQLite Online Backup API** implemented in [`database/backup_db.py`](file:///e:/Major%20Project/online_quiz_system/database/backup_db.py).

### Key Architectural Strengths:
1. **Zero-Lock Operation:** The backup process page-copies in 100-page increments without blocking active students submitting exams.
2. **Atomic Consistency:** The generated `.db` snapshot is an entirely self-contained, crash-consistent SQLite database containing all committed WAL frames.
3. **Automated Verification:** Every snapshot is immediately verified using `PRAGMA integrity_check;` before being registered as valid.

---

## 3. Automated Backup Procedures

### 3.1 On-Demand Backup Execution
To trigger an immediate hot backup from the command line:
```bash
python database/backup_db.py backup
```
*Output:*
```text
[SUCCESS] Database backup created and verified: /opt/quizverse/backups/quiz_backup_20261101_194500.db
```

### 3.2 Automated Rolling Linux Cron Schedule
Configure `/etc/cron.d/quizverse_backup`:
```cron
# Standard Off-Peak Daily Backup at 02:00 AM
0 2 * * * quizverse /opt/quizverse/venv/bin/python /opt/quizverse/database/backup_db.py backup >> /var/log/quizverse/backup.log 2>&1

# Exam Window High-Frequency Backup (Every 15 minutes during campus testing hours 08:00 - 18:00 Mon-Fri)
*/15 8-18 * * 1-5 quizverse /opt/quizverse/venv/bin/python /opt/quizverse/database/backup_db.py backup >> /var/log/quizverse/backup.log 2>&1

# Archive & Retention Cleanup (Remove snapshots older than 30 days)
0 3 * * * quizverse find /opt/quizverse/backups/ -name "quiz_backup_*.db" -mtime +30 -delete
```

### 3.3 Windows Task Scheduler Automation (PowerShell)
```powershell
$action = New-ScheduledTaskAction -Execute "python.exe" -Argument "database\backup_db.py backup" -WorkingDirectory "E:\Major Project\online_quiz_system"
$trigger = New-ScheduledTaskTrigger -Daily -At 2am
Register-ScheduledTask -Action $action -Trigger $trigger -TaskName "QuizVerse_Daily_DB_Backup" -Description "Daily verified SQLite backup"
```

---

## 4. Off-Site Replication & Cold Storage

Snapshots stored on the primary host protect against application failure, but not hardware loss or datacenter outages.

### Recommended Off-Site Synchronization:
1. **AWS S3 / Cloudflare R2 Sync (via AWS CLI):**
   ```bash
   aws s3 sync /opt/quizverse/backups/ s3://institution-exam-backups/quizverse/ --exclude "*" --include "quiz_backup_*.db"
   ```
2. **Encrypted Rsync to Campus Disaster Recovery Server:**
   ```bash
   rsync -avz -e ssh /opt/quizverse/backups/ backup-operator@dr-storage.university.edu:/var/backups/quizverse/
   ```

---

## 5. Disaster Recovery Runbook (Step-by-Step Restoration)

When recovering from accidental deletion, disk corruption, or an administrative error:

### Step 1: Identify Target Backup
Inspect the backup directory and select the most recent valid timestamped snapshot:
```bash
ls -lht /opt/quizverse/backups/
```

### Step 2: Stop Incoming Exam Traffic
Temporarily redirect incoming HTTP traffic to a maintenance page in Nginx:
```bash
sudo systemctl stop quizverse
```

### Step 3: Execute Verified Restore
Run the built-in restore tool. It automatically saves a safety copy of the current state before replacing `quiz.db`:
```bash
python database/backup_db.py restore /opt/quizverse/backups/quiz_backup_20261101_194500.db
```
*Expected Output:*
```text
[INFO] Safety pre-restore snapshot saved: /opt/quizverse/quiz.db.pre_restore_20261101_195000
[SUCCESS] Database restored from: /opt/quizverse/backups/quiz_backup_20261101_194500.db
```

### Step 4: Verify Database Health & Permissions
```bash
sqlite3 /opt/quizverse/quiz.db "PRAGMA integrity_check;"
# Output: ok

sudo chown quizverse:quizverse /opt/quizverse/quiz.db*
sudo chmod 660 /opt/quizverse/quiz.db*
```

### Step 5: Resume Production Services
```bash
sudo systemctl start quizverse
sudo systemctl status quizverse
```

### Step 6: Post-Restore Verification Smoke Test
1. Log in to the administrative portal (`/admin/dashboard`).
2. Run database health diagnostic (`/admin/health`).
3. Verify that student attempt records, questions, and active sessions match the expected recovery point.

---

## 6. Disaster Recovery Drill Schedule

To ensure institutional readiness, IT operations must perform a scheduled restoration drill **quarterly** in an isolated staging environment using the latest production backup image.

