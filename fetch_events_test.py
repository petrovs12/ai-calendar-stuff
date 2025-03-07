#!/usr/bin/env python3
"""
Simple script to fetch and print all events from the database.
This helps diagnose issues with events and calendar IDs.
"""

import sqlite3
import os
import sys
from datetime import datetime

# Use the same DB_PATH as in database.py
DB_PATH = "planner.db"

def format_date(date_str):
    """Format ISO date string for better readability."""
    if not date_str:
        return "Unknown date"
    
    try:
        # Handle ISO format dates
        if 'T' in date_str:
            date_obj = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
            return date_obj.strftime("%Y-%m-%d %H:%M:%S")
        # Handle date-only strings
        return date_str
    except Exception as e:
        print(f"Error formatting date {date_str}: {e}")
        return date_str

def get_all_events():
    """Fetch all events from the database."""
    if not os.path.exists(DB_PATH):
        print(f"Error: Database file {DB_PATH} not found.")
        sys.exit(1)
        
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    try:
        # First check the table structure
        cursor.execute("PRAGMA table_info(events)")
        columns = cursor.fetchall()
        print("Table structure:")
        for col in columns:
            print(f"- {col[1]} ({col[2]})")
        print("\n" + "="*80 + "\n")
        
        # Get the count of events
        cursor.execute("SELECT COUNT(*) FROM events")
        count = cursor.fetchone()[0]
        print(f"Total events in database: {count}\n")
        
        # Count events by calendar_id
        cursor.execute("""
            SELECT calendar_id, project_id, COUNT(*) as count 
            FROM events 
            GROUP BY calendar_id, project_id
            ORDER BY count DESC
        """)
        calendars = cursor.fetchall()
        
        print("Events by calendar:")
        for cal_id, project_id, cal_count in calendars:
            print(f"- {cal_id}, {project_id}: {cal_count} events")
        print("\n" + "="*80 + "\n")
        
        # Get all events
        cursor.execute("""
            SELECT id, event_id, title, description, start_time, end_time, calendar_id, project_id
            FROM events
            ORDER BY start_time DESC
            LIMIT 50  # Limit to avoid overwhelming output
        """)
        events = cursor.fetchall()
        
        print(f"Showing the 50 most recent events:\n")
        
        for event in events:
            event_id, google_event_id, title, description, start, end, calendar_id, project_id = event
            
            print(f"ID: {event_id}")
            print(f"Title: {title}")
            print(f"Start: {format_date(start)}")
            print(f"End: {format_date(end)}")
            print(f"Calendar: {calendar_id}")
            print(f"Project ID: {project_id if project_id else 'Not classified'}")
            print(f"Google Event ID: {google_event_id}")
            if description and len(description) > 100:
                print(f"Description: {description[:100]}...")
            elif description:
                print(f"Description: {description}")
            print("-" * 50)
    
    except Exception as e:
        print(f"Error fetching events: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    print("Fetching events from database...\n")
    get_all_events()
    print("\nDone!") 