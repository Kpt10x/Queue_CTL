
---

# README.md

```markdown
# QueueCTL — Background Job Queue System (CLI-Based)

QueueCTL is a lightweight, CLI-driven background job queue system built using Python and SQLite.  
It supports job enqueueing, worker execution, deterministic job claiming, retries with exponential backoff, and a Dead Letter Queue (DLQ).

---

## Architecture Overview

### System Components

- **queuectl.py**  
  Command-line entry point handling enqueue, list, status, worker operations, and DLQ commands.

- **worker.py**  
  Executes background jobs, performs atomic job claiming, schedules retries, applies exponential backoff, and transitions job states.

- **database.py**  
  SQLite storage layer providing durable persistence and timestamp consistency.

---

## Job Lifecycle

```

pending → processing → completed
pending → processing → failed → retry → pending
failed → dead (DLQ)

````

---

## Database Schema

```sql
CREATE TABLE IF NOT EXISTS jobs (
  id TEXT PRIMARY KEY,
  command TEXT NOT NULL,
  state TEXT NOT NULL,
  attempts INTEGER NOT NULL,
  max_retries INTEGER NOT NULL,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  next_run_at TEXT NOT NULL
);
````

---

## Atomic Job Claiming

QueueCTL uses a single-transaction SQL pattern:

```sql
BEGIN IMMEDIATE;

SELECT id, command, attempts, max_retries
FROM jobs
WHERE state = 'pending'
  AND datetime(next_run_at) <= datetime('now')
ORDER BY created_at
LIMIT 1;

UPDATE jobs
SET state = 'processing',
    updated_at = datetime('now')
WHERE id = ?;

COMMIT;
```

This prevents two workers from selecting the same job.

---

## Retry and Exponential Backoff

```python
delay_seconds = BACKOFF_BASE_SECONDS ** new_attempts
```

Backoff is scheduled by updating:

```sql
next_run_at = datetime('now', '<delay_seconds> seconds')
```

Jobs exceeding `max_retries` are moved to the **DLQ**.

---

## Setup Instructions

```bash
python -m venv .venv
.\.venv\Scripts\activate     # Windows
pip install -r requirements.txt   # if applicable
```

The application uses only the Python standard library unless noted otherwise.

---

## Usage

### Enqueue a Job

```bash
python queuectl.py enqueue --file job_ok.json
```

### List Jobs

```bash
python queuectl.py list
python queuectl.py list --state pending
```

### Run Worker

```bash
python queuectl.py worker start
python queuectl.py worker start --once
```

### Status (jobs grouped by state)

```bash
python queuectl.py status
```

### DLQ Operations

List dead jobs:

```bash
python queuectl.py dlq list
```

Retry a DLQ job:

```bash
python queuectl.py dlq retry job_fail
```

---

## Demo Script

Run the automated demo:

```powershell
powershell -ExecutionPolicy Bypass -File demo.ps1
```

This sequence shows:

* enqueue success job
* enqueue failure job
* worker success run
* worker retry + DLQ
* status
* dlq list
* dlq retry
* worker once (retry run)
## Demo Video
[Click here to view the demo](https://drive.google.com/file/d/1oA1Fr6zpjqKCWjWhx1oyVG-EX0qTBcZM/view?usp=sharing)

---

## Project Structure

```
QUEUE_CTL/
├── queuectl.py
├── worker.py
├── database.py
├── demo.ps1
├── job_ok.json
├── job_fail.json
├── queue.db
├── inspect_jobs.py
├── fix_states.py
└── README.md
```

---

## Conclusion

QueueCTL delivers a complete, deterministic, and durable job-processing pipeline with:

* Atomic job claiming
* Retry and exponential backoff
* Dead Letter Queue
* Persistent local storage
* Clean and testable CLI commands

