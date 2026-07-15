"""
send_notification.py
Always-on Telegram sport weather bot.

Features:
  - Built-in daily scheduler: pushes a personalised overview every morning
  - Per-user city tracking (persisted to JSON)
  - /city triggers a live weather fetch + analysis
  - /now gives a quick "can I go right now?" answer
  - /challenge sends the other person a nudge
  - Inline buttons for sport detail always work (bot is always running)

Usage:
  python send_notification.py              # Run the always-on bot
  python send_notification.py --push       # One-shot push only (for testing)
"""

import json
import os
import sys
import logging
import asyncio
from datetime import datetime, time as dt_time, timedelta
from zoneinfo import ZoneInfo
from pathlib import Path
from dotenv import load_dotenv

load_dotenv("sportbot.env")

CONFIG_PATH = os.path.join(os.path.dirname(__file__), "..", "config.json")
with open(CONFIG_PATH) as f:
    CONFIG = json.load(f)

TIMEZONE = ZoneInfo(CONFIG.get("timezone", "Europe/Amsterdam"))
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
USER_PREFS_PATH = os.path.join(os.path.dirname(__file__), "..", "user_prefs.json")

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger("BMsportBot")


# ---------- Per-user preferences (persisted) ----------

def load_user_prefs():
    """Load user preferences from JSON file."""
    if os.path.exists(USER_PREFS_PATH):
        try:
            with open(USER_PREFS_PATH) as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            pass
    return {}


def save_user_prefs(prefs):
    """Save user preferences to JSON file."""
    with open(USER_PREFS_PATH, "w") as f:
        json.dump(prefs, f, indent=2)


def get_user_city(prefs, chat_id):
    """Get a user's current city."""
    return prefs.get(str(chat_id), {}).get("city", CONFIG["default_city"])


def get_user_key(prefs, chat_id):
    """Get a user's identity key (martha/britt)."""
    return prefs.get(str(chat_id), {}).get("user_key", None)


def set_user_pref(prefs, chat_id, key, value):
    """Set a user preference and persist."""
    cid = str(chat_id)
    if cid not in prefs:
        prefs[cid] = {}
    prefs[cid][key] = value
    save_user_prefs(prefs)


# ---------- Live weather fetch ----------

def fetch_and_analyse(city_name):
    """Fetch weather data and run analysis for a city. Returns analysis dict or None."""
    # Import here to avoid circular imports
    sys.path.insert(0, os.path.dirname(__file__))
    from sport_weather_fetch import fetch_sport_weather
    from sport_thresholds import analyse_all_sports
    from sport_analyzer import generate_personal_comments, get_llm_client

    weather_data = fetch_sport_weather(city_name)
    if not weather_data:
        return None

    sport_results = analyse_all_sports(weather_data["hourly_consensus"])

    # Generate LLM comments
    try:
        comments = generate_personal_comments(weather_data, sport_results)
    except Exception as e:
        logger.error(f"LLM error: {e}")
        comments = {}
        for user_key, user_config in CONFIG["users"].items():
            comments[user_key] = {
                "name": user_config["name"],
                "comment": "(Bot is taking a coffee break — check the data above! ☕)"
            }

    # Build output
    output = {
        "city": weather_data["city"],
        "country": weather_data.get("country", ""),
        "date": weather_data["date"],
        "fetched_at": weather_data.get("fetched_at", ""),
        "analysed_at": datetime.now(TIMEZONE).isoformat(),
        "sources": weather_data.get("sources", []),
        "summary": weather_data.get("summary", {}),
        "sports": {},
        "personal_comments": comments,
        "hourly_consensus": weather_data["hourly_consensus"]
    }

    for sport_key, result in sport_results.items():
        output["sports"][sport_key] = {
            "display_name": result["display_name"],
            "emoji": result["emoji"],
            "overall_rating": result["overall_rating"],
            "overall_emoji": result["overall_emoji"],
            "overall_score": result["overall_score"],
            "summary_line": result["summary_line"],
            "best_window": result["best_window"],
            "worst_window": result["worst_window"],
            "hourly": result["hourly"]
        }

    # Save
    os.makedirs("docs", exist_ok=True)
    safe_city = city_name.lower().replace(" ", "_")
    output_path = f"docs/{safe_city}_sport_analysis.json"
    with open(output_path, "w") as f:
        json.dump(output, f, indent=2, default=str)
    logger.info(f"Saved analysis to {output_path}")

    return output


