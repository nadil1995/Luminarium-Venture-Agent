# Startup Agent — Task Plan

## Current: Report not showing on user profile after generation

### Symptom
API generates the report fine; callback is delivered; but the report never
appears on the user's profile in the User Management app.

### The delivery chain (where it can break)
```
[1] Agent POSTs to callback_url ................ agent logs prove this
[2] /report-complete saves content,
    sets status = pending_approval ............. Supabase function logs / DB row
[3] Admin approves ............................. their admin dashboard
[4] Approved report rendered on profile ........ their frontend
```
Steps 2–4 live in the User Management app. Their own spec: callback sets
status → pending_approval — reports are DESIGNED not to show until approved.
The approve → attach-to-profile flow (step 4) was flagged earlier as "to plan"
and is most likely NOT BUILT yet.

### Diagnosis checklist
- [ ] **D1** Agent side: on the instance that served the test, run
      `docker compose logs web | grep "\[api\]"` — confirm
      "Callback success delivered … status 2xx". If "rejected"/"FAILED",
      the problem is delivery (AGENT_API_KEY mismatch, wrong callback_url).
- [ ] **D2** Supabase: check the report row:
      `select id, user_id, status, length(report_content), created_at
       from reports where id = '<report_id>';`
      - status='processing', content null → callback never matched the row
        → check report-complete function logs + id param handling
      - status='pending_approval', content present → chain works; missing
        piece is approval + profile display (most likely)
      - status='approved' but profile empty → frontend query/render bug
- [ ] **D3** Confirm which case applies before building the fix.

### Fix plan (User Management app — need codebase path/repo)
- [ ] **F1** Admin review UI: list reports where status='pending_approval',
      preview report_content, Approve / Reject buttons.
- [ ] **F2** Approve action: status → 'approved', set approved_at/approved_by.
      (Optional per Venture IQ policy: auto-approve when report confidence
      is High — agent already embeds this in the report.)
- [ ] **F3** Profile page: query reports where user_id = <profile user> AND
      status='approved'; render report_content in a sandboxed iframe
      (srcDoc) — it is a full standalone HTML document with its own CSS/JS.
- [ ] **F4** RLS policies: users SELECT only their own approved reports;
      admins see all statuses.
- [ ] **F5** End-to-end test: form submit → agent → callback →
      pending_approval → approve → visible on profile.

### Agent repo changes needed
None — the agent's job ends at callback delivery (confirmed working).

---

## Done: API Service Layer — POST /generate-report

### Goal
Expose report generation as a REST API so an external User Management app can POST
form data, get a 202 immediately, and receive the finished HTML report via callback
URL. This becomes the SOLE entry point — the Google Form + 2-min Sheets scheduler
is retired; the in-house form calls `/generate-report` on each submit.
This app handles ONLY: receive → analyze → generate → callback.
No payment, no user accounts, no approval logic.

---

### Files to change

| File | Change |
|---|---|
| `app/config.py` | Add `AGENT_API_KEY` + `SCHEDULER_ENABLED` (default false) |
| `app/main.py` | Gate `start_scheduler()` behind `SCHEDULER_ENABLED` |
| `app/web/server.py` | Add `POST /generate-report` endpoint + auth helper |
| `app/api_worker.py` | NEW — background generation + callback with retry |
| `requirements.txt` | Add `requests>=2.31.0` |
| `.env` / `.env.example` | Add `AGENT_API_KEY`, `SCHEDULER_ENABLED=false` |
| `CLAUDE.md` | Document new endpoint, callback contract, + form field contract |

---

### Checklist

#### Phase 1 — Config
- [ ] **1.1** Add `AGENT_API_KEY` to `config.py` as a required env var
- [ ] **1.2** Add `SCHEDULER_ENABLED` to `config.py` (default `false`)
- [ ] **1.3** Add `AGENT_API_KEY=change-me-shared-secret` and `SCHEDULER_ENABLED=false`
      to `.env` and `.env.example`

