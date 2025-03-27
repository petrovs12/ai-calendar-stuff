#!/usr/bin/env python3
import database
import json

db = database.get_db_session()
events = db.query(database.EventModel).all()
print(f"Found {len(events)} events:")

for event in events:
    print(f"\nEvent: {event.title}, ID: {event.event_id}")
    print(f"Start time: {event.start_time}")
    
    # For the second event (Pydantic event), print the full raw data
    if event.event_id == "test456":
        print("\nFull raw data for test456:")
        raw_data = json.loads(event.raw_event_data)
        print(json.dumps(raw_data, indent=2))
    else:
        print(f"Raw data: {event.raw_event_data[:200]}...")  # Show beginning of raw data
    
    # Try to convert
    pydantic_event = event.to_pydantic()
    print(f"Converted event summary: {pydantic_event.summary}")
    print(f"Converted event start_dt: {pydantic_event.start_dt}")
    
    # Let's manually create a dict and validate it
    if event.start_time:
        print("Manually validating start time...")
        from models import CalendarEventTime
        start_time = CalendarEventTime(dateTime=event.start_time)
        print(f"Manual validation result: {start_time.dt}") 