"""
sport_weather_fetch.py
Fetches extended weather data from three APIs:
  1. OpenWeatherMap (OWM)
  2. WeatherAPI (WAPI)
  3. Open-Meteo (free, no key)

Outputs a unified JSON per city to docs/{city}_sport_weather.json
"""

import requests
import json
import os
import sys
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from dotenv import load_dotenv

# --- Load config and env ---
load_dotenv("sportbot.env")

CONFIG_PATH = os.path.join(os.path.dirname(__file__), "..", "config.json")
with open(CONFIG_PATH) as f:
    CONFIG = json.load(f)

OPENWEATHER_API_KEY = os.getenv("OPENWEATHER_API_KEY")
WEATHERAPI_API_KEY = os.getenv("WEATHERAPI_API_KEY")

TIMEZONE = ZoneInfo(CONFIG.get("timezone", "Europe/Amsterdam"))
FORECAST_START = CONFIG["schedule"]["forecast_window_start"]
FORECAST_END = CONFIG["schedule"]["forecast_window_end"]


def get_coordinates(city_name):
    """Use Open-Meteo geocoding (free, no key) to resolve city to lat/lon."""
    url = f"https://geocoding-api.open-meteo.com/v1/search?name={city_name}&count=1&language=en&format=json"
    try:
        data = requests.get(url, timeout=10).json()
        if "results" in data and len(data["results"]) > 0:
            r = data["results"][0]
            return {
                "lat": r["latitude"],
                "lon": r["longitude"],
                "name": r.get("name", city_name),
                "country": r.get("country_code", ""),
                "timezone": r.get("timezone", CONFIG.get("timezone", "Europe/Amsterdam"))
            }
    except Exception as e:
        print(f"Geocoding error: {e}")
    return None


# ---------- API 1: OpenWeatherMap ----------

def fetch_openweathermap(lat, lon, target_date):
    """Fetch hourly forecast from OpenWeatherMap (free tier: 5-day/3-hour)."""
    if not OPENWEATHER_API_KEY:
        print("⚠️  OPENWEATHER_API_KEY not set, skipping OWM")
        return []

    url = (
        f"https://api.openweathermap.org/data/2.5/forecast"
        f"?lat={lat}&lon={lon}&units=metric&appid={OPENWEATHER_API_KEY}"
    )
    try:
        data = requests.get(url, timeout=15).json()
    except Exception as e:
        print(f"OWM request error: {e}")
        return []

    if "list" not in data:
        print(f"OWM API error: {data.get('message', 'unknown')}")
        return []

    hourly = []
    for item in data["list"]:
        dt = datetime.fromtimestamp(item["dt"], tz=TIMEZONE)
        if dt.date() != target_date:
            continue
        if not (FORECAST_START <= dt.hour <= FORECAST_END):
            continue

        hourly.append({
            "source": "openweathermap",
            "datetime": dt.isoformat(),
            "hour": dt.hour,
            "temp_c": item["main"]["temp"],
            "feels_like_c": item["main"]["feels_like"],
            "humidity_pct": item["main"]["humidity"],
            "wind_speed_kmh": round(item["wind"]["speed"] * 3.6, 1),
            "wind_gust_kmh": round(item["wind"].get("gust", item["wind"]["speed"]) * 3.6, 1),
            "wind_deg": item["wind"].get("deg", 0),
            "rain_prob_pct": round(item.get("pop", 0) * 100),
            "weather_main": item["weather"][0]["main"] if item.get("weather") else "",
            "weather_desc": item["weather"][0]["description"] if item.get("weather") else "",
            "uv_index": None  # Not available in free OWM tier
        })

    return hourly


# ---------- API 2: WeatherAPI ----------

