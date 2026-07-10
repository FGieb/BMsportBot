import os
import json
import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from openai import OpenAI

# --- Load environment and initialize OpenAI client ---
load_dotenv("weather.env")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
client = OpenAI(api_key=OPENAI_API_KEY)

CITIES = ["Brussels", "Paris"]

def load_forecast(city):
    with open(f"docs/{city.lower()}_forecast.json") as f:
        return json.load(f)

# --- SCRAPERS ---

def scrape_forecast_yr(city):
    if city.lower() == "brussels":
        url = "https://www.yr.no/en/forecast/daily-table/2-2800866/Belgium/Brussels-Capital/Brussels"
    elif city.lower() == "paris":
        url = "https://www.yr.no/en/forecast/daily-table/2-2988507/France/Île-de-France/Paris"
    else:
        return "Unsupported city"
    try:
        response = requests.get(url)
        soup = BeautifulSoup(response.content, "html.parser")
        forecast_block = soup.find("table")
        return forecast_block.text.strip()[:1000] if forecast_block else "Could not extract data from YR.no"
    except Exception as e:
        return f"Error scraping YR.no: {e}"

def scrape_forecast_meteoblue(city):
    if city.lower() == "brussels":
        url = "https://www.meteoblue.com/en/weather/week/brussels_belgium_2800866"
    elif city.lower() == "paris":
        url = "https://www.meteoblue.com/en/weather/week/paris_france_2988507"
    else:
        return "Unsupported city"
    try:
        response = requests.get(url)
        soup = BeautifulSoup(response.content, "html.parser")
        text_block = soup.find("div", class_="tab-content")
        return text_block.text.strip()[:1000] if text_block else "Could not extract data from Meteoblue"
    except Exception as e:
        return f"Error scraping Meteoblue: {e}"

def scrape_forecast_meteo_france():
    url = "https://meteofrance.com/previsions-meteo-france/paris/75000"
    try:
        response = requests.get(url)
        soup = BeautifulSoup(response.content, "html.parser")
        div = soup.find("div", class_="day-summary")
        return div.text.strip()[:1000] if div else "Could not extract data from Météo France"
    except Exception as e:
        return f"Error scraping Météo France: {e}"

def scrape_forecast_meteo_belgique():
    url = "https://www.meteo.be/en"
    try:
        response = requests.get(url)
        soup = BeautifulSoup(response.content, "html.parser")
        div = soup.find("div", class_="daily-forecast")
        return div.text.strip()[:1000] if div else "Could not extract data from Météo Belgique"
    except Exception as e:
        return f"Error scraping Météo Belgique: {e}"

# --- GPT ANALYSIS ---

def analyze_with_chatgpt(city, summary, yr, meteoblue, meteo_local):
    prompt = f"""

You're a concise weather verifier. Analyze only 09:00–21:00 local time for {city}.

BASELINE (from OWM+WeatherAPI):
{summary}

OTHER SOURCES:
• YR.no: {yr}
• Meteoblue: {meteoblue}
• Local: {meteo_local}

Rules:
- Be concrete. Name the dissenting source(s) and the difference (°C delta, rain probability, and hours).
- If values aren't explicit, say "not stated".
- Consider "material" as: rain vs dry OR ≥3°C at peak OR rain prob difference ≥25pp in the same hours.
- Start with an alignment tag: [FULL], [PARTIAL], or ⚠️[DIVERGENT].
- Max 3 short sentences. 1st: quick verdict. 2nd: compact diffs like "Meteoblue: 40–60% rain 17–20h vs baseline dry; YR: +2–3°C 14–18h". 3rd: optional natural remark only if it truly fits.

Output only the three sentences—no lists, no bullets, no preamble.

Keep a neutral tone by default, but you may add a human remark if it fits organically based on what you would maybe say to a friend, for example based on the day of the week (e.g., “perfect for a café terrace” or “a classic spring day in {city}”). More specifically whenever there is a reason (do not force it) to include a reference to a monkey, donkey, haring, pig, hyena, gazella or bumblebee you can, but don't force it it needs to be natural.

"""

    response = client.chat.completions.create(
        model="gpt-4",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.7,
    )
    comment = response.choices[0].message.content.strip()
    comment_lower = comment.lower()

    if "⚠️" in comment or any(phrase in comment_lower for phrase in [
        "big mismatch", "major difference", "does not match", "conflict between sources", "no agreement"
    ]):
        alignment = "divergent"
    elif any(phrase in comment_lower for phrase in [
        "slightly off", "some sources", "partial alignment", "adds nuance", "not all sources agree",
        "mixed picture", "one source differs", "outlier"
    ]):
        alignment = "partial"
    elif any(phrase in comment_lower for phrase in [
        "all sources agree", "consistent across", "align well", "in line", "match", "fully agree", "no notable difference"
    ]):
        alignment = "full"
    else:
        alignment = "unknown"

    return comment, alignment

# --- MAIN ---

def main():
    for city in CITIES:
        try:
            forecast = load_forecast(city)
            summary = forecast.get("summary", "")

            yr = scrape_forecast_yr(city)
            meteoblue = scrape_forecast_meteoblue(city)
            meteo_local = scrape_forecast_meteo_france() if city.lower() == "paris" else scrape_forecast_meteo_belgique()

            gpt_comment, alignment = analyze_with_chatgpt(city, summary, yr, meteoblue, meteo_local)
            forecast["gpt_comment"] = gpt_comment
            forecast["alignment"] = alignment

            with open(f"docs/{city.lower()}_forecast.json", "w") as f:
                json.dump(forecast, f, indent=2)

            print(f"✅ Updated {city} forecast with GPT comment and alignment: {alignment.upper()}.")
        except Exception as e:
            print(f"❌ Error updating {city}: {e}")

if __name__ == "__main__":
    main()
