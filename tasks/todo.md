# Startup Submission Agent — Plan

## Architecture Overview

```
Google Form → Google Sheets API → Analyzer (Claude) → HTML Reports → S3
                                                              ↓
                               Web UI / CLI ← Scheduler (2x/day)
```

### Services (Docker Compose)
- **agent** — Python app: scheduler + Google Sheets poller + Claude analyzer + report generator
- **web** — Flask web UI: view reports, trigger manual runs, view logs

### Storage
- **AWS S3** — generated HTML reports + submission JSON snapshots
- **SQLite** (volume-mounted) — processed submission IDs + run logs + submission logs

---

## Todo Checklist

### Setup & Config
- [ ] Create `tasks/todo.md` (this file)
- [ ] Create `.env.example` with all required env vars
- [ ] Create `docker-compose.yml` with `agent` and `web` services
- [ ] Create `Dockerfile` for shared Python image

### Core Agent (`app/`)
- [ ] `app/config.py` — load env vars, validate required keys
- [ ] `app/logger.py` — structured logging to file + stdout (process log + submission log)
- [ ] `app/db.py` — SQLite: `processed_submissions`, `run_log`, `submission_log` tables
- [ ] `app/google_sheets.py` — authenticate with service account, fetch all rows from linked Sheet
- [ ] `app/analyzer.py` — send submission data to OpenAI API (gpt-4o), return structured analysis JSON
- [ ] `app/report_gen.py` — render analysis JSON into styled HTML report (matching attached style)
- [ ] `app/storage.py` — upload/download reports and snapshots to/from AWS S3
- [ ] `app/pipeline.py` — orchestrate: fetch → diff → analyze → generate → store → log
- [ ] `app/scheduler.py` — APScheduler: run pipeline at 08:00 and 20:00 UTC
- [ ] `app/cli.py` — CLI: `run`, `regenerate <submission_id>`, `list`, `status`
- [ ] `app/main.py` — entry point: start scheduler + web server

### Web UI (`app/web/`)
- [ ] `app/web/server.py` — Flask routes: `/`, `/reports`, `/logs`, `/run`, `/regenerate`
- [ ] `app/web/templates/index.html` — dashboard: run status, recent reports, trigger buttons
- [ ] `app/web/templates/logs.html` — view process + submission logs
- [ ] `app/web/templates/reports.html` — list + open generated reports

### Report Style
- [ ] Match dark-theme HTML style from `judge_report_v3.html` (leaderboard + per-startup cards)
- [ ] Match detailed single-startup style from `phont_venture_analysis.html`
- [ ] Two report types: **Batch report** (all new submissions) + **Individual report** (one startup)

### Tests & Docs
- [ ] `README.md` — setup steps, env var table, how to run locally, how to connect Google Form

---

## Environment Variables Required

| Var | Description |
|-----|-------------|
| `GOOGLE_SHEET_ID` | ID of the Sheet linked to the Google Form |
| `GOOGLE_SERVICE_ACCOUNT_JSON` | Path to service account key file (mounted as volume) |
| `OPENAI_API_KEY` | OpenAI API key |
| `AWS_ACCESS_KEY_ID` | AWS credentials |
| `AWS_SECRET_ACCESS_KEY` | AWS credentials |
| `AWS_REGION` | e.g. `us-east-1` |
| `S3_BUCKET` | Bucket name for reports |
| `SCHEDULE_HOURS` | Comma-separated UTC hours to run, default `8,20` |
| `WEB_PORT` | Flask port, default `5050` |

---

## Key Design Decisions

1. **Google Form → Sheet**: Form submissions must be linked to a Google Sheet. Agent reads the Sheet via Sheets API (no Forms API needed).
2. **Deduplication**: Each row has a `Timestamp` column. We store a hash of `(timestamp + email)` as the unique submission ID in SQLite.
3. **Regenerate**: CLI/web can force-reprocess any submission ID even if already processed.
4. **Two report modes**:
   - *Batch*: all new submissions in one run → one combined HTML (judge_report style)
   - *Individual*: deep-dive on one submission → per-startup HTML (phont_venture style)
5. **Logs**: Two separate log files — `process.log` (scheduler runs, errors) and `submissions.log` (per-submission events).

---

## Review

All tasks complete. Built:

- `Dockerfile` + `docker-compose.yml` — two services: `agent` (scheduler+web) and `web` (standalone web UI)
- `app/config.py` — env var loader with validation
- `app/db.py` — SQLite: `processed_submissions`, `run_log`, `submission_log` tables
- `app/logger.py` — `process.log` + `submissions.log`
- `app/google_sheets.py` — gspread client, fuzzy header mapping for all 25 form fields, dedup by sha256(timestamp+email)
- `app/analyzer.py` — OpenAI GPT-4o structured JSON analysis, weighted 0-100 score
- `app/report_gen.py` — Jinja2 HTML: batch (leaderboard style) + individual (deep-dive style)
- `app/storage.py` — S3 upload/download, gracefully disabled if no credentials
- `app/pipeline.py` — full orchestration with new/skip logic, regenerate support
- `app/scheduler.py` — APScheduler UTC cron (configurable hours)
- `app/cli.py` — `run`, `regenerate`, `list`, `runs`, `status` commands
- `app/main.py` — starts scheduler + Flask in same process
- `app/web/server.py` + three templates — dark-theme dashboard, reports list, logs viewer
- `.gitignore`, `.env.example`, `credentials/.gitkeep`
