#!/usr/bin/env python3
"""
Generate self-contained HTML report files with embedded charts.
Each report combines the analysis text with its corresponding chart.
"""

import base64
import os

CHARTS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "charts")
REPORTS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "reports")
os.makedirs(REPORTS_DIR, exist_ok=True)

def embed_image(filename):
    path = os.path.join(CHARTS_DIR, filename)
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode()

CSS = """
:root {
  --bg: #fafbfc;
  --card: #ffffff;
  --border: #e1e4e8;
  --text: #24292f;
  --text-dim: #57606a;
  --text-muted: #8b949e;
  --accent: #5b8a8a;
  --accent-light: #e8f0f0;
  --green: #2da44e;
  --red: #cf222e;
  --blue: #0969da;
  --gold: #9a6700;
}

* { box-sizing: border-box; margin: 0; padding: 0; }

body {
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Noto Sans', Helvetica, Arial, sans-serif;
  background: var(--bg);
  color: var(--text);
  line-height: 1.6;
  max-width: 900px;
  margin: 0 auto;
  padding: 40px 24px;
}

.header {
  border-bottom: 1px solid var(--border);
  padding-bottom: 24px;
  margin-bottom: 32px;
}

.header__brand {
  font-size: 12px;
  text-transform: uppercase;
  letter-spacing: 0.15em;
  color: var(--accent);
  font-weight: 600;
  margin-bottom: 8px;
}

.header__title {
  font-size: 28px;
  font-weight: 600;
  color: var(--text);
  margin-bottom: 4px;
}

.header__subtitle {
  font-size: 14px;
  color: var(--text-dim);
}

.meta {
  display: flex;
  gap: 24px;
  flex-wrap: wrap;
  margin-bottom: 32px;
}

.meta__item {
  display: flex;
  flex-direction: column;
}

.meta__label {
  font-size: 10px;
  text-transform: uppercase;
  letter-spacing: 0.1em;
  color: var(--text-muted);
  font-weight: 600;
}

.meta__value {
  font-size: 14px;
  color: var(--text);
  font-weight: 500;
}

.chart-container {
  margin: 32px 0;
  border: 1px solid var(--border);
  border-radius: 8px;
  overflow: hidden;
  background: #0d1117;
}

.chart-container img {
  width: 100%;
  display: block;
}

h2 {
  font-size: 18px;
  font-weight: 600;
  color: var(--text);
  margin: 32px 0 12px;
  padding-bottom: 8px;
  border-bottom: 1px solid var(--border);
}

h3 {
  font-size: 15px;
  font-weight: 600;
  color: var(--text);
  margin: 24px 0 8px;
}

p {
  font-size: 14px;
  color: var(--text-dim);
  margin-bottom: 12px;
  line-height: 1.7;
}

.highlight {
  background: var(--accent-light);
  padding: 16px 20px;
  border-left: 3px solid var(--accent);
  margin: 16px 0;
  border-radius: 0 6px 6px 0;
}

.highlight p {
  margin: 0;
  color: var(--text);
  font-size: 14px;
}

table {
  width: 100%;
  border-collapse: collapse;
  margin: 16px 0;
  font-size: 13px;
}

th {
  text-align: left;
  padding: 8px 12px;
  background: var(--bg);
  border-bottom: 2px solid var(--border);
  font-weight: 600;
  color: var(--text-dim);
  font-size: 11px;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

td {
  padding: 8px 12px;
  border-bottom: 1px solid var(--border);
  color: var(--text-dim);
}

.scenario {
  display: inline-block;
  padding: 4px 10px;
  border-radius: 12px;
  font-size: 12px;
  font-weight: 600;
  margin-right: 6px;
}

.scenario--base { background: #dbeafe; color: #1e40af; }
.scenario--bear { background: #fce7f3; color: #9d174d; }
.scenario--bull { background: #d1fae5; color: #065f46; }

ul {
  padding-left: 20px;
  margin: 12px 0;
}

li {
  font-size: 14px;
  color: var(--text-dim);
  margin-bottom: 6px;
  line-height: 1.6;
}

li strong {
  color: var(--text);
}

.disclaimer {
  margin-top: 40px;
  padding: 16px 20px;
  background: #f6f8fa;
  border: 1px solid var(--border);
  border-radius: 6px;
  font-size: 11px;
  color: var(--text-muted);
  line-height: 1.6;
}

.footer {
  margin-top: 40px;
  padding-top: 20px;
  border-top: 1px solid var(--border);
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.footer__brand {
  font-size: 13px;
  color: var(--accent);
  font-weight: 600;
}

.footer__date {
  font-size: 12px;
  color: var(--text-muted);
}

@media print {
  body { max-width: 100%; padding: 20px; }
  .chart-container { break-inside: avoid; }
}
"""

