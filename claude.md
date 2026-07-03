---
applyTo: '**'
---
Coding standards, domain knowledge, and preferences that AI should follow.

Workflow

First, think through the problem. Read the codebase and write a plan in tasks/todo.md.

The plan should be a checklist of todo items.

always use docker compose to run the project locally. If you need to run a command, add it to the docker compose file.

user separate containers for each service, and use docker compose to manage them.

use aws s3 for file storage, and add the necessary configuration to the project.

Check in with me before starting work—I’ll verify the plan.

Then, complete the todos one by one, marking them off as you go.

At every step, give me a high-level explanation of what you changed.

Keep every change simple and minimal. Avoid 
big rewrites.




At the end, add a review section in todo.md summarizing the changes.

---

# Agent API — POST /generate-report

This app runs as a report-generation service for an external User Management app.
The in-house form (replacing the retired Google Form) triggers report generation
by calling this endpoint on each submit. This app ONLY generates and returns
reports — payment, user accounts, admin approval, and report display all live in
the User Management app.

## Endpoint

```
POST /generate-report
Authorization: Bearer <AGENT_API_KEY>
Content-Type: application/json
```

### Request body
```json
{
  "report_id": "<uuid>",
  "callback_url": "https://<user-mgmt>/functions/v1/report-complete?id=<uuid>",
  "user_data":    { "id": "...", "email": "...", "full_name": "...", "created_at": "..." },
  "form_data":    { "name": "...", "startup_pitch": "...", "problem": "...", ... },
  "payment_data": { "orders": [], "has_paid": true },
  "report_meta":  { "status": "...", "created_at": "..." }
}
```
- Required: `report_id`, `form_data`, `callback_url`. Missing → `400`.
- Bad/missing Bearer token → `401`.
- `payment_data` is ignored (the User Management app owns payment enforcement).

### Immediate response
```json
HTTP 202 Accepted
{ "status": "processing", "report_id": "<uuid>" }
```
Generation runs in a background thread; the caller is not blocked.

## Callback contract

On completion the app POSTs to `callback_url` with the same Bearer token:

Success:
```json
{ "report_id": "<uuid>", "report_content": "<html>...</html>" }
```
Failure:
```json
{ "report_id": "<uuid>", "error": "<reason>" }
```
The callback is retried up to 3 times (2s/4s backoff, 10s timeout each).
An error callback is always sent on failure so no report is stuck "processing".

## form_data field contract

The in-house form must send these exact keys (same questions as the old Google
Form). Missing keys are tolerated and render as "Not provided". `email` is taken
from `user_data.email` (falls back to `form_data.email`).

```
name, linkedin, country_residence, country_represent, category,
startup_pitch, problem, solution, target_customers, wow_factor,
business_model, traction, unfair_advantage, gtm, competitors, team,
funds_raised, key_metric, biggest_risk, right_team, ten_second_pitch,
mvp, inspiration
```

## Environment variables
- `AGENT_API_KEY` — shared secret; must match the User Management app's value.
- `SCHEDULER_ENABLED` — `false` in API mode (disables legacy Google Sheets polling).
  Set `true` only to revert to Google Form polling.