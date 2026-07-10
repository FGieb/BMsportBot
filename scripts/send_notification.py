"""
send_notification.py
Sends sport weather notifications via Telegram.
Supports:
  - Daily scheduled push (overview + inline buttons for detail)
  - Interactive commands: /weather, /run, /cycle, /swim, /city, /help
"""

import json
import os
import sys
import logging
from datetime import datetime
from zoneinfo import ZoneInfo
from dotenv import load_dotenv

load_dotenv("sportbot.env")

CONFIG_PATH = os.path.join(os.path.dirname(__file__), "..", "config.json")
with open(CONFIG_PATH) as f:
    CONFIG = json.load(f)

TIMEZONE = ZoneInfo(CONFIG.get("timezone", "Europe/Amsterdam"))
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger("SportWeatherBot")


# ---------- Message formatting ----------

def format_overview_message(analysis_data, user_key=None):
    """Format the main overview message for Telegram (Markdown)."""
    city = analysis_data["city"]
    date = analysis_data["date"]
    summary = analysis_data.get("summary", {})

    lines = [
        f"*🏋️ SportWeather – {city} – {date}*",
        "",
        f"🌡️ {summary.get('temp_low', '?')}–{summary.get('temp_high', '?')}°C "
        f"(avg {summary.get('temp_avg', '?')}°C)",
        f"💨 Wind: avg {summary.get('wind_avg_kmh', '?')} km/h, max {summary.get('wind_max_kmh', '?')} km/h",
        f"🌧️ Rain: avg {summary.get('rain_avg_pct', '?')}%, max {summary.get('rain_max_pct', '?')}%",
        "",
    ]

    # Sport overview
    for sport_key, sport in analysis_data.get("sports", {}).items():
        lines.append(
            f"{sport['emoji']} {sport['display_name']}:  "
            f"{sport['overall_emoji']} {sport['summary_line']}"
        )

    # Personal comment
    if user_key and user_key in analysis_data.get("personal_comments", {}):
        comment = analysis_data["personal_comments"][user_key]
        lines.extend([
            "",
            f"💬 _{comment['comment']}_",
            "",
            f"— {CONFIG['bot_name']} ☀️"
        ])

    return "\n".join(lines)


def format_sport_detail(analysis_data, sport_key, user_key=None):
    """Format detailed view for one sport."""
    sport = analysis_data.get("sports", {}).get(sport_key)
    if not sport:
        return f"No data available for {sport_key}."

    city = analysis_data["city"]
    date = analysis_data["date"]

    lines = [
        f"*{sport['emoji']} {sport['display_name']} – {city} – {date}*",
        "",
        f"Overall: {sport['overall_emoji']} {sport['overall_rating'].upper()} (score {sport['overall_score']}/100)",
        f"_{sport['summary_line']}_",
        "",
    ]

    if sport.get("best_window"):
        bw = sport["best_window"]
        lines.append(f"🏆 Best window: {bw['start']:02d}:00–{bw['end']:02d}:00 (score {bw['avg_score']})")

    if sport.get("worst_window") and sport["worst_window"]["avg_score"] < 50:
        ww = sport["worst_window"]
        lines.append(f"⚠️ Avoid: {ww['start']:02d}:00–{ww['end']:02d}:00 (score {ww['avg_score']})")

    lines.append("")

    # Hourly breakdown
    lines.append("*Hourly breakdown:*")
    for h in sport.get("hourly", []):
        issue_str = ""
        if h["issues"]:
            # Take first issue only to keep it compact
            issue_str = f"  {h['issues'][0]}"
        lines.append(
            f"  `{h['hour']:02d}:00`  {h.get('temp_c', '?'):.0f}°C  "
            f"💨{h.get('wind_speed_kmh', '?'):.0f}km/h  "
            f"💧{h.get('rain_prob_pct', '?')}%  "
            f"{h['emoji']}{issue_str}"
        )

    # UV summary
    uv_vals = [h.get("uv_index") for h in sport.get("hourly", []) if h.get("uv_index")]
    if uv_vals:
        max_uv = max(uv_vals)
        if max_uv >= 6:
            lines.append(f"\n☀️ UV peaks at {max_uv:.0f} — sunscreen recommended!")

    # Humidity note
    hum_vals = [h.get("humidity_pct") for h in sport.get("hourly", []) if h.get("humidity_pct")]
    if hum_vals:
        avg_hum = sum(hum_vals) / len(hum_vals)
        if avg_hum >= 75:
            lines.append(f"💧 Humidity averaging {avg_hum:.0f}% — stay hydrated!")

    return "\n".join(lines)


