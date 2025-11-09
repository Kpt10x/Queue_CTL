# QueueCTL — CLI Background Job Queue

> Minimal, production-grade background job queue with retries, DLQ, and persistent storage.

**Tech Stack:** Python 3.x, SQLite, `argparse`, `subprocess`

**Submission Artifacts:** Public GitHub repo + README (this file) + demo video

**Demo Video:**
`[Watch the demo](https://drive.google.com/file/d/1oA1Fr6zpjqKCWjWhx1oyVG-EX0qTBcZM/view?usp=sharing)`

---

## 🎯 Objective

Build a CLI tool `queuectl` to enqueue jobs, run worker(s), auto-retry failures with exponential backoff, and move permanently failed jobs to a Dead Letter Queue (DLQ). Data must persist across restarts.

---

## ✅ Features (Mapped to Requirements)

* Enqueue and manage background jobs
* Single worker loop with **atomic fetch** to avoid duplicates (scales to multi-worker)
* Exponential backoff retries: `delay = base^attempts` (configurable)
* Dead Letter Queue (DLQ) with `list` and `retry`
* Persistent storage via SQLite (`queue.db`)
* CLI: `enqueue`, `worker`, `list`, `status`, `dlq`
* Minimal demo script (`demo.ps1`) that validates core flows end-to-end

---

## 📦 Job Specification

```json
{
  "id": "unique-job-id",
  "command": "echo 'Hello World'",
  "state": "pending",
  "attempts": 0,
  "max_retries": 3,
  "created_at": "2025-11-04T10:30:00Z",
  "updated_at": "2025-11-04T10:30:00Z"
}
```

Additional column used by the system:

* `next_run_at` (TEXT): when the job becomes eligible to run (supports backoff and scheduling)

---

## 🧱 Architecture Overview

### Data Model (SQLite: `queue.db`)

**Table: `jobs`**

| Column        | Type | Notes                                                   |
| ------------- | ---- | ------------------------------------------------------- |
| `id`          | TEXT | Primary key                                             |
| `command`     | TEXT | Shell command to execute                                |
| `state`       | TEXT | `pending` | `processing` | `completed` | `dead`         |
| `attempts`    | INT  | Number of attempts so far                               |
| `max_retries` | INT  | Max allowed retry attempts                              |
| `created_at`  | TEXT | UTC timestamp                                           |
| `updated_at`  | TEXT | UTC timestamp                                           |
| `next_run_at` | TEXT | UTC timestamp when eligible to run (backoff/scheduling) |

> On enqueue: `state='pending'`, `attempts=0`, and `next_run_at=created_at`.

### Worker Logic

1. **Atomic Fetch (Locking):**
   Use `BEGIN IMMEDIATE` and a single transaction to:

   * select the next runnable `pending` job (`next_run_at <= now`)
   * immediately mark it `processing`
     This prevents two workers from picking the same job.

2. **Execution:**
   Execute `command` via `subprocess.run(..., shell=True, timeout=30)`.

3. **State Transitions:**

   * Success (`returncode == 0`) → `completed`
   * Failure → increment `attempts`, compute `delay = base^attempts`, set `next_run_at = now + delay`, return to `pending`
   * If `attempts >= max_retries` → `dead` (DLQ)

4. **Backoff Config:**
   `base` is configurable (default `3` seconds). Example sequence: 3s, 9s, 27s, …

---

## 🧰 Setup Instructions

```bash
# Create & activate venv
python -m venv .venv
# Windows PowerShell
.\.venv\Scripts\Activate.ps1
# macOS/Linux
# source .venv/bin/activate

# No third-party deps required for the core CLI
# (If you use any, list them here and pip install)
```

Initialize the database happens automatically on first use (via your init function). If you have a dedicated init command, list it here.

---

## 🚀 Usage Examples

> PowerShell quoting can be tricky. Prefer JSON files or here-strings for stability.

### 1) Enqueue

**Using a file (recommended):**

`job_ok.json`

```json
{"id":"job_ok_1","command":"python -c \"print(42)\"","max_retries":3}
```

