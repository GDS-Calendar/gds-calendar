#!/usr/bin/env python3
"""
iiQ API Calendar Generator for GDS
Fetches events from iiQ API and generates ICS file
"""

import os
import json
import requests
from datetime import datetime
import pytz

# Configuration
API_TOKEN = os.environ.get('IIQ_API_TOKEN')
SITE_ID = "d3b75b85-9241-49ba-88c3-3c9b7f0d3269"
API_BASE_URL = "https://gds.incidentiq.com/api/v1.0"

def fetch_all_events():
    """Fetch all approved, non-hidden events from iiQ API"""
    
    headers = {
        'accept': 'application/json, text/plain, */*',
        'content-type': 'application/json',
        'siteid': SITE_ID,
        'client': 'ApiClient',
        'Authorization': f'Bearer {API_TOKEN}'
    }
    
    all_events = []
    seen_events = set()  # Track unique events by title+date
    page_size = 2000  # Increased to get more events in one request
    approved_count = 0
    published_count = 0
    duplicate_count = 0
    
    print(f"Fetching events with page size {page_size}...")
    
    # Since pagination is broken, just get one large page
    data = {
        "FilterByProduct": True,
        "RequestOptions": {
            "Paging": {
                "PageSize": page_size,
                "PageNumber": 0
            }
        }
    }
    
    try:
        response = requests.post(
            f"{API_BASE_URL}/events/query",
            headers=headers,
            json=data
        )
        response.raise_for_status()
        
        result = response.json()
        
        # Check if we have items
        if 'Items' not in result or not result['Items']:
            print(f"No items found.")
            return []
            
        print(f"Received {len(result['Items'])} events from API")
        
        # Filter for approved events with "Publish to Calendar" = yes
        for event in result['Items']:
            event_status = event.get('EventStatus', {})
            status_name = event_status.get('Name', 'No Status')
            event_id = str(event.get('EventId', ''))
            event_title = event.get('Title', '')
            
            # Check if event is approved
            if status_name == 'Approved':
                approved_count += 1
                
                # Check if "Publish to Calendar" is "yes"
                publish_to_calendar = False
                custom_fields = event.get('CustomFieldValues', [])
                
                for cf in custom_fields:
                    if cf.get('CustomFieldTypeId') == 'e3d6a181-2165-44e1-9a56-5fabcf87fea4':
                        if cf.get('Value', '').lower() == 'yes':
                            publish_to_calendar = True
                            break
                
                # Only add events that should be published to calendar
                if publish_to_calendar:
                    published_count += 1
                    
                    # Create unique key based on title and start time
                    event_key = f"{event.get('Title', '')}|{event.get('StartDateTime', '')}"
                    
                    # Only add if we haven't seen this exact event before
                    if event_key not in seen_events:
                        seen_events.add(event_key)
                        all_events.append(event)
                    else:
                        duplicate_count += 1
                        # Log first few duplicates to understand pattern
                        if duplicate_count <= 5:
                            print(f"  Duplicate found: {event.get('Title', '')} on {event.get('StartDateTime', '')}")
        
        # Process only one page since pagination is broken
        print(f"Processed {len(result.get('Items', []))} items, {len(all_events)} unique public events found")
        
    except requests.exceptions.RequestException as e:
        print(f"Error fetching events: {e}")
    
    print(f"\nSummary: {approved_count} approved events found, {published_count} marked for calendar, {duplicate_count} duplicates removed")
    return all_events

def escape_ics_text(text):
    """Escape text for ICS format"""
    if not text:
        return ""
    # Escape special characters
    text = text.replace('\\', '\\\\')
    text = text.replace('\n', '\\n')
    text = text.replace(',', '\\,')
    text = text.replace(';', '\\;')
    return text

