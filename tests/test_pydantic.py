#!/usr/bin/env python3
import database
from models import CalendarEvent, CalendarEventTime
from datetime import datetime

# Create a Pydantic model directly
event = CalendarEvent(
    id="test456",
    summary="Test Pydantic Event",
    description="An event created as a Pydantic model",
    start=CalendarEventTime(dateTime=datetime.now().isoformat()),
    end=CalendarEventTime(dateTime=datetime.now().isoformat()),
    calendar_id="primary"
)

# Store the event
added = database.store_events([event])
print(f"Added {added} events")

# Check all events
db = database.get_db_session()
events = db.query(database.EventModel).all()
print(f"Found {len(events)} events:")
for event in events:
    print(f"Event: {event.title}, Start: {event.start_time}, ID: {event.event_id}")

# Check unclassified events
unclassified = database.get_unclassified_events()
print(f"\nUnclassified events: {len(unclassified)}")
for event in unclassified:
    print(f"Unclassified: {event.summary}, Start: {event.start_dt}") 