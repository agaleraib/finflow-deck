#!/usr/bin/env python3
"""
FinFlow Report Generator — Multi-instrument, multilingual support.
Generates self-contained HTML reports with embedded charts.
Reports can use AI-generated analysis text or templates.
"""

import base64
import os
import sys
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from finflow.instruments import InstrumentConfig, fmt_price, INSTRUMENTS

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CHARTS_DIR = os.path.join(PROJECT_ROOT, "charts")
REPORTS_DIR = os.path.join(PROJECT_ROOT, "reports")
os.makedirs(REPORTS_DIR, exist_ok=True)

LANG_LABELS = {
    "en": "English", "es": "Español", "zh": "中文",
    "ja": "日本語", "pt": "Português", "de": "Deutsch",
}

# ── CSS ──────────────────────────────────────────────────────────────────

CSS = """
:root {
  --bg: #fafbfc; --card: #ffffff; --border: #e1e4e8;
  --text: #24292f; --text-dim: #57606a; --text-muted: #8b949e;
  --accent: #5b8a8a; --accent-light: #e8f0f0;
  --green: #2da44e; --red: #cf222e; --blue: #0969da; --gold: #9a6700;
}
* { box-sizing: border-box; margin: 0; padding: 0; }
body {
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Noto Sans', Helvetica, Arial, sans-serif;
  background: var(--bg); color: var(--text); line-height: 1.6;
  max-width: 900px; margin: 0 auto; padding: 40px 24px;
}
.header { border-bottom: 1px solid var(--border); padding-bottom: 24px; margin-bottom: 32px; }
.header__brand { font-size: 12px; text-transform: uppercase; letter-spacing: 0.15em; color: var(--accent); font-weight: 600; margin-bottom: 8px; }
.header__title { font-size: 28px; font-weight: 600; line-height: 1.2; margin-bottom: 4px; }
.header__subtitle { font-size: 14px; color: var(--text-dim); }
.meta { display: flex; gap: 24px; margin-bottom: 32px; flex-wrap: wrap; }
.meta__item { display: flex; flex-direction: column; gap: 2px; }
.meta__label { font-size: 10px; text-transform: uppercase; letter-spacing: 0.1em; color: var(--text-muted); font-weight: 600; }
.meta__value { font-size: 14px; font-weight: 500; }
.badge { display: inline-block; font-size: 10px; font-weight: 600; letter-spacing: 0.1em; padding: 3px 10px; border-radius: 12px; text-transform: uppercase; }
.badge--beginner { background: #dafbe1; color: var(--green); }
.badge--intermediate { background: #ddf4ff; color: var(--blue); }
.badge--professional { background: #fff8c5; color: var(--gold); }
.chart-container { margin: 32px 0; border-radius: 8px; overflow: hidden; border: 1px solid var(--border); }
.chart-container img { width: 100%; display: block; }
.section { margin-bottom: 28px; }
.section h2 { font-size: 18px; font-weight: 600; margin-bottom: 12px; padding-bottom: 8px; border-bottom: 1px solid var(--border); }
.section h3 { font-size: 15px; font-weight: 600; margin-bottom: 8px; color: var(--text-dim); }
.section p { margin-bottom: 12px; font-size: 14px; }
.section ul, .section ol { margin-left: 20px; margin-bottom: 12px; }
.section li { margin-bottom: 6px; font-size: 14px; }
.section li strong { color: var(--text); }
.callout { padding: 14px 18px; border-radius: 6px; margin: 16px 0; font-size: 13px; }
.callout--info { background: var(--accent-light); border-left: 3px solid var(--accent); }
.callout--warning { background: #fff8c5; border-left: 3px solid var(--gold); }
.lang-selector { margin-bottom: 24px; display: flex; gap: 8px; }
.lang-btn { padding: 6px 14px; border: 1px solid var(--border); border-radius: 4px; font-size: 12px; font-weight: 500; cursor: pointer; background: var(--card); }
.lang-btn.active { background: var(--accent); color: white; border-color: var(--accent); }
.disclaimer { margin-top: 40px; padding: 16px 20px; background: #f6f8fa; border: 1px solid var(--border); border-radius: 6px; font-size: 11px; color: var(--text-muted); line-height: 1.6; }
.footer { margin-top: 40px; padding-top: 20px; border-top: 1px solid var(--border); display: flex; justify-content: space-between; }
.footer__brand { font-size: 13px; color: var(--accent); font-weight: 600; }
.footer__date { font-size: 12px; color: var(--text-muted); }
@media print { body { max-width: 100%; padding: 20px; } .chart-container { break-inside: avoid; } }
"""

# ── HTML Template ────────────────────────────────────────────────────────

