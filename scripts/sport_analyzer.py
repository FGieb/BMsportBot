"""
sport_analyzer.py
Uses an LLM (Groq/OpenAI/Anthropic — configurable) to generate personalised
sport weather comments for each user defined in config.json.

Outputs separate messages for each person, with distinct tone and personality.
Each user gets a prompt tailored to THEIR preferred sport order and priorities.
"""

import json
import os
import sys
from datetime import datetime
from zoneinfo import ZoneInfo
from dotenv import load_dotenv

load_dotenv("sportbot.env")

CONFIG_PATH = os.path.join(os.path.dirname(__file__), "..", "config.json")
with open(CONFIG_PATH) as f:
    CONFIG = json.load(f)

TIMEZONE = ZoneInfo(CONFIG.get("timezone", "Europe/Amsterdam"))


# ---------- LLM client factory ----------

def get_llm_client():
    """Return a callable that takes a prompt and returns a string response."""
    provider = CONFIG["llm"]["provider"]
    model = CONFIG["llm"]["model"]
    temperature = CONFIG["llm"].get("temperature", 0.7)

    if provider == "groq":
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            raise ValueError("GROQ_API_KEY not set in sportbot.env")

        from groq import Groq
        client = Groq(api_key=api_key)

        def call(prompt):
            response = client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                temperature=temperature,
                max_tokens=1024
            )
            return response.choices[0].message.content.strip()

        return call

    elif provider == "openai":
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY not set in sportbot.env")

        from openai import OpenAI
        client = OpenAI(api_key=api_key)

        def call(prompt):
            response = client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                temperature=temperature,
                max_tokens=1024
            )
            return response.choices[0].message.content.strip()

        return call

    elif provider == "anthropic":
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY not set in sportbot.env")

        import anthropic
        client = anthropic.Anthropic(api_key=api_key)

        def call(prompt):
            response = client.messages.create(
                model=model,
                max_tokens=1024,
                messages=[{"role": "user", "content": prompt}],
                temperature=temperature,
            )
            return response.content[0].text.strip()

        return call

    else:
        raise ValueError(f"Unknown LLM provider: {provider}")


# ---------- Prompt building ----------

def build_weather_context_for_user(weather_data, sport_results, user_config):
    """
    Build a weather context string tailored to one user's sport priorities.
    Sports are ordered by the user's preference and include user-relevant detail.
    """
    summary = weather_data.get("summary", {})
    city = weather_data.get("city", "Unknown")
    date = weather_data.get("date", "")

    lines = [
        f"City: {city}",
        f"Date: {date}",
        f"Temperature: {summary.get('temp_low')}–{summary.get('temp_high')}°C (avg {summary.get('temp_avg')}°C)",
        f"Wind: avg {summary.get('wind_avg_kmh')} km/h, max {summary.get('wind_max_kmh')} km/h",
        f"Rain: avg {summary.get('rain_avg_pct')}%, max {summary.get('rain_max_pct')}%",
        "",
        "SPORT ASSESSMENTS (ordered by this person's preference):"
    ]

    # Order sports by user's preferred_sports, then any remaining
    preferred = user_config.get("preferred_sports", [])
    ordered_keys = []
    for sport in preferred:
        if sport in sport_results:
            ordered_keys.append(sport)
    for sport in sport_results:
        if sport not in ordered_keys:
            ordered_keys.append(sport)

    for i, sport_key in enumerate(ordered_keys):
        result = sport_results[sport_key]
        priority_label = "⭐ FAVOURITE" if i == 0 else f"#{i+1}"

        lines.append(f"\n{result['emoji']} {result['display_name']} ({priority_label}): "
                      f"{result['overall_emoji']} {result['overall_rating'].upper()} "
                      f"(score {result['overall_score']}/100)")
        lines.append(f"   {result['summary_line']}")
        if result.get("best_window"):
            bw = result["best_window"]
            lines.append(f"   Best window: {bw['start']:02d}:00–{bw['end']:02d}:00 (score {bw['avg_score']})")
        if result.get("worst_window"):
            ww = result["worst_window"]
            lines.append(f"   Worst window: {ww['start']:02d}:00–{ww['end']:02d}:00 (score {ww['avg_score']})")

        # Key issues and positives across the day
        all_issues = set()
        all_positives = set()
        for h in result.get("hourly", []):
            for issue in h.get("issues", []):
                all_issues.add(issue)
            for pos in h.get("positives", []):
                all_positives.add(pos)
        if all_issues:
            lines.append(f"   Concerns: {'; '.join(list(all_issues)[:6])}")
        if all_positives:
            lines.append(f"   Good: {'; '.join(list(all_positives)[:4])}")

        # Hour-by-hour score profile (compact)
        hourly = result.get("hourly", [])
        if hourly:
            hour_scores = " ".join(f"{h['hour']:02d}h={h['score']}" for h in hourly)
            lines.append(f"   Hourly scores: {hour_scores}")

    return "\n".join(lines)


