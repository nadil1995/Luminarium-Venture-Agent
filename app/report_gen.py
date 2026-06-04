"""
Generates two types of HTML reports:

  generate_batch_report(analyses, run_id)
      → leaderboard table + per-startup summary cards

  generate_individual_report(analysis)
      → deep-dive single startup (Getting to Wow! style)
"""
import os
from datetime import datetime, timezone
from jinja2 import Environment, BaseLoader
from app.config import config


# ── helpers ───────────────────────────────────────────────────────────────────

def _dot_class(score: float) -> str:
    """Map a 0-10 dimension score to a traffic-light class name."""
    if score >= 7.0:
        return "good"
    if score >= 5.0:
        return "mid"
    return "bad"


def _score_color(score: float) -> str:
    """Map a 0-100 total score to a hex colour for large score numbers."""
    if score >= 70:
        return "#0f8b5f"   # green — matches --green in CSS
    if score >= 50:
        return "#d99b18"   # yellow
    return "#b20d16"       # red


def _badge_class(score: float) -> str:
    """Return the badge CSS class (green / yellow / red) for a 0-10 score."""
    if score >= 7.0:
        return "green"
    if score >= 5.0:
        return "yellow"
    return "red"


def _render(template_str: str, **ctx) -> str:
    """
    Render a Jinja2 template string.
    autoescape=False is intentional — all template content is developer-controlled,
    not user input, and we inject raw HTML (CSS <style> blocks, links, etc.).
    """
    env = Environment(loader=BaseLoader(), autoescape=False)
    env.globals["dot_class"]   = _dot_class
    env.globals["score_color"] = _score_color
    env.globals["badge_class"] = _badge_class
    env.globals["now"]         = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    return env.from_string(template_str).render(**ctx)


def _save(html: str, filename: str) -> str:
    """Write HTML to the configured reports directory. Returns the file path."""
    os.makedirs(config.REPORTS_DIR, exist_ok=True)
    path = os.path.join(config.REPORTS_DIR, filename)
    with open(path, "w", encoding="utf-8") as f:
        f.write(html)
    return path


# ── shared CSS ────────────────────────────────────────────────────────────────
# Design mirrors the Luminarium Capital "Getting to Wow" reference report:
#   • Cream/paper (#f7f4ef) body background
#   • Dark hero banner with gold radial accent
#   • White section cards with subtle border + shadow
#   • Dark-header tables, coloured solid badges, left-border callouts