# ---------- Telegram bot (interactive mode) ----------

def run_telegram_bot():
    """Run the interactive Telegram bot with commands and inline buttons."""
    try:
        from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
        from telegram.ext import (
            Application, CommandHandler, CallbackQueryHandler, ContextTypes
        )
    except ImportError:
        print("❌ python-telegram-bot not installed. Run: pip install python-telegram-bot")
        return

    if not TELEGRAM_BOT_TOKEN:
        print("❌ TELEGRAM_BOT_TOKEN not set in sportbot.env")
        return

    # --- User state (in-memory, or SQLite for persistence) ---
    user_prefs = {}  # chat_id -> {"city": "...", "user_key": "martha"|"britt"}

    def get_user_city(chat_id):
        return user_prefs.get(chat_id, {}).get("city", CONFIG["default_city"])

    def get_user_key(chat_id):
        return user_prefs.get(chat_id, {}).get("user_key", None)

    def load_analysis(city):
        safe = city.lower().replace(" ", "_")
        path = f"docs/{safe}_sport_analysis.json"
        if os.path.exists(path):
            with open(path) as f:
                return json.load(f)
        return None

    # --- Command handlers ---

    async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Welcome message and user identification."""
        user_names = [u["name"] for u in CONFIG["users"].values()]
        buttons = [
            [InlineKeyboardButton(name, callback_data=f"iam_{key}")]
            for key, u in CONFIG["users"].items()
            for name in [u["name"]]
        ]
        await update.message.reply_text(
            f"Welcome to *{CONFIG['bot_name']}*! {CONFIG['bot_tagline']}\n\n"
            f"Who are you?",
            reply_markup=InlineKeyboardMarkup(buttons),
            parse_mode="Markdown"
        )

    async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
        await update.message.reply_text(
            f"*{CONFIG['bot_name']}* — Commands:\n\n"
            "/weather — Today's sport weather overview\n"
            "/run — Detailed running conditions\n"
            "/cycle — Detailed cycling conditions\n"
            "/swim — Detailed swimming conditions\n"
            "/city `CityName` — Change your city\n"
            "/help — Show this help\n\n"
            "Or just tap the buttons below any forecast! 🏃🚴🏊",
            parse_mode="Markdown"
        )

    async def cmd_weather(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Send overview with inline buttons."""
        city = get_user_city(update.effective_chat.id)
        user_key = get_user_key(update.effective_chat.id)

        # Allow one-off city: /weather Lisbon
        if context.args:
            city = " ".join(context.args)

        analysis = load_analysis(city)
        if not analysis:
            await update.message.reply_text(
                f"No forecast data for {city} yet. Data is refreshed daily at "
                f"{CONFIG['schedule']['daily_push_time']}. Try again later!"
            )
            return

        msg = format_overview_message(analysis, user_key)
        buttons = [
            [
                InlineKeyboardButton("🏃 Running", callback_data=f"detail_running_{city}"),
                InlineKeyboardButton("🚴 Cycling", callback_data=f"detail_cycling_{city}"),
                InlineKeyboardButton("🏊 Swimming", callback_data=f"detail_swimming_{city}"),
            ]
        ]
        await update.message.reply_text(
            msg,
            reply_markup=InlineKeyboardMarkup(buttons),
            parse_mode="Markdown"
        )

    async def cmd_sport(update: Update, context: ContextTypes.DEFAULT_TYPE, sport_key: str):
        """Send detail for a specific sport."""
        city = get_user_city(update.effective_chat.id)
        user_key = get_user_key(update.effective_chat.id)
        analysis = load_analysis(city)
        if not analysis:
            await update.message.reply_text(f"No data for {city} yet.")
            return
        msg = format_sport_detail(analysis, sport_key, user_key)
        await update.message.reply_text(msg, parse_mode="Markdown")

    async def cmd_run(update: Update, context: ContextTypes.DEFAULT_TYPE):
        await cmd_sport(update, context, "running")

    async def cmd_cycle(update: Update, context: ContextTypes.DEFAULT_TYPE):
        await cmd_sport(update, context, "cycling")

    async def cmd_swim(update: Update, context: ContextTypes.DEFAULT_TYPE):
        await cmd_sport(update, context, "swimming")

    async def cmd_city(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Change default city."""
        if not context.args:
            city = get_user_city(update.effective_chat.id)
            await update.message.reply_text(f"Your current city is *{city}*.\nUse `/city Amsterdam` to change it.", parse_mode="Markdown")
            return

        new_city = " ".join(context.args)
        chat_id = update.effective_chat.id
        if chat_id not in user_prefs:
            user_prefs[chat_id] = {}
        user_prefs[chat_id]["city"] = new_city
        await update.message.reply_text(f"✅ City changed to *{new_city}*!", parse_mode="Markdown")

    # --- Callback handler (inline buttons) ---

    async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()

        data = query.data
        if data.startswith("iam_"):
            user_key = data.replace("iam_", "")
            chat_id = query.message.chat_id
            if chat_id not in user_prefs:
                user_prefs[chat_id] = {}
            user_prefs[chat_id]["user_key"] = user_key
            name = CONFIG["users"][user_key]["name"]
            await query.edit_message_text(
                f"Great, welcome {name}! 🎉\n\n"
                f"Your default city is *{CONFIG['default_city']}*.\n"
                f"Type /weather to get started, or /help for all commands.",
                parse_mode="Markdown"
            )

        elif data.startswith("detail_"):
            parts = data.split("_", 2)  # detail_running_CityName
            sport_key = parts[1]
            city = parts[2] if len(parts) > 2 else get_user_city(query.message.chat_id)
            user_key = get_user_key(query.message.chat_id)

            analysis = load_analysis(city)
            if analysis:
                msg = format_sport_detail(analysis, sport_key, user_key)
                await query.message.reply_text(msg, parse_mode="Markdown")
            else:
                await query.message.reply_text(f"No data for {city}.")

    # --- Build and run ---
    app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("help", cmd_help))
    app.add_handler(CommandHandler("weather", cmd_weather))
    app.add_handler(CommandHandler("run", cmd_run))
    app.add_handler(CommandHandler("cycle", cmd_cycle))
    app.add_handler(CommandHandler("swim", cmd_swim))
    app.add_handler(CommandHandler("city", cmd_city))
    app.add_handler(CallbackQueryHandler(button_callback))

    logger.info(f"🤖 {CONFIG['bot_name']} Telegram bot starting...")
    app.run_polling()


# ---------- One-shot push (for cron/GitHub Actions) ----------

def send_daily_push():
    """
    Send the daily overview to all configured Telegram chat IDs.
    Chat IDs should be in sportbot.env as TELEGRAM_CHAT_IDS (comma-separated).
    """
    import requests

    if not TELEGRAM_BOT_TOKEN:
        print("❌ TELEGRAM_BOT_TOKEN not set")
        return

    chat_ids_str = os.getenv("TELEGRAM_CHAT_IDS", "")
    if not chat_ids_str:
        print("❌ TELEGRAM_CHAT_IDS not set in sportbot.env")
        return

    chat_ids = [cid.strip() for cid in chat_ids_str.split(",") if cid.strip()]

    city = CONFIG["default_city"]
    safe = city.lower().replace(" ", "_")
    path = f"docs/{safe}_sport_analysis.json"

    if not os.path.exists(path):
        print(f"❌ Analysis file not found: {path}")
        return

    with open(path) as f:
        analysis = json.load(f)

    for chat_id in chat_ids:
        # Try to figure out which user this chat belongs to
        # For now, we send both comments — personalised by name
        for user_key in CONFIG["users"]:
            msg = format_overview_message(analysis, user_key)

            # Add inline buttons
            buttons = {
                "inline_keyboard": [[
                    {"text": "🏃 Running", "callback_data": f"detail_running_{city}"},
                    {"text": "🚴 Cycling", "callback_data": f"detail_cycling_{city}"},
                    {"text": "🏊 Swimming", "callback_data": f"detail_swimming_{city}"},
                ]]
            }

            payload = {
                "chat_id": chat_id,
                "text": msg,
                "parse_mode": "Markdown",
                "reply_markup": json.dumps(buttons)
            }

            url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
            try:
                resp = requests.post(url, json=payload, timeout=10)
                if resp.status_code == 200:
                    print(f"✅ Sent to {chat_id} ({CONFIG['users'][user_key]['name']})")
                else:
                    print(f"❌ Failed for {chat_id}: {resp.text}")
            except Exception as e:
                print(f"❌ Error sending to {chat_id}: {e}")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--push":
        send_daily_push()
    else:
        run_telegram_bot()
