"""
Generates two types of HTML reports:

  generate_batch_report(analyses, run_id, run_meta)
      → judge_report style: leaderboard table + per-startup summary cards

  generate_individual_report(analysis)
      → phont_venture style: deep-dive single startup
"""
import os
from datetime import datetime
from jinja2 import Environment, BaseLoader
from app.config import config

# ── helpers ───────────────────────────────────────────────────────────────────

def _dot_class(score: float) -> str:
    if score >= 7.0:
        return "good"
    if score >= 5.0:
        return "mid"
    return "bad"


def _score_color(score: float) -> str:
    if score >= 70:
        return "#2ecc71"
    if score >= 50:
        return "#f1c40f"
    return "#e74c3c"


def _render(template_str: str, **ctx) -> str:
    env = Environment(loader=BaseLoader(), autoescape=False)
    env.globals["dot_class"] = _dot_class
    env.globals["score_color"] = _score_color
    env.globals["now"] = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
    tmpl = env.from_string(template_str)
    return tmpl.render(**ctx)


def _save(html: str, filename: str) -> str:
    os.makedirs(config.REPORTS_DIR, exist_ok=True)
    path = os.path.join(config.REPORTS_DIR, filename)
    with open(path, "w", encoding="utf-8") as f:
        f.write(html)
    return path


# ── shared CSS ────────────────────────────────────────────────────────────────

SHARED_CSS = """
<style>
:root{
  --bg:#0b0f19; --card:#111a2e; --muted:#9fb0d0; --text:#eaf0ff;
  --good:#2ecc71; --mid:#f1c40f; --bad:#e74c3c; --info:#64b5ff;
  --accent:#b69cff; --accent2:#8f6bff; --pill:#172447; --line:#1e2d4a;
}
*{box-sizing:border-box}
body{margin:0;background:linear-gradient(180deg,var(--bg),#070a12);
  font-family:ui-sans-serif,system-ui,-apple-system,Segoe UI,Roboto,Inter,Helvetica,Arial;
  color:var(--text)}
a{color:var(--accent);text-decoration:none}
a:hover{text-decoration:underline}
.wrap{max-width:1200px;margin:0 auto;padding:24px 20px 60px}
h1{margin:0;font-size:22px;letter-spacing:.2px}
h2{font-size:20px;margin:0 0 12px}
h3{font-size:16px;margin:0 0 8px}
.sub{color:var(--muted);font-size:13px;margin-top:6px;line-height:1.45}
.card{background:linear-gradient(180deg,rgba(255,255,255,.04),rgba(255,255,255,.02));
  border:1px solid rgba(255,255,255,.08);border-radius:16px;padding:18px;margin-top:14px}
.row{display:flex;flex-wrap:wrap;gap:10px;align-items:center;justify-content:space-between}
.small{color:var(--muted);font-size:12px;line-height:1.35}
.why{font-size:13px;line-height:1.45;color:#dbe6ff}
.hr{height:1px;background:rgba(255,255,255,.10);margin:14px 0}
.pill{background:var(--pill);border:1px solid rgba(255,255,255,.10);
  padding:6px 10px;border-radius:999px;font-size:12px;color:var(--muted);
  display:inline-flex;align-items:center;gap:6px}
.scoreBig{font-size:26px;font-weight:800}
.dot{width:10px;height:10px;border-radius:999px;display:inline-block}
.dot.good{background:var(--good)} .dot.mid{background:var(--mid)} .dot.bad{background:var(--bad)} .dot.info{background:var(--info)}
table{width:100%;border-collapse:separate;border-spacing:0;overflow:hidden}
th,td{padding:10px;border-bottom:1px solid rgba(255,255,255,.08);vertical-align:top}
th{font-size:12px;color:var(--muted);text-transform:uppercase;letter-spacing:.08em;
  text-align:left;background:rgba(255,255,255,.03)}
tr:hover td{background:rgba(255,255,255,.02)}
.twoCol{display:grid;grid-template-columns:1fr;gap:12px}
@media(min-width:960px){.twoCol{grid-template-columns:1.1fr .9fr}}
.kpi{display:flex;flex-wrap:wrap;gap:8px;justify-content:flex-end}
.topPick{border-left:4px solid var(--good);padding-left:10px}
.warn{border-left:4px solid var(--mid);padding-left:10px}
.footer{margin-top:18px;color:var(--muted);font-size:12px}
.badge{display:inline-block;padding:4px 9px;border-radius:999px;font-size:12px;font-weight:700}
.b-good{background:rgba(46,204,113,.12);color:#86efc0}
.b-mid{background:rgba(241,196,15,.12);color:#ffd77f}
.b-bad{background:rgba(231,76,60,.12);color:#ff9a9a}
.traffic{display:grid;grid-template-columns:repeat(3,1fr);gap:12px;margin-top:10px}
.light{border-radius:14px;padding:14px;border:1px solid var(--line);background:rgba(255,255,255,.025)}
.light.green{box-shadow:inset 0 0 0 1px rgba(46,204,113,.2)}
.light.yellow{box-shadow:inset 0 0 0 1px rgba(241,196,15,.2)}
.light.red{box-shadow:inset 0 0 0 1px rgba(231,76,60,.2)}
ul{margin:10px 0 0 18px;padding:0} li{margin:7px 0;color:var(--text);font-size:13px}
.score-num{font-size:44px;font-weight:800;line-height:1;margin:8px 0 4px}
.kicker{color:var(--muted);font-size:12px;text-transform:uppercase;letter-spacing:.1em}
.bar{height:10px;border-radius:999px;background:#1a2540;overflow:hidden;margin-top:10px}
.fill{height:100%;background:linear-gradient(90deg,var(--accent),var(--accent2))}
@media(max-width:760px){.traffic{grid-template-columns:1fr}}
</style>
"""

