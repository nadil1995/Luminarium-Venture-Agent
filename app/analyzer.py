"""
Sends a startup submission to OpenAI GPT-4o and returns a structured analysis.

Scoring dimensions:
  wow, problem, differentiation, traction, gtm_econ,
  product_tech, milestones, risk  (each 0–10)

Weighted total (0–100):
  Wow 15% | Problem 10% | Differentiation 15% | Traction 20%
  GTM+Econ 15% | Product+Tech 10% | Milestones 10% | Risk 5%

Score caps enforced in Python based on proof level:
  Level 1–2 → max 74 | Level 3 → max 79 | Level 4 → max 88 | Level 5 → max 95
"""
import json
from openai import OpenAI
from app.config import config
from app.logger import submission_logger

_client = OpenAI(api_key=config.OPENAI_API_KEY)

WEIGHTS = {
    "wow":             0.15,
    "problem":         0.10,
    "differentiation": 0.15,
    "traction":        0.20,
    "gtm_econ":        0.15,
    "product_tech":    0.10,
    "milestones":      0.10,
    "risk":            0.05,
}

# Hard score ceiling per proof level — enforced in Python after AI response
PROOF_SCORE_CAPS = {1: 74, 2: 74, 3: 79, 4: 88, 5: 95}

# ── System prompt ──────────────────────────────────────────────────────────────

SYSTEM_PROMPT = """You are Venture IQ by Luminarium Capital. \
You evaluate startups using the Getting to Wow framework and investor diligence standards. \
Your job is not to summarize founder submissions; your job is to assess investor readiness.

━━ IDENTITY & ROLE ━━
Always separate facts, founder claims, assumptions, and missing evidence. \
Never invent traction, revenue, customers, patents, or market data. \
Label unsupported claims as "Needs Verification." \
Use a professional, skeptical, constructive investor tone. \
The report should help a founder understand what is compelling, what is risky, \
what is missing, and what must be improved before speaking with investors.

━━ EVIDENCE LABELING ━━
For every significant claim in the submission, classify it as ONE of:
- Submitted by founder   → stated directly in the form
- Inferred by Venture IQ → reasonable inference from submitted data
- Needs Verification     → founder claims it but no supporting evidence
- External market context → industry knowledge, not from submission
When in doubt, use "Needs Verification" — never upgrade a claim to fact.

━━ GETTING TO WOW! FRAMEWORK ━━
CLEAR:     Can an investor understand what they do in 20 seconds?
COMPELLING: Is the value proposition urgent, differentiated, dramatically better than status quo?
CREDIBLE:  Is there proof — not just ambition?

━━ PROOF QUALITY HIERARCHY ━━
Level 5: Collected revenue, repeat customers, referenceable case studies
Level 4: Signed paid contracts or paid pilots
Level 3: Active unpaid pilots, live demos, real users
Level 2: LOIs, MOUs, strategic partnerships, soft commitments
Level 1: Concept, prototype, founder claims, vision only
Assign proof_level based on the STRONGEST verified evidence in the submission.

━━ SCORING GUARDRAILS ━━
- Never score > 80 without: verified paid traction + clear buyer + proven business model + \
defensible proof + credible GTM + evidence of scalability.
- IP is "strong" ONLY if you identify: patents, source code ownership, data moat, \
partner IP agreements, proprietary workflow, or technical switching costs.
- Partnerships = traction ONLY if tied to revenue, contracts, distribution, paid pilots, \
or direct customer access.
- "Scalable" ONLY if you explain what specifically repeats without custom labor.

━━ SCORE CAPS ━━
Level 1–2 → max 74 | Level 3 → max 79 | Level 4 → max 88 | Level 5 → max 95

━━ REPORT CONFIDENCE ━━
Assign a report_confidence rating based on data quality:
High        → deck attached, financials present, multiple verified proof points
Medium      → partial data, some proof points, incomplete financials
Medium-Low  → founder form only, no deck, traction is unverified claims
Low         → minimal data, contradictory claims, or single-field submission
State clearly in reason: what data is missing that lowers confidence.

━━ WHY NOW ━━
Every report must include a "Why Now?" section. \
What market timing, regulation, technology shift, cultural trend, or competitive gap \
makes this startup's moment RIGHT NOW? If there is no strong "why now," flag it.

━━ MARKET SIZING ━━
Do NOT use giant top-down TAM. Use bottom-up logic:
Who is the beachhead buyer? What is the use case? What is the price? \
How many reachable buyers exist in the first market? \
What does that imply for SAM? What is the larger TAM context?

━━ SERVICES VS SOFTWARE ━━
For every company, determine: scalable software | hybrid | custom services. \
What repeats without extra headcount? What must be rebuilt per client? \
When does recurring revenue start?

━━ COMPETITIVE LANDSCAPE ━━
Include ALL: status quo, internal teams, agencies, existing platforms, \
hardware vendors, incumbents, budget competitors. \
Key question: who owns the budget today, and why would they switch?

━━ DILIGENCE CHECKLIST ━━
Assess all 25 items as Answered / Partial / Missing. Never guess.

━━ INVESTOR ACTION ITEMS ━━
At the end of every report, produce:
- Top 10 diligence questions before investor introduction
- Top 5 documents to request from the founder
- Top 3 claims that require independent proof
- Top 3 pitch changes that must happen before sending to investors

━━ JAPAN / LUMINARIUM FIT ━━
Only include if there is a REAL connection. Do not force it.

━━ FINAL CONCLUSION ━━
Separately address: investment readiness, strategic value, main diligence blocker, \
recommended next step, founder-facing summary, investor-facing summary.

You respond ONLY with valid JSON — no markdown, no prose, no code fences."""

