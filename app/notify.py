"""
SendGrid email notifications for Luminarium Venture IQ.

Sends one email per new report generated, giving the reviewer
a summary and a direct link to the full HTML report.

Disabled gracefully if SENDGRID_API_KEY / NOTIFY_EMAIL_TO / NOTIFY_EMAIL_FROM
are not set — pipeline continues without notification.
"""
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail
from app.config import config
from app.logger import process_logger


def _score_color(score: float) -> str:
    if score >= 70:
        return "#0f8b5f"
    if score >= 50:
        return "#d99b18"
    return "#b20d16"


def _confidence_color(rating: str) -> str:
    return {
        "High":        "#0f8b5f",
        "Medium":      "#284b63",
        "Medium-Low":  "#d99b18",
        "Low":         "#b20d16",
    }.get(rating, "#d99b18")


def send_report_notification(analysis: dict, report_url: str = "") -> bool:
    """
    Send a review-notification email via SendGrid.
    Returns True on success, False on failure (non-fatal).
    """
    if not config.NOTIFY_ENABLED:
        process_logger.debug("Notifications disabled — SENDGRID_API_KEY not configured.")
        return False

    startup      = analysis.get("startup_name", "Unknown")
    founder      = analysis.get("submitter_name", "Unknown")
    score        = analysis.get("total_score", 0)
    proof_level  = analysis.get("proof_level", 1)
    proof_rat    = analysis.get("proof_level_rationale", "")
    fundability  = analysis.get("fundability_tier", "not-ready")
    strength     = analysis.get("top_strength", "—")
    risk         = analysis.get("main_risk", "—")
    sid          = analysis.get("submission_id", "")
    deck_url     = analysis.get("deck_url", "")
    capped       = analysis.get("score_capped", False)

    rc           = analysis.get("report_confidence", {})
    confidence   = rc.get("rating", "Medium-Low") if isinstance(rc, dict) else "Medium-Low"
    conf_reason  = rc.get("reason", "") if isinstance(rc, dict) else ""

    wn           = analysis.get("why_now", {})
    why_now_txt  = wn.get("summary", "—") if isinstance(wn, dict) else "—"

    sc = _score_color(score)
    cc = _confidence_color(confidence)

    report_link = report_url or f"http://{config.WEB_PORT}/"

    subject = (
        f"[Venture IQ] New Report: {startup} — "
        f"{score}/100 · L{proof_level} · {confidence} Confidence"
    )

    html = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8"/>
