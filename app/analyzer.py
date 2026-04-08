"""
Sends a startup submission to OpenAI GPT-4o and returns a structured analysis.

Scoring dimensions (matching the judge_report style):
  wow, problem, differentiation, traction, gtm_econ,
  product_tech, milestones, risk  (each 0–10)

Weighted total (0–100):
  Wow 15% | Problem 10% | Differentiation 15% | Traction 20%
  GTM+Econ 15% | Product+Tech 10% | Milestones 10% | Risk 5%
"""
import json
from openai import OpenAI
from app.config import config
from app.logger import submission_logger

_client = OpenAI(api_key=config.OPENAI_API_KEY)

WEIGHTS = {
    "wow": 0.15,
    "problem": 0.10,
    "differentiation": 0.15,
    "traction": 0.20,
    "gtm_econ": 0.15,
    "product_tech": 0.10,
    "milestones": 0.10,
    "risk": 0.05,
}

SYSTEM_PROMPT = """You are an expert venture capital analyst for Luminarium Capital.
You evaluate early-stage startups using the "Getting to Wow!" framework.
You respond ONLY with valid JSON — no markdown, no prose, no code fences."""

USER_PROMPT_TEMPLATE = """Analyze this startup submission for Luminarium Venture IQ.

--- SUBMISSION ---
Founder: {name}
LinkedIn: {linkedin}
Country: {country_residence} / representing {country_represent}
Category: {category}

Startup: {startup_pitch}
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
MVP: {mvp}
Inspiration: {inspiration}
--- END SUBMISSION ---

Return a JSON object with EXACTLY this structure (all fields required):
{{
  "startup_name": "extracted from startup_pitch field",
  "one_liner": "one sentence description of what they do",
  "category": "the category/sector",
  "scores": {{
    "wow": <0-10 float>,
    "problem": <0-10 float>,
    "differentiation": <0-10 float>,
    "traction": <0-10 float>,
    "gtm_econ": <0-10 float>,
    "product_tech": <0-10 float>,
    "milestones": <0-10 float>,
    "risk": <0-10 float>
  }},
  "traction_summary": "2-3 sentence summary of traction evidence",
  "ask_summary": "what they're asking for / current stage",
  "top_strength": "1-2 sentence top strength",
  "main_risk": "1-2 sentence main risk",
  "judge_questions": ["question 1 for judge to ask", "question 2 for judge to ask"],
  "why_scores_well": "1-2 sentence explanation",
  "investment_view": "2-3 paragraph detailed investment perspective",
  "green_lights": ["strength 1", "strength 2", "strength 3"],
  "yellow_lights": ["concern 1", "concern 2", "concern 3"],
  "red_flags": ["risk 1", "risk 2"],
  "wow_framing": "best version of the pitch in 2-3 sentences",
  "diligence_gaps": [
    {{"question": "...", "why_matters": "...", "needed_proof": "..."}}
  ],
  "pitch_improvements": ["improvement 1", "improvement 2", "improvement 3"],
  "recommended_milestones": ["milestone 1", "milestone 2", "milestone 3"],
  "bottom_line": "2-3 sentence bottom line verdict",
  "fundability_tier": "angel | pre-seed | seed | not-ready",
  "reframe": {{"not": "...", "better": "...", "best": "..."}}
}}"""


def analyze(submission: dict) -> dict:
    """
    Sends submission to GPT-4o and returns enriched analysis dict.
    Adds 'total_score' computed from weighted dimensions.
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
            {"role": "user", "content": prompt},
        ],
        temperature=0.3,
        response_format={"type": "json_object"},
    )

    raw = response.choices[0].message.content
    analysis = json.loads(raw)

    # Compute weighted total
    scores = analysis.get("scores", {})
    total = sum(scores.get(k, 0) * w * 10 for k, w in WEIGHTS.items())
    analysis["total_score"] = round(total, 1)

    # Classify score color
    analysis["score_tier"] = (
        "good" if total >= 70 else
        "mid"  if total >= 50 else
        "bad"
    )

    # Carry over submission metadata
    analysis["submission_id"] = submission.get("submission_id", "")
    analysis["submitter_name"] = submission.get("name", "")
    analysis["submitter_email"] = submission.get("email", "")
    analysis["submission_timestamp"] = submission.get("timestamp", "")
    analysis["deck_url"] = submission.get("deck_url", "")

    submission_logger.info(
        f"Scored {analysis.get('startup_name', startup_name)}: "
        f"{analysis['total_score']}/100 ({analysis['score_tier']})"
    )
    return analysis