def html_wrap(inst: InstrumentConfig, level: str, chart_filename: str, body_html: str, language: str = "en"):
    """Wrap analysis content in a self-contained HTML report."""
    level_badges = {"beginner": "badge--beginner", "intermediate": "badge--intermediate", "professional": "badge--professional"}
    badge_class = level_badges.get(level, "badge--beginner")
    level_label = level.upper()

    today = datetime.now().strftime("%B %d, %Y")
    spot = fmt_price(inst.current_price, inst.price_format) if inst.current_price else "N/A"
    lang_label = LANG_LABELS.get(language, language)

    # Embed chart
    chart_b64 = ""
    chart_path = os.path.join(CHARTS_DIR, chart_filename)
    if os.path.exists(chart_path):
        with open(chart_path, "rb") as f:
            chart_b64 = base64.b64encode(f.read()).decode()

    return f"""<!DOCTYPE html>
<html lang="{language}">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{inst.name} — {level_label} Analysis — FinFlow</title>
  <style>{CSS}</style>
</head>
<body>
  <div class="header">
    <div class="header__brand">FinFlow by WordwideFX</div>
    <div class="header__title">{inst.name} — Market Analysis</div>
    <div class="header__subtitle">AI-Generated Technical & Fundamental Analysis</div>
  </div>

  <div class="meta">
    <div class="meta__item"><span class="meta__label">Date</span><span class="meta__value">{today}</span></div>
    <div class="meta__item"><span class="meta__label">Instrument</span><span class="meta__value">{inst.name}</span></div>
    <div class="meta__item"><span class="meta__label">Spot</span><span class="meta__value">{spot}</span></div>
    <div class="meta__item"><span class="meta__label">Timeframe</span><span class="meta__value">Daily</span></div>
    <div class="meta__item"><span class="meta__label">Level</span><span class="meta__value"><span class="badge {badge_class}">{level_label}</span></span></div>
    <div class="meta__item"><span class="meta__label">Language</span><span class="meta__value">{lang_label}</span></div>
  </div>

  <div class="chart-container">
    <img src="data:image/png;base64,{chart_b64}" alt="{inst.name} {level_label} chart">
  </div>

  {body_html}

  <div class="disclaimer">
    <strong>Disclaimer:</strong> This analysis is generated by FinFlow AI and is for informational purposes only.
    It does not constitute investment advice. Past performance is not indicative of future results.
    Trading financial instruments involves significant risk of loss. Always consult a qualified financial advisor.
    <br><br>
    <strong>AI Disclosure:</strong> This report was generated using artificial intelligence (Claude by Anthropic)
    and reviewed through FinFlow's multi-agent quality arbitration pipeline.
    Human oversight is applied at multiple checkpoints.
  </div>

  <div class="footer">
    <span class="footer__brand">FinFlow by WordwideFX</span>
    <span class="footer__date">{today}</span>
  </div>
</body>
</html>"""


# ── Report Generation ────────────────────────────────────────────────────

def generate_report(
    inst: InstrumentConfig,
    level: str,
    analysis_text: str = "",
    language: str = "en",
) -> str:
    """
    Generate a single HTML report.
    analysis_text: AI-generated analysis narrative (from pipeline) or empty for template.
    Returns the output filename.
    """
    chart_map = {
        "beginner": f"{inst.slug}_beginner.png",
        "intermediate": f"{inst.slug}_intermediate.png",
        "professional": f"{inst.slug}_professional.png",
    }
    chart_filename = chart_map.get(level, f"{inst.slug}_beginner.png")

    if analysis_text:
        body_html = _format_analysis(analysis_text, level)
    else:
        body_html = _template_analysis(inst, level)

    html = html_wrap(inst, level, chart_filename, body_html, language)

    lang_suffix = f"_{language}" if language != "en" else ""
    output_filename = f"{inst.slug}_{level}{lang_suffix}.html"
    output_path = os.path.join(REPORTS_DIR, output_filename)

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html)

    print(f"  ✓ {output_filename}")
    return output_filename


def generate_all_reports(
    inst: InstrumentConfig,
    analysis_texts: dict = None,
    translations: dict = None,
) -> list[str]:
    """
    Generate all reports for an instrument.
    analysis_texts: {"beginner": "...", "intermediate": "...", "professional": "..."}
    translations: {"es": {"beginner": "...", ...}, "zh": {...}}
    """
    files = []
    levels = ["beginner", "intermediate", "professional"]

    # English reports
    for level in levels:
        text = (analysis_texts or {}).get(level, "")
        files.append(generate_report(inst, level, text, "en"))

    # Translated reports
    if translations:
        for lang, lang_texts in translations.items():
            for level in levels:
                text = lang_texts.get(level, (analysis_texts or {}).get(level, ""))
                files.append(generate_report(inst, level, text, lang))

    return files