def html_wrap(title, subtitle, badge, level_meta, body, chart_b64):
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{title} — FinFlow by WordwideFX</title>
  <style>{CSS}</style>
</head>
<body>
  <div class="header">
    <div class="header__brand">FinFlow by WordwideFX</div>
    <div class="header__title">{title}</div>
    <div class="header__subtitle">{subtitle}</div>
  </div>

  <div class="meta">
    <div class="meta__item">
      <span class="meta__label">Date</span>
      <span class="meta__value">March 25, 2026</span>
    </div>
    <div class="meta__item">
      <span class="meta__label">Instrument</span>
      <span class="meta__value">EUR/USD</span>
    </div>
    <div class="meta__item">
      <span class="meta__label">Timeframe</span>
      <span class="meta__value">Daily / Weekly</span>
    </div>
    <div class="meta__item">
      <span class="meta__label">Spot Rate</span>
      <span class="meta__value">1.1602</span>
    </div>
    <div class="meta__item">
      <span class="meta__label">Level</span>
      <span class="meta__value">{badge}</span>
    </div>
    {level_meta}
  </div>

  <div class="chart-container">
    <img src="data:image/png;base64,{chart_b64}" alt="EUR/USD Chart">
  </div>

  {body}

  <div class="disclaimer">
    <strong>Disclaimer:</strong> This analysis is provided for informational purposes only and does not constitute investment advice or a solicitation to trade. Foreign exchange trading carries significant risk of loss. Past performance does not guarantee future results. Consult a qualified financial professional before acting on any information contained herein. FinFlow AI is an automated analysis system developed by WordwideFX.
  </div>

  <div class="footer">
    <div class="footer__brand">FinFlow by WordwideFX</div>
    <div class="footer__date">Generated March 25, 2026 &bull; wordwidefx.com</div>
  </div>
</body>
</html>"""

# ── Beginner Report ──────────────────────────────────────────────────────

def beginner_report():
    body = """
  <h2>What Is Happening Right Now?</h2>
  <p>The euro is currently trading at <strong>$1.1602</strong> against the US dollar. Over the past few weeks, the euro has been slowly losing ground — think of it like a gentle slide rather than a sharp drop.</p>

  <h2>Why Is This Happening?</h2>
  <p>Three main forces are pushing the euro lower:</p>
  <ul>
    <li><strong>Middle East tensions are boosting the dollar.</strong> When global uncertainty rises, investors tend to buy US dollars as a "safe haven" — a place to park money when things feel risky. The ongoing conflict involving Iran and US strikes has created exactly that kind of anxiety.</li>
    <li><strong>Europe's economy is slowing down.</strong> A key survey of business activity (called PMI) came in weaker than expected at 50.5 — barely above the 50 line that separates growth from contraction. Meanwhile, energy prices are pushing costs up for European businesses.</li>
    <li><strong>Interest rate expectations are shifting.</strong> The European Central Bank revised its inflation forecast upward to 2.6% while cutting growth projections. This uncertainty makes traders hesitant to buy euros.</li>
  </ul>

  <h2>What Does This Mean For You?</h2>
  <div class="highlight">
    <p><strong>If you hold euros and need dollars:</strong> The current rate is still historically favorable. A year ago, the euro was worth about 5% less against the dollar.</p>
  </div>
  <div class="highlight">
    <p><strong>If you are waiting to convert dollars to euros:</strong> You may want to be patient. Analysts are split — some see the euro recovering to $1.20 by mid-year, while others see a dip toward $1.10 first.</p>
  </div>

  <h2>Simple Takeaways</h2>
  <ul>
    <li>The euro is in a <strong>mild downtrend</strong> but not in freefall</li>
    <li><strong>Geopolitics</strong> (Middle East) is the biggest wildcard right now</li>
    <li>The next few weeks depend heavily on whether tensions escalate or ease</li>
    <li>Most major banks expect the euro to <strong>end 2026 higher</strong> than today, in the $1.20–$1.24 range</li>
  </ul>
