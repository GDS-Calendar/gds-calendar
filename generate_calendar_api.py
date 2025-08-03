#!/usr/bin/env python3
"""
iiQ API Calendar Generator for GDS
Fetches events from iiQ API and generates ICS file
"""

import os
import json
import requests
from datetime import datetime, timezone
from ics import Calendar, Event
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
    page_size = 100
    page_number = 0
    
    while True:
        print(f"Fetching page {page_number}...")
        # Prepare request body with pagination
        data = {
            "FilterByProduct": True,
            "RequestOptions": {
                "Paging": {
                    "PageSize": page_size,
                    "PageNumber": page_number
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
                break
                
            # Filter for approved events
            for event in result['Items']:
                event_status = event.get('EventStatus', {})
                status_name = event_status.get('Name', 'No Status')
                
                # Just check if event is approved
                if status_name == 'Approved':
                    all_events.append(event)
                    
                    # Debug: print first few events to see CustomFieldValues
                    if len(all_events) <= 3:
                        print(f"\nEvent: {event.get('Title', 'Untitled')}")
                        print(f"Status: {status_name}")
                        custom_fields = event.get('CustomFieldValues', [])
                        for cf in custom_fields:
                            print(f"  CustomField {cf.get('CustomFieldTypeId', 'Unknown')}: {cf.get('Value', 'No value')}")
                        print("---")
            
            # Check if we have more pages
            if len(result['Items']) < page_size:
                break
                
            page_number += 1
            
            # Stop after first page for now to debug
            if page_number >= 1:
                print(f"\nStopping after first page. Found {len(all_events)} approved events")
                break
            
        except requests.exceptions.RequestException as e:
            print(f"Error fetching events: {e}")
            break
    
    return all_events

def create_ics_from_events(events):
    """Convert iiQ events to ICS format"""
    
    calendar = Calendar()
    eastern = pytz.timezone('America/New_York')
    
    for event_data in events:
        try:
            event = Event()
            
            # Basic event info
            event.name = event_data.get('Title', 'Untitled Event')
            
            # Description - this is what we were missing before!
            description = event_data.get('Description', '')
            if description:
                event.description = description
            
            # Times
            start_str = event_data.get('StartDateTime')
            end_str = event_data.get('EndDateTime')
            
            if start_str and end_str:
                # Parse the datetime strings
                start_dt = datetime.fromisoformat(start_str.replace('Z', '+00:00'))
                end_dt = datetime.fromisoformat(end_str.replace('Z', '+00:00'))
                
                # Convert to Eastern time
                event.begin = start_dt.astimezone(eastern)
                event.end = end_dt.astimezone(eastern)
            
            # Location
            location_parts = []
            
            # Add location name
            location = event_data.get('Location', {})
            if location and location.get('Name'):
                location_parts.append(location['Name'])
            
            # Add room info if available
            location_rooms = event_data.get('LocationRooms', [])
            if location_rooms:
                room_names = [room.get('Name', '') for room in location_rooms if room.get('Name')]
                if room_names:
                    location_parts.append(', '.join(room_names))
            
            if location_parts:
                event.location = ' - '.join(location_parts)
            
            # Organizer
            owner = event_data.get('Owner', {})
            if owner:
                organizer_name = f"{owner.get('FirstName', '')} {owner.get('LastName', '')}".strip()
                organizer_email = owner.get('Email', '')
                if organizer_email:
                    event.organizer = f"{organizer_name} <{organizer_email}>"
            
            # Add UID for better compatibility
            event_id = event_data.get('EventId', '')
            if event_id:
                event.uid = f"{event_id}@gds.incidentiq.com"
            
            calendar.events.add(event)
            
        except Exception as e:
            print(f"Error processing event {event_data.get('Title', 'Unknown')}: {e}")
            continue
    
    return calendar

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
        calendar = create_ics_from_events(events)
        
        # Write ICS file
        with open('school_events.ics', 'w') as f:
            f.write(str(calendar))
        
        print("Successfully created school_events.ics")
        
        # Also save events as JSON for the web display
        with open('events.json', 'w') as f:
            json.dump(events, f, indent=2)
        
        print("Successfully created events.json for web display")
    else:
        print("No events found")
        # Create empty files
        Calendar().events.clear()
        with open('school_events.ics', 'w') as f:
            f.write(str(Calendar()))
        with open('events.json', 'w') as f:
            json.dump([], f)

if __name__ == "__main__":
    main()