`job_fail.json`

```json
{"id":"job_fail","command":"cmd /c exit 1","max_retries":3}
```

```powershell
python queuectl.py enqueue --file job_ok.json
python queuectl.py enqueue --file job_fail.json
```

**Using inline JSON (PowerShell escaping):**

```powershell
python queuectl.py enqueue "{\"id\":\"ok2\",\"command\":\"python -c \\\"print(99)\\\"",\"max_retries\":3}"
```

### 2) List Jobs

```powershell
python queuectl.py list
python queuectl.py list --state pending
```

### 3) Start the Worker

Process one job and exit:

```powershell
python queuectl.py worker start --once
```

Run continuously (Ctrl+C to stop):

```powershell
python queuectl.py worker start
```

### 4) Status

```powershell
python queuectl.py status
# → [{"state":"completed","count":1}, {"state":"dead","count":1}, ...]
```

### 5) Dead Letter Queue (DLQ)

```powershell
python queuectl.py dlq list
python queuectl.py dlq retry job_fail
```

---

## 🧪 Testing Instructions

You can run the automated demo script (used for the video):

```powershell
# Allow running local scripts once per session
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass

# Run demo (creates/uses queue.db in the repo folder)
powershell -ExecutionPolicy Bypass -File demo.ps1
```

The demo covers:

* enqueue success + failure
* worker `--once` (success completes)
* worker continuous (failure → retries → DLQ)
* status
* dlq list
* dlq retry
* worker `--once` to process the retried DLQ job

---

## 🗺️ CLI Surface (Reference)

```
queuectl enqueue [JSON or --file <path>]
queuectl worker start [--once]
queuectl list [--state pending|processing|completed|dead]
queuectl status
queuectl dlq list
queuectl dlq retry <job_id>
```

---

## 📁 Repository Structure

```
.
├─ queuectl.py          # CLI entrypoint (argparse subcommands)
├─ worker.py            # Worker loop, atomic fetch, retry/DLQ logic
├─ database.py          # DB helpers and schema init
├─ demo.ps1             # End-to-end demo script (used in the video)
├─ inspect_jobs.py      # Helper: prints full jobs table as JSON (debug)
├─ fix_states.py        # Helper: normalizes legacy states to 'pending' (debug)
├─ job_ok.json          # Sample success job
├─ job_fail.json        # Sample failing job
└─ README.md
```

> Include `demo.ps1` in the repo so reviewers can reproduce the exact flow. Do **not** ignore it.

---

## 🧠 Assumptions & Trade-offs

* **Single-host, process-based workers**: Focused on assignment scope. For scale, move to a service manager (systemd/K8s) and a network DB (e.g., Postgres).
* **SQLite + WAL-ready**: Durable enough for a demo; production systems may require stronger isolation/observability.
* **Optimistic job claiming** with `BEGIN IMMEDIATE`: simple and safe for multiple local workers; avoids duplicate processing.
* **Shell execution**: Kept simple for the assignment. Real systems would sandbox commands and capture structured logs/metrics.

---

## 🌟 Bonus Ideas (Not required, easy to add)

* `timeout_seconds` per job (override default 30s)
* Priority queues (already supported by schema extension)
* Scheduled jobs: set `next_run_at` in the future
* Per-job stdout/stderr logs in `logs/{job_id}.log`
* Metrics (attempt histograms, mean latency)

---

## 🎬 Demo Video (exact line to include)

`[Watch the demo](https://drive.google.com/file/d/1oA1Fr6zpjqKCWjWhx1oyVG-EX0qTBcZM/view?usp=sharing)`

---

## 📌 Notes for Reviewers

* Core robustness hinges on the **atomic fetch** (transaction with `BEGIN IMMEDIATE`), which guarantees no duplicate consumption under multi-worker scenarios.
* All lifecycle transitions are persisted; restarts do not lose state.
* The demo script intentionally uses one success job and one failure job to exercise the full state machine.

---

## License

MIT (or your preferred license)
