#!/usr/bin/env python3
"""
Debug script to inspect iiQ event data structure
This will help us find where event type information is stored
"""

import os
import json
import requests
from datetime import datetime, timedelta

# Configuration
API_TOKEN = os.environ.get('IIQ_API_TOKEN')
SITE_ID = "d3b75b85-9241-49ba-88c3-3c9b7f0d3269"
API_BASE_URL = "https://gds.incidentiq.com/api/v1.0"
VIEW_ID = "8028a2ba-887f-f011-b481-000d3ae39e88"

def fetch_and_inspect_events():
    """Fetch events and inspect their structure"""
    
    headers = {
        'accept': 'application/json, text/plain, */*',
        'content-type': 'application/json',
        'siteid': SITE_ID,
        'client': 'ApiClient',
        'Authorization': f'Bearer {API_TOKEN}'
    }
    
    data = {
        "FilterByProduct": True,
        "ViewId": VIEW_ID,
        "RequestOptions": {
            "Paging": {
                "PageSize": 5,  # Just get a few for inspection
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
        
        if 'Items' not in result or not result['Items']:
            print("No events found")
            return
            
        print(f"Found {len(result['Items'])} events for inspection\n")
        
        # Look at the first few events
        for i, event in enumerate(result['Items'][:3]):
            print(f"=== EVENT {i+1} ===")
            print(f"Title: {event.get('Title', 'No Title')}")
            print(f"Status: {event.get('EventStatus', {}).get('Name', 'No Status')}")
            
            # Print all top-level keys to see what's available
            print("\nAll available fields:")
            for key in sorted(event.keys()):
                value = event[key]
                if isinstance(value, dict):
                    print(f"  {key}: {type(value).__name__} with keys: {list(value.keys())}")
                elif isinstance(value, list):
                    print(f"  {key}: {type(value).__name__} with {len(value)} items")
                else:
                    print(f"  {key}: {value}")
            
            # Look specifically for anything that might be event type
            print(f"\nLooking for type-related fields:")
            type_candidates = [k for k in event.keys() if 'type' in k.lower() or 'category' in k.lower() or 'kind' in k.lower()]
            if type_candidates:
                for candidate in type_candidates:
                    print(f"  {candidate}: {event[candidate]}")
            else:
                print("  No obvious type-related fields found")
            
            # Check if there's a Type field and what it contains
            if 'Type' in event:
                print(f"\nType field contents: {json.dumps(event['Type'], indent=2)}")
            
            print("\n" + "="*50 + "\n")
            
    except requests.exceptions.RequestException as e:
        print(f"Error fetching events: {e}")

if __name__ == "__main__":
    if not API_TOKEN:
        print("Error: IIQ_API_TOKEN environment variable not set")
    else:
        fetch_and_inspect_events()
