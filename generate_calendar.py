from playwright.sync_api import sync_playwright
from ics import Calendar, Event
from bs4 import BeautifulSoup
from datetime import datetime
import pytz
import json

# 🌎 Set your timezone here (the one used in the HTML calendar, not your local machine)
SOURCE_TIMEZONE = pytz.timezone('America/New_York')

# 📍 Replace with your actual calendar page URL
CALENDAR_URL = "https://gdsorg-5045-us-east1-01.preview.finalsitecdn.com/calendar-test"

print("🚀 Launching headless browser...")

with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page()
    print("🌐 Navigating to calendar page...")
    page.goto(CALENDAR_URL)

    print("🕵️‍♂️ Waiting for #eventData element...")
    page.wait_for_selector("input#eventData", timeout=15000, state="attached")

    content = page.content()
    browser.close()

# 🧠 Parse the event data
soup = BeautifulSoup(content, "html.parser")
event_data_input = soup.find("input", {"id": "eventData"})

if not event_data_input:
    raise Exception("❌ Could not find input#eventData on page")

event_list = json.loads(event_data_input["value"])

calendar = Calendar()

for event in event_list:
    try:
        e = Event()
        e.name = event["title"]

        start_time = SOURCE_TIMEZONE.localize(datetime.fromisoformat(event["start"]))
        end_time = SOURCE_TIMEZONE.localize(datetime.fromisoformat(event["end"]))

        e.begin = start_time
        e.end = end_time

        e.location = event.get("location", "")
        e.description = event.get("description", "")

        calendar.events.add(e)
    except Exception as err:
        print(f"⚠️ Skipping event due to error: {err}")

# 💾 Write to .ics file
with open("school_events.ics", "w") as f:
    f.writelines(calendar)

print("✅ Calendar exported to school_events.ics")