"""
    return html_wrap(
        "EUR/USD Market Analysis",
        "A clear, jargon-free overview of what's moving the euro",
        "Beginner",
        "",
        body,
        embed_image("eurusd_beginner.png")
    )

# ── Intermediate Report ──────────────────────────────────────────────────

def intermediate_report():
    body = """
  <h2>Technical Overview</h2>
  <p>EUR/USD is trading within a medium-term downtrend after failing to break above the 1.1648–1.1663 resistance zone earlier this month. Price action has been contained in the <strong>1.1525–1.1630 corridor</strong>, and a decisive break in either direction will likely trigger the next leg.</p>

  <h3>Key Levels</h3>
  <table>
    <thead>
      <tr><th>Type</th><th>Level</th><th>Significance</th></tr>
    </thead>
    <tbody>
      <tr><td>Resistance 2</td><td>1.1686</td><td>76.4% Fibonacci retracement — major ceiling</td></tr>
      <tr><td>Resistance 1</td><td>1.1648</td><td>Near-term resistance tested and rejected</td></tr>
      <tr><td>Pivot</td><td>1.1635</td><td>Daily pivot point</td></tr>
      <tr><td>Support 1</td><td>1.1550</td><td>Floor of the consolidation range</td></tr>
      <tr><td>Support 2</td><td>1.1200–1.1300</td><td>Medium-term structural support</td></tr>
    </tbody>
  </table>

  <h3>Indicators</h3>
  <ul>
    <li><strong>RSI (14):</strong> 53–54, trending downward from overbought territory. Still neutral but losing momentum. A break below 50 would confirm bearish control.</li>
    <li><strong>MACD:</strong> Signal line crossover to the downside. Histogram printing negative bars, indicating selling momentum is building even though price hasn't collapsed.</li>
    <li><strong>Moving Averages:</strong> Both the 50-day and 200-day SMAs sit above the current price, confirming the bearish structure. The 50 SMA acted as dynamic resistance on March 20.</li>
  </ul>

  <h2>Fundamental Drivers</h2>
  <p><strong>ECB (March 19 decision):</strong> Held the deposit rate at 2.0%. Revised 2026 inflation forecast sharply higher to <strong>2.6%</strong> while cutting GDP growth to <strong>0.9%</strong>. The stagflationary tone is weighing on the euro — the ECB is caught between fighting inflation and supporting a weakening economy.</p>
  <p><strong>Federal Reserve:</strong> Markets expect two rate cuts in 2026, bringing the Fed funds rate to 3.00–3.25%. The narrowing rate differential between the US (3.75%) and the Eurozone (2.0%) had been supporting the euro through Q1, but this narrative is fading as geopolitical risk rises.</p>
  <p><strong>Eurozone PMI (March flash):</strong> Composite fell to <strong>50.5</strong> from 51.9, well below the 51.0 consensus. Services slumped to a 10-month low. Input cost inflation is running at a 3-year high.</p>
  <p><strong>DXY Context:</strong> The Dollar Index recovered to <strong>99.28</strong>, gaining 1.6% over the past month on safe-haven flows.</p>

  <h2>Outlook &amp; Scenarios</h2>
  <p>
    <span class="scenario scenario--base">Base case 55%</span>
    <span class="scenario scenario--bear">Bearish break 30%</span>
    <span class="scenario scenario--bull">Bullish reversal 15%</span>
  </p>
  <ul>
    <li><strong>Base case (55%):</strong> Continued consolidation in 1.1525–1.1650. Bias modestly bearish.</li>
    <li><strong>Bearish break (30%):</strong> A close below 1.1525 opens the path to 1.1200–1.1300 support.</li>
    <li><strong>Bullish reversal (15%):</strong> A break above 1.1686 (76.4% Fib) on easing geopolitical risk could reignite the move toward 1.20.</li>
  </ul>
