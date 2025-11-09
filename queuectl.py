import argparse
from concurrent.futures.thread import _worker
import json,sys,sqlite3,time,math
from datetime import datetime
from database import get_connection, init_database, now_sql
from worker import run_worker
def cmd_enqueue(args):
    #to parse the "job" argument as a JSON object
    # Resolve payload source: --file > positional > stdin
    if args.file:
        with open(args.file, "r", encoding="utf-8") as fh:
            raw = fh.read()
    elif args.job_json:
        raw = args.job_json
    else:
        raw = sys.stdin.read()

    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as e:
        raise SystemExit(f"Invalid JSON: {e}")
    
    #trying to do minimal validation using id
    for k in ("id","command"):
        if k not in payload:
            raise SystemExit(f"Missing required field: {k}")
    
    job_id= str(payload["id"])
    command= str(payload["command"])
    max_retries= int(payload.get("max_retries",3))
    
    created=now_sql()
    next_run_at = created
    #inserting the job into the database
    init_database()
    try:
        with get_connection() as conn:
            conn.execute("""
                INSERT INTO jobs (
                    id, command, state, attempts, max_retries,
                    created_at, updated_at, next_run_at
                )
                VALUES (?, ?, 'pending', 0, ?, DATETIME('now'), DATETIME('now'), DATETIME('now'));
            """, (job_id, command, max_retries))
        print(f"Enqueued job {job_id}")
    except sqlite3.IntegrityError:
        raise SystemExit(f"Job with id {job_id} already exists.")
    
def cmd_list(args):
    init_database()
    state=args.state
    with get_connection() as conn:
        if state:
            rows=conn.execute("SELECT * FROM jobs WHERE state=? ORDER BY created_at;", (state,)).fetchall()
        else:
            rows=conn.execute("SELECT * FROM jobs ORDER BY created_at;").fetchall()
        
        for row in rows:
            print(dict(row))
    out=[dict(r) for r in rows]
    print(json.dumps(out, indent=2))

def build_parser():
    p= argparse.ArgumentParser(prog="queuectl", description="Job Queue Management CLI")
    sub=p.add_subparsers(dest="command", required=True)
    # Enqueue command
    pe= sub.add_parser("enqueue", help="Enqueue a new job from JSON")
    pe.add_argument("job_json", nargs="?", help="JSON String for the job to enqueue")
    pe.add_argument("--file", "-f", help="Path to JSON file containing the job definition")
    pe.set_defaults(func=cmd_enqueue)
    
    # in built worker command
    pw= sub.add_parser("worker", help="Start a worker to process jobs")
    pw_sub= pw.add_subparsers(dest="worker_command", required=True)
    pws= pw_sub.add_parser("start", help="Start the worker (foreground)")
    pws.set_defaults(func=lambda args: run_worker())
    
    #list command
    pl= sub.add_parser("list", help="List jobs in the queue")
    pl.add_argument("--state", choices=["pending","processing","completed","failed","dead"], help="Filter jobs by state")
    pl.set_defaults(func=cmd_list)
    
    return p

def cmd_worker_start(args):
    run_worker()

def main():
    parser= build_parser()
    args= parser.parse_args()
    args.func(args)
if __name__ == "__main__":
    main()