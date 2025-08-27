#!/usr/bin/env python3
"""
iiQ API Email Generator for GDS - Facilities & Security
Fetches events from iiQ API and sends automated email via Gmail
"""

import os
import json
import requests
from datetime import datetime, timedelta
import pytz
import base64
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

# Configuration
API_TOKEN = os.environ.get('IIQ_API_TOKEN')
SITE_ID = "d3b75b85-9241-49ba-88c3-3c9b7f0d3269"
API_BASE_URL = "https://gds.incidentiq.com/api/v1.0"

# Email view specific configuration
VIEW_ID = "8028a2ba-887f-f011-b481-000d3ae39e88"
OUTPUT_JSON_FILE = "email_events.json"
OUTPUT_HTML_FILE = "facilities_security_email.html"

# Gmail configuration
SCOPES = ['https://www.googleapis.com/auth/gmail.send']
CREDENTIALS_FILE = 'credentials.json'
TOKEN_FILE = 'token.json'

# Email settings - UPDATE THESE WITH ACTUAL EMAIL ADDRESSES
FROM_EMAIL = os.environ.get('FROM_EMAIL', 'tlyons@gds.org')  # Your Gmail address
TO_EMAILS = [
    'tlyons@gds.org',  # Update with actual email addresses
   
]
CC_EMAILS = [
    'tlyons@gds.org'  # Your email for monitoring
]