def build_personal_prompt(user_key, user_config, weather_context, weather_data, sport_results):
    """Build a personalised prompt for one user."""
    partner_key = user_config.get("partner")
    partner_name = CONFIG["users"][partner_key]["name"] if partner_key else "your partner"
    user_name = user_config["name"]

    # Check for special dates
    today = datetime.now(TIMEZONE)
    special_note = ""
    if CONFIG.get("special_dates"):
        ann = CONFIG["special_dates"].get("wedding_anniversary")
        if ann and today.strftime("%m-%d") == ann[5:]:  # Compare month-day
            special_note = f"\n🎉 TODAY IS {user_name} AND {partner_name}'s WEDDING ANNIVERSARY! Weave in a warm congratulations naturally."

        bday = user_config.get("birthday")
        if bday and today.strftime("%m-%d") == bday[5:]:
            special_note = f"\n🎂 TODAY IS {user_name}'s BIRTHDAY! Include a happy birthday wish naturally."

        partner_bday = CONFIG["users"].get(partner_key, {}).get("birthday")
        if partner_bday and today.strftime("%m-%d") == partner_bday[5:]:
            special_note = f"\n🎂 TODAY IS {partner_name}'s BIRTHDAY! Suggest {user_name} might surprise {partner_name} with something sport-related."

        for custom in CONFIG["special_dates"].get("custom", []):
            if today.strftime("%m-%d") == custom.get("date", "")[5:]:
                special_note += f"\n✨ Special note: {custom.get('note', '')}"

    day_name = today.strftime("%A")

    # Handle example_voice as either a string or list
    examples_raw = user_config.get('example_voice', '')
    if isinstance(examples_raw, list):
        examples_formatted = '\n'.join(f'  - "{ex}"' for ex in examples_raw)
    else:
        examples_formatted = f'  - "{examples_raw}"'

    # Determine the "lead" sport recommendation for this user
    preferred = user_config.get("preferred_sports", [])
    lead_sport = None
    lead_sport_name = ""
    if preferred:
        # Find the best-scoring sport from their preferences
        best_score = -1
        for sport_key in preferred:
            if sport_key in sport_results:
                if sport_results[sport_key]["overall_score"] > best_score:
                    best_score = sport_results[sport_key]["overall_score"]
                    lead_sport = sport_key
                    lead_sport_name = sport_results[sport_key]["display_name"]

    prompt = f"""You are writing a daily sport weather message for {user_name}.
This is a personal gift — a bot that knows {user_name} and {partner_name} well.
They are a couple who recently got married. Both doctors, both busy, both sporty.
They enjoy camper trips where they cycle, and they like a good drink after exercise.

ABOUT {user_name.upper()}:
- Favourite sport order: {', '.join(preferred) if preferred else 'running, cycling, swimming'}
- Background: {user_config['style']}
- Partner: {partner_name}
- Tone: {user_config['tone']}

EXAMPLES of the right voice and register (study these carefully):
{examples_formatted}

TODAY'S WEATHER & SPORT DATA (tailored for {user_name}):
{weather_context}

Today is {day_name}.
{user_name}'s #1 sport today: {lead_sport_name} ({sport_results.get(lead_sport, {}).get('overall_rating', '?').upper() if lead_sport else 'N/A'})
{special_note}

RULES:
- Write 2–4 sentences. Short and natural. Like a text from a friend, not a weather report.
- FOCUS on {user_name}'s top sport first. Only mention other sports if they contrast
  interestingly (e.g. "not great for running but perfect swimming weather").
- Mention specific numbers (temperature, wind, time windows) but weave them in casually.
- If the scores differ across the day, highlight WHEN to go — don't just say "it's good".
- If there are issues (wind, heat, rain), mention them honestly — don't sugarcoat.
- {partner_name} can feature naturally — "drag {partner_name} along", "surprise {partner_name}
  with a swim", "when {partner_name} gets home" — but only when it fits. Not every message
  needs to mention the partner. Maybe every other day.
- Never be cheesy. Never be a life coach. No motivational quotes.
- Don't over-explain the weather. They can read the data themselves.
- Start with their name. No "Hey" or "Hi".
- End naturally — no forced sign-off catchphrase. Just let the message land.
- Vary your style day to day. Sometimes practical, sometimes cheeky, sometimes just
  "not today, open some wine".

Output ONLY the message text. Nothing else.
"""
    return prompt


