# Startup Submission Agent — Plan

## Architecture Overview

```
Google Form → Google Sheets API → Analyzer (GPT-4o) → HTML Reports → S3
                                                              ↓
                               Web UI / CLI ← Scheduler (2x/day)
```

### Services (Docker Compose)
- **agent** — Python app: scheduler + Google Sheets poller + GPT-4o analyzer + report generator
- **web** — Flask web UI: view reports, trigger manual runs, view logs

### Storage
- **AWS S3** — generated HTML reports + logs
- **SQLite** (volume-mounted) — processed submission IDs + run logs + submission logs

---

## Venture IQ Upgrade — Comprehensive Analyzer Enhancement

### Goal
Transform the analyzer from a generic pitch summarizer into a venture analyst trained on
Luminarium Capital's "Getting to Wow" assessment style — separating what is interesting
from what is investable, and exposing what is real vs. claimed vs. missing.

---

## Todo Checklist

### Phase 1 — analyzer.py rewrite

- [ ] **1.1 New system prompt**
  - Role: senior VC analyst trained on Getting to Wow! framework
  - Instruction to never invent data — say "Missing / needs diligence" if not in submission
  - Instruction to be skeptical, not optimistic
  - Three-lens evaluation: investment readiness, strategic collaboration, pitch improvement

- [ ] **1.2 Proof level classifier (in prompt)**
  - Level 5: Collected revenue, repeat customers, referenceable case studies
  - Level 4: Signed paid contracts or paid pilots
  - Level 3: Active unpaid pilots, live demos, real users
  - Level 2: LOIs, MOUs, strategic partnerships, soft commitments
  - Level 1: Concept, prototype, founder claims, vision only
  - AI must assign a proof_level (1–5) and proof_level_rationale

- [ ] **1.3 Score cap enforcement (Python, post-AI)**
  - Level 1–2 → cap total_score at 74
  - Level 3    → cap total_score at 79
  - Level 4    → cap at 88
  - Level 5    → cap at 95
  - Above 95 blocked unless manually overridden
  - Log a warning when score is capped

- [ ] **1.4 Scoring guardrails (in prompt)**
  - Never >80 without: verified paid traction + clear buyer + business model + defensible proof + GTM
  - IP "strong" only if: patent / source code / data moat / partner IP / proprietary workflow
  - Partnership = traction only if tied to: revenue / contracts / distribution / paid pilot
  - "Scalable" only if the report explains what repeats without custom labor

- [ ] **1.5 Expanded JSON output schema**
  New fields the AI must return (in addition to existing):
  ```
  proof_level              int 1–5
  proof_level_rationale    string
  pitch_oneliners          {current, better, best, what_to_say_instead,
                            what_to_remove, what_proof_moves_earlier}
  services_vs_software     {verdict, reusable_parts, custom_parts,
                            gross_margin_estimate, recurring_revenue_start,
                            scale_evidence}
  first_wedge              {who_buys_first, who_owns_budget, why_buy_now,
                            first_repeatable_use_case, expansion_path,
                            focus_risk_flag}
  product_buy_button       {product_name, buyer, pricing_logic,
                            delivery_model, reusable_ip, custom_work,
                            repeatability_proof}
  competitive_landscape    {status_quo, internal_teams, agencies,
                            existing_platforms, incumbents,
                            budget_owner_today, why_switch}
  unit_economics           {cac, ltv, gross_margin, sales_cycle,
                            contract_length, free_to_paid, retention,
                            mau_dau, notes}
  ip_defensibility         {verdict, evidence, patent_filings,
                            data_moat, switching_costs, notes}
  diligence_checklist      [{item, status, notes}]  — covers all 25 items
  japan_luminarium_fit     {japan_relevance, luminarium_fit,
                            venture_iq_potential, love_my_robot_fit,
                            pilot_ideas, notes}
  next_90_day_proof_plan   [{action, purpose, timeline}]
  final_conclusion         {investment_readiness, strategic_value,
                            main_diligence_blocker, recommended_next_step,
                            founder_facing_summary, investor_facing_summary}
  ```

- [ ] **1.6 Diligence checklist (25 items) in prompt**
  AI must evaluate each item as: Answered | Partial | Missing
  Items: R&D milestones, roadmap, prototype/demo, user interviews, MAU/DAU,
  paid vs unpaid users, free-to-paid conversion, CAC, LTV, retention,
  sales cycle, contract length, regulatory risk, privacy/data, IP ownership,
  legal issues, founder background, runway, use of funds, existing debt/SAFEs,
  director/advisor contracts, team completeness, competitive alternatives,
  business model proof, go-to-market evidence

---

### Phase 2 — report_gen.py new sections

- [ ] **2.1 Update INDIVIDUAL_TEMPLATE** — add new sections after existing ones:
  - **20-Second Wow** — current / better / best one-liner + what to say instead + what to remove
  - **Proof Hierarchy** — visual level badge (1–5) with rationale
  - **Services vs Software** — verdict card + breakdown table
  - **First Wedge Market** — who buys, why now, expansion path, focus risk flag
  - **Product Buy Button** — what can be purchased today, by whom, at what price
  - **Competitive Landscape** — expanded table (status quo, agencies, incumbents, budget owner)
  - **Unit Economics** — table with all metrics, "Missing" shown clearly in red
  - **IP & Defensibility** — evidence-based verdict
  - **Diligence Checklist** — 25-item table with Answered / Partial / Missing badges
  - **Japan / Luminarium Fit** — conditional section (only shown if relevant)
  - **Next 90-Day Proof Plan** — action table
  - **Final Conclusion** — 6-part separated verdict replacing current "Bottom Line"

- [ ] **2.2 Update BATCH_TEMPLATE** — add proof level badge to leaderboard row

---

### Phase 3 — deploy

- [ ] **3.1** Rebuild Docker image locally to test
- [ ] **3.2** Push to GitHub → Jenkins pipeline redeploys to EC2
- [ ] **3.3** Regenerate all existing reports to apply new template
- [ ] **3.4** Verify one report end-to-end against Carolina's manual assessment style

---

## Files Changed

| File | Change |
|---|---|
| `app/analyzer.py` | Full rewrite of system prompt, user prompt, scoring logic, score caps |
| `app/report_gen.py` | Add 11 new sections to INDIVIDUAL_TEMPLATE, proof badge to BATCH_TEMPLATE |

No changes needed to: `pipeline.py`, `db.py`, `storage.py`, `web/server.py`, `scheduler.py`

---

## Review

_To be filled after implementation._
