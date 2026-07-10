"""
sport_thresholds.py
Evaluates hourly weather data against sport-specific thresholds.
Produces ✅ (great), ⚠️ (caution), ❌ (not recommended) per hour per sport.
Also identifies the best time window for each sport.
"""

import json
import os

CONFIG_PATH = os.path.join(os.path.dirname(__file__), "..", "config.json")
with open(CONFIG_PATH) as f:
    CONFIG = json.load(f)

SPORTS = CONFIG["sports"]


# ---------- Rating logic ----------

def rate_hour(sport_key, hour_data):
    """
    Rate a single hour for a given sport.
    Returns: {
        "rating": "great" | "ok" | "caution" | "avoid",
        "emoji": "✅" | "🟢" | "⚠️" | "❌",
        "issues": ["list of specific concerns"],
        "score": 0-100 (higher = better)
    }
    """
    t = SPORTS[sport_key]["thresholds"]
    issues = []
    score = 100  # Start perfect, deduct for issues

    temp = hour_data.get("temp_c")
    feels_like = hour_data.get("feels_like_c")
    humidity = hour_data.get("humidity_pct")
    wind = hour_data.get("wind_speed_kmh")
    gust = hour_data.get("wind_gust_kmh")
    rain = hour_data.get("rain_prob_pct")
    uv = hour_data.get("uv_index")
    thunder = hour_data.get("thunderstorm_risk", False)

    # Use feels_like if available, otherwise temp
    effective_temp = feels_like if feels_like is not None else temp

    # --- Temperature ---
    if effective_temp is not None:
        if "temp_danger_max" in t and effective_temp >= t["temp_danger_max"]:
            issues.append(f"🌡️ Dangerously hot ({effective_temp:.0f}°C)")
            score -= 50
        elif "temp_warn_max" in t and effective_temp >= t["temp_warn_max"]:
            issues.append(f"🌡️ Hot ({effective_temp:.0f}°C)")
            score -= 25
        elif "temp_danger_min" in t and effective_temp <= t["temp_danger_min"]:
            issues.append(f"🥶 Too cold ({effective_temp:.0f}°C)")
            score -= 50
        elif "temp_warn_min" in t and effective_temp <= t["temp_warn_min"]:
            issues.append(f"🥶 Cold ({effective_temp:.0f}°C)")
            score -= 20
        elif t.get("temp_ideal_min") and t.get("temp_ideal_max"):
            if t["temp_ideal_min"] <= effective_temp <= t["temp_ideal_max"]:
                score += 5  # Bonus for ideal range

    # --- Humidity ---
    if humidity is not None:
        if "humidity_danger" in t and humidity >= t["humidity_danger"]:
            issues.append(f"💧 Very humid ({humidity}%)")
            score -= 35
        elif "humidity_warn" in t and humidity >= t["humidity_warn"]:
            issues.append(f"💧 Humid ({humidity}%)")
            score -= 15

    # --- Wind ---
    if wind is not None:
        if "wind_danger_kmh" in t and wind >= t["wind_danger_kmh"]:
            issues.append(f"💨 Dangerous wind ({wind:.0f} km/h)")
            score -= 45
        elif "wind_warn_kmh" in t and wind >= t["wind_warn_kmh"]:
            issues.append(f"💨 Windy ({wind:.0f} km/h)")
            score -= 20

    # --- Wind gusts (mainly cycling) ---
    if gust is not None and sport_key == "cycling":
        if "gust_danger_kmh" in t and gust >= t["gust_danger_kmh"]:
            issues.append(f"💨 Dangerous gusts ({gust:.0f} km/h)")
            score -= 40
        elif "gust_warn_kmh" in t and gust >= t["gust_warn_kmh"]:
            issues.append(f"💨 Gusty ({gust:.0f} km/h)")
            score -= 15

    # --- Rain ---
    if rain is not None:
        if "rain_prob_danger" in t and rain >= t["rain_prob_danger"]:
            issues.append(f"🌧️ High rain chance ({rain}%)")
            score -= 35
        elif "rain_prob_warn" in t and rain >= t["rain_prob_warn"]:
            issues.append(f"🌧️ Possible rain ({rain}%)")
            score -= 15

    # --- UV ---
    if uv is not None:
        if "uv_danger" in t and uv >= t["uv_danger"]:
            issues.append(f"☀️ Very high UV ({uv:.0f})")
            score -= 20
        elif "uv_warn" in t and uv >= t["uv_warn"]:
            issues.append(f"☀️ High UV ({uv:.0f}) — sunscreen!")
            score -= 5  # Minor, just a heads-up

    # --- Thunderstorm (critical for swimming) ---
    if thunder and t.get("thunderstorm_danger"):
        issues.append("⛈️ Thunderstorm risk — avoid outdoor swimming!")
        score -= 60

    # Clamp score
    score = max(0, min(100, score))

    # Determine rating
    if score >= 75:
        rating, emoji = "great", "✅"
    elif score >= 55:
        rating, emoji = "ok", "🟢"
    elif score >= 35:
        rating, emoji = "caution", "⚠️"
    else:
        rating, emoji = "avoid", "❌"

    return {
        "rating": rating,
        "emoji": emoji,
        "score": score,
        "issues": issues
    }


