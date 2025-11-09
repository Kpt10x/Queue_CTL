import sqlite3, json
con = sqlite3.connect('queue.db')
con.row_factory = sqlite3.Row
rows = con.execute("SELECT id, state, attempts, max_retries, created_at, updated_at, next_run_at FROM jobs ORDER BY created_at").fetchall()
print(json.dumps([dict(r) for r in rows], indent=2))
