from playwright.sync_api import sync_playwright
from ics import Calendar, Event
from bs4 import BeautifulSoup
from datetime import datetime
import pytz
import json
import time

# 🌎 Set your timezone here (the one used in the HTML calendar, not your local machine)
SOURCE_TIMEZONE = pytz.timezone('America/New_York')

# 📍 Updated to production calendar URL
CALENDAR_URL = "https://www.gds.org/community/calendar"

print("🚀 Launching headless browser...")

with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page()
    
    print("🌐 Navigating to calendar page...")
    page.goto(CALENDAR_URL, wait_until="networkidle")
    
    # Wait a bit for any JavaScript to execute
    print("⏳ Waiting for page to fully load...")
    time.sleep(5)
    
    # Try multiple methods to find the element
    print("🕵️‍♂️ Looking for eventData element...")
    
    try:
        # Method 1: Direct selector
        element = page.query_selector("input#eventData")
        if element:
            print("✅ Found element with query_selector")
            event_data_value = element.get_attribute("value")
        else:
            # Method 2: Wait and retry
            print("🔄 Element not found, waiting longer...")
            page.wait_for_selector("input[id='eventData']", timeout=30000)
            element = page.query_selector("input#eventData")
            event_data_value = element.get_attribute("value")
    except Exception as e:
        print(f"❌ Failed to find element: {e}")
        # Let's see what's actually on the page
        print("📄 Page content preview:")
        print(page.content()[:1000])
        raise

    browser.close()

# Rest of your script remains the same...
print(f"📊 Found event data with {len(event_data_value)} characters")

event_list = json.loads(event_data_value)

# Debug: Let's see what fields are in the first event
if event_list:
    print("🔍 First event fields:", list(event_list[0].keys()))
    print("🔍 Sample event:", json.dumps(event_list[0], indent=2)[:500])

calendar = Calendar()
events_with_descriptions = 0

for event in event_list:
    try:
        e = Event()
        e.name = event["title"]

        start_time = SOURCE_TIMEZONE.localize(datetime.fromisoformat(event["start"]))
        end_time = SOURCE_TIMEZONE.localize(datetime.fromisoformat(event["end"]))

        e.begin = start_time
        e.end = end_time

        # Try to get location - might be in different fields
        location_parts = []
        if event.get("location"):
            location_parts.append(event["location"])
        if event.get("LocationName"):
            location_parts.append(event["LocationName"])
        e.location = ", ".join(location_parts) if location_parts else ""
        
        # Get description with capital D
        description = event.get("Description", "")
        if description:
            e.description = description
            events_with_descriptions += 1
            print(f"📝 Found description for '{event['title']}': {description[:50]}...")

        calendar.events.add(e)
    except Exception as err:
        print(f"⚠️ Skipping event due to error: {err}")

print(f"📊 Total events: {len(event_list)}, Events with descriptions: {events_with_descriptions}")

# 💾 Write to .ics file
with open("school_events.ics", "w") as f:
    f.writelines(calendar)

print("✅ Calendar exported to school_events.ics")

from datetime import datetime
print(f"🕒 Calendar generated at: {datetime.now()}")