def fetch_weatherapi(city_name, target_date):
    """Fetch hourly forecast from WeatherAPI (free tier: 3-day hourly)."""
    if not WEATHERAPI_API_KEY:
        print("⚠️  WEATHERAPI_API_KEY not set, skipping WeatherAPI")
        return []

    url = (
        f"http://api.weatherapi.com/v1/forecast.json"
        f"?key={WEATHERAPI_API_KEY}&q={city_name}&days=3&aqi=no&alerts=yes"
    )
    try:
        data = requests.get(url, timeout=15).json()
    except Exception as e:
        print(f"WeatherAPI request error: {e}")
        return []

    if "forecast" not in data:
        print(f"WeatherAPI error: {data.get('error', {}).get('message', 'unknown')}")
        return []

    hourly = []
    for day in data["forecast"]["forecastday"]:
        if day["date"] != target_date.isoformat():
            continue
        for h in day["hour"]:
            dt = datetime.strptime(h["time"], "%Y-%m-%d %H:%M")
            if not (FORECAST_START <= dt.hour <= FORECAST_END):
                continue

            hourly.append({
                "source": "weatherapi",
                "datetime": dt.replace(tzinfo=TIMEZONE).isoformat(),
                "hour": dt.hour,
                "temp_c": h["temp_c"],
                "feels_like_c": h["feelslike_c"],
                "humidity_pct": h["humidity"],
                "wind_speed_kmh": h["wind_kph"],
                "wind_gust_kmh": h.get("gust_kph", h["wind_kph"]),
                "wind_deg": h.get("wind_degree", 0),
                "rain_prob_pct": h.get("chance_of_rain", 0),
                "weather_main": h["condition"]["text"],
                "weather_desc": h["condition"]["text"],
                "uv_index": h.get("uv", None)
            })

    return hourly


# ---------- API 3: Open-Meteo (FREE, no key) ----------

def fetch_open_meteo(lat, lon, target_date, timezone_str):
    """Fetch hourly forecast from Open-Meteo (completely free, no API key)."""
    date_str = target_date.isoformat()
    url = (
        f"https://api.open-meteo.com/v1/forecast"
        f"?latitude={lat}&longitude={lon}"
        f"&hourly=temperature_2m,relative_humidity_2m,apparent_temperature,"
        f"precipitation_probability,wind_speed_10m,wind_gusts_10m,"
        f"wind_direction_10m,uv_index,weathercode"
        f"&timezone={timezone_str}"
        f"&start_date={date_str}&end_date={date_str}"
    )
    try:
        data = requests.get(url, timeout=15).json()
    except Exception as e:
        print(f"Open-Meteo request error: {e}")
        return []

    if "hourly" not in data:
        print(f"Open-Meteo error: {data.get('reason', 'unknown')}")
        return []

    h = data["hourly"]
    hourly = []
    for i, time_str in enumerate(h["time"]):
        dt = datetime.strptime(time_str, "%Y-%m-%dT%H:%M")
        if not (FORECAST_START <= dt.hour <= FORECAST_END):
            continue

        wmo_code = h["weathercode"][i] if h.get("weathercode") else 0
        weather_main = _wmo_to_description(wmo_code)

        hourly.append({
            "source": "open_meteo",
            "datetime": dt.replace(tzinfo=TIMEZONE).isoformat(),
            "hour": dt.hour,
            "temp_c": h["temperature_2m"][i],
            "feels_like_c": h["apparent_temperature"][i],
            "humidity_pct": h["relative_humidity_2m"][i],
            "wind_speed_kmh": h["wind_speed_10m"][i],
            "wind_gust_kmh": h["wind_gusts_10m"][i] if h.get("wind_gusts_10m") else None,
            "wind_deg": h["wind_direction_10m"][i] if h.get("wind_direction_10m") else 0,
            "rain_prob_pct": h["precipitation_probability"][i] if h.get("precipitation_probability") else 0,
            "weather_main": weather_main,
            "weather_desc": weather_main,
            "uv_index": h["uv_index"][i] if h.get("uv_index") else None
        })

    return hourly


def _wmo_to_description(code):
    """Convert WMO weather code to human-readable description."""
    mapping = {
        0: "Clear sky", 1: "Mainly clear", 2: "Partly cloudy", 3: "Overcast",
        45: "Fog", 48: "Rime fog",
        51: "Light drizzle", 53: "Moderate drizzle", 55: "Dense drizzle",
        56: "Freezing drizzle", 57: "Dense freezing drizzle",
        61: "Slight rain", 63: "Moderate rain", 65: "Heavy rain",
        66: "Freezing rain", 67: "Heavy freezing rain",
        71: "Slight snow", 73: "Moderate snow", 75: "Heavy snow", 77: "Snow grains",
        80: "Slight showers", 81: "Moderate showers", 82: "Violent showers",
        85: "Slight snow showers", 86: "Heavy snow showers",
        95: "Thunderstorm", 96: "Thunderstorm with hail", 99: "Thunderstorm with heavy hail"
    }
    return mapping.get(code, f"Unknown ({code})")


# ---------- Combine & average ----------