<style>
  body{{margin:0;padding:0;background:#f7f4ef;font-family:Inter,Arial,sans-serif}}
  .wrap{{max-width:600px;margin:0 auto;background:#fff;border-radius:16px;overflow:hidden;
         box-shadow:0 4px 24px rgba(0,0,0,.08)}}
  .hero{{background:linear-gradient(135deg,#080808 0%,#1a1113 52%,#4b0a12 100%);
         padding:32px;color:white}}
  .kicker{{letter-spacing:.12em;text-transform:uppercase;color:#f0d69b;
           font-weight:700;font-size:11px;margin-bottom:8px}}
  .hero h1{{font-size:22px;margin:0 0 6px;font-weight:800}}
  .hero .sub{{font-size:13px;color:#f4efe6}}
  .body{{padding:28px}}
  .row{{display:flex;gap:12px;margin-bottom:16px}}
  .metric{{flex:1;background:#f7f4ef;border:1px solid #ded6c8;
           border-radius:12px;padding:14px;text-align:center}}
  .metric .val{{font-size:26px;font-weight:850}}
  .metric .lbl{{font-size:11px;text-transform:uppercase;letter-spacing:.08em;
                color:#6b7280;margin-top:2px}}
  .section{{margin-bottom:18px}}
  .section h3{{font-size:13px;text-transform:uppercase;letter-spacing:.08em;
               color:#6b7280;margin:0 0 6px}}
  .section p{{font-size:14px;color:#333;margin:0;line-height:1.5}}
  .badge{{display:inline-block;padding:4px 10px;border-radius:999px;
          font-size:12px;font-weight:700;color:white}}
  .btn{{display:inline-block;padding:12px 24px;border-radius:999px;
        background:linear-gradient(135deg,#080808,#4b0a12);color:white;
        text-decoration:none;font-weight:700;font-size:14px}}
  .footer{{background:#f7f4ef;padding:16px 28px;font-size:11px;color:#888;
           border-top:1px solid #ded6c8}}
  .divider{{height:1px;background:#ded6c8;margin:16px 0}}
  .warn{{background:#fff8e8;border-left:4px solid #d99b18;
         border-radius:8px;padding:10px 14px;font-size:13px;color:#555}}
</style>
</head>
<body>
<div class="wrap">
  <div class="hero">
    <div class="kicker">Luminarium Capital · Venture IQ</div>
    <h1>New Report Ready for Review</h1>
    <div class="sub">{startup} · {founder}</div>
  </div>

  <div class="body">

    <div class="row">
      <div class="metric">
        <div class="val" style="color:{sc}">{score}</div>
        <div class="lbl">Score / 100</div>
        {'<div style="font-size:11px;color:#b20d16;margin-top:4px">Score capped</div>' if capped else ''}
      </div>
      <div class="metric">
        <div class="val">L{proof_level}</div>
        <div class="lbl">Proof Level</div>
      </div>
      <div class="metric">
        <div class="val" style="font-size:16px;color:{cc}">{confidence}</div>
        <div class="lbl">Report Confidence</div>
      </div>
      <div class="metric">
        <div class="val" style="font-size:15px">{fundability}</div>
        <div class="lbl">Fundability</div>
      </div>
    </div>

    <div class="warn" style="margin-bottom:18px">
      <b>Confidence note:</b> {conf_reason}
    </div>

    <div class="section">
      <h3>Proof Level Rationale</h3>
      <p>{proof_rat}</p>
    </div>

    <div class="divider"></div>

    <div class="section">
      <h3>Top Strength</h3>
      <p>{strength}</p>
    </div>

    <div class="section">
      <h3>Main Risk</h3>
      <p>{risk}</p>
    </div>

    <div class="section">
      <h3>Why Now?</h3>
      <p>{why_now_txt}</p>
    </div>

    <div class="divider"></div>

    <div style="text-align:center;margin:24px 0">
      <a href="{report_link}" class="btn">View Full Report →</a>
    </div>

    {'<div style="text-align:center;margin-bottom:16px"><a href="' + deck_url + '" style="font-size:13px;color:#284b63">View Founder Deck ↗</a></div>' if deck_url else ''}

    <div class="warn">
      <b>Review required.</b> This report must be reviewed and approved before
      delivery to the founder.  Submission ID: <code>{sid}</code>
    </div>

  </div>
  <div class="footer">
    Luminarium Capital · Venture IQ · {analysis.get("submission_timestamp", "")}
    · Not financial advice.
  </div>
</div>
</body>
</html>"""

    plain = (
        f"New Venture IQ Report: {startup}\n"
        f"Founder: {founder}\n"
        f"Score: {score}/100 | Proof: L{proof_level} | Confidence: {confidence}\n"
        f"Top Strength: {strength}\n"
        f"Main Risk: {risk}\n"
        f"Why Now: {why_now_txt}\n\n"
        f"View report: {report_link}\n\n"
        f"Submission ID: {sid}\n"
        f"Review required before delivery to founder."
    )

    recipients = ", ".join(config.NOTIFY_EMAIL_TO)
    try:
        sg = SendGridAPIClient(config.SENDGRID_API_KEY)
        for recipient in config.NOTIFY_EMAIL_TO:
            message = Mail(
                from_email=config.NOTIFY_EMAIL_FROM,
                to_emails=recipient,
                subject=subject,
                html_content=html,
                plain_text_content=plain,
            )
            sg.send(message)
        process_logger.info(f"Notification sent for {startup} → {recipients}")
        return True
    except Exception as e:
        process_logger.warning(f"SendGrid notification failed for {startup}: {e}")
        return False
