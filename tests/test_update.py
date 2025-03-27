#!/usr/bin/env python3
import database

# Get the first unclassified event
unclassified = database.get_unclassified_events(limit=1)
if unclassified:
    event = unclassified[0]
    print(f"Found unclassified event: {event.summary}, ID: {event.id}")
    
    # Get the project we created earlier
    projects = database.get_projects()
    if projects:
        project = projects[0]
        print(f"Assigning to project: {project.name}, ID: {project.id}")
        
        # Get the database ID for the event
        db = database.get_db_session()
        db_event = db.query(database.EventModel).filter(
            database.EventModel.event_id == event.id
        ).first()
        
        if db_event:
            print(f"Database event ID: {db_event.id}")
            
            # Update the event's project
            success = database.update_event_project(db_event.id, project.id)
            print(f"Update success: {success}")
            
            # Verify the update
            updated = database.get_classified_events(limit=1)
            if updated:
                print(f"Updated event: {updated[0].summary}, Project: {updated[0].project_name}")
            else:
                print("No classified events found")
        else:
            print("Database event not found")
    else:
        print("No projects found")
else:
    print("No unclassified events found") 