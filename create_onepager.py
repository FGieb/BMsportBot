"""
Creates a one-pager PDF for Britt & Martha explaining their Coach Sunny bot.
"""

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm, cm
from reportlab.lib.colors import HexColor, white, black
from reportlab.pdfgen import canvas
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import Paragraph
from reportlab.lib.enums import TA_LEFT, TA_CENTER

WIDTH, HEIGHT = A4  # 210 x 297 mm

# --- Colours ---
BG_DARK = HexColor("#0f172a")
CARD_BG = HexColor("#1e293b")
ACCENT = HexColor("#38bdf8")
GREEN = HexColor("#4ade80")
YELLOW = HexColor("#facc15")
TEXT_WHITE = HexColor("#e2e8f0")
TEXT_MUTED = HexColor("#94a3b8")
CORAL = HexColor("#f87171")
PURPLE = HexColor("#a78bfa")


def draw_rounded_rect(c, x, y, w, h, radius=8, fill_color=CARD_BG):
    """Draw a rounded rectangle."""
    c.setFillColor(fill_color)
    c.setStrokeColor(fill_color)
    c.roundRect(x, y, w, h, radius, fill=1, stroke=0)


def create_onepager(output_path="BMsportBot_Guide.pdf"):
    c = canvas.Canvas(output_path, pagesize=A4)
    c.setTitle("Coach Sunny — Your Sport Weather Bot")

    # --- Background ---
    c.setFillColor(BG_DARK)
    c.rect(0, 0, WIDTH, HEIGHT, fill=1, stroke=0)

    # --- Decorative accent bar at top ---
    c.setFillColor(ACCENT)
    c.rect(0, HEIGHT - 6*mm, WIDTH, 6*mm, fill=1, stroke=0)

    # --- Header ---
    y = HEIGHT - 22*mm
    c.setFillColor(TEXT_WHITE)
    c.setFont("Helvetica-Bold", 26)
    c.drawCentredString(WIDTH/2, y, "Coach Sunny")
    y -= 8*mm
    c.setFont("Helvetica", 11)
    c.setFillColor(ACCENT)
    c.drawCentredString(WIDTH/2, y, "Your personal sport weather coach")

    y -= 6*mm
    c.setFillColor(TEXT_MUTED)
    c.setFont("Helvetica-Oblique", 9)
    c.drawCentredString(WIDTH/2, y, "A wedding gift from Francien  \u2764")

    # --- What is it? ---
    y -= 14*mm
    card_x = 18*mm
    card_w = WIDTH - 36*mm
    card_h = 38*mm

    draw_rounded_rect(c, card_x, y - card_h + 6*mm, card_w, card_h)

    c.setFillColor(ACCENT)
    c.setFont("Helvetica-Bold", 13)
    c.drawString(card_x + 12*mm, y - 2*mm, "What is Coach Sunny?")

    c.setFillColor(TEXT_WHITE)
    c.setFont("Helvetica", 9.5)
    lines = [
        "Every morning at 07:30, Coach Sunny sends each of you a personal",
        "Telegram message about the weather for the day ahead \u2014 and whether",
        "it\u2019s a good day for running, cycling, or swimming.",
        "",
        "The messages are different for each of you. Sunny knows your favourite",
        "sports, checks three weather sources, and keeps it real \u2014 no fluff.",
    ]
    text_y = y - 12*mm
    for line in lines:
        c.drawString(card_x + 12*mm, text_y, line)
        text_y -= 4.2*mm

    # --- How the message looks ---
    y = text_y - 8*mm
    card_h = 43*mm
    draw_rounded_rect(c, card_x, y - card_h + 6*mm, card_w, card_h)

    c.setFillColor(ACCENT)
    c.setFont("Helvetica-Bold", 13)
    c.drawString(card_x + 12*mm, y - 2*mm, "What you\u2019ll see each morning")

    c.setFillColor(TEXT_WHITE)
    c.setFont("Helvetica", 9.5)
    desc = [
        "1.  A weather summary: temperature, wind, rain chance",
        "2.  Sport ratings:  \u2705 Great   \U0001f7e2 OK   \u26a0\ufe0f Caution   \u274c Avoid",
        "3.  The best time window to go out for each sport",
        "4.  A personal message from Sunny \u2014 just for you",
        "",
        "Tap the sport buttons under the message for detailed hourly",
        "breakdowns: temperature, wind, UV, rain chance per hour.",
    ]
    text_y = y - 12*mm
    for line in desc:
        c.drawString(card_x + 12*mm, text_y, line)
        text_y -= 4.2*mm

    # --- Commands ---
    y = text_y - 8*mm
    card_h = 55*mm
    draw_rounded_rect(c, card_x, y - card_h + 6*mm, card_w, card_h)

    c.setFillColor(ACCENT)
    c.setFont("Helvetica-Bold", 13)
    c.drawString(card_x + 12*mm, y - 2*mm, "Telegram Commands")

    commands = [
        ("/start", "Set up the bot and tell it who you are"),
        ("/weather", "Get today\u2019s sport weather overview"),
        ("/weather Lisbon", "One-off forecast for a different city"),
        ("/run", "Detailed running conditions with hourly breakdown"),
        ("/cycle", "Detailed cycling conditions"),
        ("/swim", "Detailed swimming conditions"),
        ("/city Amsterdam", "Change your default city permanently"),
        ("/help", "Show all available commands"),
    ]

    text_y = y - 13*mm
    for cmd, desc in commands:
        c.setFillColor(GREEN)
        c.setFont("Courier-Bold", 9)
        c.drawString(card_x + 12*mm, text_y, cmd)
        c.setFillColor(TEXT_MUTED)
        c.setFont("Helvetica", 8.5)
        c.drawString(card_x + 56*mm, text_y, desc)
        text_y -= 5*mm

    # --- Change City tip ---
    y = text_y - 6*mm
    card_h = 24*mm
    draw_rounded_rect(c, card_x, y - card_h + 6*mm, card_w, card_h, fill_color=HexColor("#1a2744"))

    c.setFillColor(YELLOW)
    c.setFont("Helvetica-Bold", 11)
    c.drawString(card_x + 12*mm, y - 2*mm, "\U0001f4cd Going on a trip?")

    c.setFillColor(TEXT_WHITE)
    c.setFont("Helvetica", 9.5)
    trip_lines = [
        "Type /city followed by any city name to change your location.",
        "Coach Sunny will send forecasts for that city from then on.",
        "Perfect for camper trips! Change it back anytime.",
    ]
    text_y = y - 12*mm
    for line in trip_lines:
        c.drawString(card_x + 12*mm, text_y, line)
        text_y -= 4.2*mm

    # --- Web page ---
    y = text_y - 6*mm
    card_h = 19*mm
    draw_rounded_rect(c, card_x, y - card_h + 6*mm, card_w, card_h)

    c.setFillColor(ACCENT)
    c.setFont("Helvetica-Bold", 11)
    c.drawString(card_x + 12*mm, y - 2*mm, "\U0001f310 Web Page")

    c.setFillColor(TEXT_WHITE)
    c.setFont("Helvetica", 9.5)
    c.drawString(card_x + 12*mm, y - 12*mm, "There\u2019s also a web page with expandable sport cards and hourly")
    c.drawString(card_x + 12*mm, y - 16.2*mm, "timelines. Bookmark it on your phone for a quick visual check.")

    # --- Footer ---
    c.setFillColor(TEXT_MUTED)
    c.setFont("Helvetica", 7.5)
    c.drawCentredString(WIDTH/2, 12*mm, "Data from OpenWeatherMap, WeatherAPI & Open-Meteo  \u00b7  Powered by Groq AI  \u00b7  Built with love by Francien")

    # Accent bar at bottom
    c.setFillColor(ACCENT)
    c.rect(0, 0, WIDTH, 3*mm, fill=1, stroke=0)

    c.save()
    print(f"Created {output_path}")
    return output_path


if __name__ == "__main__":
    create_onepager()