def create_ics_manually(events):
    """Create ICS file manually to control timezone handling"""
    lines = []
    
    # Calendar header
    lines.append("BEGIN:VCALENDAR")
    lines.append("VERSION:2.0")
    lines.append("PRODID:-//Georgetown Day School//GDS Calendar//EN")
    lines.append("X-WR-CALNAME:GDS School Calendar")
    lines.append("X-WR-TIMEZONE:America/New_York")
    lines.append("CALSCALE:GREGORIAN")
    lines.append("METHOD:PUBLISH")
    
    # Add timezone definition
    lines.append("BEGIN:VTIMEZONE")
    lines.append("TZID:America/New_York")
    lines.append("BEGIN:STANDARD")
    lines.append("DTSTART:20071104T020000")
    lines.append("RRULE:FREQ=YEARLY;BYMONTH=11;BYDAY=1SU")
    lines.append("TZOFFSETFROM:-0400")
    lines.append("TZOFFSETTO:-0500")
    lines.append("TZNAME:EST")
    lines.append("END:STANDARD")
    lines.append("BEGIN:DAYLIGHT")
    lines.append("DTSTART:20070311T020000")
    lines.append("RRULE:FREQ=YEARLY;BYMONTH=3;BYDAY=2SU")
    lines.append("TZOFFSETFROM:-0500")
    lines.append("TZOFFSETTO:-0400")
    lines.append("TZNAME:EDT")
    lines.append("END:DAYLIGHT")
    lines.append("END:VTIMEZONE")
    
    # Add events
    for event_data in events:
        lines.append("BEGIN:VEVENT")
        
        # UID
        event_id = event_data.get('EventId', '')
        if event_id:
            lines.append(f"UID:{event_id}@gds.incidentiq.com")
        
        # Title
        title = escape_ics_text(event_data.get('Title', 'Untitled Event'))
        lines.append(f"SUMMARY:{title}")
        
        # Times - with explicit timezone
        start_str = event_data.get('StartDateTime', '').rstrip('Z')
        end_str = event_data.get('EndDateTime', '').rstrip('Z')
        
        if start_str and end_str:
            # Format: YYYYMMDDTHHMMSS
            start_dt = datetime.fromisoformat(start_str)
            end_dt = datetime.fromisoformat(end_str)
            
            start_formatted = start_dt.strftime('%Y%m%dT%H%M%S')
            end_formatted = end_dt.strftime('%Y%m%dT%H%M%S')
            
            # Use TZID to specify timezone
            lines.append(f"DTSTART;TZID=America/New_York:{start_formatted}")
            lines.append(f"DTEND;TZID=America/New_York:{end_formatted}")
        
        # Description
        description = event_data.get('Description', '')
        if description:
            desc_escaped = escape_ics_text(description)
            # Wrap long lines at 75 characters
            if len(desc_escaped) > 75:
                wrapped = []
                line = "DESCRIPTION:" + desc_escaped[:60]
                wrapped.append(line)
                remaining = desc_escaped[60:]
                while remaining:
                    line = " " + remaining[:74]  # Continuation lines start with space
                    wrapped.append(line)
                    remaining = remaining[74:]
                lines.extend(wrapped)
            else:
                lines.append(f"DESCRIPTION:{desc_escaped}")
        
        # Location
        location_parts = []
        location = event_data.get('Location', {})
        if location and location.get('Name'):
            location_parts.append(location['Name'])
        
        location_rooms = event_data.get('LocationRooms', [])
        if location_rooms:
            room_names = [room.get('Name', '') for room in location_rooms if room.get('Name')]
            if room_names:
                location_parts.append(', '.join(room_names))
        
        if location_parts:
            location_text = escape_ics_text(' - '.join(location_parts))
            lines.append(f"LOCATION:{location_text}")
        
        # Organizer
        owner = event_data.get('Owner', {})
        if owner:
            organizer_name = f"{owner.get('FirstName', '')} {owner.get('LastName', '')}".strip()
            organizer_email = owner.get('Email', '')
            if organizer_email and organizer_name:
                lines.append(f"ORGANIZER;CN={organizer_name}:mailto:{organizer_email}")
        
        lines.append("END:VEVENT")
    
    lines.append("END:VCALENDAR")
    
    return '\r\n'.join(lines)

def main():
    """Main function to fetch events and generate ICS file"""
    
    if not API_TOKEN:
        print("Error: IIQ_API_TOKEN environment variable not set")
        return
    
    print("Fetching events from iiQ API...")
    events = fetch_all_events()
    print(f"Found {len(events)} approved public events")
    
    if events:
        print("Creating ICS file...")
        
        # Create ICS content manually
        ics_content = create_ics_manually(events)
        
        # Write ICS file
        with open('school_events.ics', 'w') as f:
            f.write(ics_content)
        
        print("Successfully created school_events.ics")
        
        # Also save events as JSON for the web display
        with open('events.json', 'w') as f:
            json.dump(events, f, indent=2)
        
        print("Successfully created events.json for web display")
    else:
        print("No events found")
        # Create empty files
        with open('school_events.ics', 'w') as f:
            f.write("BEGIN:VCALENDAR\r\nVERSION:2.0\r\nPRODID:-//GDS//Calendar//EN\r\nEND:VCALENDAR")
        with open('events.json', 'w') as f:
            json.dump([], f)

if __name__ == "__main__":
    main()