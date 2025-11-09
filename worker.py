# worker.py
import sqlite3, subprocess, time, math

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

def run_worker(poll_interval_seconds: float = 1.0):
    print("[worker] starting...")
    while True:
        job = fetch_next_job()
        if not job:
            time.sleep(poll_interval_seconds)
            continue

        jid = job["id"]
        cmd = job["command"]
        print(f"[worker] processing {jid}: {cmd}")

        try:
            result = subprocess.run(
                cmd,
                shell=True,
                capture_output=True,
                text=True,
                timeout=COMMAND_TIMEOUT_SECONDS
            )
            if result.returncode == 0:
                mark_job_completed(jid)
                print(f"[worker] completed {jid}")
            else:
                handle_job_failure(jid, result.stderr or result.stdout or f"exit={result.returncode}")
        except subprocess.TimeoutExpired:
            print(f"[worker] timeout {jid}")
            handle_job_failure(jid, "timeout")
