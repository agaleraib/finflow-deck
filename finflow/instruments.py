"""
Central instrument configuration for FinFlow.
All chart generators, report builders, and agents import from here.
"""

from dataclasses import dataclass, field


def fmt_price(price: float, price_format: str) -> str:
    """Format price, handling comma thousands separator that % operator can't do."""
    if "%," in price_format:
        return f"${price:,.2f}"
    return price_format % price


@dataclass
class InstrumentConfig:
    # Identifiers
    ticker: str                  # yfinance symbol (e.g., "EURUSD=X")
    finnhub_symbol: str          # Finnhub symbol for news (e.g., "EURUSD")
    name: str                    # Display name (e.g., "EUR/USD")
    slug: str                    # File prefix (e.g., "eurusd")
    asset_class: str             # "forex", "commodity"

    # Formatting
    price_format: str            # Python format string: "%.4f" or "$%,.2f"
    price_decimals: int          # Number of decimal places for display

    # Key levels (updated periodically for demo accuracy)
    support: float
    resistance: float
    current_price: float = 0.0   # Updated at runtime from yfinance

    # Demo orchestration — ensures TA/FA disagree for deliberation demo
    ta_bias: str = "bullish"     # Soft bias for TA agent system prompt
    fa_bias: str = "bearish"     # Opposite bias for FA agent
    compliance_seed_phrase: str = ""  # Phrase agents are prompted to include, which compliance will flag

    # Scenario analysis
    scenarios: list = field(default_factory=list)

    # Translation
    target_languages: list = field(default_factory=lambda: ["es", "zh"])
    client: str = "oanda"        # Client glossary profile to use

    # Compliance
    jurisdiction: str = "mifid2"  # "mifid2", "sec", "fca", "asic", "mas"


# ── EUR/USD ──────────────────────────────────────────────────────────────

EURUSD = InstrumentConfig(
    ticker="EURUSD=X",
    finnhub_symbol="OANDA:EUR_USD",
    name="EUR/USD",
    slug="eurusd",
    asset_class="forex",
    price_format="%.4f",
    price_decimals=4,
    support=1.1300,
    resistance=1.1686,
    ta_bias="bullish",
    fa_bias="bearish",
    compliance_seed_phrase="EUR/USD will likely test 1.1300 within the coming weeks",
    scenarios=[
        {
            "title": "RANGE-BOUND",
            "prob": "50%",
            "target": "1.1525 — 1.1650",
            "catalyst": "Mixed data, CBs on hold",
            "color": "#85c1e9",
            "bias": "NEUTRAL",
        },
        {
            "title": "BEARISH BREAK",
            "prob": "30%",
            "target": "1.1200 — 1.1300",
            "catalyst": "Iran escalation, PMIs < 50",
            "color": "#f1948a",
            "bias": "BEARISH",
        },
        {
            "title": "BULLISH REVERSAL",
            "prob": "15%",
            "target": "1.1686 — 1.1800",
            "catalyst": "Ceasefire, accelerated Fed cuts",
            "color": "#7dcea0",
            "bias": "BULLISH",
        },
        {
            "title": "TAIL RISK",
            "prob": "5%",
            "target": "1.0943 — 1.1000",
            "catalyst": "Energy embargo, EU recession",
            "color": "#f0b27a",
            "bias": "EXTREME BEAR",
        },
    ],
    target_languages=["es", "zh"],
    client="oanda",
    jurisdiction="mifid2",
)

# ── Gold (XAU/USD) ──────────────────────────────────────────────────────

GOLD = InstrumentConfig(
    ticker="GC=F",
    finnhub_symbol="OANDA:XAU_USD",
    name="Gold (XAU/USD)",
    slug="gold",
    asset_class="commodity",
    price_format="$%,.2f",
    price_decimals=2,
    support=4200.0,
    resistance=4600.0,
    ta_bias="bullish",
    fa_bias="bearish",
    compliance_seed_phrase="Gold is guaranteed to remain above $4,000 given central bank demand",
    scenarios=[
        {
            "title": "SUSTAINED RALLY",
            "prob": "40%",
            "target": "$5,000 — $5,500",
            "catalyst": "Prolonged conflict, safe-haven flows",
            "color": "#7dcea0",
            "bias": "BULLISH",
        },
        {
            "title": "CONSOLIDATION",
            "prob": "35%",
            "target": "$4,200 — $4,600",
            "catalyst": "Gradual de-escalation, mixed signals",
            "color": "#85c1e9",
            "bias": "NEUTRAL",
        },
        {
            "title": "PULLBACK",
            "prob": "15%",
            "target": "$3,800 — $4,100",
            "catalyst": "Rapid ceasefire, risk-on rotation",
            "color": "#f0b27a",
            "bias": "BEARISH",
        },
        {
            "title": "SPIKE",
            "prob": "10%",
            "target": "$6,000+",
            "catalyst": "Broader regional war, USD crisis",
            "color": "#f1948a",
            "bias": "EXTREME BULL",
        },
    ],
    target_languages=["es", "zh"],
    client="oanda",
    jurisdiction="mifid2",
)

# ── Brent Crude Oil ──────────────────────────────────────────────────────

OIL = InstrumentConfig(
    ticker="BZ=F",
    finnhub_symbol="OANDA:BCO_USD",
    name="Brent Crude Oil",
    slug="oil",
    asset_class="commodity",
    price_format="$%,.2f",
    price_decimals=2,
    support=105.0,
    resistance=120.0,
    ta_bias="bearish",
    fa_bias="bullish",
    compliance_seed_phrase="Oil prices will definitely exceed $130 if the Strait remains closed",
    scenarios=[
        {
            "title": "GRADUAL DECLINE",
            "prob": "30%",
            "target": "$75 — $85",
            "catalyst": "Strait reopens, OPEC+ adds supply",
            "color": "#7dcea0",
            "bias": "BEARISH",
        },
        {
            "title": "PARTIAL RECOVERY",
            "prob": "30%",
            "target": "$90 — $105",
            "catalyst": "Partial strait reopening, naval escorts",
            "color": "#85c1e9",
            "bias": "NEUTRAL",
        },
        {
            "title": "SUSTAINED HIGH",
            "prob": "25%",
            "target": "$110 — $130",
            "catalyst": "Continued closure, low inventories",
            "color": "#f0b27a",
            "bias": "BULLISH",
        },
        {
            "title": "SUPER-SPIKE",
            "prob": "15%",
            "target": "$130 — $150+",
            "catalyst": "Escalation, GCC infrastructure attacks",
            "color": "#f1948a",
            "bias": "EXTREME BULL",
        },
    ],
    target_languages=["es", "zh"],
    client="oanda",
    jurisdiction="mifid2",
)

# ── Registry ─────────────────────────────────────────────────────────────

INSTRUMENTS = {
    "eurusd": EURUSD,
    "gold": GOLD,
    "oil": OIL,
}


def get_instrument(slug: str) -> InstrumentConfig:
    """Get instrument config by slug."""
    inst = INSTRUMENTS.get(slug.lower())
    if not inst:
        available = ", ".join(INSTRUMENTS.keys())
        raise ValueError(f"Unknown instrument '{slug}'. Available: {available}")
    return inst
