from dotenv import load_dotenv
load_dotenv()

import logging
import os
import asyncio
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from telegram import Update, BotCommand
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    CallbackQueryHandler, filters, ContextTypes
)
from handlers.start import start_handler, help_handler
from handlers.downloader import handle_url, handle_callback
from utils.logger import setup_logger

setup_logger()
logger = logging.getLogger(__name__)

BOT_TOKEN = os.environ.get("BOT_TOKEN")
if not BOT_TOKEN:
    raise ValueError("❌ BOT_TOKEN not found in environment variables!")

PORT = int(os.environ.get("PORT", 8080))


# ── Tiny health-check HTTP server (keeps Render Web Service happy) ────────
class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"OK")

    def log_message(self, format, *args):
        pass  # Silence access logs


def run_health_server():
    server = HTTPServer(("0.0.0.0", PORT), HealthHandler)
    logger.info(f"🌐 Health server running on port {PORT}")
    server.serve_forever()


# ── Bot setup ─────────────────────────────────────────────────────────────
async def set_commands(app: Application):
    commands = [
        BotCommand("start", "🚀 Start the bot"),
        BotCommand("help", "ℹ️ How to use the bot"),
    ]
    await app.bot.set_my_commands(commands)


async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
    logger.error(f"Exception: {context.error}", exc_info=context.error)
    if isinstance(update, Update) and update.effective_message:
        await update.effective_message.reply_text(
            "⚠️ Something went wrong. Please try again or send another link."
        )


def main():
    logger.info("🤖 Starting Downloader Bot...")

    # Start health server in background thread
    health_thread = threading.Thread(target=run_health_server, daemon=True)
    health_thread.start()

    async def run():
        app = Application.builder().token(BOT_TOKEN).build()

        app.add_handler(CommandHandler("start", start_handler))
        app.add_handler(CommandHandler("help", help_handler))
        app.add_handler(CallbackQueryHandler(handle_callback))
        app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_url))
        app.add_error_handler(error_handler)

        await set_commands(app)

        logger.info("✅ Bot is running! Polling for updates...")
        async with app:
            await app.start()
            await app.updater.start_polling(
                allowed_updates=Update.ALL_TYPES,
                drop_pending_updates=True
            )
            await asyncio.Event().wait()

    asyncio.run(run())


if __name__ == "__main__":
    main()