# ── BATCH report template ─────────────────────────────────────────────────────

BATCH_TEMPLATE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width,initial-scale=1"/>
<title>Luminarium Venture IQ — Judging Pack {{ run_id }}</title>
{{ css }}
</head>
<body>
<div class="wrap">
  <div class="row">
    <div>
      <h1>Luminarium Venture IQ — Judging Pack</h1>
      <div class="sub">
        Run <b>{{ run_id }}</b> · {{ now }} · {{ analyses|length }} startup(s) analyzed ·
        Using <b>Investor Questions</b> + <b>Getting to Wow!</b> framework.
      </div>
    </div>
    <div class="pill"><span class="dot info"></span>Score = weighted 0–100</div>
  </div>

  {# ── Leaderboard ── #}
  <div class="card">
    <div class="row">
      <div class="small"><b>Leaderboard — most investable today</b><br/>Higher score = stronger evidence in deck today.</div>
      <div class="pill"><span class="dot good"></span>Green ≥ 70</div>
      <div class="pill"><span class="dot mid"></span>Yellow 50–69</div>
      <div class="pill"><span class="dot bad"></span>Red &lt; 50</div>
    </div>
    <div class="hr"></div>
    <table>
      <thead><tr>
        <th style="width:22%">Company</th>
        <th style="width:26%">Traction</th>
        <th style="width:20%">Ask / Stage</th>
        <th style="width:8%">Score</th>
        <th style="width:24%">Snapshot</th>
      </tr></thead>
      <tbody>
      {% for a in analyses %}
      <tr>
        <td>
          <b>{{ a.startup_name }}</b>
          <div class="small">{{ a.one_liner }}</div>
          {% if a.deck_url %}<div class="small"><a href="{{ a.deck_url }}" target="_blank">View deck ↗</a></div>{% endif %}
        </td>
        <td class="small">{{ a.traction_summary }}</td>
        <td class="small">{{ a.ask_summary }}</td>
        <td><span class="scoreBig" style="color:{{ score_color(a.total_score) }}">{{ a.total_score }}</span></td>
        <td class="why">
          <div class="topPick">{{ a.top_strength }}</div>
          <div class="warn" style="margin-top:8px">{{ a.main_risk }}</div>
        </td>
      </tr>
      {% endfor %}
      </tbody>
    </table>
  </div>

  {# ── Scoring matrix ── #}
  <div class="card">
    <div class="small"><b>Scoring matrix (0–10 each dimension)</b></div>
    <div class="hr"></div>
    <table>
      <thead><tr>
        <th>Company</th>
        <th>Wow</th><th>Problem</th><th>Diff.</th><th>Traction</th>
        <th>GTM+Econ</th><th>Prod+Tech</th><th>Milestones</th><th>Risk</th>
        <th>Total</th>
      </tr></thead>
      <tbody>
      {% for a in analyses %}
      <tr>
        <td><b>{{ a.startup_name }}</b></td>
        {% for key in ['wow','problem','differentiation','traction','gtm_econ','product_tech','milestones','risk'] %}
        {% set s = a.scores.get(key, 0) %}
        <td class="small"><span class="dot {{ dot_class(s) }}"></span> {{ "%.1f"|format(s) }}</td>
        {% endfor %}
        <td class="small"><b>{{ a.total_score }}</b></td>
      </tr>
      {% endfor %}
      </tbody>
    </table>
    <div class="small" style="margin-top:10px">
      Weights: Wow 15% · Problem 10% · Differentiation 15% · Traction 20% · GTM+Econ 15% · Product+Tech 10% · Milestones 10% · Risk 5%
    </div>
  </div>

  <div class="footer">
    <b>Live judging script:</b> ask (1) proof/traction, (2) who pays + why now, (3) moat + 12-month milestone.
    If tied: CAC–payback–LTV in 30 seconds.
  </div>

  {# ── Per-startup cards ── #}
  {% for a in analyses %}
  <div class="card" id="{{ a.submission_id }}">
    <div class="row">
      <div>
        <div style="display:flex;align-items:center;gap:8px">
          <span class="dot info"></span>
          <b style="font-size:17px">{{ a.startup_name }}</b>
          <span class="pill">{{ a.category }}</span>
        </div>
        <div class="small" style="margin-top:4px">{{ a.one_liner }}</div>
        <div class="small">Founder: {{ a.submitter_name }} · {{ a.submission_timestamp }}</div>
      </div>
      <div class="kpi">
        {% set sc = a.scores %}
        <span class="pill"><span class="dot {{ dot_class(sc.get('wow',0)) }}"></span>Wow: <b>{{ "%.1f"|format(sc.get('wow',0)) }}</b></span>
        <span class="pill"><span class="dot {{ dot_class(sc.get('traction',0)) }}"></span>Traction: <b>{{ "%.1f"|format(sc.get('traction',0)) }}</b></span>
        <span class="pill"><span class="dot {{ dot_class(sc.get('gtm_econ',0)) }}"></span>GTM+Econ: <b>{{ "%.1f"|format(sc.get('gtm_econ',0)) }}</b></span>
        <span class="pill"><span class="dot {{ dot_class(sc.get('risk',0)) }}"></span>Risk: <b>{{ "%.1f"|format(sc.get('risk',0)) }}</b></span>
        <div class="pill">Total: <b style="color:{{ score_color(a.total_score) }}">{{ a.total_score }}/100</b></div>
        <a class="pill" href="/reports/{{ a.submission_id }}" target="_blank">Deep-dive ↗</a>
      </div>
    </div>
    <div class="hr"></div>
    <div class="twoCol">
      <div>
        <div class="small"><b>Traction</b></div>
        <div class="why">{{ a.traction_summary }}</div>
        <div class="small" style="margin-top:10px"><b>Ask / Stage</b></div>
        <div class="why">{{ a.ask_summary }}</div>
        <div class="small" style="margin-top:10px"><b>Main risk</b></div>
        <div class="why">{{ a.main_risk }}</div>
      </div>
      <div>
        <div class="small"><b>2 best judge questions</b></div>
        <div class="why">
          {% for q in a.judge_questions %}1) {{ q }}{% if not loop.last %} 2) {% endif %}{% endfor %}
        </div>
        <div class="small" style="margin-top:10px"><b>Why it scores well</b></div>
        <div class="why">{{ a.why_scores_well }}</div>
      </div>
    </div>
  </div>
  {% endfor %}

</div>
</body>
</html>"""

# ── INDIVIDUAL report template ─────────────────────────────────────────────────

INDIVIDUAL_TEMPLATE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width,initial-scale=1"/>
<title>{{ a.startup_name }} — Luminarium Venture IQ</title>
{{ css }}
<style>
.hero{background:radial-gradient(circle at top left,rgba(182,156,255,.18),transparent 40%),
  linear-gradient(135deg,#151520,#0f0f16);border:1px solid var(--line);
  border-radius:20px;padding:28px}
.eyebrow{letter-spacing:.12em;text-transform:uppercase;color:var(--accent);font-size:12px;font-weight:700}
.grid12{display:grid;grid-template-columns:repeat(12,1fr);gap:16px;margin-top:16px}
.s4{grid-column:span 4} .s6{grid-column:span 6} .s8{grid-column:span 8} .s12{grid-column:span 12}
@media(max-width:900px){.s4,.s6,.s8,.s12{grid-column:span 12}}
</style>
</head>
<body>
<div class="wrap">

  {# Hero #}
  <div class="hero">
    <div class="eyebrow">Luminarium Capital — Venture Analysis</div>
    <h1 style="font-size:36px;margin:8px 0 10px">{{ a.startup_name }}</h1>
    <div class="sub" style="font-size:15px">{{ a.one_liner }}</div>
    <div style="display:flex;flex-wrap:wrap;gap:8px;margin-top:16px">
      <div class="pill">Category: {{ a.category }}</div>
      <div class="pill">Founder: {{ a.submitter_name }}</div>
      <div class="pill">Submitted: {{ a.submission_timestamp }}</div>
      {% if a.deck_url %}<a class="pill" href="{{ a.deck_url }}" target="_blank">View Deck ↗</a>{% endif %}
      <div class="pill">Generated: {{ now }}</div>
    </div>
  </div>

  <div class="grid12">

    {# Overall score #}
    <section class="card s4">
      <div class="kicker">Overall score</div>
      <div class="score-num" style="color:{{ score_color(a.total_score) }}">{{ a.total_score }} / 100</div>
      <p style="font-size:13px;color:#dbe6ff;margin:8px 0 0">
        <b>Fundability:</b> {{ a.fundability_tier }}
      </p>
      <div class="bar"><div class="fill" style="width:{{ a.total_score }}%"></div></div>
    </section>

    {# Investment view #}
    <section class="card s8">
      <h2>Investment view</h2>
      <div class="why" style="font-size:14px">{{ a.investment_view }}</div>
    </section>

    {# Traffic lights #}
    <section class="card s12">
      <h2>Traffic-light summary</h2>
      <div class="traffic">
        <div class="light green">
          <h3><span class="dot good"></span> Green lights</h3>
          <ul>{% for g in a.green_lights %}<li>{{ g }}</li>{% endfor %}</ul>
        </div>
        <div class="light yellow">
          <h3><span class="dot mid"></span> Yellow lights</h3>
          <ul>{% for y in a.yellow_lights %}<li>{{ y }}</li>{% endfor %}</ul>
        </div>
        <div class="light red">
          <h3><span class="dot bad"></span> Red flags</h3>
          <ul>{% for r in a.red_flags %}<li>{{ r }}</li>{% endfor %}</ul>
        </div>
      </div>
    </section>

    {# What is the wow #}
    <section class="card s6">
      <h2>What is the WOW?</h2>
      <p style="font-size:13px;color:#dbe6ff">{{ a.wow_framing }}</p>
    </section>

    {# Reframe #}
    <section class="card s6">
      <h2>How to frame the company</h2>
      <p class="small"><b>Not:</b> "{{ a.reframe.not }}"</p>
      <p class="small"><b>Better:</b> "{{ a.reframe.better }}"</p>
      <p class="small"><b>Best:</b> "{{ a.reframe.best }}"</p>
    </section>

    {# Scorecard #}
    <section class="card s12">
      <h2>Detailed scorecard</h2>
      <table>
        <thead><tr><th>Dimension</th><th>Score</th><th>Weight</th></tr></thead>
        <tbody>
        {% set dim_labels = {
          'wow': ('WOW Factor', '15%'),
          'problem': ('Problem Importance', '10%'),
          'differentiation': ('Differentiation', '15%'),
          'traction': ('Traction Quality', '20%'),
          'gtm_econ': ('GTM + Economics', '15%'),
          'product_tech': ('Product + Tech', '10%'),
          'milestones': ('Milestones', '10%'),
          'risk': ('Risk Profile', '5%')
        } %}
        {% for key, (label, weight) in dim_labels.items() %}
        {% set s = a.scores.get(key, 0) %}
        <tr>
          <td>{{ label }}</td>
          <td>
            <span class="badge b-{{ dot_class(s) }}">{{ "%.1f"|format(s) }} / 10</span>
          </td>
          <td class="small">{{ weight }}</td>
        </tr>
        {% endfor %}
        <tr>
          <td><b>Weighted Total</b></td>
          <td><span class="badge b-{{ dot_class(a.total_score / 10) }}"><b>{{ a.total_score }} / 100</b></span></td>
          <td></td>
        </tr>
        </tbody>
      </table>
    </section>

    {# Diligence gaps #}
    <section class="card s12">
      <h2>Key diligence gaps</h2>
      <table>
        <thead><tr><th>Question</th><th>Why it matters</th><th>Needed proof</th></tr></thead>
        <tbody>
        {% for gap in a.diligence_gaps %}
        <tr>
          <td class="why">{{ gap.question }}</td>
          <td class="small">{{ gap.why_matters }}</td>
          <td class="small">{{ gap.needed_proof }}</td>
        </tr>
        {% endfor %}
        </tbody>
      </table>
    </section>

    {# Pitch improvements #}
    <section class="card s6">
      <h2>Pitch improvements</h2>
      <ul>{% for p in a.pitch_improvements %}<li>{{ p }}</li>{% endfor %}</ul>
    </section>

    {# Recommended milestones #}
    <section class="card s6">
      <h2>Recommended next milestones</h2>
      <ul>{% for m in a.recommended_milestones %}<li>{{ m }}</li>{% endfor %}</ul>
    </section>

    {# Bottom line #}
    <section class="card s12">
      <h2>Bottom line</h2>
      <div class="why" style="font-size:14px">{{ a.bottom_line }}</div>
      <div class="footer" style="margin-top:12px">
        Submission ID: {{ a.submission_id }} · Analyzed by Luminarium Venture IQ · {{ now }}
      </div>
    </section>

  </div>
</div>
</body>
</html>"""


# ── public API ────────────────────────────────────────────────────────────────

def generate_batch_report(analyses: list[dict], run_id: str) -> str:
    """Renders leaderboard + cards for all analyses. Returns file path."""
    sorted_analyses = sorted(analyses, key=lambda a: a.get("total_score", 0), reverse=True)
    html = _render(BATCH_TEMPLATE, css=SHARED_CSS, analyses=sorted_analyses, run_id=run_id)
    filename = f"batch_{run_id}.html"
    return _save(html, filename)


def generate_individual_report(analysis: dict) -> str:
    """Renders deep-dive report for one startup. Returns file path."""
    html = _render(INDIVIDUAL_TEMPLATE, css=SHARED_CSS, a=analysis)
    sid = analysis.get("submission_id", "unknown")
    filename = f"individual_{sid}.html"
    return _save(html, filename)
