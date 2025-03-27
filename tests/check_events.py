#!/usr/bin/env python3
import database

db = database.get_db_session()
events = db.query(database.EventModel).all()
print(f"Found {len(events)} events:")
for event in events:
    print(f"Event: {event.title}, Start: {event.start_time}, ID: {event.event_id}")

# Let's also check get_unclassified_events function
unclassified = database.get_unclassified_events()
print(f"\nUnclassified events: {len(unclassified)}")
for event in unclassified:
    print(f"Unclassified: {event.summary}, Start: {event.start_dt}") 