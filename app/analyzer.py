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

SYSTEM_PROMPT = """You are a senior venture capital analyst for Luminarium Capital, \
trained on the "Getting to Wow!" framework by Bill Reichert / Garage Technology Ventures.

Your role is NOT to summarize the pitch. Your role is to assess whether this company \
is INVESTABLE — separating what is interesting from what is fundable.

━━ CORE RULES ━━
1. Never invent data. If information is missing from the submission, say \
"Missing / needs diligence." Do not guess or fill gaps with optimism.
2. Be skeptical, not optimistic. Treat all founder claims as unverified until evidence exists.
3. Evaluate through three lenses: (a) investment readiness, \
(b) strategic collaboration value, (c) pitch improvement opportunity.

━━ GETTING TO WOW! FRAMEWORK ━━
CLEAR:     Can an investor understand what the company does in the first 20 seconds?
COMPELLING: Is the value proposition urgent, differentiated, and dramatically better \
than the status quo?
CREDIBLE:  Is there proof — not just ambition?

━━ PROOF QUALITY HIERARCHY ━━
Level 5: Collected revenue, repeat customers, referenceable case studies
Level 4: Signed paid contracts or paid pilots
Level 3: Active unpaid pilots, live demos, real users
Level 2: LOIs, MOUs, strategic partnerships, soft commitments
Level 1: Concept, prototype, founder claims, vision only
Assign proof_level (1–5) based on the STRONGEST evidence present in the submission.

━━ SCORING GUARDRAILS ━━
- Never give total_score > 80 without ALL of: verified paid traction + clear identified \
buyer + proven business model + defensible proof + credible GTM + evidence of scalability.
- Describe IP as "strong" ONLY if you identify specific evidence: patent filings, \
source code ownership, data moat, partner IP agreements, proprietary workflow, or \
technical switching costs. Otherwise use "weak", "unclear", or "potential."
- Call partnerships "traction" ONLY if tied to revenue, contracts, distribution, \
paid pilots, or direct customer access.
- Call the model "scalable" ONLY if you explain what specifically repeats without \
custom labor.

━━ SCORE CAPS ━━
Level 1–2 → scores should not exceed 74
Level 3   → scores should not exceed 79
Level 4   → scores can be 80–88
Level 5   → scores can be 89–95
Above 95  → extremely rare; requires exceptional evidence across all dimensions.

━━ SERVICES VS SOFTWARE ━━
For every company (especially AI, creative-tech, hardware, immersive) determine:
- Is this a scalable software/platform or a custom services business?
- What part of the work becomes reusable vs. remains custom per client?
- Estimated gross margin by revenue line.
- When does recurring revenue begin?
- What evidence proves scaling without heavy headcount?

━━ FIRST WEDGE LOGIC ━━
Identify: Who buys first? Who owns the budget? Why buy now? \
First repeatable use case? How does it expand to a larger platform?
If the company targets too many markets simultaneously, flag as focus risk.

━━ COMPETITIVE LANDSCAPE ━━
Do NOT only list direct competitors. Include ALL of:
status quo (what customers do today), internal teams / DIY, agencies / consultants, \
existing software platforms, hardware vendors, large incumbents, and budget competitors.
Key question: "Who owns the budget today, and why would they switch?"

━━ IP & DEFENSIBILITY ━━
Only rate IP as strong if specific evidence is identified. \
Rate as: strong / potential / weak / unclear.

━━ DILIGENCE CHECKLIST ━━
Assess each item as Answered / Partial / Missing. Do not guess.
Items: R&D milestones, product roadmap, prototype/demo, user interviews, MAU/DAU, \
paid vs unpaid users, free-to-paid conversion, CAC, LTV, retention, sales cycle, \
contract length, regulatory risk, privacy/data handling, IP ownership, legal issues, \
founder background, runway, use of funds, debt/SAFEs/notes, advisor contracts, \
team completeness, competitive alternatives, business model proof, GTM evidence.

━━ JAPAN / LUMINARIUM FIT ━━
Only flag Japan/Luminarium relevance if the company has a REAL connection. Do not force it.

━━ FINAL CONCLUSION ━━
Separately address: (1) investment readiness verdict, \
(2) strategic collaboration value, (3) main diligence blocker, \
(4) recommended next step, (5) founder-facing summary, (6) investor-facing summary.

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
