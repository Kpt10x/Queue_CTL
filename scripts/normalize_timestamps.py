import sqlite3
con = sqlite3.connect("queue.db")
cur = con.cursor()
# Normalize known Z/T formats into a consistent SQLite datetime
cur.execute("""
UPDATE jobs
SET
  created_at  = COALESCE(datetime(created_at),  created_at),
  updated_at  = COALESCE(datetime(updated_at),  updated_at),
  next_run_at = COALESCE(datetime(next_run_at), next_run_at)
""")
con.commit()
print("Timestamps normalized.")
