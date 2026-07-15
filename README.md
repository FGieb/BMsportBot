# 🏃🚴🏊 BMsportBot — Britt & Martha's Sport Weather Bot

A personalised sport weather bot that tells Martha and Britt whether conditions are right for running, cycling, or swimming — with AI-powered personal messages.

Built with love as a wedding gift 💒

---

## How it works

```
┌──────────────┐   ┌──────────────┐   ┌──────────────┐
│ OpenWeather  │   │  WeatherAPI  │   │  Open-Meteo   │
│  Map (OWM)   │   │   (WAPI)     │   │  (free/open)  │
└──────┬───────┘   └──────┬───────┘   └──────┬────────┘
       │                  │                   │
       └──────────┬───────┴───────────────────┘
                  ▼
       ┌──────────────────────┐
       │  sport_weather_fetch  │  Fetches temp, wind, gusts,
       │                      │  humidity, UV, rain, storms
       └──────────┬───────────┘
                  ▼
       ┌──────────────────────┐
       │  sport_thresholds     │  Rates each hour per sport:
       │                      │  ✅ Great  🟢 OK  ⚠️ Caution  ❌ Avoid
       └──────────┬───────────┘
                  ▼
       ┌──────────────────────┐
       │  sport_analyzer       │  LLM generates personal messages
       │  (Groq / Claude /    │  — different tone for each person
       │   OpenAI)            │
       └──────────┬───────────┘
                  ▼
       ┌──────────┴───────────┐
       │                      │
  ┌────▼─────┐         ┌─────▼──────┐
  │ Telegram  │         │  Web Page   │
  │   Bot     │         │ (GitHub     │
  │ (always-  │         │  Pages)     │
  │  on)      │         │             │
  └───────────┘         └─────────────┘
```

---

## Features

- **Three weather sources** compared for reliability
- **Sport-specific analysis** with thresholds for:
  - 🏃 Running (heat, humidity, wind, rain, UV, time of day)
  - 🚴 Cycling (wind, gusts, rain, temperature, headwind)
  - 🏊 Swimming (air temperature, storms, wind, UV)
- **Best/worst time windows** per sport
- **Personalised AI messages** — different tone and content for Martha vs Britt
- **Special date detection** — birthday wishes, anniversary mentions
- **Per-user city tracking** — each person can set their own city
- **Live city change** — `/city Barcelona` fetches weather immediately
- **Challenge mode** — nudge your partner to go out
- **Always-on bot** with inline buttons that actually work
- **Web page** hosted on GitHub Pages

---

## 🗂 Project Structure

```
BMsportBot/
├── config.json                    # Personalisation: names, sports, thresholds, LLM
├── sportbot.env                   # API keys (not committed)
├── user_prefs.json                # Per-user settings (not committed, auto-created)
├── Dockerfile                     # For cloud deployment (Koyeb, Railway, etc.)
├── Procfile                       # For Heroku-style platforms
├── scripts/
│   ├── sport_weather_fetch.py     # Fetches from 3 weather APIs
│   ├── sport_thresholds.py        # Sport rating engine (✅/⚠️/❌ per hour)
│   ├── sport_analyzer.py          # LLM personal comments + full pipeline
│   └── send_notification.py       # Always-on Telegram bot + scheduler
├── docs/
│   ├── index.html                 # Web page (GitHub Pages)
│   ├── {city}_sport_weather.json  # Raw weather data
│   └── {city}_sport_analysis.json # Full analysis with ratings + comments
└── .github/
    └── workflows/
        └── sportbot.yml           # Backup data fetch (GitHub Actions)
```

---

## 🚀 Setup

### 1. Create `sportbot.env`

```env
# Weather APIs
OPENWEATHER_API_KEY=your_key_here
WEATHERAPI_API_KEY=your_key_here

# LLM (pick one)
GROQ_API_KEY=your_groq_key          # Free at groq.com

# Telegram
TELEGRAM_BOT_TOKEN=your_bot_token
TELEGRAM_CHAT_IDS=martha:123456789,britt:987654321
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Run the bot

```bash
# Always-on mode (recommended) — handles commands, buttons, daily push
python scripts/send_notification.py

# One-shot push (for testing)
python scripts/send_notification.py --push
```

### 4. Deploy (recommended)

The bot needs to run 24/7 for commands and buttons to work. Free options:

**Koyeb (easiest):**
1. Push code to GitHub
2. Go to [koyeb.com](https://www.koyeb.com) → Create App → GitHub
3. Select this repo, set build type to Dockerfile
4. Add environment variables (from sportbot.env)
5. Deploy

**Docker (any server):**
```bash
docker build -t bmsportbot .
docker run -d --env-file sportbot.env bmsportbot
```

---

## 🤖 Telegram Commands

| Command | What it does |
|---|---|
| `/start` | Set up — tell the bot who you are |
| `/weather` | Today's sport weather overview |
| `/weather Lisbon` | One-off forecast for another city |
| `/run` | Detailed running conditions (hourly) |
| `/cycle` | Detailed cycling conditions |
| `/swim` | Detailed swimming conditions |
| `/now` | Can I go right now? Quick check |
| `/city Amsterdam` | Change your default city (fetches live) |
| `/city reset` | Back to Utrecht |
| `/challenge` | Nudge your partner to go out 💪 |
| `/settings` | Show your current settings |
| `/help` | Show all commands |

Inline buttons appear under each forecast — tap a sport for the full hourly breakdown.

---

## 🌐 Web Page

Enable GitHub Pages (Settings → Pages → Source: `docs/`) to host the web interface.

---

## 🔧 Customisation

Edit `config.json` to:
- Change names, tones, sport preferences
- Add/remove sports
- Adjust thresholds (e.g. what counts as "too windy")
- Switch LLM provider
- Set special dates (birthdays, anniversaries)
- Change daily push time

---

## LLM Providers

| Provider | Cost | Model |
|---|---|---|
| **Groq** (Llama 3.3 70B) | Free | `llama-3.3-70b-versatile` |
| **OpenAI** (GPT-4) | ~€0.01/request | Set in config.json |
| **Anthropic** (Claude) | ~€0.01/request | Set in config.json |

---

Built with ❤️ by Francien
