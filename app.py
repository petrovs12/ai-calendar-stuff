import streamlit as st
import sqlite3
import logging
from datetime import datetime, timedelta
from dotenv import load_dotenv
import pandas as pd

# Local module imports
import google_calendar
import scheduler
import database  # Import the database module
import classification  # Import the classification module

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def store_events_in_db(events, db_path="planner.db"): 
    """Store calendar events in the SQLite database using the events table defined in database.py."""
    logger.info(f"Storing {len(events)} events in database: {db_path}")
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    
    # Ensure the database is initialized with required tables
    try:
        database.init_db()  # Initialize the database if not already done
        logger.info("Database tables verified/created through database.init_db()")
    except Exception as e:
        logger.error(f"Error initializing database: {e}")
        # If init_db fails, try to create the events table directly
        try:
            c.execute("""
                CREATE TABLE IF NOT EXISTS events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    project_id INTEGER,
                    title TEXT NOT NULL,
                    description TEXT,
                    start_time TEXT NOT NULL,
                    end_time TEXT NOT NULL,
                    event_id TEXT UNIQUE,
                    calendar_id TEXT,
                    FOREIGN KEY(project_id) REFERENCES projects(id)
                );
            """)
            logger.info("Events table created directly as fallback")
        except Exception as inner_e:
            logger.error(f"Error creating events table: {inner_e}")
            raise
    
    # Insert events
    events_added = 0
    for event in events:
        try:
            event_id = event['id']
            title = event.get('summary', 'No Title')
            description = event.get('description', '')
            calendar_id = event.get('calendarId', 'unknown')
            
            # Handle both datetime and date-only events
            start = event['start'].get('dateTime', event['start'].get('date'))
            end = event['end'].get('dateTime', event['end'].get('date'))
            
            # Insert into the events table using the schema from database.py
            c.execute("""
                INSERT OR REPLACE INTO events 
                (title, description, start_time, end_time, event_id, calendar_id)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (title, description, start, end, event_id, calendar_id))
            events_added += 1
        except Exception as e:
            logger.error(f"Error storing event {event.get('id', 'unknown')}: {e}")
    
    logger.info(f"Successfully stored {events_added} events in database")
    conn.commit()
    conn.close()

def get_unclassified_events(limit=100):
    """Retrieve events that haven't been classified (project_id is NULL)."""
    conn = sqlite3.connect(database.DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, event_id, title, description, start_time, end_time, calendar_id 
        FROM events 
        WHERE project_id IS NULL
        ORDER BY start_time 
        LIMIT ?
    """, (limit,))
    events = cursor.fetchall()
    conn.close()
    for event in events:
        print(event)
    return events

def get_classified_events(limit=1000):
    """Retrieve events that have been classified with their project names."""
    conn = sqlite3.connect(database.DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT e.id, e.event_id, e.title, e.description, e.start_time, e.end_time, 
               e.calendar_id, e.project_id, p.name as project_name
        FROM events e
        JOIN projects p ON e.project_id = p.id
        ORDER BY e.start_time 
        LIMIT ?
    """, (limit,))
    events = cursor.fetchall()
    conn.close()
    return events

def update_event_project(event_id, project_id):
    """Update an event's project classification."""
    conn = sqlite3.connect(database.DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE events
        SET project_id = ?
        WHERE id = ?
    """, (project_id, event_id))
    conn.commit()
    conn.close()

def auto_classify_events(limit=1000):
    """Auto-classify unclassified events using the classification module."""
    try:
        # Import the classification module
        import classification
        
        # Get unclassified events
        unclassified_events = get_unclassified_events(limit)
        classified_events = get_classified_events(limit)
        
        results = []
        for event in unclassified_events:
            event_id, google_event_id, title, description, start_time, end_time, calendar_id = event
            
            # Try to classify the event
            try:
                project_id, confidence = classification.classify_event(title, description)
                
                if project_id:
                    # Update the event with the classified project
                    update_event_project(event_id, project_id)
                    results.append((event_id, project_id, title, confidence))
                else:
                    # Could not classify or low confidence
                    results.append((event_id, None, title, 0.0))
            except Exception as e:
                logger.error(f"Error classifying event {event_id}: {e}")
                results.append((event_id, None, title, 0.0))
        
        return results
    except Exception as e:
        logger.error(f"Auto-classification failed: {e}")
        return []

def get_calendar_name(calendar_id):
    """Get the name of a calendar from its ID, with error handling."""
    if not calendar_id:
        return "Unknown Calendar"
    
    try:
        if not st.session_state.service:
            return calendar_id  # Just return the ID if no Google service
        
        name = google_calendar.get_calendar_name(st.session_state.service, calendar_id)
        return name
    except Exception as e:
        logger.error(f"Error getting calendar name for {calendar_id}: {e}")
        return calendar_id  # Fallback to using the ID itself

# Initialize session state for calendar selection
if 'selected_calendars' not in st.session_state:
    logger.info("Initializing selected_calendars in session state")
    st.session_state.selected_calendars = []
if 'available_calendars' not in st.session_state:
    logger.info("Initializing available_calendars in session state")
    st.session_state.available_calendars = []
if 'service' not in st.session_state:
    logger.info("Initializing service in session state")
    st.session_state.service = None
if 'active_tab' not in st.session_state:
    st.session_state.active_tab = "Calendar"
if 'new_project_name' not in st.session_state:
    st.session_state.new_project_name = ""
if 'new_project_hours' not in st.session_state:
    st.session_state.new_project_hours = 10
if 'new_project_priority' not in st.session_state:
    st.session_state.new_project_priority = 3

# Load environment variables (if any)
try:
    load_dotenv()
    logger.info("Environment variables loaded from .env file")
except Exception as e:
    logger.warning(f"Error loading environment variables: {e}")

# App title and description
logger.info("Setting up Streamlit UI")
st.title("Interview Practice Scheduler")

# Create tabs for different sections of the app
tabs = ["Calendar", "Classification", "Projects", "Scheduling"]
active_tab = st.sidebar.radio("Navigation", tabs, index=tabs.index(st.session_state.active_tab))
st.session_state.active_tab = active_tab

if active_tab == "Calendar":
    st.write("This app fetches your Google Calendar events and generates a schedule for interview practice sessions.")

    # Authentication section
    with st.expander("Calendar Authentication", expanded=not st.session_state.service):
        if not st.session_state.service:
            logger.info("User not authenticated yet")
            if st.button("Authenticate with Google Calendar"):
                logger.info("Authentication button clicked")
                with st.spinner("Authenticating..."):
                    try:
                        # Authenticate and get the Calendar API service
                        logger.info("Starting authentication process")
                        st.session_state.service = google_calendar.get_calendar_service()
                        logger.info("Authentication successful")
                        st.success("Authentication successful!")
                        
                        # Fetch available calendars
                        logger.info("Fetching available calendars")
                        st.session_state.available_calendars = google_calendar.list_calendars(st.session_state.service)
                        logger.info(f"Found {len(st.session_state.available_calendars)} calendars")
                        
                        # Pre-select primary calendar
                        primary_calendars = [cal['id'] for cal in st.session_state.available_calendars if cal.get('primary', False)]
                        st.session_state.selected_calendars = primary_calendars
                        logger.info(f"Pre-selected primary calendar(s): {primary_calendars}")
                        
                        try:
                            st.rerun()  # Changed from experimental_rerun() to rerun()
                        except Exception as e:
                            logger.warning(f"Rerun failed, will continue without refresh: {e}")
                    except Exception as e:
                        logger.error(f"Authentication failed: {e}")
                        st.error(f"Authentication failed: {e}")
        else:
            logger.info("User is already authenticated")
            st.success("You are authenticated with Google Calendar.")
            if st.button("Sign Out"):
                logger.info("Sign out button clicked")
                st.session_state.service = None
                st.session_state.available_calendars = []
                st.session_state.selected_calendars = []
                logger.info("User signed out, session state reset")
                try:
                    st.rerun()  # Changed from experimental_rerun() to rerun()
                except Exception as e:
                    logger.warning(f"Rerun failed, will continue without refresh: {e}")

    # Calendar selection section (only shown when authenticated)
    if st.session_state.service and st.session_state.available_calendars:
        logger.info("Displaying calendar selection UI")
        with st.expander("Select Calendars", expanded=True):
            st.write("Choose which calendars to include:")
            
            # Create checkboxes for each calendar
            for calendar in st.session_state.available_calendars:
                # Determine if this calendar should be checked by default
                is_selected = calendar['id'] in st.session_state.selected_calendars
                calendar_label = f"{calendar['summary']} {' (Primary)' if calendar.get('primary', False) else ''}"
                
                # Create a checkbox for this calendar
                checkbox_key = f"cal_{calendar['id']}"
                if st.checkbox(calendar_label, value=is_selected, key=checkbox_key):
                    # Add to selected calendars if not already there
                    if calendar['id'] not in st.session_state.selected_calendars:
                        st.session_state.selected_calendars.append(calendar['id'])
                        logger.info(f"Calendar selected: {calendar['summary']} (ID: {calendar['id']})")
                else:
                    # Remove from selected calendars if it was there
                    if calendar['id'] in st.session_state.selected_calendars:
                        st.session_state.selected_calendars.remove(calendar['id'])
                        logger.info(f"Calendar deselected: {calendar['summary']} (ID: {calendar['id']})")
            
            # Show which calendars are selected
            if st.session_state.selected_calendars:
                selected_count = len(st.session_state.selected_calendars)
                logger.info(f"Total calendars selected: {selected_count}")
                st.write(f"Selected {selected_count} calendar(s)")
            else:
                logger.warning("No calendars selected")
                st.warning("No calendars selected. Please select at least one calendar.")

    # Button to generate schedule
    button_disabled = not st.session_state.service or not st.session_state.selected_calendars
    if st.button("Generate Schedule", disabled=button_disabled):
        logger.info("Generate Schedule button clicked")
        if button_disabled:
            logger.warning("Button was disabled but somehow clicked - should not happen")
        else:
            with st.spinner("Fetching events and generating schedule..."):
                try:
                    # Fetch events from selected calendars
                    selected_cal_ids = st.session_state.selected_calendars
                    logger.info(f"Fetching events from {len(selected_cal_ids)} selected calendars")
                    events = google_calendar.fetch_events(
                        st.session_state.service, 
                        max_results=2000, 
                        calendar_ids=selected_cal_ids
                    )
                    logger.info(f"Retrieved {len(events)} total events")
                    
                    # Store events in database
                    try:
                        store_events_in_db(events)
                        st.write("Calendar events have been stored in the database.")
                        logger.info("Events successfully stored in database")
                    except Exception as e:
                        logger.error(f"Error storing events in database: {e}")
                        st.error(f"Error storing events: {e}")
                    
                    if not events:
                        logger.warning("No upcoming events found in the selected calendars")
                        st.write("No upcoming events found in the selected calendars.")
                    else:
                        # Display events grouped by calendar
                        st.subheader("Upcoming Events:")
                        
                        # Group events by calendar
                        events_by_calendar = {}
                        for event in events:
                            calendar_id = event.get('calendarId', 'unknown')
                            if calendar_id not in events_by_calendar:
                                events_by_calendar[calendar_id] = []
                            events_by_calendar[calendar_id].append(event)
                        
                        # Display events for each calendar
                        logger.info(f"Displaying events from {len(events_by_calendar)} calendars")
                        for calendar_id, calendar_events in events_by_calendar.items():
                            calendar_name = get_calendar_name(calendar_id)
                            logger.info(f"Displaying {len(calendar_events)} events from calendar: {calendar_name}")
                            with st.expander(f"{calendar_name} ({len(calendar_events)} events)", expanded=True):
                                for event in calendar_events:
                                    # Extract event start time (dateTime or date for all-day events)
                                    start = event['start'].get('dateTime', event['start'].get('date'))
                                    summary = event.get('summary', 'No Title')
                                    st.write(f"{start} - {summary}")
                        
                        # Generate practice schedule suggestions based on fetched events
                        st.subheader("Suggested Practice Sessions")
                        logger.info("Generating schedule suggestions")
                        try:
                            suggestions = scheduler.schedule_practice(events, duration_minutes=60, days_ahead=14)
                            logger.info(f"Generated {len(suggestions)} schedule suggestions")
                            
                            if suggestions:
                                for start, end in suggestions:
                                    formatted_time = f"{start.strftime('%a, %b %d, %Y %I:%M %p')} to {end.strftime('%I:%M %p')}"
                                    st.write(formatted_time)
                            else:
                                logger.warning("No available free slots found")
                                st.write("No available free slots found for practice sessions.")
                        except Exception as e:
                            logger.error(f"Error generating schedule suggestions: {e}")
                            st.error(f"Error generating schedule: {e}")
                except Exception as e:
                    logger.error(f"Error in schedule generation: {e}")
                    st.error(f"Error: {e}")

elif active_tab == "Classification":
    st.header("Event Classification")
    st.write("Classify your calendar events into projects for better organization and scheduling.")
    
    # Create sidebar menu for classification tab
    classification_options = ["Manual Classification", "Auto-Classification", "Classified Events"]
    classification_selection = st.sidebar.radio(
        "Classification Options", 
        classification_options, 
        index=0, 
        key="classification_selection"
    )
    
    # Ensure database is initialized
    try:
        database.init_db()
    except Exception as e:
        st.error(f"Error initializing database: {e}")
        st.stop()
    
    # Get projects for classification
    projects = database.get_projects()
    
    # New Project Creation Form
    with st.sidebar.expander("Create New Project", expanded=False):
        st.write("Add a new project for classifying events")
        new_project_name = st.text_input("Project Name", key="new_project_name_input")
        new_project_hours = st.number_input("Estimated Weekly Hours", min_value=1, max_value=168, value=10, key="new_project_hours_input")
        new_project_priority = st.number_input("Priority (1=highest)", min_value=1, max_value=10, value=3, key="new_project_priority_input")
        new_project_desc = st.text_area("Description", key="new_project_desc_input")
        
        if st.button("Create Project"):
            if new_project_name:
                try:
                    project_id = database.add_project(new_project_name, new_project_hours, new_project_priority, new_project_desc)
                    st.success(f"Project '{new_project_name}' created successfully!")
                    # Refresh projects list
                    projects = database.get_projects()
                except Exception as e:
                    st.error(f"Error creating project: {e}")
            else:
                st.warning("Project name is required")
    
    # Format projects for display
    project_options = {p[0]: p[1] for p in projects}  # id: name
    
    if classification_selection == "Manual Classification":
        st.subheader("Manual Event Classification")
        
        # Get unclassified events
        unclassified_events = get_unclassified_events(25)
        
        if not unclassified_events:
            st.info("No unclassified events found. Fetch new events from the Calendar tab or all events have been classified.")
        else:
            st.write(f"Found {len(unclassified_events)} unclassified events. Select a project for each event:")
            
            # Create a form for classifying events
            for event in unclassified_events:
                event_id, google_event_id, title, description, start_time, end_time, calendar_id = event
                
                # Format the date for better readability
                try:
                    start_dt = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
                    formatted_date = start_dt.strftime("%a, %b %d, %Y %I:%M %p")
                except:
                    formatted_date = start_time
                
                # Create a container for each event for better styling
                with st.container():
                    col1, col2 = st.columns([3, 1])
                    with col1:
                        st.write(f"**{title}**")
                        st.write(f"*{formatted_date}*")
                        # Display the calendar ID to help identify which calendar the event is from
                        calendar_name = get_calendar_name(calendar_id)
                        st.write(f"📅 {calendar_name}")
                        if description:
                            with st.expander("Description"):
                                st.write(description)
                    
                    with col2:
                        # Dropdown for project selection
                        selected_project = st.selectbox(
                            "Project",
                            options=list(project_options.keys()),
                            format_func=lambda x: project_options[x],
                            key=f"project_select_{event_id}"
                        )
                        
                        # Button to save classification
                        if st.button("Classify", key=f"classify_btn_{event_id}"):
                            update_event_project(event_id, selected_project)
                            st.success(f"Event classified as '{project_options[selected_project]}'")
                    
                    st.divider()
    
    elif classification_selection == "Auto-Classification":
        st.subheader("Automatic Event Classification")
        st.write("Use AI to automatically classify events based on their titles and descriptions.")
        
        # Check if OpenAI API key is configured
        import os
        openai_key = os.getenv("OPENAI_API_KEY", "")
        if not openai_key:
            st.warning("OpenAI API key not found in environment variables. Auto-classification requires this to be set.")
        else:
            # Button to trigger auto-classification
            if st.button("Run Auto-Classification", type="primary"):
                try:
                    with st.spinner("Classifying events..."):
                        # Get unclassified events
                        limit = 100
                        events_to_classify = get_unclassified_events(limit)
                        
                        if not events_to_classify:
                            st.info("No unclassified events to process.")
                        else:
                            results = auto_classify_events(limit)
                            st.success(f"Auto-classification completed! {len(results)} events processed.")
                            
                            # Display results
                            for event_id, project_id, title, confidence in results:
                                project_name = project_options.get(project_id, "Unknown Project")
                                
                                # Get event details
                                event_details = None
                                for e in events_to_classify:
                                    if e[0] == event_id:
                                        event_details = e
                                        break
                                
                                if event_details:
                                    _, _, _, _, start_time, end_time, calendar_id = event_details
                                    # Format the date
                                    try:
                                        start_dt = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
                                        formatted_date = start_dt.strftime("%a, %b %d, %Y %I:%M %p")
                                    except:
                                        formatted_date = start_time
                                    
                                    # Get calendar name
                                    calendar_name = get_calendar_name(calendar_id)
                                    
                                    with st.container():
                                        st.write(f"**{title}** → {project_name} (Confidence: {confidence:.0%})")
                                        st.write(f"*{formatted_date}*")
                                        st.write(f"📅 {calendar_name}")
                                        st.divider()
                                else:
                                    st.write(f"**{title}** → {project_name} (Confidence: {confidence:.0%})")
                except Exception as e:
                    st.error(f"Error during auto-classification: {e}")
                    logger.error(f"Auto-classification error: {e}")
    
    elif classification_selection == "Classified Events":
        st.subheader("Classified Events")
        
        classified_events = get_classified_events(100)
        
        if not classified_events:
            st.info("No classified events found. Use Manual or Auto-Classification to classify some events first.")
        else:
            st.write(f"Found {len(classified_events)} classified events.")
            
            # Group by project for better organization
            by_project = {}
            for event in classified_events:
                event_id, google_event_id, title, description, start_time, end_time, calendar_id, project_id, project_name = event
                if project_name not in by_project:
                    by_project[project_name] = []
                by_project[project_name].append((event_id, title, description, start_time, end_time, calendar_id))
            
            # Display events by project
            for project_name, events in by_project.items():
                with st.expander(f"{project_name} ({len(events)} events)"):
                    for event_id, title, description, start_time, end_time, calendar_id in events:
                        try:
                            start_dt = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
                            formatted_date = start_dt.strftime("%a, %b %d, %Y %I:%M %p")
                        except:
                            formatted_date = start_time
                        
                        with st.container():
                            st.write(f"**{title}**")
                            st.write(f"*{formatted_date}*")
                            # Display the calendar ID to help identify which calendar the event is from
                            calendar_name = get_calendar_name(calendar_id)
                            st.write(f"📅 {calendar_name}")
                            if description:
                                with st.expander("Description"):
                                    st.write(description)
                            st.divider()

elif active_tab == "Projects":
    st.header("Projects Management")
    st.write("Manage your projects and view project-related statistics.")
    
    # Ensure database is initialized
    try:
        database.init_db()
    except Exception as e:
        st.error(f"Error initializing database: {e}")
        st.stop()
    
    # Get projects
    projects = database.get_projects()
    
    # Create columns for project metrics
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Total Projects", len(projects))
    
    # New Project Creation Form
    with st.expander("Create New Project", expanded=False):
        st.write("Add a new project for classifying events")
        new_project_name = st.text_input("Project Name")
        new_project_hours = st.number_input("Estimated Weekly Hours", min_value=1, max_value=168, value=10)
        new_project_priority = st.number_input("Priority (1=highest)", min_value=1, max_value=10, value=3)
        new_project_desc = st.text_area("Description")
        
        if st.button("Create Project"):
            if new_project_name:
                try:
                    project_id = database.add_project(new_project_name, new_project_hours, new_project_priority, new_project_desc)
                    st.success(f"Project '{new_project_name}' created successfully!")
                    # Refresh projects list
                    projects = database.get_projects()
                except Exception as e:
                    st.error(f"Error creating project: {e}")
            else:
                st.warning("Project name is required")
    
    # Display projects
    if not projects:
        st.info("No projects found. Create your first project above.")
    else:
        st.subheader("Your Projects")
        
        # Convert to DataFrame for better display
        df = pd.DataFrame(projects, columns=['id', 'name', 'estimated_hours', 'priority', 'description'])
        
        # Show projects in a table
        st.dataframe(
            df[['name', 'estimated_hours', 'priority', 'description']],
            use_container_width=True,
            column_config={
                "name": "Project Name",
                "estimated_hours": "Weekly Hours",
                "priority": "Priority",
                "description": "Description"
            },
            hide_index=True
        )

elif active_tab == "Scheduling":
    st.header("Schedule Planning")
    st.write("Generate and view schedules for your projects.")
    
    # This section will be expanded in the future for more advanced scheduling

# Add some information about the app
with st.sidebar.expander("About this app"):
    st.write("""
    This app helps you schedule interview practice sessions by:
    1. Connecting to your Google Calendar
    2. Fetching your upcoming events from selected calendars
    3. Classifying events into projects
    4. Finding available time slots for practice
    5. Suggesting optimal times for interview practice
    
    The scheduler takes into account your existing commitments and tries to find
    the best times for focused practice sessions.
    """)

logger.info("App UI setup complete")