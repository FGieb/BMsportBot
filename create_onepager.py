"""
Creates a one-pager PDF for Britt & Martha explaining their sport weather bot.
"""

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib.colors import HexColor
from reportlab.pdfgen import canvas

WIDTH, HEIGHT = A4

# --- Colours ---
BG_DARK = HexColor("#0f172a")
CARD_BG = HexColor("#1e293b")
ACCENT = HexColor("#38bdf8")
GREEN = HexColor("#4ade80")
YELLOW = HexColor("#facc15")
TEXT_WHITE = HexColor("#e2e8f0")
TEXT_MUTED = HexColor("#94a3b8")


def draw_rounded_rect(c, x, y, w, h, radius=8, fill_color=CARD_BG):
    c.setFillColor(fill_color)
    c.setStrokeColor(fill_color)
    c.roundRect(x, y, w, h, radius, fill=1, stroke=0)


def create_onepager(output_path="BMsportBot_Guide.pdf"):
    c = canvas.Canvas(output_path, pagesize=A4)
    c.setTitle("BM Sport Weather Bot")

    # Background
    c.setFillColor(BG_DARK)
    c.rect(0, 0, WIDTH, HEIGHT, fill=1, stroke=0)

    # Accent bar top
    c.setFillColor(ACCENT)
    c.rect(0, HEIGHT - 6*mm, WIDTH, 6*mm, fill=1, stroke=0)

    # Header
    y = HEIGHT - 22*mm
    c.setFillColor(TEXT_WHITE)
    c.setFont("Helvetica-Bold", 26)
    c.drawCentredString(WIDTH/2, y, "BM Sport Weather")
    y -= 7*mm
    c.setFont("Helvetica", 10)
    c.setFillColor(ACCENT)
    c.drawCentredString(WIDTH/2, y, "Your personal sport weather bot  \U0001f3c3\U0001f6b4\U0001f3ca")
    y -= 6*mm
    c.setFillColor(TEXT_MUTED)
    c.setFont("Helvetica-Oblique", 9)
    c.drawCentredString(WIDTH/2, y, "A wedding gift from Francien  \u2764")

    card_x = 18*mm
    card_w = WIDTH - 36*mm

    # --- What is it? ---
    y -= 13*mm
    card_h = 36*mm
    draw_rounded_rect(c, card_x, y - card_h + 6*mm, card_w, card_h)
    c.setFillColor(ACCENT)
    c.setFont("Helvetica-Bold", 12)
    c.drawString(card_x + 12*mm, y - 2*mm, "What is this?")
    c.setFillColor(TEXT_WHITE)
    c.setFont("Helvetica", 9.5)
    lines = [
        "Every morning at 07:30, the bot sends each of you a personal",
        "Telegram message with the weather forecast and whether it\u2019s a",
        "good day for running, cycling, or swimming.",
        "",
        "The messages are different for each of you \u2014 it knows your",
        "favourite sports and keeps it honest. No fluff.",
    ]
    text_y = y - 12*mm
    for line in lines:
        c.drawString(card_x + 12*mm, text_y, line)
        text_y -= 4*mm

    # --- What you see ---
    y = text_y - 7*mm
    card_h = 32*mm
    draw_rounded_rect(c, card_x, y - card_h + 6*mm, card_w, card_h)
    c.setFillColor(ACCENT)
    c.setFont("Helvetica-Bold", 12)
    c.drawString(card_x + 12*mm, y - 2*mm, "What you\u2019ll see")
    c.setFillColor(TEXT_WHITE)
    c.setFont("Helvetica", 9.5)
    desc = [
        "1.  Weather summary: temperature, wind, rain chance",
        "2.  Sport ratings:  \u2705 Great   \U0001f7e2 OK   \u26a0\ufe0f Caution   \u274c Avoid",
        "3.  Best time window for each sport",
        "4.  A personal message \u2014 just for you",
        "",
        "Tap the sport buttons for a detailed hourly breakdown.",
    ]
    text_y = y - 12*mm
    for line in desc:
        c.drawString(card_x + 12*mm, text_y, line)
        text_y -= 4*mm

    # --- Commands ---
    y = text_y - 7*mm
    card_h = 62*mm
    draw_rounded_rect(c, card_x, y - card_h + 6*mm, card_w, card_h)
    c.setFillColor(ACCENT)
    c.setFont("Helvetica-Bold", 12)
    c.drawString(card_x + 12*mm, y - 2*mm, "Commands")

    commands = [
        ("/start", "Set up the bot \u2014 tell it who you are"),
        ("/weather", "Today\u2019s sport weather overview"),
        ("/weather Lisbon", "One-off forecast for a different city"),
        ("/run", "Detailed running conditions (hourly)"),
        ("/cycle", "Detailed cycling conditions"),
        ("/swim", "Detailed swimming conditions"),
        ("/now", "Can I go right now? Quick check"),
        ("/city Amsterdam", "Change your default city"),
        ("/city reset", "Back to Utrecht"),
        ("/challenge", "Nudge your partner to go out \U0001f4aa"),
        ("/settings", "Show your current settings"),
    ]
    text_y = y - 13*mm
    for cmd, desc in commands:
        c.setFillColor(GREEN)
        c.setFont("Courier-Bold", 8.5)
        c.drawString(card_x + 12*mm, text_y, cmd)
        c.setFillColor(TEXT_MUTED)
        c.setFont("Helvetica", 8.5)
        c.drawString(card_x + 56*mm, text_y, desc)
        text_y -= 4.8*mm

    # --- City tip ---
    y = text_y - 5*mm
    card_h = 22*mm
    draw_rounded_rect(c, card_x, y - card_h + 6*mm, card_w, card_h, fill_color=HexColor("#1a2744"))
    c.setFillColor(YELLOW)
    c.setFont("Helvetica-Bold", 11)
    c.drawString(card_x + 12*mm, y - 2*mm, "\U0001f4cd Going on a trip?")
    c.setFillColor(TEXT_WHITE)
    c.setFont("Helvetica", 9.5)
    trip = [
        "Type /city followed by any city name. The bot immediately",
        "fetches the weather for that city and sends you forecasts",
        "from then on. Type /city reset to go back to Utrecht.",
    ]
    text_y = y - 12*mm
    for line in trip:
        c.drawString(card_x + 12*mm, text_y, line)
        text_y -= 4*mm

    # --- Challenge tip ---
    y = text_y - 5*mm
    card_h = 17*mm
    draw_rounded_rect(c, card_x, y - card_h + 6*mm, card_w, card_h, fill_color=HexColor("#1a2744"))
    c.setFillColor(YELLOW)
    c.setFont("Helvetica-Bold", 11)
    c.drawString(card_x + 12*mm, y - 2*mm, "\U0001f4aa Challenge mode")
    c.setFillColor(TEXT_WHITE)
    c.setFont("Helvetica", 9.5)
    c.drawString(card_x + 12*mm, y - 12*mm, "Type /challenge and the bot sends your partner a nudge")
    c.drawString(card_x + 12*mm, y - 16*mm, "to go out \u2014 with today\u2019s best sport suggestion.")

    # Footer
    c.setFillColor(TEXT_MUTED)
    c.setFont("Helvetica", 7.5)
    c.drawCentredString(WIDTH/2, 12*mm, "Data from OpenWeatherMap, WeatherAPI & Open-Meteo  \u00b7  Powered by Groq AI  \u00b7  Built with love by Francien")

    # Accent bar bottom
    c.setFillColor(ACCENT)
    c.rect(0, 0, WIDTH, 3*mm, fill=1, stroke=0)

    c.save()
    print(f"Created {output_path}")


if __name__ == "__main__":
    create_onepager()