"""
    return html_wrap(
        "EUR/USD Technical & Fundamental Analysis",
        "Technical indicators with balanced TA + FA perspective",
        "Intermediate",
        "",
        body,
        embed_image("eurusd_intermediate.png")
    )

# ── Professional Report ──────────────────────────────────────────────────

def professional_report():
    body = """
  <h2>I. Technical Structure</h2>
  <p>Price rejected the 1.1648 resistance cleanly on March 20 and has since retraced into the mid-range of the 1.1525–1.1630 consolidation channel. The broader structure remains bearish with both SMA50 and SMA200 overhead as dynamic resistance.</p>

  <h3>Indicator Snapshot</h3>
  <table>
    <thead>
      <tr><th>Indicator</th><th>Value</th><th>Signal</th></tr>
    </thead>
    <tbody>
      <tr><td>RSI (14, daily)</td><td>53.1</td><td>Neutral, declining. Below-50 cross imminent</td></tr>
      <tr><td>MACD (12,26,9)</td><td>+0.00137</td><td>Below signal line, histogram contracting</td></tr>
      <tr><td>Stochastic (14,3,3)</td><td>42/48</td><td>Neutral, %K below %D</td></tr>
      <tr><td>ATR (14)</td><td>0.0068</td><td>Compressed vs. 20-day avg — breakout pending</td></tr>
      <tr><td>Bollinger Width</td><td>Narrowing</td><td>Volatility squeeze forming</td></tr>
    </tbody>
  </table>

  <h3>Fibonacci Framework (Jan low 1.0200 to Feb high 1.1686)</h3>
  <table>
    <thead>
      <tr><th>Fib Level</th><th>Price</th><th>Status</th></tr>
    </thead>
    <tbody>
      <tr><td>78.6%</td><td>1.1686</td><td>Tested, rejected — key ceiling</td></tr>
      <tr><td>61.8%</td><td>1.1118</td><td>Untested — next major support</td></tr>
      <tr><td>50.0%</td><td>1.0943</td><td>Structural pivot</td></tr>
      <tr><td>38.2%</td><td>1.0768</td><td>Bear scenario target</td></tr>
    </tbody>
  </table>

  <h2>II. Positioning &amp; Flow</h2>
  <p><strong>CFTC COT (as of March 17):</strong> Net-long speculative positions <strong>declined by 36k contracts</strong>, driven primarily by long liquidation rather than fresh shorts. Asset managers reduced longs while shorts increased by 2.8k contracts (+2.1%). The multi-year net-long positioning peak appears to be unwinding — orderly, consistent with correction rather than reversal.</p>

  <h2>III. Policy Divergence</h2>
  <table>
    <thead>
      <tr><th>Central Bank</th><th>Current Rate</th><th>Year-End Implied</th><th>Direction</th></tr>
    </thead>
    <tbody>
      <tr><td>Federal Reserve</td><td>3.75%</td><td>3.00–3.25% (2 cuts)</td><td>Easing</td></tr>
      <tr><td>ECB</td><td>2.00%</td><td>2.00–2.25% (hold/1 hike)</td><td>Neutral-to-hawkish</td></tr>
    </tbody>
  </table>
  <p>The <strong>175bp spread</strong> (Fed-ECB) has been compressing from 225bp at the start of 2026. The convergence trade is fully priced — incremental compression requires either more aggressive Fed cuts or ECB hikes.</p>

  <h3>ECB March 19 Key Points</h3>
  <ul>
    <li>Held at 2.0%, unanimous</li>
    <li>2026 HICP revised to <strong>2.6%</strong> (from 2.1% in December)</li>
    <li>GDP growth slashed to <strong>0.9%</strong> (from 1.3%)</li>
    <li>Lagarde explicitly flagged stagflation risks</li>
    <li>Employment sub-index contracting for first time since October 2025</li>
  </ul>

  <h2>IV. Cross-Asset Context</h2>
  <ul>
    <li><strong>DXY:</strong> 99.28, up 1.62% monthly. Safe-haven bid on Middle East escalation.</li>
    <li><strong>US 10Y yield:</strong> Holding near 3.85–3.90%.</li>
    <li><strong>Gold (XAU/USD):</strong> $4,460–4,550 at ATH. Gold + USD strength co-existing signals geopolitical driver, not monetary policy.</li>
    <li><strong>Brent crude:</strong> Above $95 on Middle East supply concerns, feeding Eurozone cost-push inflation.</li>
  </ul>

  <h2>V. Scenario Analysis</h2>
  <table>
    <thead>
      <tr><th>Scenario</th><th>Probability</th><th>Target</th><th>Catalyst</th></tr>
    </thead>
    <tbody>
      <tr><td>Range-bound</td><td>50%</td><td>1.1525–1.1650</td><td>Mixed data, CBs on hold</td></tr>
      <tr><td>Bearish breakdown</td><td>30%</td><td>1.1300–1.1200</td><td>Iran escalation, PMIs break 50</td></tr>
      <tr><td>Bullish breakout</td><td>15%</td><td>1.1686–1.1800</td><td>Ceasefire, accelerated Fed cuts</td></tr>
      <tr><td>Tail risk</td><td>5%</td><td>1.0943–1.1000</td><td>Energy embargo, EU recession</td></tr>
    </tbody>
  </table>
  <div class="highlight">
    <p><strong>Confidence interval (1-week):</strong> 1.1480–1.1700 (90%)</p>
  </div>

  <h2>VI. Trade Considerations</h2>
  <ul>
    <li>Short-term momentum favors sellers below 1.1630 with stops above 1.1686</li>
    <li>Compressed ATR + narrowing Bollinger Bands suggest a volatility breakout is imminent</li>
    <li>COT unwind is orderly — watch for acceleration below 1.1525</li>
    <li>Cross-asset confirmation: DXY above 100 validates bearish thesis; crude below $90 undermines it</li>
  </ul>
