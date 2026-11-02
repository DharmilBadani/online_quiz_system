# BACKUP & DISASTER RECOVERY GUIDE

## 1. Overview
QuizVerse persistence relies on SQLite in Write-Ahead Logging (WAL) mode. Live backups are taken using the SQLite Online Backup API (`sqlite3.Connection.backup()`), which creates atomic, non-blocking snapshots without taking the application offline.

---

## 2. Retention Architecture
Backups are organized by isolated storage tiers under `backups/`:
- `backups/daily/`: Nightly snapshots retained for 30 rolling days (`--keep 30`).
- `backups/exam_window/`: High-frequency snapshots every 15 minutes during active exams (`--keep 40` = 10 hours of rollback points).
- `backups/manual/`: On-demand pre-migration backups retained for 10 snapshots (`--keep 10`).

Pruning is strictly directory-scoped; pruning in `exam_window/` never touches snapshots in `daily/` or `manual/`.

---

## 3. Command-Line Reference

```bash
# 1. Create a snapshot in a specific tier
python database/backup_db.py create --tier exam_window --keep 40

# 2. List all available backups with size, timestamp, and integrity verification
python database/backup_db.py list

# 3. Restore a specific snapshot into the active database
python database/backup_db.py restore backups/exam_window/quiz_backup_20261102_150118.db

# 4. Prune snapshots exceeding retention in a tier
python database/backup_db.py prune --tier daily --keep 30
```

---

## 4. Systemd Timers (Linux Production)

### 15-Minute Exam Window Backup
```ini
# /etc/systemd/system/quizverse-backup.service
[Unit]
Description=QuizVerse 15-Minute Exam Window Backup

[Service]
Type=oneshot
User=quizverse
WorkingDirectory=/var/www/quizverse
EnvironmentFile=/var/www/quizverse/.env
ExecStart=/var/www/quizverse/venv/bin/python database/backup_db.py create --tier exam_window --keep 40
```
```ini
# /etc/systemd/system/quizverse-backup.timer
[Unit]
Description=Run QuizVerse Backup Every 15 Minutes

[Timer]
OnCalendar=*:00,15,30,45
Persistent=true

[Install]
WantedBy=timers.target
```
Enable timer:
```bash
sudo systemctl daemon-reload
sudo systemctl enable --now quizverse-backup.timer
```