# ── User prompt ────────────────────────────────────────────────────────────────

USER_PROMPT_TEMPLATE = """Analyze this startup submission for Luminarium Venture IQ.

━━ SUBMISSION ━━
Founder: {name}
LinkedIn: {linkedin}
Country: {country_residence} / representing {country_represent}
Category: {category}

Startup / Pitch: {startup_pitch}
Problem: {problem}
Solution: {solution}
Target customers: {target_customers}
WOW factor: {wow_factor}
Business model: {business_model}
Traction: {traction}
Unfair advantage: {unfair_advantage}
GTM strategy: {gtm}
Competitors: {competitors}
Team: {team}
Funds raised: {funds_raised}
Key metric: {key_metric}
Biggest risk: {biggest_risk}
Why this team: {right_team}
10-second pitch: {ten_second_pitch}
MVP / demo: {mvp}
Inspiration: {inspiration}
━━ END SUBMISSION ━━

Return a JSON object with EXACTLY this structure (all fields required, \
use "Missing / needs diligence" where data is absent — never invent):

{{
  "startup_name": "extracted company name",
  "one_liner": "one sentence — what they do, for whom, and the outcome",
  "category": "sector / vertical",

  "scores": {{
    "wow":             <0-10 float>,
    "problem":         <0-10 float>,
    "differentiation": <0-10 float>,
    "traction":        <0-10 float>,
    "gtm_econ":        <0-10 float>,
    "product_tech":    <0-10 float>,
    "milestones":      <0-10 float>,
    "risk":            <0-10 float>
  }},

  "proof_level": <int 1-5>,
  "proof_level_rationale": "one sentence explaining the assigned level",

  "traction_summary":  "2-3 sentences of verified traction evidence only",
  "ask_summary":       "funding stage + amount asked + current runway if known",
  "top_strength":      "single strongest signal — specific, not generic",
  "main_risk":         "single most critical risk to investability",
  "fundability_tier":  "not-ready | angel | pre-seed | seed | series-a",

  "investment_view": "2-3 paragraph honest investment perspective — separates interesting from fundable",

  "pitch_oneliners": {{
    "current":                "exact current one-liner from their pitch (or closest equivalent)",
    "better":                 "improved version — clearer, more specific",
    "best":                   "Getting to Wow! version — urgent, differentiated, credible in one sentence",
    "what_to_say_instead":    "what the founder should lead with",
    "what_to_remove":         "what is hurting the pitch and should be cut",
    "what_proof_moves_earlier": "what evidence should appear in slide 1-3 instead of later"
  }},

  "green_lights":  ["specific strength 1", "specific strength 2", "specific strength 3"],
  "yellow_lights": ["specific concern 1", "specific concern 2", "specific concern 3"],
  "red_flags":     ["critical gap 1", "critical gap 2"],

  "wow_framing": "best 2-sentence investor positioning statement",
  "reframe": {{
    "not":    "what the founder is currently implying",
    "better": "a clearer framing",
    "best":   "the strongest possible framing"
  }},

  "services_vs_software": {{
    "verdict":                "scalable software | hybrid | custom services",
    "reusable_parts":         "what becomes a reusable asset",
    "custom_parts":           "what must be rebuilt per client",
    "gross_margin_estimate":  "estimate with rationale, or Missing",
    "recurring_revenue_start": "when / what triggers recurring revenue",
    "scale_evidence":         "specific evidence of non-linear scaling, or Missing"
  }},

  "first_wedge": {{
    "who_buys_first":              "specific buyer persona",
    "who_owns_budget":             "budget holder",
    "why_buy_now":                 "urgency driver",
    "first_repeatable_use_case":   "the one thing that repeats",
    "expansion_path":              "how wedge grows into larger platform",
    "focus_risk_flag":             true or false,
    "focus_risk_notes":            "explanation if flag is true, else empty string"
  }},

  "product_buy_button": {{
    "product_name":       "what the customer actually purchases",
    "buyer":              "who signs / pays",
    "pricing_logic":      "how it is priced — subscription / project / per-seat / etc.",
    "delivery_model":     "SaaS / on-site / hybrid / service / other",
    "reusable_ip":        "what IP is reused across customers",
    "custom_work":        "what is custom per engagement",
    "repeatability_proof": "evidence this can be sold again, or Missing"
  }},

  "competitive_landscape": {{
    "status_quo":          "what customers do today without this product",
    "internal_teams":      "internal / DIY alternatives",
    "agencies":            "agencies or consultants competing for same budget",
    "existing_platforms":  "software tools customers already use",
    "incumbents":          "large companies in the space",
    "budget_owner_today":  "who owns the budget today",
    "why_switch":          "compelling reason to switch — or Missing if not proven"
  }},

  "unit_economics": {{
    "cac":               "value or Missing",
    "ltv":               "value or Missing",
    "gross_margin":      "value or Missing",
    "sales_cycle":       "value or Missing",
    "contract_length":   "value or Missing",
    "free_to_paid":      "conversion rate or Missing",
    "retention":         "rate or Missing",
    "mau_dau":           "value or Missing",
    "notes":             "any additional economics context"
  }},

  "ip_defensibility": {{
    "verdict":         "strong | potential | weak | unclear",
    "evidence":        ["specific evidence item 1", "or Missing if none"],
    "patent_filings":  "yes / no / pending / Missing",
    "data_moat":       "description or Missing",
    "switching_costs": "description or Missing",
    "notes":           "overall defensibility narrative"
  }},

  "diligence_checklist": [
    {{"item": "R&D milestones",              "status": "Answered|Partial|Missing", "notes": "..."}},
    {{"item": "Product roadmap",             "status": "Answered|Partial|Missing", "notes": "..."}},
    {{"item": "Prototype / demo",            "status": "Answered|Partial|Missing", "notes": "..."}},
    {{"item": "User interviews",             "status": "Answered|Partial|Missing", "notes": "..."}},
    {{"item": "MAU / DAU metrics",           "status": "Answered|Partial|Missing", "notes": "..."}},
    {{"item": "Paid vs unpaid users",        "status": "Answered|Partial|Missing", "notes": "..."}},
    {{"item": "Free-to-paid conversion",     "status": "Answered|Partial|Missing", "notes": "..."}},
    {{"item": "CAC",                         "status": "Answered|Partial|Missing", "notes": "..."}},
    {{"item": "LTV",                         "status": "Answered|Partial|Missing", "notes": "..."}},
    {{"item": "Retention rate",              "status": "Answered|Partial|Missing", "notes": "..."}},
    {{"item": "Sales cycle length",          "status": "Answered|Partial|Missing", "notes": "..."}},
    {{"item": "Contract length",             "status": "Answered|Partial|Missing", "notes": "..."}},
    {{"item": "Regulatory risk",             "status": "Answered|Partial|Missing", "notes": "..."}},
    {{"item": "Privacy / data handling",     "status": "Answered|Partial|Missing", "notes": "..."}},
    {{"item": "IP ownership",                "status": "Answered|Partial|Missing", "notes": "..."}},
    {{"item": "Legal issues",                "status": "Answered|Partial|Missing", "notes": "..."}},
    {{"item": "Founder background risks",    "status": "Answered|Partial|Missing", "notes": "..."}},
    {{"item": "Runway",                      "status": "Answered|Partial|Missing", "notes": "..."}},
    {{"item": "Use of funds",                "status": "Answered|Partial|Missing", "notes": "..."}},
    {{"item": "Debt / SAFEs / notes",        "status": "Answered|Partial|Missing", "notes": "..."}},
    {{"item": "Advisor / director contracts","status": "Answered|Partial|Missing", "notes": "..."}},
    {{"item": "Team completeness",           "status": "Answered|Partial|Missing", "notes": "..."}},
    {{"item": "Competitive alternatives",    "status": "Answered|Partial|Missing", "notes": "..."}},
    {{"item": "Business model proof",        "status": "Answered|Partial|Missing", "notes": "..."}},
    {{"item": "GTM evidence",                "status": "Answered|Partial|Missing", "notes": "..."}}
  ],

  "japan_luminarium_fit": {{
    "japan_relevance":      "high | medium | low | none",
    "luminarium_fit":       "strong | potential | weak | none",
    "venture_iq_potential": "description or Not applicable",
    "love_my_robot_fit":    "description or Not applicable",
    "pilot_ideas":          ["idea 1", "or empty list if not applicable"],
    "notes":                "overall fit narrative or Not applicable"
  }},

  "report_confidence": {{
    "rating": "High | Medium | Medium-Low | Low",
    "reason": "specific explanation of what data is missing or present that drives this rating"
  }},

  "why_now": {{
    "summary":       "1-2 sentence answer: why does this startup's moment exist right now?",
    "drivers":       ["market timing driver 1", "regulation / tech shift", "competitive gap"],
    "strength":      "strong | moderate | weak | missing",
    "notes":         "additional context or flag if why-now is not clear"
  }},

  "bottom_up_market": {{
    "beachhead_buyer":      "specific buyer persona in first market",
    "use_case":             "primary use case",
    "price_per_customer":   "estimated ACV or project value",
    "reachable_buyers":     "estimated number of buyers in beachhead market",
    "sam_estimate":         "beachhead × price = first SAM estimate",
    "tam_context":          "broader market context (not generic TAM)",
    "notes":                "limitations of this estimate or missing data"
  }},

  "claims_needing_verification": [
    {{
      "claim":               "the founder's claim",
      "label":               "Submitted by founder | Inferred by Venture IQ | Needs Verification | External market context",
      "verification_needed": "what specific evidence would verify this"
    }}
  ],

  "missing_slides": [
    "slide or section missing from the pitch that investors will ask for"
  ],

  "judge_questions": ["sharpest question 1 for a live Q&A", "sharpest question 2"],
  "why_scores_well":  "1-2 sentences on the strongest signal in the deck",

  "diligence_gaps": [
    {{"question": "...", "why_matters": "...", "needed_proof": "..."}}
  ],

  "pitch_improvements": ["specific improvement 1", "improvement 2", "improvement 3"],
  "recommended_milestones": ["milestone 1 with timeframe", "milestone 2", "milestone 3"],

  "next_90_day_proof_plan": [
    {{"action": "...", "purpose": "...", "timeline": "..."}}
  ],

  "top_diligence_questions": [
    "question 1 before investor introduction",
    "question 2", "question 3", "question 4", "question 5",
    "question 6", "question 7", "question 8", "question 9", "question 10"
  ],

  "top_docs_to_request": [
    "document 1 to request from founder",
    "document 2", "document 3", "document 4", "document 5"
  ],

  "top_claims_needing_proof": [
    "claim 1 that requires independent verification",
    "claim 2",
    "claim 3"
  ],

  "pitch_changes_before_investors": [
    "change 1 that must happen before sending to investors",
    "change 2",
    "change 3"
  ],

  "final_conclusion": {{
    "investment_readiness":      "one honest paragraph",
    "strategic_value":           "one paragraph on collaboration / pilot / non-investment value",
    "main_diligence_blocker":    "the single most important gap to resolve",
    "recommended_next_step":     "concrete action Luminarium should take",
    "founder_facing_summary":    "direct, constructive 2-3 sentences the founder can act on",
    "investor_facing_summary":   "honest 2-3 sentences for an investor deciding whether to advance"
  }}
}}"""


