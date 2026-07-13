import sqlite3
import json
import os
from typing import Optional

DB_PATH = os.path.join(os.getcwd(), 'jobs.db')

def _conn():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = _conn()
    cur = conn.cursor()
    cur.execute('''
    CREATE TABLE IF NOT EXISTS jobs (
        id TEXT PRIMARY KEY,
        repo TEXT,
        upload_dir TEXT,
        status TEXT,
        payload TEXT,
        result TEXT
    )
    ''')
    conn.commit()
    conn.close()


def create_job(job_id: str, repo: Optional[str]=None, upload_dir: Optional[str]=None, payload: Optional[dict]=None):
    conn = _conn()
    cur = conn.cursor()
    cur.execute('INSERT OR REPLACE INTO jobs (id, repo, upload_dir, status, payload) VALUES (?,?,?,?,?)',
                (job_id, repo, upload_dir, 'queued', json.dumps(payload or {})))
    conn.commit()
    conn.close()


def update_job_status(job_id: str, status: str, result: Optional[dict]=None):
    conn = _conn()
    cur = conn.cursor()
    cur.execute('UPDATE jobs SET status=?, result=? WHERE id=?', (status, json.dumps(result or {}), job_id))
    conn.commit()
    conn.close()


def get_job(job_id: str):
    conn = _conn()
    cur = conn.cursor()
    cur.execute('SELECT * FROM jobs WHERE id=?', (job_id,))
    row = cur.fetchone()
    conn.close()
    if not row:
        return None
    return dict(row)
