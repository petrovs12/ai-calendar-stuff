#!/usr/bin/env python3
import database
from models import CalendarEvent, CalendarEventTime
from datetime import datetime, timedelta
import json

# Create a completely new event
timestamp = datetime.now().isoformat()
event = CalendarEvent(
    id=f"new_event_{timestamp}",
    summary=f"Brand New Event {timestamp[:10]}",
    description=f"A brand new event created at {timestamp}",
    start=CalendarEventTime(dateTime=(datetime.now() + timedelta(days=1)).isoformat()),
    end=CalendarEventTime(dateTime=(datetime.now() + timedelta(days=1, hours=1)).isoformat()),
    calendar_id="primary"
)

# Print the event properties
print(f"New event ID: {event.id}")
print(f"New event summary: {event.summary}")
print(f"New event start: {event.start_dt}")

# Store the new event
added = database.store_events([event])
print(f"Added {added} events")

# Retrieve the event from the database
db = database.get_db_session()
db_event = db.query(database.EventModel).filter(
    database.EventModel.event_id == event.id
).first()

if db_event:
    print(f"Retrieved event title: {db_event.title}")
    print(f"Retrieved event start: {db_event.start_time}")
    
    # Convert to Pydantic model
    pydantic_event = db_event.to_pydantic()
    print(f"Pydantic event summary: {pydantic_event.summary}")
    print(f"Pydantic event start_dt: {pydantic_event.start_dt}")
else:
    print("Failed to retrieve the new event") 