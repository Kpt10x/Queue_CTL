# worker.py
import sqlite3, subprocess, time, math, signal
from datetime import datetime
STOP=False
DB = "queue.db"
BACKOFF_BASE_SECONDS = 3     
COMMAND_TIMEOUT_SECONDS = 30 

def fetch_next_job():
    """
    Atomically claim the next runnable job.
    BEGIN IMMEDIATE grabs the write lock so no other worker can claim the same job.
    """
    with sqlite3.connect(DB) as conn:
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        try:
            cur.execute("BEGIN IMMEDIATE;")
            cur.execute("""
                SELECT id, command, attempts, max_retries
                FROM jobs
                WHERE state = 'pending'
                  AND datetime(next_run_at) <= datetime('now')
                ORDER BY created_at ASC
                LIMIT 1;
            """)
            job = cur.fetchone()
            if job:
                cur.execute("""
                    UPDATE jobs
                    SET state = 'processing', updated_at = datetime('now')
                    WHERE id = ?;
                """, (job["id"],))
            conn.commit()
            return dict(job) if job else None
        except sqlite3.Error as e:
            conn.rollback()
            print(f"[fetch_next_job] DB error: {e}")
            return None

def mark_job_completed(job_id: str):
    with sqlite3.connect(DB) as conn:
        conn.execute("""
            UPDATE jobs
            SET state='completed', updated_at = datetime('now')
            WHERE id = ?;
        """, (job_id,))

def handle_job_failure(job_id: str, error_message: str):
    with sqlite3.connect(DB) as conn:
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute("SELECT attempts, max_retries FROM jobs WHERE id = ?;", (job_id,))
        row = cur.fetchone()
        if not row:
            return
        new_attempts = (row["attempts"] or 0) + 1
        if new_attempts >= row["max_retries"]:
            # DLQ
            cur.execute("""
                UPDATE jobs
                SET state='dead', attempts=?, updated_at=datetime('now')
                WHERE id = ?;
            """, (new_attempts, job_id))
            conn.commit()
            print(f"[worker] Job {job_id} -> DLQ")
            return
        # Retry with exponential backoff
        delay = BACKOFF_BASE_SECONDS ** new_attempts
        cur.execute("""
            UPDATE jobs
            SET state='pending',
                attempts=?,
                updated_at=datetime('now'),
                next_run_at=datetime('now', ? || ' seconds')
            WHERE id=?;
        """, (new_attempts, str(int(delay)), job_id))
        conn.commit()
        print(f"[worker] Job {job_id} retry scheduled in {int(delay)}s (attempt {new_attempts})")

def run_worker(once: bool = False):
    print("[worker] starting...")
    try:
        while not STOP:
            job = fetch_next_job()
            if job:
                print(f"[worker] processing {job['id']}: {job['command']}")
                try:
                    result = subprocess.run(
                        job['command'],
                        shell=True,
                        capture_output=True,
                        text=True,
                        timeout=30
                    )
                    if result.returncode == 0:
                        mark_job_completed(job['id'])
                        print(f"[worker] completed {job['id']}")
                    else:
                        handle_job_failure(job['id'], result.stderr or result.stdout or "non-zero exit")
                except subprocess.TimeoutExpired:
                    handle_job_failure(job['id'], "timeout")
                    print(f"[worker] {job['id']} timed out")
                if once:
                    print("[worker] --once: exiting after one job")
                    return
            else:
                time.sleep(1.5)
    except KeyboardInterrupt:
        print("\n[worker] received Ctrl+C, exiting gracefully")
    finally:
        pass  # nothing to clean up for now