# ── public API ─────────────────────────────────────────────────────────────────

def analyze(submission: dict) -> dict:
    """
    Send submission to GPT-4o, enforce proof-level score caps, return enriched analysis dict.
    """
    startup_name = submission.get("startup_pitch", "Unknown")[:60]
    submission_logger.info(f"Analyzing: {startup_name} (id={submission.get('submission_id')})")

    prompt = USER_PROMPT_TEMPLATE.format(**{
        k: submission.get(k, "Not provided") for k in [
            "name", "linkedin", "country_residence", "country_represent",
            "category", "startup_pitch", "problem", "solution",
            "target_customers", "wow_factor", "business_model", "traction",
            "unfair_advantage", "gtm", "competitors", "team", "funds_raised",
            "key_metric", "biggest_risk", "right_team", "ten_second_pitch",
            "mvp", "inspiration",
        ]
    })

    response = _client.chat.completions.create(
        model=config.OPENAI_MODEL,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user",   "content": prompt},
        ],
        temperature=0.2,        # lower than before — more consistent, less hallucination
        response_format={"type": "json_object"},
    )

    analysis = json.loads(response.choices[0].message.content)

    # ── Compute weighted total ─────────────────────────────────────────────────
    scores = analysis.get("scores", {})
    raw_total = sum(scores.get(k, 0) * w * 10 for k, w in WEIGHTS.items())
    raw_total = round(raw_total, 1)

    # ── Enforce proof-level score cap ──────────────────────────────────────────
    proof_level = int(analysis.get("proof_level", 1))
    proof_level = max(1, min(5, proof_level))       # clamp to valid range
    cap = PROOF_SCORE_CAPS.get(proof_level, 74)

    if raw_total > cap:
        submission_logger.warning(
            f"Score capped: {raw_total} → {cap} "
            f"(proof_level={proof_level} for {startup_name})"
        )
        # Scale down dimension scores proportionally so scorecard stays consistent
        scale = cap / raw_total
        for k in scores:
            scores[k] = round(scores[k] * scale, 1)
        analysis["scores"]      = scores
        analysis["total_score"] = cap
        analysis["score_capped"] = True
    else:
        analysis["total_score"] = raw_total
        analysis["score_capped"] = False

    analysis["proof_level"] = proof_level

    # ── Score tier for colour coding ───────────────────────────────────────────
    analysis["score_tier"] = (
        "good" if analysis["total_score"] >= 70 else
        "mid"  if analysis["total_score"] >= 50 else
        "bad"
    )

    # ── Carry over submission metadata ─────────────────────────────────────────
    analysis["submission_id"]        = submission.get("submission_id", "")
    analysis["submitter_name"]       = submission.get("name", "")
    analysis["submitter_email"]      = submission.get("email", "")
    analysis["submission_timestamp"] = submission.get("timestamp", "")
    analysis["deck_url"]             = submission.get("deck_url", "")

    submission_logger.info(
        f"Scored {analysis.get('startup_name', startup_name)}: "
        f"{analysis['total_score']}/100 "
        f"(proof_level={proof_level}, capped={analysis['score_capped']})"
    )
    return analysis