def load_analysis(city):
    """Load existing analysis from disk."""
    safe = city.lower().replace(" ", "_")
    path = f"docs/{safe}_sport_analysis.json"
    if os.path.exists(path):
        with open(path) as f:
            return json.load(f)
    return None


# ---------- Message formatting ----------

def format_overview_message(analysis_data, user_key=None):
    """Format the main overview message for Telegram (Markdown)."""
    city = analysis_data["city"]
    date = analysis_data["date"]
    summary = analysis_data.get("summary", {})

    # Order sports by user's preferences
    sport_keys = list(analysis_data.get("sports", {}).keys())
    if user_key and user_key in CONFIG.get("users", {}):
        preferred = CONFIG["users"][user_key].get("preferred_sports", [])
        ordered = [s for s in preferred if s in sport_keys]
        ordered += [s for s in sport_keys if s not in ordered]
        sport_keys = ordered

    lines = [
        f"*☀️ {city} — {date}*",
        "",
        f"🌡️ {summary.get('temp_low', '?')}–{summary.get('temp_high', '?')}°C  "
        f"💨 {summary.get('wind_avg_kmh', '?')} km/h  "
        f"🌧️ {summary.get('rain_avg_pct', '?')}%",
        "",
    ]

    for sport_key in sport_keys:
        sport = analysis_data["sports"][sport_key]
        bw = sport.get("best_window")
        bw_str = f" · best {bw['start']:02d}–{bw['end']:02d}h" if bw else ""
        lines.append(
            f"{sport['emoji']} {sport['display_name']}: "
            f"{sport['overall_emoji']} _{sport['overall_rating'].upper()}_ "
            f"({sport['overall_score']}/100){bw_str}"
        )

    # Personal comment
    if user_key and user_key in analysis_data.get("personal_comments", {}):
        comment = analysis_data["personal_comments"][user_key]
        lines.extend([
            "",
            f"💬 _{comment['comment']}_",
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
        f"*{sport['emoji']} {sport['display_name']} — {city} — {date}*",
        "",
        f"Overall: {sport['overall_emoji']} {sport['overall_rating'].upper()} (score {sport['overall_score']}/100)",
        f"_{sport['summary_line']}_",
        "",
    ]

    if sport.get("best_window"):
        bw = sport["best_window"]
        lines.append(f"🏆 Best window: {bw['start']:02d}:00–{bw['end']:02d}:00 (score {bw['avg_score']})")

    if sport.get("worst_window") and sport["worst_window"]["avg_score"] < 55:
        ww = sport["worst_window"]
        lines.append(f"⚠️ Avoid: {ww['start']:02d}:00–{ww['end']:02d}:00 (score {ww['avg_score']})")

    lines.append("")
    lines.append("*Hourly:*")
    for h in sport.get("hourly", []):
        issue_str = ""
        if h.get("issues"):
            issue_str = f"  {h['issues'][0]}"
        lines.append(
            f"  `{h['hour']:02d}:00`  {h.get('temp_c', 0):.0f}°C  "
            f"💨{h.get('wind_speed_kmh', 0):.0f}km/h  "
            f"💧{h.get('rain_prob_pct', 0)}%  "
            f"{h['emoji']}{issue_str}"
        )

    uv_vals = [h.get("uv_index") for h in sport.get("hourly", []) if h.get("uv_index")]
    if uv_vals and max(uv_vals) >= 6:
        lines.append(f"\n☀️ UV peaks at {max(uv_vals):.0f} — sunscreen!")

    hum_vals = [h.get("humidity_pct") for h in sport.get("hourly", []) if h.get("humidity_pct")]
    if hum_vals and sum(hum_vals) / len(hum_vals) >= 70:
        lines.append(f"💧 Humidity averaging {sum(hum_vals)/len(hum_vals):.0f}% — stay hydrated!")

    return "\n".join(lines)


def format_now_message(analysis_data, user_key=None):
    """Format a 'can I go now?' response for the current hour."""
    now = datetime.now(TIMEZONE)
    current_hour = now.hour
    city = analysis_data["city"]

    # Order sports by user's preferences
    sport_keys = list(analysis_data.get("sports", {}).keys())
    if user_key and user_key in CONFIG.get("users", {}):
        preferred = CONFIG["users"][user_key].get("preferred_sports", [])
        ordered = [s for s in preferred if s in sport_keys]
        ordered += [s for s in sport_keys if s not in ordered]
        sport_keys = ordered

    lines = [f"*Right now in {city}* ({now.strftime('%H:%M')})", ""]

    found_any = False
    for sport_key in sport_keys:
        sport = analysis_data.get("sports", {}).get(sport_key)
        if not sport:
            continue
        # Find the closest hour
        hourly = sport.get("hourly", [])
        hour_data = None
        for h in hourly:
            if h["hour"] == current_hour:
                hour_data = h
                break
        if not hour_data:
            # Find closest
            closest = min(hourly, key=lambda h: abs(h["hour"] - current_hour)) if hourly else None
            hour_data = closest

        if hour_data:
            found_any = True
            issue_str = ""
            if hour_data.get("issues"):
                issue_str = f"\n   ⚡ {hour_data['issues'][0]}"
            lines.append(
                f"{sport['emoji']} {sport['display_name']}: {hour_data['emoji']} "
                f"{hour_data.get('temp_c', '?'):.0f}°C, "
                f"💨{hour_data.get('wind_speed_kmh', '?'):.0f}km/h, "
                f"💧{hour_data.get('rain_prob_pct', '?')}%"
                f"{issue_str}"
            )

    if not found_any:
        lines.append("No data for the current hour. Try /weather for the full overview.")

    return "\n".join(lines)


# ---------- Telegram bot ----------

def run_telegram_bot():
    """Run the always-on Telegram bot with scheduler."""
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

    user_prefs = load_user_prefs()

    def _sport_buttons(city):
        """Create inline keyboard with sport buttons."""
        return InlineKeyboardMarkup([[
            InlineKeyboardButton("🏃 Running", callback_data=f"detail_running_{city}"),
            InlineKeyboardButton("🚴 Cycling", callback_data=f"detail_cycling_{city}"),
            InlineKeyboardButton("🏊 Swimming", callback_data=f"detail_swimming_{city}"),
        ]])

    # --- Command handlers ---

    async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
        buttons = [
            [InlineKeyboardButton(u["name"], callback_data=f"iam_{key}")]
            for key, u in CONFIG["users"].items()
        ]
        await update.message.reply_text(
            "Welcome! 🏃🚴🏊\n\nWho are you?",
            reply_markup=InlineKeyboardMarkup(buttons),
            parse_mode="Markdown"
        )

    async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
        await update.message.reply_text(
            "*Commands:*\n\n"
            "/weather — Sport weather overview\n"
            "/weather `City` — One-off forecast for another city\n"
            "/run — Detailed running conditions\n"
            "/cycle — Detailed cycling conditions\n"
            "/swim — Detailed swimming conditions\n"
            "/now — Can I go right now?\n"
            "/city `City` — Change your default city\n"
            "/city reset — Back to Utrecht\n"
            "/challenge — Nudge your partner to go out\n"
            "/settings — Your current settings\n"
            "/help — This message",
            parse_mode="Markdown"
        )

    async def cmd_weather(update: Update, context: ContextTypes.DEFAULT_TYPE):
        chat_id = update.effective_chat.id
        city = get_user_city(user_prefs, chat_id)
        user_key = get_user_key(user_prefs, chat_id)

        # One-off city: /weather Lisbon
        if context.args:
            city = " ".join(context.args)

        analysis = load_analysis(city)
        if not analysis:
            await update.message.reply_text(f"No data for *{city}* yet. Fetching now...", parse_mode="Markdown")
            analysis = fetch_and_analyse(city)
            if not analysis:
                await update.message.reply_text(f"❌ Could not fetch weather for *{city}*.", parse_mode="Markdown")
                return

        msg = format_overview_message(analysis, user_key)
        await update.message.reply_text(
            msg,
            reply_markup=_sport_buttons(city),
            parse_mode="Markdown"
        )

    async def cmd_sport(update: Update, context: ContextTypes.DEFAULT_TYPE, sport_key: str):
        chat_id = update.effective_chat.id
        city = get_user_city(user_prefs, chat_id)
        user_key = get_user_key(user_prefs, chat_id)
        analysis = load_analysis(city)
        if not analysis:
            await update.message.reply_text(f"No data for *{city}* yet. Use /weather first.", parse_mode="Markdown")
            return
        msg = format_sport_detail(analysis, sport_key, user_key)
        await update.message.reply_text(msg, parse_mode="Markdown")

    async def cmd_run(update: Update, context: ContextTypes.DEFAULT_TYPE):
        await cmd_sport(update, context, "running")

    async def cmd_cycle(update: Update, context: ContextTypes.DEFAULT_TYPE):
        await cmd_sport(update, context, "cycling")

    async def cmd_swim(update: Update, context: ContextTypes.DEFAULT_TYPE):
        await cmd_sport(update, context, "swimming")

    async def cmd_now(update: Update, context: ContextTypes.DEFAULT_TYPE):
        chat_id = update.effective_chat.id
        city = get_user_city(user_prefs, chat_id)
        user_key = get_user_key(user_prefs, chat_id)
        analysis = load_analysis(city)
        if not analysis:
            await update.message.reply_text(f"No data for *{city}* yet. Use /weather first.", parse_mode="Markdown")
            return
        msg = format_now_message(analysis, user_key)
        await update.message.reply_text(msg, parse_mode="Markdown")

    async def cmd_city(update: Update, context: ContextTypes.DEFAULT_TYPE):
        chat_id = update.effective_chat.id

        if not context.args:
            city = get_user_city(user_prefs, chat_id)
            await update.message.reply_text(
                f"Your current city is *{city}*.\n\n"
                f"Use `/city Amsterdam` to change it.\n"
                f"Use `/city reset` to go back to {CONFIG['default_city']}.",
                parse_mode="Markdown"
            )
            return

        new_city = " ".join(context.args)

        # Handle reset
        if new_city.lower() == "reset":
            new_city = CONFIG["default_city"]
            set_user_pref(user_prefs, chat_id, "city", new_city)
            await update.message.reply_text(f"✅ City reset to *{new_city}*!", parse_mode="Markdown")
            return

        # Save preference
        set_user_pref(user_prefs, chat_id, "city", new_city)

        # Check if we already have data for this city
        analysis = load_analysis(new_city)
        if analysis:
            await update.message.reply_text(
                f"✅ City changed to *{new_city}*!\nI already have today's forecast.",
                parse_mode="Markdown"
            )
            return

        # Fetch fresh data
        await update.message.reply_text(
            f"✅ City changed to *{new_city}*!\n⏳ Fetching weather data...",
            parse_mode="Markdown"
        )

        analysis = fetch_and_analyse(new_city)
        if analysis:
            user_key = get_user_key(user_prefs, chat_id)
            msg = format_overview_message(analysis, user_key)
            await update.message.reply_text(
                msg,
                reply_markup=_sport_buttons(new_city),
                parse_mode="Markdown"
            )
        else:
            await update.message.reply_text(
                f"⚠️ Couldn't fetch weather for *{new_city}*. "
                f"Check the city name and try again.\n"
                f"Your city is still set to *{new_city}* — I'll retry on the next daily update.",
                parse_mode="Markdown"
            )

    async def cmd_challenge(update: Update, context: ContextTypes.DEFAULT_TYPE):
        chat_id = update.effective_chat.id
        user_key = get_user_key(user_prefs, chat_id)

        if not user_key or user_key not in CONFIG["users"]:
            await update.message.reply_text("Use /start first so I know who you are!")
            return

        user_config = CONFIG["users"][user_key]
        partner_key = user_config.get("partner")
        if not partner_key:
            await update.message.reply_text("Couldn't find your partner in the config.")
            return

        partner_name = CONFIG["users"][partner_key]["name"]
        user_name = user_config["name"]

        # Find the partner's chat_id
        partner_chat_id = None
        for cid, pref in user_prefs.items():
            if pref.get("user_key") == partner_key:
                partner_chat_id = cid
                break

        if not partner_chat_id:
            await update.message.reply_text(
                f"{partner_name} hasn't set up the bot yet! "
                f"Tell them to open the bot and type /start."
            )
            return

        # Get current conditions for a challenge message
        city = get_user_city(user_prefs, chat_id)
        analysis = load_analysis(city)

        challenge_text = f"💪 *{user_name} challenges you!*\n\n"
        if analysis:
            # Find the best sport right now
            best_sport = None
            best_score = -1
            for sport_key, sport in analysis.get("sports", {}).items():
                if sport["overall_score"] > best_score:
                    best_score = sport["overall_score"]
                    best_sport = sport
            if best_sport:
                challenge_text += (
                    f"{best_sport['emoji']} {best_sport['display_name']} looks "
                    f"{best_sport['overall_rating']} today — "
                    f"{user_name} wants to drag you out. No excuses!"
                )
            else:
                challenge_text += f"{user_name} wants to go out. Weather be damned!"
        else:
            challenge_text += f"{user_name} wants to go out. Are you in?"

        try:
            await context.bot.send_message(
                chat_id=partner_chat_id,
                text=challenge_text,
                parse_mode="Markdown"
            )
            await update.message.reply_text(f"✅ Challenge sent to {partner_name}! 💪")
        except Exception as e:
            logger.error(f"Failed to send challenge: {e}")
            await update.message.reply_text(f"❌ Couldn't send the challenge to {partner_name}.")

    async def cmd_settings(update: Update, context: ContextTypes.DEFAULT_TYPE):
        chat_id = update.effective_chat.id
        user_key = get_user_key(user_prefs, chat_id)
        city = get_user_city(user_prefs, chat_id)

        if user_key and user_key in CONFIG["users"]:
            name = CONFIG["users"][user_key]["name"]
            preferred = CONFIG["users"][user_key].get("preferred_sports", [])
            sports_str = ", ".join(preferred) if preferred else "all"
        else:
            name = "Not set"
            sports_str = "all"

        await update.message.reply_text(
            f"*Your settings:*\n\n"
            f"👤 Name: {name}\n"
            f"📍 City: {city}\n"
            f"🏅 Sports: {sports_str}\n"
            f"⏰ Daily push: {CONFIG['schedule']['daily_push_time']}\n\n"
            f"Use /start to change identity\n"
            f"Use /city to change location",
            parse_mode="Markdown"
        )

    # --- Callback handler (inline buttons) ---

    async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        data = query.data

        if data.startswith("iam_"):
            user_key = data.replace("iam_", "")
            chat_id = query.message.chat_id
            set_user_pref(user_prefs, chat_id, "user_key", user_key)
            name = CONFIG["users"][user_key]["name"]
            await query.edit_message_text(
                f"Hey {name}! 👋\n\n"
                f"Your city is *{CONFIG['default_city']}*.\n"
                f"Type /weather to get started, or /help for all commands.",
                parse_mode="Markdown"
            )

        elif data.startswith("detail_"):
            parts = data.split("_", 2)
            sport_key = parts[1]
            city = parts[2] if len(parts) > 2 else get_user_city(user_prefs, query.message.chat_id)
            user_key = get_user_key(user_prefs, query.message.chat_id)

            analysis = load_analysis(city)
            if analysis:
                msg = format_sport_detail(analysis, sport_key, user_key)
                await query.message.reply_text(msg, parse_mode="Markdown")
            else:
                await query.message.reply_text(f"No data for {city}.")

    # --- Daily scheduled push ---

    async def daily_push(context: ContextTypes.DEFAULT_TYPE):
        """Send daily overview to all registered users."""
        logger.info("⏰ Running daily push...")

        chat_ids_str = os.getenv("TELEGRAM_CHAT_IDS", "")

        # Build map of user_key -> chat_id from env AND from saved prefs
        user_chat_map = {}

        # From env variable
        for entry in chat_ids_str.split(","):
            entry = entry.strip()
            if not entry:
                continue
            if ":" in entry:
                ukey, cid = entry.split(":", 1)
                user_chat_map[ukey.strip()] = cid.strip()
            else:
                for ukey in CONFIG["users"]:
                    user_chat_map.setdefault(ukey, entry)

        # Also from saved prefs (in case someone used /start but isn't in env)
        for cid, pref in user_prefs.items():
            ukey = pref.get("user_key")
            if ukey and ukey in CONFIG["users"]:
                user_chat_map.setdefault(ukey, cid)

        # Collect unique cities to fetch
        cities_needed = set()
        for ukey, cid in user_chat_map.items():
            city = get_user_city(user_prefs, cid)
            cities_needed.add(city)

        # Fetch weather for each city
        for city in cities_needed:
            logger.info(f"📡 Fetching weather for {city}...")
            fetch_and_analyse(city)

        # Send messages
        for ukey, cid in user_chat_map.items():
            if ukey not in CONFIG["users"]:
                continue

            city = get_user_city(user_prefs, cid)
            analysis = load_analysis(city)
            if not analysis:
                logger.warning(f"No data for {city}, skipping {ukey}")
                continue

            msg = format_overview_message(analysis, ukey)
            try:
                await context.bot.send_message(
                    chat_id=cid,
                    text=msg,
                    reply_markup=_sport_buttons(city),
                    parse_mode="Markdown"
                )
                logger.info(f"✅ Sent daily push to {CONFIG['users'][ukey]['name']} ({cid})")
            except Exception as e:
                logger.error(f"❌ Failed to send to {cid}: {e}")

    # --- Build and run ---
    app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    # Commands
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("help", cmd_help))
    app.add_handler(CommandHandler("weather", cmd_weather))
    app.add_handler(CommandHandler("run", cmd_run))
    app.add_handler(CommandHandler("cycle", cmd_cycle))
    app.add_handler(CommandHandler("swim", cmd_swim))
    app.add_handler(CommandHandler("now", cmd_now))
    app.add_handler(CommandHandler("city", cmd_city))
    app.add_handler(CommandHandler("challenge", cmd_challenge))
    app.add_handler(CommandHandler("settings", cmd_settings))
    app.add_handler(CallbackQueryHandler(button_callback))

    # Schedule daily push
    push_time_str = CONFIG["schedule"]["daily_push_time"]  # "07:30"
    hour, minute = map(int, push_time_str.split(":"))
    push_time = dt_time(hour=hour, minute=minute, tzinfo=TIMEZONE)

    app.job_queue.run_daily(daily_push, time=push_time, name="daily_push")
    logger.info(f"📅 Daily push scheduled at {push_time_str} ({CONFIG.get('timezone', 'Europe/Amsterdam')})")

    logger.info("🤖 Bot starting... (always-on mode)")
    app.run_polling()