# ---------- Main analysis ----------

def generate_personal_comments(weather_data, sport_results):
    """Generate personalised LLM comments for each user. Returns dict keyed by user."""
    llm_call = get_llm_client()

    comments = {}
    for user_key, user_config in CONFIG["users"].items():
        print(f"🤖 Generating comment for {user_config['name']}...")

        # Build user-specific weather context (sport order, priorities)
        weather_context = build_weather_context_for_user(weather_data, sport_results, user_config)
        prompt = build_personal_prompt(user_key, user_config, weather_context, weather_data, sport_results)

        try:
            comment = llm_call(prompt)
            comments[user_key] = {
                "name": user_config["name"],
                "comment": comment
            }
            print(f"   ✅ Done ({len(comment)} chars)")
        except Exception as e:
            print(f"   ❌ LLM error for {user_config['name']}: {e}")
            comments[user_key] = {
                "name": user_config["name"],
                "comment": f"(Coach {CONFIG['bot_name']} is taking a coffee break — check the data above! ☕)"
            }

    return comments


# ---------- Full pipeline ----------

def run_analysis(city_name=None):
    """Load weather data, run sport thresholds, generate LLM comments, save."""
    from sport_thresholds import analyse_all_sports

    city_name = city_name or CONFIG["default_city"]
    safe_city = city_name.lower().replace(" ", "_")
    weather_path = f"docs/{safe_city}_sport_weather.json"

    if not os.path.exists(weather_path):
        print(f"❌ Weather data not found at {weather_path}. Run sport_weather_fetch.py first.")
        return None

    with open(weather_path) as f:
        weather_data = json.load(f)

    # Run sport threshold analysis
    print("📊 Running sport threshold analysis...")
    sport_results = analyse_all_sports(weather_data["hourly_consensus"])

    # Generate personalised LLM comments
    print("🤖 Generating personalised comments...")
    comments = generate_personal_comments(weather_data, sport_results)

    # Save enriched output
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

    output_path = f"docs/{safe_city}_sport_analysis.json"
    with open(output_path, "w") as f:
        json.dump(output, f, indent=2, default=str)
    print(f"💾 Full analysis saved to {output_path}")

    return output


if __name__ == "__main__":
    city = sys.argv[1] if len(sys.argv) > 1 else None
    run_analysis(city)
