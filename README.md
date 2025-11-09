QueueCTL — Background Job Queue System (CLI-Based)

QueueCTL is a lightweight, production-grade background job processing system implemented using Python and SQLite. It provides a command-line interface for job creation, worker execution, lifecycle management, retries with exponential backoff, and Dead Letter Queue (DLQ) operations.

The design prioritizes operational reliability, atomicity, and deterministic behavior.

Architecture Overview

System Components

CLI Layer (queuectl.py): Handles all inbound user commands such as enqueueing jobs, listing queue states, worker operations, DLQ operations, and status reporting.

Worker Engine (worker.py): Executes background jobs. Ensures atomic job claiming, retry scheduling, exponential backoff, and complete state transitions.

Storage Layer (database.py): SQLite-based storage providing durability, locking guarantees, and timestamp consistency.

Atomic Job Claiming

QueueCTL uses the following SQL pattern in a single transaction to ensure exclusive job access and prevent race conditions:

-- Start a write-lock immediately
BEGIN IMMEDIATE;

-- Find the next available job
SELECT id, command, attempts, max_retries 
FROM jobs 
WHERE state = 'pending' AND next_run_at <= DATETIME('now')
ORDER BY created_at
LIMIT 1;

-- Immediately lock the selected job so no other worker can take it
UPDATE jobs 
SET state = 'processing', updated_at = DATETIME('now') 
WHERE id = ?;

-- End transaction
COMMIT;


This approach prevents duplicate execution even when multiple workers run in parallel.

Job Lifecycle State Machine

QueueCTL ensures deterministic state transitions with timestamps:

Success: pending → processing → completed

Retry: pending → processing → failed → pending (with future next_run_at)

DLQ: pending → processing → failed (at max retries) → dead

Retry and Backoff Strategy

QueueCTL implements exponential backoff for failed jobs. The delay is calculated as:

delay_seconds = base ^ attempts

The job's next_run_at timestamp is pushed into the future to ensure controlled, delayed retries without blocking the worker.

Setup Instructions

1. Install Dependencies

(Assuming a requirements.txt file is present. If not, list packages like pip install ...)

pip install -r requirements.txt


2. Initialize Database

No manual setup required. The database file (queue.db) is created automatically in the local directory on first command execution.

3. Verify Installation

python queuectl.py status


CLI Usage

Enqueue a Job

You can enqueue a job from a JSON file or a raw JSON string.

From file:

python queuectl.py enqueue --file job.json


From string:

python queuectl.py enqueue '{"id":"task1","command":"python -c \"print(42)\"","max_retries":3}'


List Jobs

List all jobs or filter by a specific state.

# List all jobs
python queuectl.py list

# List only pending jobs
python queuectl.py list --state pending

# List completed or dead jobs
python queuectl.py list --state completed
python queuectl.py list --state dead


Start Worker

Start a worker to process jobs.

Continuous mode (runs until Ctrl+C):

python queuectl.py worker start


Single job mode (runs one job and exits):

python queuectl.py worker start --once


Get Queue Status

Shows a summary of all jobs grouped by their state.

python queuectl.py status


DLQ (Dead Letter Queue) Operations

Manage jobs that have permanently failed.

List all jobs in the DLQ:

python queuectl.py dlq list


Retry a specific job from the DLQ:
(This resets its attempts and moves it back to pending)

python queuectl.py dlq retry <job_id>


Example Scenarios

Success Case

# Enqueue a job that will succeed
python queuectl.py enqueue '{"id":"ok_job","command":"echo Hello World"}'

# Run one worker job and exit
python queuectl.py worker start --once

# Verify it completed
python queuectl.py list --state completed


Retry & DLQ Case

# Enqueue a job that will fail (max_retries defaults to 3)
python queuectl.py enqueue '{"id":"fail_job","command":"cmd /c exit 1"}'

# Run the worker and watch it retry (Ctrl+C to stop)
python queuectl.py worker start
# (You will see it attempt, fail, backoff 3s, fail, backoff 9s, fail...)

# Verify it landed in the DLQ
python queuectl.py dlq list


Retry DLQ Job

# Retry the job that failed
python queuectl.py dlq retry fail_job

# Verify it's back in pending
python queuectl.py list --state pending

# This time, let's fix it (This is a conceptual step)
# (In a real system, you might deploy a fix or change the job command)

# Run the worker again
python queuectl.py worker start --once
# (Assuming it's fixed, it will now complete)


Assumptions & Design Trade-offs

SQLite: Chosen for its built-in nature, file-based persistence, and robust BEGIN IMMEDIATE locking guarantees, which are critical for safe concurrency.

Single-threaded Worker: The worker loop is single-threaded for simplicity, but multi-worker support is enabled at the database level via atomic locking.

Shell Execution: Jobs are executed via subprocess.run(shell=True) per the assignment's allowance for commands like echo 'Hello'.

Minimal Dependencies: The project avoids external libraries for core logic (like argparse, sqlite3, subprocess) to ensure portability.

Demo Video

Click here for the QueueCTL Demo Video