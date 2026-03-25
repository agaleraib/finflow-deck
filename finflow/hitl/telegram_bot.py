"""
Telegram HITL (Human-in-the-Loop) Bot.
Handles 3 approval checkpoints with inline keyboard buttons.
Supports rejection with notes for pipeline reprocessing.
"""

import asyncio
import json
import os
import threading
import time
from dataclasses import dataclass, field
from typing import Callable

TELEGRAM_AVAILABLE = True
try:
    from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
    from telegram.ext import Application, CallbackQueryHandler, CommandHandler, ContextTypes
except ImportError:
    TELEGRAM_AVAILABLE = False


@dataclass
class HITLDecision:
    """Result of a HITL checkpoint."""
    checkpoint: str          # "quality", "compliance", "translation"
    approved: bool = False
    action: str = ""         # "approve", "reject", "edit_glossary", "meaning_error"
    notes: str = ""          # Rejection reason or edit instructions
    corrections: dict = field(default_factory=dict)  # For glossary edits
    responded_at: str = ""


class TelegramHITL:
    """
    Telegram bot for HITL approvals.
    Each checkpoint sends a formatted message with inline buttons.
    The pipeline blocks until a button is pressed.
    """

    def __init__(self):
        self.bot_token = os.environ.get("TELEGRAM_BOT_TOKEN", "")
        self.chat_id = os.environ.get("TELEGRAM_CHAT_ID", "")
        self._pending_decisions: dict[str, HITLDecision | None] = {}
        self._app = None
        self._running = False
        self._on_decision_callback: Callable | None = None

    @property
    def is_configured(self) -> bool:
        return bool(self.bot_token and self.chat_id and TELEGRAM_AVAILABLE)

    def start(self, on_decision: Callable | None = None):
        """Start the Telegram bot in a background thread."""
        if not self.is_configured:
            print("  ⚠ Telegram not configured — HITL will auto-approve")
            return

        self._on_decision_callback = on_decision
        self._app = Application.builder().token(self.bot_token).build()

        # Register callback handler for button presses
        self._app.add_handler(CallbackQueryHandler(self._handle_callback))
        self._app.add_handler(CommandHandler("status", self._handle_status))

        # Run in background thread
        self._running = True
        thread = threading.Thread(target=self._run_polling, daemon=True)
        thread.start()

    def _run_polling(self):
        """Run the bot polling loop."""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(self._app.initialize())
        loop.run_until_complete(self._app.start())
        loop.run_until_complete(self._app.updater.start_polling())
        loop.run_forever()

    def stop(self):
        """Stop the bot."""
        self._running = False

    def request_approval(
        self,
        checkpoint: str,
        summary: str,
        details: str = "",
        language: str = "",
        timeout: int = 300,
    ) -> HITLDecision:
        """
        Send approval request to Telegram and wait for response.
        Blocks until button pressed or timeout.
        """
        request_id = f"{checkpoint}_{int(time.time())}"
        self._pending_decisions[request_id] = None

        if not self.is_configured:
            # Auto-approve if Telegram isn't set up
            time.sleep(2)  # Brief pause for demo effect
            return HITLDecision(
                checkpoint=checkpoint,
                approved=True,
                action="approve",
                notes="Auto-approved (Telegram not configured)",
            )

        # Send the message
        self._send_checkpoint_message(request_id, checkpoint, summary, details, language)

        # Wait for response
        start_time = time.time()
        while time.time() - start_time < timeout:
            if self._pending_decisions.get(request_id) is not None:
                decision = self._pending_decisions.pop(request_id)
                return decision
            time.sleep(0.5)

        # Timeout — auto-approve with note
        self._pending_decisions.pop(request_id, None)
        return HITLDecision(
            checkpoint=checkpoint,
            approved=True,
            action="approve",
            notes=f"Auto-approved after {timeout}s timeout",
        )

    def _send_checkpoint_message(
        self,
        request_id: str,
        checkpoint: str,
        summary: str,
        details: str,
        language: str,
    ):
        """Send formatted checkpoint message with inline buttons."""
        import requests as req

        icons = {
            "quality": "📋",
            "compliance": "🏛️",
            "translation": "🌐",
        }
        titles = {
            "quality": "QUALITY REVIEW",
            "compliance": "COMPLIANCE SIGN-OFF",
            "translation": f"TRANSLATION APPROVAL ({language.upper()})" if language else "TRANSLATION APPROVAL",
        }

        icon = icons.get(checkpoint, "📌")
        title = titles.get(checkpoint, checkpoint.upper())

        text = (
            f"{icon} *FinFlow — {title}*\n\n"
            f"{summary}\n"
        )
        if details:
            text += f"\n{details}\n"

        # Build inline keyboard based on checkpoint type
        if checkpoint == "quality":
            keyboard = [
                [
                    {"text": "✅ Approve", "callback_data": json.dumps({"id": request_id, "action": "approve"})},
                    {"text": "✏️ Changes", "callback_data": json.dumps({"id": request_id, "action": "changes"})},
                    {"text": "❌ Reject", "callback_data": json.dumps({"id": request_id, "action": "reject"})},
                ]
            ]
        elif checkpoint == "compliance":
            keyboard = [
                [
                    {"text": "✅ Approve", "callback_data": json.dumps({"id": request_id, "action": "approve"})},
                    {"text": "🚩 Flag", "callback_data": json.dumps({"id": request_id, "action": "flag"})},
                    {"text": "❌ Reject", "callback_data": json.dumps({"id": request_id, "action": "reject"})},
                ]
            ]
        elif checkpoint == "translation":
            keyboard = [
                [
                    {"text": "✅ Approve", "callback_data": json.dumps({"id": request_id, "action": "approve"})},
                    {"text": "✏️ Edit Terms", "callback_data": json.dumps({"id": request_id, "action": "edit_glossary"})},
                ],
                [
                    {"text": "🔄 Retranslate", "callback_data": json.dumps({"id": request_id, "action": "retranslate"})},
                    {"text": "⚠️ Meaning Error", "callback_data": json.dumps({"id": request_id, "action": "meaning_error"})},
                ]
            ]
        else:
            keyboard = [
                [
                    {"text": "✅ Approve", "callback_data": json.dumps({"id": request_id, "action": "approve"})},
                    {"text": "❌ Reject", "callback_data": json.dumps({"id": request_id, "action": "reject"})},
                ]
            ]

        # Send via Telegram API
        url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
        payload = {
            "chat_id": self.chat_id,
            "text": text,
            "parse_mode": "Markdown",
            "reply_markup": json.dumps({"inline_keyboard": keyboard}),
        }

        try:
            req.post(url, json=payload, timeout=10)
        except Exception as e:
            print(f"  ⚠ Failed to send Telegram message: {e}")

    async def _handle_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle button press callback from Telegram."""
        query = update.callback_query
        await query.answer()

        try:
            data = json.loads(query.data)
        except json.JSONDecodeError:
            return

        request_id = data.get("id", "")
        action = data.get("action", "")

        decision = HITLDecision(
            checkpoint=request_id.split("_")[0] if "_" in request_id else "",
            approved=action in ("approve",),
            action=action,
            responded_at=str(time.time()),
        )

        # For rejections/edits, add demo-appropriate notes
        if action == "reject":
            decision.notes = "Remove definitive language, add 'may' qualifier"
        elif action == "edit_glossary":
            decision.notes = "Use 'nivel de soporte clave' not 'soporte principal'"
            decision.corrections = {"key support level": "nivel de soporte clave"}
        elif action == "meaning_error":
            decision.notes = "Translation changes the meaning of the trade setup"
        elif action == "flag":
            decision.notes = "Forward-looking statement needs probabilistic language"
            decision.approved = False
        elif action == "changes":
            decision.notes = "Strengthen the risk warning section"
            decision.approved = False

        self._pending_decisions[request_id] = decision

        # Update Telegram message
        action_labels = {
            "approve": "✅ Approved",
            "reject": "❌ Rejected",
            "edit_glossary": "✏️ Glossary Edit Requested",
            "meaning_error": "⚠️ Meaning Error Flagged",
            "flag": "🚩 Flagged for Review",
            "changes": "✏️ Changes Requested",
            "retranslate": "🔄 Retranslation Requested",
        }
        label = action_labels.get(action, action)

        await query.edit_message_text(
            text=f"{query.message.text}\n\n*Decision: {label}*",
            parse_mode="Markdown",
        )

        # Notify callback
        if self._on_decision_callback:
            self._on_decision_callback(decision)

    async def _handle_status(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /status command."""
        pending = len([k for k, v in self._pending_decisions.items() if v is None])
        await update.message.reply_text(
            f"🤖 FinFlow HITL Bot\n"
            f"Pending approvals: {pending}\n"
            f"Status: {'Active' if self._running else 'Inactive'}"
        )