#### Phase 1b — Disable Google Sheets scheduler
- [ ] **1b.1** In `main.py`, only call `start_scheduler()` if `config.SCHEDULER_ENABLED`;
      log "Scheduler disabled — API mode" otherwise. Code stays intact for revert.

#### Phase 2 — Endpoint in server.py
- [ ] **2.1** Add `_check_bearer(request)` helper — reads `Authorization: Bearer <token>`,
      compares to `config.AGENT_API_KEY`, returns `(True, None)` or `(False, Response 401)`
- [ ] **2.2** Add `POST /generate-report` route:
  - Call auth helper → abort 401 if invalid
  - Parse JSON body → 400 if `report_id`, `form_data`, or `callback_url` missing
    (`user_data`, `payment_data`, `report_meta` are optional pass-through context)
  - Spin up daemon thread: `api_worker.run(payload)`
  - Return `202 { "status": "processing", "report_id": "..." }`

#### Phase 3 — app/api_worker.py (new file)
- [ ] **3.1** `run(report_id, form_data, callback_url, user_data, payment_data)` — background fn:
  - Build submission dict from `form_data` + `user_data` (name/email); set `submission_id = report_id`
  - Call `analyzer.analyze(submission)`
  - Call `report_gen.generate_individual_report(analysis)`
  - Read HTML content from the generated file path
  - Call `_post_callback(callback_url, report_id, report_content=html)`
  - On any exception: call `_post_callback(callback_url, report_id, error=str(e))`
  - Log each stage clearly

- [ ] **3.2** `_post_callback(url, report_id, *, report_content=None, error=None)` with retry:
  - 3 attempts, exponential backoff: wait 2s → 4s → 8s between attempts
  - Headers: `Authorization: Bearer <AGENT_API_KEY>`, `Content-Type: application/json`
  - Success body: `{ "report_id": "...", "report_content": "<html>..." }`
  - Error body:   `{ "report_id": "...", "error": "reason" }`
  - Per-attempt timeout: 10 seconds
  - Log clearly on every attempt and final failure

#### Phase 4 — Dependencies
- [ ] **4.1** Add `requests>=2.31.0` to `requirements.txt`

#### Phase 5 — Documentation
- [ ] **5.1** Update `CLAUDE.md` with endpoint docs + callback contract

---

### API Contract (reference)