# ---------- Analyse full day ----------

def analyse_sport_day(sport_key, hourly_consensus):
    """
    Analyse a full day of hourly consensus data for one sport.
    Returns: {
        "sport": "running",
        "overall_rating": "great",
        "overall_emoji": "✅",
        "best_window": {"start": 7, "end": 10, "avg_score": 92},
        "worst_window": {"start": 14, "end": 16, "avg_score": 35},
        "hourly": [ ... rated hours ... ],
        "summary_line": "Great conditions all morning, avoid afternoon heat"
    }
    """
    hourly_rated = []
    for h in hourly_consensus:
        rating = rate_hour(sport_key, h)
        hourly_rated.append({
            "hour": h["hour"],
            "rating": rating["rating"],
            "emoji": rating["emoji"],
            "score": rating["score"],
            "issues": rating["issues"],
            "temp_c": h.get("temp_c"),
            "feels_like_c": h.get("feels_like_c"),
            "wind_speed_kmh": h.get("wind_speed_kmh"),
            "wind_gust_kmh": h.get("wind_gust_kmh"),
            "humidity_pct": h.get("humidity_pct"),
            "rain_prob_pct": h.get("rain_prob_pct"),
            "uv_index": h.get("uv_index")
        })

    scores = [h["score"] for h in hourly_rated]
    if not scores:
        return None

    # Overall rating = average score
    avg_score = sum(scores) / len(scores)
    if avg_score >= 75:
        overall_rating, overall_emoji = "great", "✅"
    elif avg_score >= 55:
        overall_rating, overall_emoji = "ok", "🟢"
    elif avg_score >= 35:
        overall_rating, overall_emoji = "caution", "⚠️"
    else:
        overall_rating, overall_emoji = "avoid", "❌"

    # Find best and worst windows (sliding window of 3 hours)
    best_window = _find_best_window(hourly_rated, window_size=3)
    worst_window = _find_worst_window(hourly_rated, window_size=3)

    # Generate concise summary line
    summary_line = _generate_summary_line(sport_key, overall_rating, best_window, worst_window, hourly_rated)

    return {
        "sport": sport_key,
        "display_name": SPORTS[sport_key]["display_name"],
        "emoji": SPORTS[sport_key]["emoji"],
        "overall_rating": overall_rating,
        "overall_emoji": overall_emoji,
        "overall_score": round(avg_score),
        "best_window": best_window,
        "worst_window": worst_window,
        "hourly": hourly_rated,
        "summary_line": summary_line
    }


