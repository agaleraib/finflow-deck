#!/usr/bin/env python3
"""
FinFlow Demo — Single-command pipeline runner.
Usage: python -m finflow.demo [--instrument eurusd|gold|oil] [--serve]
"""

import argparse
import os
import sys
import time

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env"))

from finflow.instruments import get_instrument, INSTRUMENTS
from finflow.pipeline import FinFlowPipeline, PipelineEvent

# ANSI colors for terminal output
class C:
    RESET = "\033[0m"
    BOLD = "\033[1m"
    DIM = "\033[2m"
    GREEN = "\033[92m"
    RED = "\033[91m"
    YELLOW = "\033[93m"
    BLUE = "\033[94m"
    CYAN = "\033[96m"
    MAGENTA = "\033[95m"
    BG_DARK = "\033[48;5;235m"


STAGE_ICONS = {
    "news": "📰",
    "data": "📊",
    "ta_agent": "📈",
    "fa_agent": "🌍",
    "quality": "⚖️",
    "deliberation": "💬",
    "hitl_quality": "👤",
    "compliance": "🏛️",
    "hitl_compliance": "👤",
    "translation": "🌐",
    "glossary": "📖",
    "hitl_translation": "👤",
    "report": "📄",
    "distribution": "📤",
    "reprocessing": "🔄",
    "pipeline": "🚀",
    "error": "❌",
}


def print_header():
    """Print branded terminal header."""
    print(f"\n{C.BG_DARK}{C.BOLD}")
    print("  ╔══════════════════════════════════════════════════╗")
    print("  ║                                                  ║")
    print(f"  ║  {C.CYAN}FinFlow{C.RESET}{C.BG_DARK}{C.BOLD} by WordwideFX                        ║")
    print(f"  ║  {C.DIM}AI-Powered Financial Analysis Pipeline{C.RESET}{C.BG_DARK}{C.BOLD}          ║")
    print("  ║                                                  ║")
    print(f"  ╚══════════════════════════════════════════════════╝{C.RESET}")
    print()


def on_event(event: PipelineEvent):
    """Handle pipeline events with formatted terminal output."""
    icon = STAGE_ICONS.get(event.stage, "•")
    stage = event.stage.replace("_", " ").upper()

    if event.status == "chunk":
        # Don't print streaming chunks in terminal (too noisy)
        return

    if event.status == "running":
        print(f"  {icon} {C.YELLOW}[{stage}]{C.RESET} {event.message}")
    elif event.status == "complete":
        print(f"  {icon} {C.GREEN}[{stage}]{C.RESET} ✓ {event.message}")
    elif event.status == "waiting":
        print(f"  {icon} {C.BLUE}[{stage}]{C.RESET} ⏳ {event.message}")
    elif event.status == "approved":
        print(f"  {icon} {C.GREEN}[{stage}]{C.RESET} ✅ {event.message}")
    elif event.status == "rejected":
        print(f"  {icon} {C.RED}[{stage}]{C.RESET} ❌ {event.message}")
    elif event.status == "reprocessing":
        print(f"  {icon} {C.MAGENTA}[{stage}]{C.RESET} 🔄 {event.message}")
    elif event.status == "error":
        print(f"  {icon} {C.RED}[{stage}]{C.RESET} ❌ {event.message}")
    else:
        print(f"  {icon} [{stage}] {event.message}")


def run_demo(instrument_slug: str):
    """Run the full pipeline for one instrument."""
    instrument = get_instrument(instrument_slug)

    print(f"\n{C.BOLD}  Starting pipeline for {C.CYAN}{instrument.name}{C.RESET}")
    print(f"  {'─' * 50}")
    print(f"  Target languages: {', '.join(instrument.target_languages)}")
    print(f"  Client profile: {instrument.client}")
    print(f"  Jurisdiction: {instrument.jurisdiction.upper()}")
    print(f"  {'─' * 50}\n")

    pipeline = FinFlowPipeline(on_event=on_event)
    result = pipeline.run(instrument)

    print(f"\n  {'═' * 50}")
    if result.success:
        print(f"  {C.GREEN}{C.BOLD}✓ Pipeline completed successfully{C.RESET}")
        print(f"  Duration: {result.duration_seconds:.1f}s")
        if result.translations:
            langs = ", ".join(result.translations.keys())
            print(f"  Translations: {langs}")
    else:
        print(f"  {C.RED}{C.BOLD}✗ Pipeline failed: {result.error}{C.RESET}")
    print(f"  {'═' * 50}\n")

    return result


def main():
    parser = argparse.ArgumentParser(description="FinFlow Demo Pipeline")
    parser.add_argument(
        "--instrument", "-i",
        default="eurusd",
        choices=list(INSTRUMENTS.keys()),
        help="Instrument to analyze (default: eurusd)",
    )
    parser.add_argument(
        "--all", "-a",
        action="store_true",
        help="Run pipeline for all instruments",
    )
    parser.add_argument(
        "--serve", "-s",
        action="store_true",
        help="Start Flask demo server after pipeline completes",
    )
    args = parser.parse_args()

    print_header()

    # Check for required environment variables
    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        print(f"  {C.RED}ERROR: ANTHROPIC_API_KEY not set.{C.RESET}")
        print(f"  Create a .env file with your API key or export it.")
        sys.exit(1)

    telegram_configured = bool(os.environ.get("TELEGRAM_BOT_TOKEN"))
    finnhub_configured = bool(os.environ.get("FINNHUB_API_KEY"))

    print(f"  {C.DIM}Environment:{C.RESET}")
    print(f"    Anthropic API: {C.GREEN}✓{C.RESET}")
    print(f"    Telegram HITL: {C.GREEN + '✓' if telegram_configured else C.YELLOW + '⚠ auto-approve'}{C.RESET}")
    print(f"    Finnhub News:  {C.GREEN + '✓' if finnhub_configured else C.YELLOW + '⚠ using demo data'}{C.RESET}")
    print()

    if args.all:
        for slug in INSTRUMENTS:
            run_demo(slug)
    else:
        run_demo(args.instrument)

    if args.serve:
        print(f"\n  {C.CYAN}Starting demo server...{C.RESET}")
        from finflow.demo_server import app
        app.run(host="0.0.0.0", port=5000, debug=False)


if __name__ == "__main__":
    main()
