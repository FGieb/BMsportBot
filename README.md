# 🏃🚴🏊 BMsportBot — Martha & Britt's Sport Weather Coach

A personalised sport weather bot that tells Martha and Britt whether conditions are right for running, cycling, or swimming — with AI-powered personal coaching messages.

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
  │ (push +   │         │  Pages)     │
  │ interact) │         │             │
  └───────────┘         └─────────────┘
```

---

## Features

- **Three weather sources** compared for reliability
- **Sport-specific analysis** with thresholds for:
  - 🏃 Running (heat, humidity, wind, rain, UV)
  - 🚴 Cycling (wind, gusts, rain, temperature)
  - 🏊 Swimming (temperature, storms, wind, UV)
- **Best/worst time windows** identified automatically
- **Personalised AI messages** — different tone and content for Martha vs Britt
- **Special date detection** — birthday wishes, anniversary mentions
- **Layered UI** — overview first, tap/click for sport details
- **Flexible location** — change city any time
- **Telegram bot** with interactive buttons
- **Web page** hosted on GitHub Pages

---

## 🗂 Project Structure

```
BMsportBot/
├── config.json                    # Personalisation: names, sports, thresholds, LLM config
├── sportbot.env                   # API keys (not committed — see below)
├── scripts/
│   ├── sport_weather_fetch.py     # Fetches from 3 weather APIs
│   ├── sport_thresholds.py        # Sport rating engine (✅/⚠️/❌ per hour)
│   ├── sport_analyzer.py          # LLM personal comments + full pipeline
│   └── send_notification.py       # Telegram bot + daily push
├── docs/
│   ├── index.html                 # Web page (GitHub Pages)
│   ├── {city}_sport_weather.json  # Raw weather data
│   └── {city}_sport_analysis.json # Full analysis with ratings + comments
└── .github/
    └── workflows/
        └── sportbot.yml           # Daily automation (GitHub Actions)
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
# OPENAI_API_KEY=your_openai_key    # Optional
# ANTHROPIC_API_KEY=your_claude_key  # Optional

# Telegram
TELEGRAM_BOT_TOKEN=your_bot_token
TELEGRAM_CHAT_IDS=123456789,987654321
```

### 2. Install dependencies

```bash
pip install requests python-dotenv python-telegram-bot groq
# Optional: pip install openai anthropic
```

### 3. Run manually

```bash
# Step 1: Fetch weather data
python scripts/sport_weather_fetch.py

# Step 2: Analyse + generate personal comments
python scripts/sport_analyzer.py

# Step 3a: Send daily push via Telegram (overview only)
python scripts/send_notification.py --push

# Step 3b: Send push WITH full sport details (no bot needed)
python scripts/send_notification.py --push --full

# Step 3c: Send push + listen for button clicks for 3 min
python scripts/send_notification.py --push --full --listen=180

# Step 3d: Or run the interactive Telegram bot
python scripts/send_notification.py
```

---

## 🤖 Telegram Bot Commands

| Command | What it does |
|---|---|
| `/start` | Welcome + identify yourself |
| `/weather` | Today's sport weather overview |
| `/weather Lisbon` | One-off forecast for another city |
| `/run` | Detailed running conditions |
| `/cycle` | Detailed cycling conditions |
| `/swim` | Detailed swimming conditions |
| `/city Amsterdam` | Change your default city |
| `/help` | Show all commands |

Inline buttons appear under each forecast for quick drill-down.

---

## 🌐 Web Page

Enable GitHub Pages (Settings → Pages → Source: `docs/`) to host the web interface.

The page loads the latest `{city}_sport_analysis.json` from the `docs/` folder and displays:
- Weather overview
- Sport cards with expandable detail
- Hourly scrollable timeline
- Personalised comments per person

---

## 🔧 Customisation

Edit `config.json` to:
- Change names, tones, sport preferences
- Add/remove sports
- Adjust thresholds (e.g. what counts as "too windy")
- Switch LLM provider
- Set special dates (birthdays, anniversaries)

---

## LLM Providers

| Provider | Cost | Config |
|---|---|---|
| **Groq** (Llama 3.1 70B) | Free | `"provider": "groq"` |
| **OpenAI** (GPT-4) | ~€0.01/request | `"provider": "openai"` |
| **Anthropic** (Claude) | ~€0.01/request | `"provider": "anthropic"` |

Switch by changing `llm.provider` in `config.json` and setting the matching API key in `sportbot.env`.

---

Built with ❤️ by Francien · Powered by Coach Sunny ☀️
