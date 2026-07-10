"""
sport_analyzer.py
Uses an LLM (Groq/OpenAI/Anthropic — configurable) to generate personalised
sport weather comments for each user defined in config.json.

Outputs separate messages for each person, with distinct tone and personality.
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

def build_weather_context(weather_data, sport_results):
    """Build a concise weather context string for the LLM."""
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
        "SPORT ASSESSMENTS:"
    ]

    for sport_key, result in sport_results.items():
        lines.append(f"\n{result['emoji']} {result['display_name']}: {result['overall_emoji']} {result['overall_rating'].upper()} (score {result['overall_score']}/100)")
        lines.append(f"   {result['summary_line']}")
        if result.get("best_window"):
            bw = result["best_window"]
            lines.append(f"   Best window: {bw['start']:02d}:00–{bw['end']:02d}:00 (score {bw['avg_score']})")
        # Top issues across the day
        all_issues = set()
        for h in result.get("hourly", []):
            for issue in h.get("issues", []):
                all_issues.add(issue)
        if all_issues:
            lines.append(f"   Key issues: {'; '.join(list(all_issues)[:5])}")

    return "\n".join(lines)


def build_personal_prompt(user_key, user_config, weather_context, weather_data):
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

    prompt = f"""You are "{CONFIG['bot_name']}", a personal sport weather coach.
You are writing a message specifically for {user_name}.

ABOUT {user_name.upper()}:
- Sports: {', '.join(user_config['preferred_sports'])}
- Style: {user_config['style']}
- Partner: {partner_name}
- Your tone with {user_name}: {user_config['tone']}
- Example of how you talk to {user_name}: "{user_config['example_voice']}"

TODAY'S WEATHER & SPORT DATA:
{weather_context}

Today is {day_name}.
{special_note}

INSTRUCTIONS:
- Write a short, personal message (3–5 sentences max) for {user_name}.
- Reference specific conditions: temperatures, wind, times.
- Recommend the best activity and time window for {user_name} based on their preferences.
- Where natural, suggest something they could do together with {partner_name} — but don't force it.
- If conditions are poor for their favourite sport, suggest the best alternative or the least-bad window.
- Match the tone described above. This should feel like a message from a friend who knows them well, not a weather report.
- Do NOT use bullet points or lists. Write flowing text.
- Do NOT start with "Hey" or "Hi" — jump straight into the content with their name.
- End with a short, punchy sign-off line that fits the vibe (no more than 5 words).

Output ONLY the message text, nothing else.
"""
    return prompt


# ---------- Main analysis ----------

def generate_personal_comments(weather_data, sport_results):
    """Generate personalised LLM comments for each user. Returns dict keyed by user."""
    llm_call = get_llm_client()
    weather_context = build_weather_context(weather_data, sport_results)

    comments = {}
    for user_key, user_config in CONFIG["users"].items():
        print(f"🤖 Generating comment for {user_config['name']}...")
        prompt = build_personal_prompt(user_key, user_config, weather_context, weather_data)

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