def compute_consensus(all_sources):
    """
    Group by hour, compute averaged/consensus values across sources.
    Returns a list of hourly consensus dicts.
    """
    by_hour = {}
    for entry in all_sources:
        hr = entry["hour"]
        if hr not in by_hour:
            by_hour[hr] = []
        by_hour[hr].append(entry)

    consensus = []
    for hr in sorted(by_hour.keys()):
        entries = by_hour[hr]
        n = len(entries)

        def avg(field):
            vals = [e[field] for e in entries if e.get(field) is not None]
            return round(sum(vals) / len(vals), 1) if vals else None

        def any_match(field, keywords):
            for e in entries:
                val = (e.get(field) or "").lower()
                if any(k in val for k in keywords):
                    return True
            return False

        consensus.append({
            "hour": hr,
            "temp_c": avg("temp_c"),
            "feels_like_c": avg("feels_like_c"),
            "humidity_pct": avg("humidity_pct"),
            "wind_speed_kmh": avg("wind_speed_kmh"),
            "wind_gust_kmh": avg("wind_gust_kmh"),
            "wind_deg": avg("wind_deg"),
            "rain_prob_pct": avg("rain_prob_pct"),
            "uv_index": avg("uv_index"),
            "thunderstorm_risk": any_match("weather_main", ["thunder", "storm"]),
            "sources": n,
            "source_details": entries
        })

    return consensus


# ---------- Main ----------

def fetch_sport_weather(city_name=None, target_date=None):
    """
    Main entry point. Fetches from all three APIs, merges, and saves.
    Returns the full data dict.
    """
    city_name = city_name or CONFIG["default_city"]
    if target_date is None:
        target_date = (datetime.now(TIMEZONE) + timedelta(days=1)).date()

    print(f"📡 Fetching sport weather for {city_name} on {target_date}...")

    # Geocode
    geo = get_coordinates(city_name)
    if not geo:
        print(f"❌ Could not geocode '{city_name}'")
        return None

    lat, lon = geo["lat"], geo["lon"]
    tz_str = geo.get("timezone", CONFIG.get("timezone", "Europe/Amsterdam"))
    print(f"📍 {geo['name']} ({geo['country']}) — {lat:.4f}, {lon:.4f}")

    # Fetch from all three sources
    owm_data = fetch_openweathermap(lat, lon, target_date)
    wapi_data = fetch_weatherapi(city_name, target_date)
    meteo_data = fetch_open_meteo(lat, lon, target_date, tz_str)

    all_data = owm_data + wapi_data + meteo_data
    sources_ok = []
    if owm_data:
        sources_ok.append("openweathermap")
    if wapi_data:
        sources_ok.append("weatherapi")
    if meteo_data:
        sources_ok.append("open_meteo")

    print(f"✅ Sources retrieved: {', '.join(sources_ok)} ({len(all_data)} total data points)")

    if not all_data:
        print("❌ No weather data retrieved from any source.")
        return None

    # Compute consensus
    consensus = compute_consensus(all_data)

    # Build summary stats
    temps = [h["temp_c"] for h in consensus if h["temp_c"] is not None]
    winds = [h["wind_speed_kmh"] for h in consensus if h["wind_speed_kmh"] is not None]
    rains = [h["rain_prob_pct"] for h in consensus if h["rain_prob_pct"] is not None]

    output = {
        "city": geo["name"],
        "country": geo["country"],
        "lat": lat,
        "lon": lon,
        "date": target_date.isoformat(),
        "fetched_at": datetime.now(TIMEZONE).isoformat(),
        "sources": sources_ok,
        "summary": {
            "temp_avg": round(sum(temps) / len(temps), 1) if temps else None,
            "temp_high": max(temps) if temps else None,
            "temp_low": min(temps) if temps else None,
            "wind_avg_kmh": round(sum(winds) / len(winds), 1) if winds else None,
            "wind_max_kmh": max(winds) if winds else None,
            "rain_avg_pct": round(sum(rains) / len(rains)) if rains else None,
            "rain_max_pct": max(rains) if rains else None,
        },
        "hourly_consensus": consensus,
        "raw_sources": {
            "openweathermap": owm_data,
            "weatherapi": wapi_data,
            "open_meteo": meteo_data
        }
    }

    # Save to docs/
    os.makedirs("docs", exist_ok=True)
    safe_city = city_name.lower().replace(" ", "_")
    filepath = f"docs/{safe_city}_sport_weather.json"
    with open(filepath, "w") as f:
        json.dump(output, f, indent=2, default=str)
    print(f"💾 Saved to {filepath}")

    return output


if __name__ == "__main__":
    city = sys.argv[1] if len(sys.argv) > 1 else None
    fetch_sport_weather(city)
