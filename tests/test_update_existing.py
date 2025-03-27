#!/usr/bin/env python3
import database
from models import CalendarEvent, CalendarEventTime
from datetime import datetime, timedelta
import json

# Get an existing event
db = database.get_db_session()
existing = db.query(database.EventModel).first()

if existing:
    print(f"Found existing event: {existing.title}, ID: {existing.event_id}")
    
    # Create a modified version of the event with unique timestamp
    timestamp = datetime.now().isoformat()
    event = CalendarEvent(
        id=existing.event_id,
        summary=f"Updated Title {timestamp[:10]}",
        description=f"Updated description {timestamp}",
        start=CalendarEventTime(dateTime=existing.start_time),
        end=CalendarEventTime(dateTime=existing.end_time),
        calendar_id=existing.calendar_id
    )
    
    # Print the event properties
    print(f"Modified event summary: {event.summary}")
    print(f"Modified event description: {event.description[:50]}...")
    
    # Manually create the model_dict to see what we're storing
    model_dict = {
        "event_id": event.id,
        "title": event.summary,  # This is what goes into the database title field
        "description": event.description or "",
        "start_time": event.start_dt.isoformat() if event.start_dt else "",
        "end_time": event.end_dt.isoformat() if event.end_dt else "",
        "calendar_id": event.calendar_id or "",
        "project_id": event.project_id,
        "raw_event_data": json.dumps(event.model_dump(), cls=database.DateTimeEncoder)
    }
    
    print(f"Model dict title: {model_dict['title']}")
    
    # Store the updated event
    added = database.store_events([event])
    print(f"Updated {added} events")
    
    # Check that it was updated
    updated = db.query(database.EventModel).filter(
        database.EventModel.event_id == existing.event_id
    ).first()
    
    print(f"Updated event title: {updated.title}")
    print(f"Updated event description: {updated.description[:50]}...")
    
    if updated.raw_event_data:
        raw_data = json.loads(updated.raw_event_data)
        print(f"Raw data summary: {raw_data.get('summary')}")
        
        # Check what happens when we convert back to Pydantic
        pydantic_event = updated.to_pydantic()
        print(f"Pydantic event summary: {pydantic_event.summary}")
else:
    print("No existing events found") 