def _find_best_window(hourly_rated, window_size=3):
    """Find the best consecutive window of `window_size` hours."""
    if len(hourly_rated) < window_size:
        return None
    best = None
    best_avg = -1
    for i in range(len(hourly_rated) - window_size + 1):
        window = hourly_rated[i:i + window_size]
        avg = sum(h["score"] for h in window) / window_size
        if avg > best_avg:
            best_avg = avg
            best = {
                "start": window[0]["hour"],
                "end": window[-1]["hour"],
                "avg_score": round(avg)
            }
    return best


def _find_worst_window(hourly_rated, window_size=3):
    """Find the worst consecutive window of `window_size` hours."""
    if len(hourly_rated) < window_size:
        return None
    worst = None
    worst_avg = 999
    for i in range(len(hourly_rated) - window_size + 1):
        window = hourly_rated[i:i + window_size]
        avg = sum(h["score"] for h in window) / window_size
        if avg < worst_avg:
            worst_avg = avg
            worst = {
                "start": window[0]["hour"],
                "end": window[-1]["hour"],
                "avg_score": round(avg)
            }
    return worst


def _generate_summary_line(sport_key, overall_rating, best_window, worst_window, hourly_rated):
    """Generate a short human-readable summary."""
    sport_name = SPORTS[sport_key]["display_name"].lower()

    if overall_rating == "great":
        base = f"Great {sport_name} conditions"
    elif overall_rating == "ok":
        base = f"Decent {sport_name} conditions"
    elif overall_rating == "caution":
        base = f"Mixed {sport_name} conditions"
    else:
        base = f"Tough day for {sport_name}"

    parts = [base]

    if best_window and overall_rating != "great":
        parts.append(f"best {best_window['start']:02d}:00–{best_window['end']:02d}:00")

    if worst_window and worst_window["avg_score"] < 50 and overall_rating != "avoid":
        # Collect the main issues in the worst window
        worst_hours = [h for h in hourly_rated if worst_window["start"] <= h["hour"] <= worst_window["end"]]
        all_issues = []
        for h in worst_hours:
            all_issues.extend(h["issues"])
        # Deduplicate issue types
        issue_types = set()
        for issue in all_issues:
            if "hot" in issue.lower() or "heat" in issue.lower():
                issue_types.add("heat")
            elif "wind" in issue.lower() or "gust" in issue.lower():
                issue_types.add("wind")
            elif "rain" in issue.lower():
                issue_types.add("rain")
            elif "thunder" in issue.lower():
                issue_types.add("storms")
            elif "humid" in issue.lower():
                issue_types.add("humidity")

        if issue_types:
            parts.append(f"watch out for {', '.join(sorted(issue_types))} after {worst_window['start']:02d}:00")

    return " — ".join(parts)


# ---------- Analyse all sports ----------

def analyse_all_sports(hourly_consensus):
    """Run analysis for all configured sports. Returns dict keyed by sport."""
    results = {}
    for sport_key in SPORTS:
        result = analyse_sport_day(sport_key, hourly_consensus)
        if result:
            results[sport_key] = result
    return results


if __name__ == "__main__":
    # Test with existing data
    import glob
    files = glob.glob("docs/*_sport_weather.json")
    if not files:
        print("No sport weather data found. Run sport_weather_fetch.py first.")
    else:
        for f in files:
            with open(f) as fp:
                data = json.load(fp)
            print(f"\n{'='*50}")
            print(f"📍 {data['city']} — {data['date']}")
            print(f"{'='*50}")
            results = analyse_all_sports(data["hourly_consensus"])
            for sport_key, result in results.items():
                print(f"\n{result['emoji']} {result['display_name']}: {result['overall_emoji']} {result['overall_rating'].upper()} (score: {result['overall_score']})")
                print(f"   {result['summary_line']}")
                if result['best_window']:
                    bw = result['best_window']
                    print(f"   🏆 Best: {bw['start']:02d}:00–{bw['end']:02d}:00 (score {bw['avg_score']})")