# ---------- One-shot push (for testing / GitHub Actions fallback) ----------

def send_one_shot_push():
    """Send overview to all configured users. Used for testing or CI."""
    import requests as http_requests

    if not TELEGRAM_BOT_TOKEN:
        print("❌ TELEGRAM_BOT_TOKEN not set")
        return

    chat_ids_str = os.getenv("TELEGRAM_CHAT_IDS", "")
    if not chat_ids_str:
        print("❌ TELEGRAM_CHAT_IDS not set")
        return

    user_prefs = load_user_prefs()
    user_chat_map = {}
    for entry in chat_ids_str.split(","):
        entry = entry.strip()
        if not entry:
            continue
        if ":" in entry:
            ukey, cid = entry.split(":", 1)
            user_chat_map[ukey.strip()] = cid.strip()
        else:
            for ukey in CONFIG["users"]:
                user_chat_map.setdefault(ukey, entry)

    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"

    # Fetch weather for default city
    city = CONFIG["default_city"]
    analysis = load_analysis(city)
    if not analysis:
        print(f"Fetching weather for {city}...")
        analysis = fetch_and_analyse(city)
    if not analysis:
        print(f"❌ Could not get data for {city}")
        return

    for ukey, cid in user_chat_map.items():
        if ukey not in CONFIG["users"]:
            continue

        msg = format_overview_message(analysis, ukey)
        buttons = {
            "inline_keyboard": [[
                {"text": "🏃 Running", "callback_data": f"detail_running_{city}"},
                {"text": "🚴 Cycling", "callback_data": f"detail_cycling_{city}"},
                {"text": "🏊 Swimming", "callback_data": f"detail_swimming_{city}"},
            ]]
        }
        payload = {
            "chat_id": cid,
            "text": msg,
            "parse_mode": "Markdown",
            "reply_markup": json.dumps(buttons)
        }
        try:
            resp = http_requests.post(url, json=payload, timeout=10)
            if resp.status_code == 200:
                print(f"✅ Sent to {CONFIG['users'][ukey]['name']} ({cid})")
            else:
                print(f"❌ Failed: {resp.text}")
        except Exception as e:
            print(f"❌ Error: {e}")


if __name__ == "__main__":
    if "--push" in sys.argv:
        send_one_shot_push()
    else:
        run_telegram_bot()
