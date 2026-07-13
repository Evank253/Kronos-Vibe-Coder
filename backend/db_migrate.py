import shutil
import os
import sqlite3
from datetime import datetime, timezone

DB = os.path.join(os.getcwd(), 'jobs.db')
BACKUP_DIR = os.path.join(os.getcwd(), 'db_backups')
MIGRATIONS_DIR = os.path.join(os.path.dirname(__file__), 'migrations')


def run_migrations():
    os.makedirs(BACKUP_DIR, exist_ok=True)

    if os.path.exists(DB):
        ts = datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')
        dest = os.path.join(BACKUP_DIR, f'jobs.db.{ts}.bak')
        shutil.copy2(DB, dest)
        print('Backup created:', dest)
    else:
        print('No jobs.db found — creating new DB')

    # apply SQL migrations in order
    sql_files = sorted([f for f in os.listdir(MIGRATIONS_DIR) if f.endswith('.sql')])
    if not sql_files:
        print('No migrations found')
        return

    conn = sqlite3.connect(DB)
    try:
        for fname in sql_files:
            path = os.path.join(MIGRATIONS_DIR, fname)
            with open(path, 'r', encoding='utf-8') as fh:
                sql = fh.read()
            conn.executescript(sql)
            print('Applied', fname)
        conn.commit()
    finally:
        conn.close()


if __name__ == '__main__':
    run_migrations()

