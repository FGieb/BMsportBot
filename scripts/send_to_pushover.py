import os
import json
import requests
from datetime import datetime
from dotenv import load_dotenv

# --- Load environment variables ---
load_dotenv("weather.env")
PUSHOVER_TOKEN = os.getenv("PUSHOVER_TOKEN")
PUSHOVER_USER = os.getenv("PUSHOVER_USER")

# --- Config ---
CITIES = ["Paris", "Brussels"]
ALIGNMENT_EMOJIS = {
    "full": "✅",
    "partial": "⚠️",
    "divergent": "❌",
    "unknown": "ℹ️"
}

def send_pushover_message(city, forecast):
    summary = forecast.get("summary", "")
    gpt_comment = forecast.get("gpt_comment", "(No GPT comment available)")
    alignment = forecast.get("alignment", "unknown")
    graph_file = forecast.get("graph_file")

    emoji = ALIGNMENT_EMOJIS.get(alignment, "ℹ️")
    today = datetime.now().strftime("%b %d")
    title = f"{emoji} {city} Forecast – {today}"

    message = f"""{summary}

🤖 GPT: {gpt_comment}

📊 Chart attached."""

    # Prepare payload
    payload = {
        "token": PUSHOVER_TOKEN,
        "user": PUSHOVER_USER,
        "title": title,
        "message": message
    }

    # Attach PNG chart
    files = {
        "attachment": (os.path.basename(graph_file), open(graph_file, "rb"), "image/png")
    }

    print(f"\nSending notification for {city}...")
    response = requests.post("https://api.pushover.net/1/messages.json", data=payload, files=files)

    if response.status_code == 200:
        print(f"✅ Notification sent for {city}.")
    else:
        print(f"❌ Failed to send for {city}: {response.text}")


def main():
    for city in CITIES:
        try:
            with open(f"docs/{city.lower()}_forecast.json") as f:
                forecast = json.load(f)
            send_pushover_message(city, forecast)
        except Exception as e:
            print(f"❌ Error processing {city}: {e}")


if __name__ == "__main__":
    main()