**Request** (exact shape sent by the User Management app's trigger-agent function)
```
POST /generate-report
Authorization: Bearer <AGENT_API_KEY>
Content-Type: application/json

{
  "report_id":  "<uuid>",
  "callback_url": "https://<supabase>/functions/v1/report-complete?id=<uuid>",
  "user_data":    { "id", "email", "full_name", "created_at" },
  "form_data":    { ...questionnaire fields (name, startup_pitch, problem, ...) },
  "payment_data": { "orders": [...], "has_paid": true|false },
  "report_meta":  { "status", "created_at" }
}
```

**Immediate response**
```
HTTP 202 Accepted
{ "status": "processing", "report_id": "<uuid>" }
```

**Callback (success)** — matches their inbound /report-complete which sets status → pending_approval
```
POST {callback_url}
Authorization: Bearer <AGENT_API_KEY>
Content-Type: application/json

{ "report_id": "<uuid>", "report_content": "<html>...</html>" }
```

**Callback (failure)**
```
POST {callback_url}
Authorization: Bearer <AGENT_API_KEY>
Content-Type: application/json

{ "report_id": "<uuid>", "error": "OpenAI timeout after 3 retries" }
```

### form_data field contract (for the in-house form team)
The in-house form must send `form_data` using these EXACT key names (same questions
as the old Google Form). Any missing key is tolerated → rendered as "Not provided".

| Key | Question / meaning |
|---|---|
| `name` | Founder full name |
| `linkedin` | LinkedIn URL |
| `country_residence` | Country of residence |
| `country_represent` | Country the startup represents |
| `category` | Industry / category |
| `startup_pitch` | One-line startup pitch |
| `problem` | Problem being solved |
| `solution` | The solution |
| `target_customers` | Target customers |
| `wow_factor` | What makes it wow / unique |
| `business_model` | How it makes money |
| `traction` | Traction so far |
| `unfair_advantage` | Unfair advantage / moat |
| `gtm` | Go-to-market strategy |
| `competitors` | Competitors |
| `team` | Team background |
| `funds_raised` | Funds raised to date |
| `key_metric` | Most important metric |
| `biggest_risk` | Biggest risk |
| `right_team` | Why this is the right team |
| `ten_second_pitch` | 10-second pitch |
| `mvp` | MVP built/launched? (link or description) |
| `inspiration` | What inspires the founder |

`email` comes from `user_data.email` (falls back to `form_data.email` if present).

### Ownership boundary (full flow)
```
User Mgmt app (admin trigger)  →  POST /generate-report  →  THIS APP
THIS APP  →  analyze + generate  →  POST callback { report_id, report_content }
User Mgmt app  →  status = pending_approval  →  admin approves  →  attaches to profile
```
Approval + attaching the report to the user's profile happens ENTIRELY in the User
Management app. This app never touches approval, profiles, or display.

---

### Decisions
- **Payment gate:** IGNORE `payment_data.has_paid` — always generate when called.
  Their admin-only trigger already decides eligibility; payment stays their concern.

### What this does NOT change
- Google Sheets code (`google_sheets.py`, `pipeline.py`, `scheduler.py`) — kept intact,
  just no longer triggered (scheduler gated off). Easy revert if needed.
- SendGrid notifications — not sent for API-triggered reports
- SQLite mark_processed — not called (report_id is external, no deduplication needed)
- S3 upload — not done for API reports (report_content returned inline in callback)

---

## Review

Implemented the agent API service layer. Summary of changes:

- **config.py** — added `AGENT_API_KEY` (Bearer secret) and `SCHEDULER_ENABLED`
  (default `false`, disables legacy Google Sheets polling in API mode).
- **main.py** — `start_scheduler()` now gated behind `SCHEDULER_ENABLED`; logs
  "Scheduler disabled (API mode)" otherwise. Shutdown handles `scheduler=None`.
- **api_worker.py** (new) — `run()` maps `form_data`+`user_data` onto the analyzer's
  submission shape, runs analyze + generate, reads the HTML, and delivers it via
  `_post_callback()`. Callback retries 3x with 2s/4s backoff (10s timeout each);
  always sends an error callback on failure so nothing is stuck "processing".
- **web/server.py** — `POST /generate-report`: Bearer auth (`_bearer_ok`), payload
  validation (400 on missing `report_id`/`form_data`/`callback_url`), fires a daemon
  thread and returns `202 {status: processing, report_id}` immediately.
- **requirements.txt** — added `requests>=2.31.0`.
- **.env / .env.example** — added `SCHEDULER_ENABLED=false`, `AGENT_API_KEY`.
- **CLAUDE.md** — documented endpoint, auth, callback contract, and form field contract.

### Tests (run in Docker against luminarium-local:test)
- no auth → 401 ✓
- bad token → 401 ✓
- missing fields → 400 with clear message ✓
- valid request → 202 immediate; background generation → callback delivered with
  Bearer auth, correct report_id, 43KB HTML ✓
- unreachable callback → 3 attempts, ~6s backoff, error logged, returns False ✓

### Not changed (kept for easy revert)
Google Sheets code (`google_sheets.py`, `pipeline.py`, `scheduler.py`) intact but
dormant. API reports skip SQLite dedup, S3, and SendGrid by design.

### Deploy notes
- Set a real `AGENT_API_KEY` on EC2 `.env` (must match the User Management app).
- Keep `SCHEDULER_ENABLED=false` on EC2.
- Ensure EC2 security group allows the User Management app to reach port 5050,
  and that this app can reach the Supabase callback URL outbound.