def _format_analysis(text: str, level: str) -> str:
    """Convert AI-generated analysis text to HTML sections."""
    # Split on double newlines for paragraphs
    paragraphs = text.strip().split("\n\n")
    html = '<div class="section">\n'
    html += f'<h2>Analysis</h2>\n'

    for para in paragraphs:
        para = para.strip()
        if not para:
            continue
        if para.startswith("##"):
            heading = para.lstrip("#").strip()
            html += f'</div>\n<div class="section">\n<h2>{heading}</h2>\n'
        elif para.startswith("#"):
            heading = para.lstrip("#").strip()
            html += f'</div>\n<div class="section">\n<h2>{heading}</h2>\n'
        elif para.startswith("- ") or para.startswith("* "):
            items = para.split("\n")
            html += '<ul>\n'
            for item in items:
                item = item.lstrip("- *").strip()
                if item:
                    html += f'  <li>{item}</li>\n'
            html += '</ul>\n'
        else:
            html += f'<p>{para}</p>\n'

    html += '</div>\n'
    return html


def _template_analysis(inst: InstrumentConfig, level: str) -> str:
    """Generate template analysis when no AI text is available."""
    spot = fmt_price(inst.current_price, inst.price_format) if inst.current_price else "N/A"
    support = fmt_price(inst.support, inst.price_format)
    resistance = fmt_price(inst.resistance, inst.price_format)

    if level == "beginner":
        return f"""
<div class="section">
  <h2>What Is {inst.name} Doing?</h2>
  <p>{inst.name} is currently trading at {spot}. The key support level to watch is {support},
  and resistance sits at {resistance}.</p>
  <div class="callout callout--info">
    <strong>Key Takeaway:</strong> Watch the {support} support level — if it holds, the current trend remains intact.
    A break above {resistance} could signal the next significant move.
  </div>
</div>
<div class="section">
  <h2>Key Levels</h2>
  <ul>
    <li><strong>Support:</strong> {support} — buyers are expected to step in here</li>
    <li><strong>Resistance:</strong> {resistance} — selling pressure expected at this level</li>
  </ul>
</div>"""

    elif level == "intermediate":
        return f"""
<div class="section">
  <h2>Technical Setup</h2>
  <p>{inst.name} at {spot} is positioned between key support at {support} and resistance at {resistance}.
  The Bollinger Bands and moving average alignment suggest the current trend structure remains active.</p>
</div>
<div class="section">
  <h2>Indicator Summary</h2>
  <ul>
    <li><strong>RSI(14):</strong> Check chart for current reading — overbought above 70, oversold below 30</li>
    <li><strong>MACD:</strong> Monitor for crossover signals confirming directional bias</li>
    <li><strong>Bollinger Bands:</strong> Position relative to bands indicates volatility regime</li>
  </ul>
</div>
<div class="section">
  <h2>Trade Setup</h2>
  <p>Key support at {support} serves as the invalidation level. A sustained break above {resistance}
  would confirm bullish continuation. Position sizing should account for current ATR-based volatility.</p>
</div>"""

    else:  # professional
        return f"""
<div class="section">
  <h2>Institutional Overview</h2>
  <p>{inst.name} trading at {spot} within the {support} — {resistance} range.
  Fibonacci retracement levels from the recent swing provide additional confluence zones.
  The EMA ribbon structure and multi-timeframe momentum alignment inform the probabilistic outlook.</p>
</div>
<div class="section">
  <h2>Multi-Factor Analysis</h2>
  <ul>
    <li><strong>Trend Structure:</strong> Evaluate higher highs/lows vs lower highs/lows across timeframes</li>
    <li><strong>Momentum:</strong> RSI, MACD, and Stochastic alignment for confirmation</li>
    <li><strong>Volatility:</strong> ATR and Bollinger Band width for position sizing</li>
    <li><strong>Volume Profile:</strong> Key volume nodes for support/resistance validation</li>
  </ul>
</div>
<div class="section">
  <h2>Scenario Framework</h2>
  <p>See the scenario analysis dashboard for probability-weighted outcomes across multiple
  resolution timelines. Cross-asset correlations and macro regime assessment inform the weighting.</p>
</div>"""


# ── Main ─────────────────────────────────────────────────────────────────

def main():
    """Generate template reports for all instruments."""
    from finflow.data.market_data import fetch_ohlcv

    print("FinFlow Report Generator — Multi-Instrument")
    print("=" * 50)

    all_files = []
    for slug, inst in INSTRUMENTS.items():
        # Get current price
        try:
            df = fetch_ohlcv(inst.ticker, period="5d")
            inst.current_price = float(df["Close"].iloc[-1])
        except Exception:
            inst.current_price = 0

        print(f"\n  Generating {inst.name} reports...")
        files = generate_all_reports(inst)
        all_files.extend(files)

    print(f"\n{'=' * 50}")
    print(f"Generated {len(all_files)} reports in {REPORTS_DIR}/")


if __name__ == "__main__":
    main()