"""
    return html_wrap(
        "EUR/USD Institutional Research Note",
        "Full institutional depth — Fibonacci, COT, cross-asset, scenario matrix",
        "Professional",
        """<div class="meta__item">
      <span class="meta__label">DXY</span>
      <span class="meta__value">99.28</span>
    </div>""",
        body,
        embed_image("eurusd_professional.png")
    )

# ── Scenario Report ──────────────────────────────────────────────────────

def scenario_report():
    body = """
  <h2>Scenario Framework</h2>
  <p>Four probability-weighted scenarios for EUR/USD over the next 1–4 weeks. The central variable is the Middle East conflict trajectory and its impact on energy prices, safe-haven flows, and ECB/Fed policy responses.</p>

  <table>
    <thead>
      <tr><th>Scenario</th><th>Probability</th><th>Target Range</th><th>Primary Catalyst</th></tr>
    </thead>
    <tbody>
      <tr><td><strong>Range-Bound Consolidation</strong></td><td>50%</td><td>1.1525 – 1.1650</td><td>No resolution on geopolitics; mixed data keeps both central banks on hold</td></tr>
      <tr><td><strong>Bearish Breakdown</strong></td><td>30%</td><td>1.1200 – 1.1300</td><td>Iran escalation, Eurozone PMIs break below 50, energy shock deepens</td></tr>
      <tr><td><strong>Bullish Reversal</strong></td><td>15%</td><td>1.1686 – 1.1800</td><td>Ceasefire/de-escalation, Fed signals accelerated cuts, PMI recovery</td></tr>
      <tr><td><strong>Tail Risk: Deep Sell-Off</strong></td><td>5%</td><td>1.0943 – 1.1000</td><td>Full-scale energy embargo, EU recession confirmation, risk-off capitulation</td></tr>
    </tbody>
  </table>

  <h2>Key Indicators Supporting This Framework</h2>
  <table>
    <thead>
      <tr><th>Indicator</th><th>Current Value</th><th>Interpretation</th></tr>
    </thead>
    <tbody>
      <tr><td>RSI (14)</td><td>53.1</td><td>Neutral but declining — bearish momentum building</td></tr>
      <tr><td>MACD</td><td>Bearish crossover</td><td>Selling pressure increasing beneath the surface</td></tr>
      <tr><td>ATR (14)</td><td>0.0068 (compressed)</td><td>Volatility squeeze — sharp move imminent in either direction</td></tr>
      <tr><td>CFTC COT</td><td>Net-long -36K</td><td>Orderly long liquidation, not panic — correction not reversal</td></tr>
      <tr><td>DXY</td><td>99.28 (+1.6%)</td><td>Safe-haven dollar bid persists while geopolitical risk premium holds</td></tr>
      <tr><td>90% CI (1-week)</td><td>1.1480 – 1.1700</td><td>Wider than average — market pricing elevated uncertainty</td></tr>
    </tbody>
  </table>

  <h2>Cross-Asset Signals</h2>
  <ul>
    <li><strong>Gold at ATH ($4,460–4,550) alongside USD strength</strong> — confirms geopolitical risk is the primary driver, not monetary policy divergence. If risk recedes, both gold and USD could reverse simultaneously.</li>
    <li><strong>Brent crude above $95</strong> — directly feeding Eurozone cost-push inflation and the ECB's stagflation dilemma. A crude reversal below $90 would be the most bullish signal for EUR/USD.</li>
    <li><strong>US 10Y at 3.85–3.90%</strong> — markets reluctant to price aggressive Fed easing. A break below 3.75% would signal pivot expectations and weaken the dollar.</li>
  </ul>

  <div class="highlight">
    <p><strong>Bottom line:</strong> The market is coiled in a compressed range waiting for a catalyst. The most likely outcome (50%) is continued consolidation, but the asymmetry favors the downside — bearish scenarios carry 35% combined probability vs. 15% bullish. Position sizing should reflect the elevated tail risk.</p>
  </div>
"""
    return html_wrap(
        "EUR/USD Scenario Analysis",
        "Probability-weighted outlook with cross-asset confirmation signals",
        "All Levels",
        """<div class="meta__item">
      <span class="meta__label">DXY</span>
      <span class="meta__value">99.28</span>
    </div>
    <div class="meta__item">
      <span class="meta__label">Gold</span>
      <span class="meta__value">$4,460–4,550</span>
    </div>
    <div class="meta__item">
      <span class="meta__label">Brent</span>
      <span class="meta__value">&gt;$95</span>
    </div>""",
        body,
        embed_image("eurusd_scenarios.png")
    )

# ── Main ─────────────────────────────────────────────────────────────────

def main():
    reports = [
        ("beginner.html", beginner_report),
        ("intermediate.html", intermediate_report),
        ("professional.html", professional_report),
        ("scenarios.html", scenario_report),
    ]

    for filename, fn in reports:
        path = os.path.join(REPORTS_DIR, filename)
        with open(path, "w") as f:
            f.write(fn())
        size_kb = os.path.getsize(path) / 1024
        print(f"  ✓ {filename} ({size_kb:.0f} KB)")

    print(f"\nAll reports saved to: {REPORTS_DIR}/")

if __name__ == "__main__":
    main()