def fetch_all_events():
    """Fetch all approved events from iiQ API"""
    
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
    duplicate_count = 0
    
    print(f"Fetching events from view {VIEW_ID} with page size {page_size}...")
    
    # Since pagination is broken, just get one large page
    data = {
        "FilterByProduct": True,
        "ViewId": VIEW_ID,
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
            print(f"No items found for view {VIEW_ID}.")
            return []
            
        print(f"Received {len(result['Items'])} events from API")
        
        # Filter for approved events (ALL approved events, no "Publish to Calendar" filter)
        for event in result['Items']:
            event_status = event.get('EventStatus', {})
            status_name = event_status.get('Name', 'No Status')
            
            # Check if event is approved
            if status_name == 'Approved':
                approved_count += 1
                
                # Include ALL approved events (no custom field filtering)
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
        
        print(f"Processed {len(result.get('Items', []))} items, {len(all_events)} unique approved events found")
        
    except requests.exceptions.RequestException as e:
        print(f"Error fetching events: {e}")
    
    print(f"\nSummary: {approved_count} approved events found, {duplicate_count} duplicates removed")
    return all_events

def filter_events_for_email(events):
    """Filter events for the next 14 days"""
    
    # Get current date and 14 days ahead
    today = datetime.now()
    two_weeks = today + timedelta(days=14)
    
    relevant_events = []
    
    print(f"Filtering for events between {today.strftime('%Y-%m-%d')} and {two_weeks.strftime('%Y-%m-%d')}")
    
    for event in events:
        start_str = event.get('StartDateTime', '').rstrip('Z')
        if not start_str:
            continue
            
        try:
            start_dt = datetime.fromisoformat(start_str)
            
            # Filter for events in next 14 days
            if today <= start_dt <= two_weeks:
                relevant_events.append(event)
                
        except ValueError:
            print(f"Could not parse date: {start_str}")
            continue
    
    # Sort by start time
    relevant_events.sort(key=lambda x: x.get('StartDateTime', ''))
    
    return relevant_events

def generate_email_html(events):
    """Generate compact, professional HTML email content with GDS branding"""
    
    today = datetime.now()
    two_weeks = today + timedelta(days=14)
    
    # Compact, professional styling with GDS colors
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <title>GDS Facilities & Security - Event Summary</title>
        <style>
            body {{ 
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; 
                margin: 0; 
                padding: 0; 
                background-color: #f8f9fa;
                font-size: 13px;
                line-height: 1.3;
            }}
            .container {{ 
                max-width: 700px; 
                margin: 0 auto; 
                background-color: white;
            }}
            .header {{ 
                background: linear-gradient(135deg, #2E7D32, #4CAF50); 
                color: white; 
                padding: 15px 20px;
                position: relative;
            }}
            .header-logo {{
                display: flex;
                align-items: center;
                gap: 12px;
            }}
            .gds-logo {{
                width: 45px;
                height: 45px;
                background: white;
                border-radius: 50%;
                display: flex;
                align-items: center;
                justify-content: center;
                font-weight: bold;
                color: #2E7D32;
                font-size: 16px;
            }}
            .header h1 {{ 
                margin: 0; 
                font-size: 18px; 
                font-weight: 600;
            }}
            .header .subtitle {{ 
                margin: 2px 0 0 0; 
                opacity: 0.9; 
                font-size: 11px;
                font-weight: normal;
            }}
            .summary {{ 
                background-color: #E8F5E8; 
                padding: 12px 20px; 
                border-left: 4px solid #2E7D32;
                margin: 0;
            }}
            .summary h3 {{ 
                margin: 0 0 5px 0; 
                color: #2E7D32; 
                font-size: 14px;
            }}
            .summary p {{ 
                margin: 3px 0; 
                font-size: 12px;
            }}
            .events-container {{
                padding: 15px 20px;
            }}
            .event {{ 
                border-left: 3px solid #2E7D32;
                margin: 8px 0; 
                padding: 8px 0 8px 12px; 
                background-color: #fafafa;
                border-radius: 0 3px 3px 0;
            }}
            .event-header {{
                display: flex;
                justify-content: space-between;
                align-items: flex-start;
                margin-bottom: 4px;
            }}
            .event-title {{ 
                font-weight: 600; 
                font-size: 14px; 
                color: #1B5E20; 
                flex: 1;
                margin-right: 10px;
            }}
            .event-number {{
                background-color: #2E7D32;
                color: white;
                padding: 2px 6px;
                border-radius: 10px;
                font-size: 10px;
                font-weight: bold;
                min-width: 20px;
                text-align: center;
            }}
            .event-details {{ 
                margin: 2px 0;
                font-size: 12px;
                color: #424242;
            }}
            .event-details strong {{
                color: #2E7D32;
                font-weight: 600;
            }}
            .description {{ 
                margin-top: 6px; 
                padding: 6px 8px;
                background-color: white;
                border-radius: 3px;
                font-size: 11px;
                color: #555;
                border-left: 2px solid #4CAF50;
            }}
            .no-events {{ 
                text-align: center; 
                padding: 30px 20px; 
                color: #666; 
                font-style: italic;
            }}
            .footer {{
                background-color: #f0f0f0;
                padding: 12px 20px;
                text-align: center;
                color: #666;
                font-size: 10px;
                border-top: 1px solid #ddd;
            }}
            .action-items {{
                background-color: #FFF3E0;
                border-left: 4px solid #FF9800;
                padding: 10px 15px;
                margin: 15px 0;
            }}
            .action-items h4 {{
                margin: 0 0 5px 0;
                color: #E65100;
                font-size: 13px;
            }}
            .action-items ul {{
                margin: 5px 0;
                padding-left: 15px;
                font-size: 11px;
                line-height: 1.4;
            }}
            .action-items li {{
                margin: 2px 0;
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <div class="header-logo">
                    <div class="gds-logo">GDS</div>
                    <div>
                        <h1>Facilities & Security Event Summary</h1>
                        <div class="subtitle">Generated {today.strftime('%m/%d/%Y')} • Events {today.strftime('%m/%d')} - {two_weeks.strftime('%m/%d/%Y')}</div>
                    </div>
                </div>
            </div>
            
            <div class="summary">
                <h3>{len(events)} Events Requiring Attention</h3>
                <p>Next 14 days • All approved events • Review for setup, access, and security needs</p>
            </div>
            
            <div class="events-container">
    """
    
    if not events:
        html_content += """
                <div class="no-events">
                    <h3>No Events Scheduled</h3>
                    <p>No approved events requiring facilities/security attention in the next 14 days.</p>
                </div>
        """
    else:
        for i, event in enumerate(events, 1):
            title = event.get('Title', 'Untitled Event')
            start_str = event.get('StartDateTime', '').rstrip('Z')
            description = event.get('Description', '')
            
            # Format date/time - more compact
            if start_str:
                try:
                    start_dt = datetime.fromisoformat(start_str)
                    # Compact date format
                    formatted_date = start_dt.strftime('%a %m/%d')
                    formatted_time = start_dt.strftime('%I:%M%p').lower()
                    date_time = f"{formatted_date} at {formatted_time}"
                except ValueError:
                    date_time = "Date TBD"
            else:
                date_time = "Date TBD"
            
            # Format location - more compact
            location_parts = []
            location = event.get('Location', {})
            if location and location.get('Name'):
                location_parts.append(location['Name'])
            
            location_rooms = event.get('LocationRooms', [])
            if location_rooms:
                room_names = [room.get('Name', '') for room in location_rooms if room.get('Name')]
                if room_names:
                    location_parts.append(', '.join(room_names))
            
            location_text = ' - '.join(location_parts) if location_parts else 'Location TBD'
            
            # Format organizer - more compact
            owner = event.get('Owner', {})
            organizer = f"{owner.get('FirstName', '')} {owner.get('LastName', '')}".strip()
            organizer_email = owner.get('Email', '')
            
            html_content += f"""
                <div class="event">
                    <div class="event-header">
                        <div class="event-title">{title}</div>
                        <div class="event-number">{i}</div>
                    </div>
                    <div class="event-details"><strong>When:</strong> {date_time}</div>
                    <div class="event-details"><strong>Where:</strong> {location_text}</div>
            """
            
            if organizer:
                contact_info = organizer
                if organizer_email:
                    contact_info += f" ({organizer_email})"
                html_content += f'<div class="event-details"><strong>Contact:</strong> {contact_info}</div>'
            
            if description and description.strip():
                # Show full description
                html_content += f'<div class="description">{description}</div>'
            
            html_content += "</div>"
    
    html_content += f"""
            </div>
            
            <div class="action-items">
                <h4>Action Items</h4>
                <ul>
                    <li><strong>Review</strong> each event for setup requirements and equipment needs</li>
                    <li><strong>Coordinate</strong> with organizers for building access and security</li>
                    <li><strong>Schedule</strong> any preparations at least 24 hours in advance</li>
                    <li><strong>Contact</strong> organizers directly for questions or changes</li>
                </ul>
            </div>
            
            <div class="footer">
                <p>Automated bi-weekly report • Generated from iiQ • Questions: Natalie Markley</p>
            </div>
        </div>
    </body>
    </html>
    """
    
    return html_content

def authenticate_gmail():
    """Authenticate and return Gmail service"""
    creds = None
    
    # Load existing token
    if os.path.exists(TOKEN_FILE):
        creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)
    
    # If no valid credentials, get new ones
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not os.path.exists(CREDENTIALS_FILE):
                print(f"Error: {CREDENTIALS_FILE} not found. Please download from Google Cloud Console.")
                return None
            
            flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_FILE, SCOPES)
            creds = flow.run_local_server(port=0)
        
        # Save credentials for next run
        with open(TOKEN_FILE, 'w') as token:
            token.write(creds.to_json())
    
    return build('gmail', 'v1', credentials=creds)

def send_email(service, html_content, events_count):
    """Send the email via Gmail API"""
    
    today = datetime.now()
    two_weeks = today + timedelta(days=14)
    
    # Create message
    message = MIMEMultipart('alternative')
    message['to'] = ', '.join(TO_EMAILS)
    if CC_EMAILS:
        message['cc'] = ', '.join(CC_EMAILS)
    message['from'] = FROM_EMAIL
    message['subject'] = f"GDS Facilities & Security: {events_count} Events - {today.strftime('%b %d')} to {two_weeks.strftime('%b %d, %Y')}"
    
    # Create plain text version (fallback)
    text_content = f"""
GDS Facilities & Security - Bi-weekly Event Summary

Generated on {today.strftime('%A, %B %d, %Y at %I:%M %p')}
Covering events from {today.strftime('%B %d')} to {two_weeks.strftime('%B %d, %Y')}

{events_count} approved events requiring facilities/security attention in the next 14 days.

Please see the HTML version of this email for full event details.

For questions, contact or Natalie Markley.
    """
    
    # Attach both versions
    text_part = MIMEText(text_content, 'plain')
    html_part = MIMEText(html_content, 'html')
    
    message.attach(text_part)
    message.attach(html_part)
    
    # Send the message
    try:
        raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode()
        send_message = service.users().messages().send(
            userId="me", 
            body={'raw': raw_message}
        ).execute()
        
        print(f"Email sent successfully! Message ID: {send_message['id']}")
        return True
        
    except Exception as error:
        print(f"Error sending email: {error}")
        return False

def main():
    """Main function to fetch events and send email"""
    
    if not API_TOKEN:
        print("Error: IIQ_API_TOKEN environment variable not set")
        return
    
    print("Fetching events from iiQ API for facilities/security email...")
    
    # Fetch all approved events
    all_events = fetch_all_events()
    print(f"Found {len(all_events)} total approved events")
    
    # Filter for events in next 14 days
    email_events = filter_events_for_email(all_events)
    print(f"Found {len(email_events)} events for next 14 days")
    
    # Generate HTML email content
    print("Creating HTML email content...")
    html_content = generate_email_html(email_events)
    
    # Write HTML file for backup/reference
    with open(OUTPUT_HTML_FILE, 'w') as f:
        f.write(html_content)
    print(f"Created {OUTPUT_HTML_FILE} for reference")
    
    # Save events as JSON for reference
    with open(OUTPUT_JSON_FILE, 'w') as f:
        json.dump(email_events, f, indent=2)
    print(f"Created {OUTPUT_JSON_FILE} for reference")
    
    # Authenticate and send email
    print("Authenticating with Gmail...")
    service = authenticate_gmail()
    
    if service:
        print("Sending email...")
        success = send_email(service, html_content, len(email_events))
        
        if success:
            print("Email sent successfully!")
            print(f"Sent to: {', '.join(TO_EMAILS)}")
            if CC_EMAILS:
                print(f"CC'd to: {', '.join(CC_EMAILS)}")
            print(f"Events included: {len(email_events)}")
        else:
            print("Failed to send email")
    else:
        print("Failed to authenticate with Gmail")
    
    # Print summary
    print(f"\nEmail Summary:")
    print(f"- {len(email_events)} events in next 14 days")
    if email_events:
        print(f"- Date range: {email_events[0].get('StartDateTime', '')[:10]} to {email_events[-1].get('StartDateTime', '')[:10]}")

if __name__ == "__main__":
    main()