SHARED_CSS = """<style>
:root{
  --black:#0b0b0c; --ink:#171717; --muted:#6b7280;
  --paper:#f7f4ef; --white:#fff;
  --red:#b20d16; --gold:#caa45d; --green:#0f8b5f;
  --yellow:#d99b18; --orange:#d65f21; --blue:#284b63;
  --soft:#ede7dc; --border:#ded6c8;
}
/* ── reset / base ── */
*{box-sizing:border-box}
body{
  margin:0;
  font-family:Inter,Arial,Helvetica,sans-serif;
  background:var(--paper);
  color:var(--ink);
  line-height:1.55;
}
a{color:var(--blue);text-decoration:none}
a:hover{text-decoration:underline}
.wrap{max-width:1180px;margin:0 auto;padding:28px}

/* ── hero banner ── */
.hero{
  background:linear-gradient(135deg,#080808 0%,#1a1113 52%,#4b0a12 100%);
  color:white;
  border-radius:28px;
  padding:44px;
  box-shadow:0 18px 55px rgba(0,0,0,.18);
  position:relative;
  overflow:hidden;
}
/* decorative gold glow in top-right corner */
.hero:after{
  content:"";
  position:absolute;right:-120px;top:-100px;
  width:420px;height:420px;
  background:radial-gradient(circle,rgba(202,164,93,.32),transparent 66%);
  border-radius:50%;
}
.kicker{
  letter-spacing:.14em;text-transform:uppercase;
  color:#f0d69b;font-weight:700;font-size:12px;margin-bottom:12px;
}
.hero h1{font-size:38px;line-height:1.08;margin:0 0 12px;font-weight:850;max-width:900px}
.hero .subtitle{font-size:17px;color:#f4efe6;max-width:880px;margin:0 0 22px}
.meta{display:flex;gap:10px;flex-wrap:wrap;margin-top:22px}
.meta .pill{
  border:1px solid rgba(255,255,255,.25);
  background:rgba(255,255,255,.08);
  padding:7px 12px;border-radius:999px;font-size:13px;color:#f4efe6;
}

/* ── content sections ── */
section{
  background:var(--white);
  border:1px solid var(--border);
  border-radius:24px;
  padding:28px;
  margin:22px 0;
  box-shadow:0 10px 30px rgba(30,20,10,.06);
}
section h2{font-size:24px;margin:0 0 16px;color:#111}
section h3{font-size:16px;margin:16px 0 6px;color:#111}
.lead{font-size:16px;color:#333;line-height:1.6}
.small{font-size:13px;color:var(--muted)}

/* ── grid helpers ── */
.grid{display:grid;gap:16px}
.grid-2{grid-template-columns:repeat(2,minmax(0,1fr))}
.grid-3{grid-template-columns:repeat(3,minmax(0,1fr))}
.grid-4{grid-template-columns:repeat(4,minmax(0,1fr))}

/* ── inner cards (inside sections) ── */
.card{
  background:#fbfaf8;
  border:1px solid var(--border);
  border-radius:18px;
  padding:18px;
}
.card h3{margin-top:0}

/* ── score metric (large number) ── */
.metric{font-size:30px;font-weight:850;color:#111}
.label{font-size:12px;letter-spacing:.1em;text-transform:uppercase;color:var(--muted);font-weight:700}

/* ── score row (dimension list) ── */
.score-row{
  display:flex;align-items:center;justify-content:space-between;gap:18px;
  border-bottom:1px solid var(--border);padding:11px 0;
}
.score-row:last-child{border-bottom:0}

/* ── coloured badges ── */
.badge{
  padding:5px 10px;border-radius:999px;
  font-weight:800;font-size:12px;color:white;white-space:nowrap;
}
.badge.green{background:var(--green)}
.badge.yellow{background:var(--yellow)}
.badge.red{background:var(--red)}
.badge.orange{background:var(--orange)}
.badge.blue{background:var(--blue)}
.badge.gold{background:var(--gold);color:#111}

/* ── tables ── */
table{width:100%;border-collapse:collapse;border-radius:16px;overflow:hidden;background:#fff}
th,td{padding:12px 13px;border-bottom:1px solid var(--border);vertical-align:top;text-align:left}
th{
  background:#161616;color:white;
  font-size:12px;text-transform:uppercase;letter-spacing:.08em;
}
tr:last-child td{border-bottom:0}
tr:hover td{background:#faf7f2}

/* ── callout boxes ── */
.callout{
  border-left:5px solid var(--gold);
  background:#fff8e8;border-radius:14px;
  padding:16px 18px;margin:16px 0;
}
.callout.warning{border-left-color:var(--red);background:#fff1f1}
.callout.ok{border-left-color:var(--green);background:#eefaf5}
.callout .quote{font-size:16px;font-weight:800;color:#111;margin-bottom:6px}

/* ── traffic light panel ── */
.traffic-grid{display:grid;grid-template-columns:repeat(3,1fr);gap:14px;margin-top:12px}
.traffic-panel{border-radius:14px;padding:16px;border:1px solid var(--border);background:#faf7f2}
.traffic-panel.green{border-color:rgba(15,139,95,.3);background:#eefaf5}
.traffic-panel.yellow{border-color:rgba(217,155,24,.3);background:#fff8e8}
.traffic-panel.red{border-color:rgba(178,13,22,.3);background:#fff1f1}
.traffic-panel h3{margin-top:0;font-size:15px}
.traffic-panel ul{padding-left:18px;margin:6px 0}
.traffic-panel li{margin:5px 0;font-size:13px;color:#333}

/* ── coloured dot indicator ── */
.dot{display:inline-block;width:10px;height:10px;border-radius:50%;margin-right:6px}
.dot.good,.dot.green{background:var(--green)}
.dot.mid,.dot.yellow{background:var(--yellow)}
.dot.bad,.dot.red{background:var(--red)}

/* ── score progress bar ── */
.bar{height:10px;border-radius:999px;background:#ede7dc;overflow:hidden;margin-top:10px}
.bar-fill{height:100%;background:linear-gradient(90deg,var(--gold),#b20d16);border-radius:999px}

/* ── footer ── */
.footer{font-size:12px;color:#888;text-align:center;padding:22px 0 40px}

/* ── pill tag ── */
.tag{
  display:inline-block;
  background:var(--soft);border:1px solid var(--border);
  padding:5px 10px;border-radius:999px;font-size:12px;color:#555;
}

/* ── mono / code block ── */
.mono{
  font-family:ui-monospace,SFMono-Regular,Menlo,monospace;
  background:#f2eee7;border:1px solid #e3d9cc;
  border-radius:12px;padding:14px;white-space:pre-wrap;font-size:13px;
}

/* ── PDF download button ── */
.pdf-btn{
  position:fixed;bottom:28px;right:28px;z-index:999;
  background:linear-gradient(135deg,#080808,#4b0a12);
  color:white;border:none;border-radius:999px;
  padding:12px 22px;font-size:14px;font-weight:700;
  cursor:pointer;box-shadow:0 6px 24px rgba(0,0,0,.28);
  display:flex;align-items:center;gap:8px;
  transition:opacity .2s;
}
.pdf-btn:hover{opacity:.85}
.pdf-btn svg{width:16px;height:16px;fill:white}

/* ── hide button + hero decoration when printing ── */
@media print{
  .pdf-btn{display:none!important}
  .hero:after{display:none}
  body{background:white}
}

/* ── responsive ── */
@media(max-width:900px){
  .grid-2,.grid-3,.grid-4{grid-template-columns:1fr}
  .hero{padding:28px}
  .hero h1{font-size:28px}
  .traffic-grid{grid-template-columns:1fr}
}
</style>"""


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

  {# ── Hero ── #}
  <div class="hero">
    <div class="kicker">Luminarium Capital · Venture IQ · Judging Pack</div>
    <h1>Startup Batch Analysis</h1>
    <p class="subtitle">
      {{ analyses|length }} startup(s) scored using the
      <b>Getting to Wow!</b> investor-readiness framework.
      Weighted 0–100 across eight dimensions.
    </p>
    <div class="meta">
      <span class="pill">Run: {{ run_id }}</span>
      <span class="pill">Generated: {{ now }}</span>
      <span class="pill">{{ analyses|length }} startup(s) analyzed</span>
    </div>
  </div>

  {# ── Legend ── #}
  <section>
    <h2>Score Legend</h2>
    <div class="grid grid-3">
      <div class="card">
        <span class="badge green">GREEN ≥ 70</span>
        <p class="small" style="margin-top:8px">
          Strong investor-ready signals. Priority for deep-dive diligence.
        </p>
      </div>
      <div class="card">
        <span class="badge yellow">YELLOW 50–69</span>
        <p class="small" style="margin-top:8px">
          Promising but incomplete. Needs key gaps filled before advancing.
        </p>
      </div>
      <div class="card">
        <span class="badge red">RED &lt; 50</span>
        <p class="small" style="margin-top:8px">
          Significant gaps. Early stage or lacks traction evidence.
        </p>
      </div>
    </div>
  </section>

  {# ── Leaderboard ── #}
  <section>
    <h2>Leaderboard — Most Investable Today</h2>
    <p class="small">Sorted by weighted total score (highest = strongest evidence in deck today).</p>
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
          <b>{{ a.startup_name }}</b><br/>
          <span class="small">{{ a.one_liner }}</span>
          {% if a.deck_url %}
          <br/><a href="{{ a.deck_url }}" target="_blank" class="small">View deck ↗</a>
          {% endif %}
        </td>
        <td class="small">{{ a.traction_summary }}</td>
        <td class="small">{{ a.ask_summary }}</td>
        <td>
          <span style="font-size:28px;font-weight:850;color:{{ score_color(a.total_score) }}">
            {{ a.total_score }}
          </span>
          <span class="badge {{ badge_class(a.total_score / 10) }}" style="display:block;margin-top:4px;width:fit-content">
            /100
          </span>
        </td>
        <td>
          <div style="border-left:4px solid var(--green);padding-left:10px;margin-bottom:8px">
            <span class="small">{{ a.top_strength }}</span>
          </div>
          <div style="border-left:4px solid var(--red);padding-left:10px">
            <span class="small">{{ a.main_risk }}</span>
          </div>
        </td>
      </tr>
      {% endfor %}
      </tbody>
    </table>
  </section>

  {# ── Scoring matrix ── #}
  <section>
    <h2>Scoring Matrix — All Dimensions</h2>
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
        <td>
          <span class="dot {{ dot_class(s) }}"></span>
          <span class="small">{{ "%.1f"|format(s) }}</span>
        </td>
        {% endfor %}
        <td>
          <b style="color:{{ score_color(a.total_score) }}">{{ a.total_score }}</b>
        </td>
      </tr>
      {% endfor %}
      </tbody>
    </table>
    <p class="small" style="margin-top:12px">
      Weights: Wow 15% · Problem 10% · Differentiation 15% · Traction 20% ·
      GTM+Econ 15% · Product+Tech 10% · Milestones 10% · Risk 5%
    </p>
  </section>

  {# ── Per-startup summary cards ── #}
  {% for a in analyses %}
  <section id="{{ a.submission_id }}">
    <div style="display:flex;justify-content:space-between;align-items:flex-start;flex-wrap:wrap;gap:14px">
      <div>
        <h2 style="margin-bottom:4px">{{ a.startup_name }}</h2>
        <p class="small">{{ a.one_liner }}</p>
        <p class="small">Founder: {{ a.submitter_name }} · {{ a.submission_timestamp }}</p>
      </div>
      <div style="display:flex;align-items:center;gap:12px;flex-wrap:wrap">
        <div style="text-align:center">
          <div style="font-size:36px;font-weight:850;color:{{ score_color(a.total_score) }}">{{ a.total_score }}</div>
          <span class="badge {{ badge_class(a.total_score / 10) }}">/100</span>
        </div>
        <a href="/reports/{{ a.submission_id }}" target="_blank" class="badge blue">Deep-dive ↗</a>
        {% if a.deck_url %}
        <a href="{{ a.deck_url }}" target="_blank" class="badge gold">View Deck ↗</a>
        {% endif %}
      </div>
    </div>

    <div class="grid grid-2" style="margin-top:16px">
      <div>
        <h3>Traction</h3>
        <p class="small">{{ a.traction_summary }}</p>
        <h3>Ask / Stage</h3>
        <p class="small">{{ a.ask_summary }}</p>
        <h3>Main Risk</h3>
        <p class="small">{{ a.main_risk }}</p>
      </div>
      <div>
        <h3>Best Judge Questions</h3>
        <ol style="padding-left:18px;margin:0">
          {% for q in a.judge_questions %}
          <li class="small" style="margin:6px 0">{{ q }}</li>
          {% endfor %}
        </ol>
        <h3>Why It Scores Well</h3>
        <p class="small">{{ a.why_scores_well }}</p>
      </div>
    </div>

    {# Dimension score bars #}
    {% set dims = [
      ('wow','WOW',15),('problem','Problem',10),
      ('differentiation','Diff.',15),('traction','Traction',20),
      ('gtm_econ','GTM+Econ',15),('product_tech','Prod+Tech',10),
      ('milestones','Milestones',10),('risk','Risk',5)
    ] %}
    <div class="grid grid-4" style="margin-top:14px">
      {% for key, label, weight in dims %}
      {% set s = a.scores.get(key, 0) %}
      <div class="card">
        <div class="label">{{ label }} ({{ weight }}%)</div>
        <div class="metric" style="color:{{ score_color(s * 10) }}">{{ "%.1f"|format(s) }}</div>
        <div class="bar"><div class="bar-fill" style="width:{{ (s/10*100)|int }}%"></div></div>
      </div>
      {% endfor %}
    </div>
  </section>
  {% endfor %}

  <div class="footer">
    Luminarium Capital · Venture IQ · Judging Pack · {{ now }}<br/>
    Live judging script: ask (1) proof/traction, (2) who pays + why now, (3) moat + 12-month milestone.
  </div>

</div>

{# ── PDF download button ── #}
<button class="pdf-btn" onclick="downloadPDF()">
  <svg viewBox="0 0 24 24"><path d="M12 16l-5-5 1.4-1.4 2.6 2.6V4h2v8.2l2.6-2.6L17 11zm-7 4h14v2H5z"/></svg>
  Download PDF
</button>

<script src="https://cdnjs.cloudflare.com/ajax/libs/html2pdf.js/0.10.1/html2pdf.bundle.min.js"></script>
<script>
function downloadPDF() {
  var filename = "Luminarium_Batch_{{ run_id }}_Report.pdf";

  var btn = document.querySelector('.pdf-btn');
  btn.textContent = 'Generating…';
  btn.disabled = true;

  var opt = {
    margin:       [8, 8, 8, 8],
    filename:     filename,
    image:        { type: 'jpeg', quality: 0.97 },
    html2canvas:  { scale: 2, useCORS: true, logging: false },
    jsPDF:        { unit: 'mm', format: 'a4', orientation: 'landscape' },
    pagebreak:    { mode: ['avoid-all', 'css'] }
  };

  html2pdf().set(opt).from(document.body).save().then(function() {
    btn.innerHTML = '<svg viewBox="0 0 24 24" style="width:16px;height:16px;fill:white"><path d="M12 16l-5-5 1.4-1.4 2.6 2.6V4h2v8.2l2.6-2.6L17 11zm-7 4h14v2H5z"/></svg> Download PDF';
    btn.disabled = false;
  });
}
</script>

</body>
</html>"""


# ── INDIVIDUAL report template ────────────────────────────────────────────────

INDIVIDUAL_TEMPLATE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width,initial-scale=1"/>
<title>{{ a.startup_name }} — Luminarium Venture IQ</title>
{{ css }}
</head>
<body>
<div class="wrap">

  {# ── Hero ── #}
  <div class="hero">
    <div class="kicker">Luminarium Capital · Getting to Wow! Framework · Venture IQ Assessment</div>
    <h1>{{ a.startup_name }}</h1>
    <p class="subtitle">{{ a.one_liner }}</p>
    <div class="meta">
      <span class="pill">Category: {{ a.category }}</span>
      <span class="pill">Founder: {{ a.submitter_name }}</span>
      <span class="pill">Submitted: {{ a.submission_timestamp }}</span>
      {% if a.deck_url %}
      <a class="pill" href="{{ a.deck_url }}" target="_blank">View Deck ↗</a>
      {% endif %}
      <span class="pill">Generated: {{ now }}</span>
    </div>
  </div>

  {# ── Executive Snapshot ── #}
  <section>
    <h2>Executive Investment Snapshot</h2>
    <p class="lead">{{ a.investment_view }}</p>

    {% if a.wow_framing %}
    <div class="callout">
      <div class="quote">Recommended investor positioning:</div>
      <p><b>"{{ a.wow_framing }}"</b></p>
    </div>
    {% endif %}

    <div class="grid grid-4">
      <div class="card">
        <div class="label">Overall Score</div>
        <div class="metric" style="color:{{ score_color(a.total_score) }}">{{ a.total_score }}/100</div>
        <div class="bar" style="margin-top:8px">
          <div class="bar-fill" style="width:{{ a.total_score }}%"></div>
        </div>
      </div>
      <div class="card">
        <div class="label">Fundability</div>
        <div class="metric" style="font-size:22px">{{ a.fundability_tier }}</div>
        <p class="small" style="margin-top:6px">{{ a.score_tier }} signals</p>
      </div>
      <div class="card">
        <div class="label">Category</div>
        <div class="metric" style="font-size:20px">{{ a.category }}</div>
        <p class="small" style="margin-top:6px">{{ a.submission_timestamp }}</p>
      </div>
      <div class="card">
        <div class="label">Top Strength</div>
        <p class="small" style="margin-top:6px">{{ a.top_strength }}</p>
      </div>
    </div>
  </section>

  {# ── Traffic Light Risk Assessment ── #}
  <section>
    <h2>Traffic Light Risk Assessment</h2>
    <div class="traffic-grid">
      <div class="traffic-panel green">
        <h3><span class="dot green"></span> Green Lights</h3>
        <ul>{% for g in a.green_lights %}<li>{{ g }}</li>{% endfor %}</ul>
      </div>
      <div class="traffic-panel yellow">
        <h3><span class="dot yellow"></span> Yellow Cautions</h3>
        <ul>{% for y in a.yellow_lights %}<li>{{ y }}</li>{% endfor %}</ul>
      </div>
      <div class="traffic-panel red">
        <h3><span class="dot red"></span> Red Flags</h3>
        <ul>{% for r in a.red_flags %}<li>{{ r }}</li>{% endfor %}</ul>
      </div>
    </div>
  </section>

  {# ── Getting to Wow! Analysis ── #}
  <section>
    <h2>Getting to Wow! Analysis</h2>
    <p class="lead">
      Using the investor-readiness lens, the company must be
      <b>clear, compelling, and credible</b> in the first 20 seconds.
    </p>
    <div class="grid grid-3">
      <div class="card">
        <h3>Clear</h3>
        {% set wow = a.scores.get('wow', 0) %}
        <span class="badge {{ badge_class(wow) }}">{{ "%.1f"|format(wow) }} / 10</span>
        <p class="small" style="margin-top:10px">{{ a.wow_framing }}</p>
      </div>
      <div class="card">
        <h3>Compelling</h3>
        {% set diff = a.scores.get('differentiation', 0) %}
        <span class="badge {{ badge_class(diff) }}">{{ "%.1f"|format(diff) }} / 10</span>
        <p class="small" style="margin-top:10px">{{ a.top_strength }}</p>
      </div>
      <div class="card">
        <h3>Credible</h3>
        {% set tr = a.scores.get('traction', 0) %}
        <span class="badge {{ badge_class(tr) }}">{{ "%.1f"|format(tr) }} / 10</span>
        <p class="small" style="margin-top:10px">{{ a.traction_summary }}</p>
      </div>
    </div>

    {% if a.reframe %}
    <h3>How to Frame the Company</h3>
    <div class="callout warning">
      <b>Not:</b> "{{ a.reframe.not }}"
    </div>
    <div class="callout">
      <b>Better:</b> "{{ a.reframe.better }}"
    </div>
    <div class="callout ok">
      <b>Best:</b> "{{ a.reframe.best }}"
    </div>
    {% endif %}
  </section>

  {# ── Detailed Scorecard ── #}
  <section>
    <h2>Detailed Scorecard</h2>
    {% set dim_labels = [
      ('wow',           'WOW Factor',         '15%'),
      ('problem',       'Problem Importance',  '10%'),
      ('differentiation','Differentiation',    '15%'),
      ('traction',      'Traction Quality',    '20%'),
      ('gtm_econ',      'GTM + Economics',     '15%'),
      ('product_tech',  'Product + Tech',      '10%'),
      ('milestones',    'Milestones',          '10%'),
      ('risk',          'Risk Profile',        '5%'),
    ] %}
    <div class="grid grid-4">
      {% for key, label, weight in dim_labels %}
      {% set s = a.scores.get(key, 0) %}
      <div class="card">
        <div class="label">{{ label }}</div>
        <div class="label" style="font-size:10px">Weight {{ weight }}</div>
        <div class="metric" style="font-size:32px;color:{{ score_color(s * 10) }};margin-top:6px">
          {{ "%.1f"|format(s) }}
        </div>
        <div class="bar"><div class="bar-fill" style="width:{{ (s/10*100)|int }}%"></div></div>
        <span class="badge {{ badge_class(s) }}" style="margin-top:8px;display:inline-block">/10</span>
      </div>
      {% endfor %}
    </div>
    <div style="margin-top:20px;text-align:right">
      <span style="font-size:32px;font-weight:850;color:{{ score_color(a.total_score) }}">
        {{ a.total_score }} / 100
      </span>
      <span class="badge {{ badge_class(a.total_score / 10) }}" style="margin-left:8px;font-size:14px">
        {{ a.fundability_tier }}
      </span>
    </div>
  </section>

  {# ── Key Diligence Gaps ── #}
  <section>
    <h2>Key Diligence Gaps</h2>
    <table>
      <thead><tr>
        <th style="width:30%">Question</th>
        <th style="width:35%">Why It Matters</th>
        <th style="width:35%">Needed Proof</th>
      </tr></thead>
      <tbody>
      {% for gap in a.diligence_gaps %}
      <tr>
        <td><b>{{ gap.question }}</b></td>
        <td class="small">{{ gap.why_matters }}</td>
        <td class="small">{{ gap.needed_proof }}</td>
      </tr>
      {% endfor %}
      </tbody>
    </table>
  </section>

  {# ── Pitch Improvements & Milestones ── #}
  <section>
    <div class="grid grid-2">
      <div>
        <h2>Pitch Improvements</h2>
        <ol style="padding-left:18px">
          {% for p in a.pitch_improvements %}
          <li style="margin:10px 0;font-size:14px;color:#333">{{ p }}</li>
          {% endfor %}
        </ol>
      </div>
      <div>
        <h2>Recommended Next Milestones</h2>
        <ol style="padding-left:18px">
          {% for m in a.recommended_milestones %}
          <li style="margin:10px 0;font-size:14px;color:#333">{{ m }}</li>
          {% endfor %}
        </ol>
      </div>
    </div>
  </section>

  {# ── Ask & Stage ── #}
  <section>
    <h2>Funding Ask & Stage</h2>
    <p class="lead">{{ a.ask_summary }}</p>
  </section>

  {# ── Bottom Line ── #}
  <section>
    <h2>Final Luminarium Capital View</h2>
    <p class="lead">{{ a.bottom_line }}</p>
    <div class="callout ok" style="margin-top:16px">
      <div class="quote">Decision</div>
      <p><b>{{ a.fundability_tier }}</b> — Score {{ a.total_score }}/100</p>
    </div>
    <p class="small" style="margin-top:16px">
      Submission ID: {{ a.submission_id }} · Analyzed by Luminarium Venture IQ · {{ now }}
    </p>
  </section>

  <div class="footer">
    Prepared by Luminarium Capital · Venture IQ / Getting to Wow! style assessment ·
    For discussion purposes only, not financial or legal advice.
  </div>

</div>

{# ── PDF download button ── #}
<button class="pdf-btn" onclick="downloadPDF()">
  <svg viewBox="0 0 24 24"><path d="M12 16l-5-5 1.4-1.4 2.6 2.6V4h2v8.2l2.6-2.6L17 11zm-7 4h14v2H5z"/></svg>
  Download PDF
</button>

<script src="https://cdnjs.cloudflare.com/ajax/libs/html2pdf.js/0.10.1/html2pdf.bundle.min.js"></script>
<script>
function downloadPDF() {
  // Build filename: StartupName_SubmitterName_Report.pdf
  // sanitize() strips any character that isn't a letter, digit, or hyphen
  function sanitize(s) {
    return (s || 'Unknown').replace(/[^a-zA-Z0-9\-]/g, '_').replace(/_+/g, '_').replace(/^_|_$/g, '');
  }
  var startup   = sanitize("{{ a.startup_name }}");
  var submitter = sanitize("{{ a.submitter_name }}");
  var filename  = startup + "_" + submitter + "_Report.pdf";

  var btn = document.querySelector('.pdf-btn');
  btn.textContent = 'Generating…';
  btn.disabled = true;

  var opt = {
    margin:       [8, 8, 8, 8],        // mm: top, left, bottom, right
    filename:     filename,
    image:        { type: 'jpeg', quality: 0.97 },
    html2canvas:  { scale: 2, useCORS: true, logging: false },
    jsPDF:        { unit: 'mm', format: 'a4', orientation: 'portrait' },
    pagebreak:    { mode: ['avoid-all', 'css'] }
  };

  html2pdf().set(opt).from(document.body).save().then(function() {
    btn.innerHTML = '<svg viewBox="0 0 24 24" style="width:16px;height:16px;fill:white"><path d="M12 16l-5-5 1.4-1.4 2.6 2.6V4h2v8.2l2.6-2.6L17 11zm-7 4h14v2H5z"/></svg> Download PDF';
    btn.disabled = false;
  });
}
</script>

</body>
</html>"""


# ── public API ────────────────────────────────────────────────────────────────

def generate_batch_report(analyses: list[dict], run_id: str) -> str:
    """Render leaderboard + per-startup cards for all analyses. Returns file path."""
    sorted_analyses = sorted(analyses, key=lambda a: a.get("total_score", 0), reverse=True)
    html = _render(BATCH_TEMPLATE, css=SHARED_CSS, analyses=sorted_analyses, run_id=run_id)
    return _save(html, f"batch_{run_id}.html")


def generate_individual_report(analysis: dict) -> str:
    """Render deep-dive Getting to Wow! report for one startup. Returns file path."""
    html = _render(INDIVIDUAL_TEMPLATE, css=SHARED_CSS, a=analysis)
    sid = analysis.get("submission_id", "unknown")
    return _save(html, f"individual_{sid}.html")
