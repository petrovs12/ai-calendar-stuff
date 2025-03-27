import streamlit as st
import sqlite3
import logging
from datetime import datetime, timedelta
from dotenv import load_dotenv
import pandas as pd
import os
from typing import List, Dict, Tuple, Any, Optional, Union, Callable, Set, cast

# Local module imports
import google_calendar
import scheduler
import database  # Import the database module
import classification  # Import the classification module
from models import CalendarEvent, Project  # Import the Pydantic models directly

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# DSPy Configuration Section
with st.sidebar:
    st.header("DSPy Configuration")
    
    # Model selection
    model_name: str = st.text_input(
        "OpenAI Model Name",
        value=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
        help="Enter the OpenAI model name (e.g., gpt-4o-mini)"
    )
    
    # API key input
    api_key: str = st.text_input(
        "OpenAI API Key",
        type="password",
        value=os.getenv("OPENAI_API_KEY", ""),
        help="Enter your OpenAI API key"
    )
    
    # Only show configure button if not already configured
    if not st.session_state.get('dspy_configured', False):
        # Configure button
        if st.button("Configure DSPy"):
            with st.spinner("Configuring DSPy..."):
                lm = classification.configure_dspy(model_name, api_key)
                if lm is not None:
                    st.success("DSPy configured successfully!")
                else:
                    st.error("Failed to configure DSPy. Please check your API key and try again.")
    else:
        st.success(f"DSPy configured with model: {st.session_state.get('dspy_model_name', 'unknown')}")
        
        # Add button to reconfigure if needed
        if st.button("Reconfigure"):
            # Clear previous configuration
            if 'dspy_lm' in st.session_state:
                del st.session_state.dspy_lm
            if 'dspy_configured' in st.session_state:
                st.session_state.dspy_configured = False
            st.rerun()

# MLflow Information (simplified - just informational)
st.sidebar.header("MLflow Tracking")
MLFLOW_PORT = 5000
MLFLOW_URL = f"http://127.0.0.1:{MLFLOW_PORT}"
st.sidebar.info(f"MLflow UI: [Open MLflow Dashboard]({MLFLOW_URL})")

# No need to check if MLflow server is running, since autolog will handle it gracefully

def auto_classify_events(limit: int = 1000) -> List[Tuple[str, Optional[int], str, float]]:
    """Auto-classify unclassified events using the classification module."""
    try:
        # Check if DSPy is configured
        if 'dspy_lm' not in st.session_state:
            logger.warning("DSPy not configured. Please configure DSPy first.")
            return []
        
        # Get the LM from session state
        lm = st.session_state.dspy_lm
        
        # Get unclassified events
        unclassified_events: List[CalendarEvent] = database.get_unclassified_events(limit, include_past=True)
        classified_events: List[CalendarEvent] = database.get_classified_events(limit)
        
        if not unclassified_events:
            logger.info("No unclassified events to process")
            return []
        
        logger.info(f"Found {len(unclassified_events)} unclassified events")
        
        # Prepare events for batch classification
        event_data_list: List[Dict[str, str]] = []
        for event in unclassified_events:
            # Each event is now a CalendarEvent Pydantic model
            event_data_list.append({
                'id': event.id,  # This is the database ID
                'title': event.summary,
                'description': event.description or '',
                'calendar_id': event.calendar_id or ''
            })
        
        # Use batch classification to get all results
        batch_results: Dict[str, Tuple[Optional[int], float]] = classification.batch_classify_events(
            event_data_list,
            lm=lm,
            run_name=f"app_classify_batch_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        )
        
        # Process the classification results
        results: List[Tuple[str, Optional[int], str, float]] = []
        for event_id, (project_id, confidence) in batch_results.items():
            # Get the event details for the result entry
            event_data: Optional[Dict[str, str]] = next((e for e in event_data_list if e['id'] == event_id), None)
            title: str = event_data['title'] if event_data else f"Event {event_id}"
            
            if project_id:
                # Update the event with the classified project
                classification.update_event_with_classification(event_id, project_id)
                results.append((event_id, project_id, title, confidence))
            else:
                # Could not classify or low confidence
                results.append((event_id, None, title, confidence))
        
        return results
    except Exception as e:
        logger.error(f"Auto-classification failed: {e}")
        logger.exception(str(e))
        return []

# Initialize session state for calendar selection
if 'selected_calendars' not in st.session_state:
    logger.info("Initializing selected_calendars in session state")
    st.session_state.selected_calendars: List[str] = []
if 'available_calendars' not in st.session_state:
    logger.info("Initializing available_calendars in session state")
    st.session_state.available_calendars: List[Dict[str, Any]] = []
if 'service' not in st.session_state:
    logger.info("Initializing service in session state")
    st.session_state.service: Any = None
if 'active_tab' not in st.session_state:
    st.session_state.active_tab: str = "Calendar"
if 'new_project_name' not in st.session_state:
    st.session_state.new_project_name: str = ""
if 'new_project_hours' not in st.session_state:
    st.session_state.new_project_hours: int = 10
if 'new_project_priority' not in st.session_state:
    st.session_state.new_project_priority: int = 3

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
tabs: List[str] = ["Calendar", "Classification", "Projects", "Scheduling"]
active_tab: str = st.sidebar.radio("Navigation", tabs, index=tabs.index(st.session_state.active_tab))
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
                        st.session_state.available_calendars: List[Dict[str, Any]] = google_calendar.list_calendars(st.session_state.service)
                        logger.info(f"Found {len(st.session_state.available_calendars)} calendars")
                        
                        # Pre-select primary calendar
                        primary_calendars: List[str] = [cal['id'] for cal in st.session_state.available_calendars if cal.get('primary', False)]
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
                is_selected: bool = calendar['id'] in st.session_state.selected_calendars
                calendar_label: str = f"{calendar['summary']} {' (Primary)' if calendar.get('primary', False) else ''}"
                
                # Create a checkbox for this calendar
                checkbox_key: str = f"cal_{calendar['id']}"
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
                selected_count: int = len(st.session_state.selected_calendars)
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
                    selected_cal_ids: List[str] = st.session_state.selected_calendars
                    logger.info(f"Fetching events from {len(selected_cal_ids)} selected calendars")
                    events: List[CalendarEvent] = google_calendar.fetch_events(
                        st.session_state.service, 
                        max_results=2000, 
                        calendar_ids=selected_cal_ids
                    )
                    logger.info(f"Retrieved {len(events)} total events")
                    
                    # Store events in database
                    try:
                        # events are already dictionaries from Google Calendar API
                        # No need to convert them ahead of time - the database.store_events 
                        # function will handle conversion
                        if events:
                            stored_count = database.store_events(events)
                            logger.info(f"Stored {stored_count} events in the database")
                            st.success(f"Stored {stored_count} events in the database")
                        else:
                            logger.warning("No events retrieved from Google Calendar")
                            st.warning("No events could be retrieved from Google Calendar")
                    except Exception as e:
                        logger.error(f"Error storing events: {e}")
                        st.error(f"Error storing events: {e}")
                    
                    if not events:
                        logger.warning("No upcoming events found in the selected calendars")
                        st.write("No upcoming events found in the selected calendars.")
                    else:
                        # Display events grouped by calendar
                        st.subheader("Upcoming Events:")
                        
                        # Group events by calendar
                        events_by_calendar: Dict[str, List[CalendarEvent]] = {}
                        for event in events:
                            calendar_id = event.get('calendar_id', '')
                            if calendar_id not in events_by_calendar:
                                events_by_calendar[calendar_id] = []
                            events_by_calendar[calendar_id].append(event)
                        
                        # Display events for each calendar
                        logger.info(f"Displaying events from {len(events_by_calendar)} calendars")
                        for calendar_id, calendar_events in events_by_calendar.items():
                            # Use calendar_id directly 
                            logger.info(f"Displaying {len(calendar_events)} events from calendar: {calendar_id}")
                            with st.expander(f"{calendar_id} ({len(calendar_events)} events)", expanded=True):
                                for event in calendar_events:
                                    # Extract event start time
                                    start_time: str = event.get('start', {}).get('dateTime', "No date")
                                    summary: str = event.get('summary', "No title")
                                    st.write(f"{start_time} - {summary}")
                        
                        # Fix the scheduler to use Pydantic models
                        st.subheader("Suggested Practice Sessions")
                        logger.info("Generating schedule suggestions")
                        try:
                            # Use Pydantic models directly instead of converting to dictionaries
                            suggestions: List[Tuple[datetime, datetime]] = scheduler.schedule_practice(events, duration_minutes=60, days_ahead=14)
                            logger.info(f"Generated {len(suggestions)} schedule suggestions")
                            
                            if suggestions:
                                for start, end in suggestions:
                                    formatted_time: str = f"{start.strftime('%a, %b %d, %Y %I:%M %p')} to {end.strftime('%I:%M %p')}"
                                    st.write(formatted_time)
                            else:
                                logger.warning("No available free slots found")
                                st.write("No available free slots found for practice sessions.")
                        except Exception as e:
                            logger.error(f"Error generating schedule suggestions: {e}")
                            st.error(f"Error generating schedule: {e}")
                except Exception as e:
                    logger.error(f"Error in schedule generation: {e}")
                    logger.exception(str(e))
                    st.error(f"Error: {e}")

elif active_tab == "Classification":
    st.header("Event Classification")
    st.write("Classify your calendar events into projects for better organization and scheduling.")
    
    # Create sidebar menu for classification tab
    classification_options: List[str] = ["Manual Classification", "Auto-Classification", "Classified Events", "MLflow Testing"]
    classification_selection: str = st.sidebar.radio(
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
    projects: List[Project] = database.get_projects()
    
    # New Project Creation Form
    with st.sidebar.expander("Create New Project", expanded=False):
        st.write("Add a new project for classifying events")
        new_project_name: str = st.text_input("Project Name", key="new_project_name_input")
        new_project_hours: int = st.number_input("Estimated Weekly Hours", min_value=1, max_value=168, value=10, key="new_project_hours_input")
        new_project_priority: int = st.number_input("Priority (1=highest)", min_value=1, max_value=10, value=3, key="new_project_priority_input")
        new_project_desc: str = st.text_area("Description", key="new_project_desc_input")
        
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
    project_options: Dict[int, str] = {p.id: p.name for p in projects if p.id is not None}
    
    if classification_selection == "Manual Classification":
        st.subheader("Manual Event Classification")
        
        # Get unclassified events
        unclassified_events: List[CalendarEvent] = database.get_unclassified_events(25, include_past=True)
        
        if not unclassified_events:
            st.info("No unclassified events found. Fetch new events from the Calendar tab or all events have been classified.")
        else:
            st.write(f"Found {len(unclassified_events)} unclassified events. Select a project for each event:")
            
            # Create a form for classifying events
            for event in unclassified_events:
                # Format the date for better readability
                try:
                    formatted_date: str = event.start_dt.strftime("%a, %b %d, %Y %I:%M %p") if event.start_dt else "No date"
                except:
                    formatted_date: str = str(event.start.date_time) if event.start else "No date"
                
                # Create a container for each event for better styling
                with st.container():
                    col1, col2 = st.columns([3, 1])
                    with col1:
                        st.write(f"**{event.summary}**")
                        st.write(f"*{formatted_date}*")
                        # Display the calendar name
                        st.write(f"📅 {event.calendar_id or 'Unknown Calendar'}")
                        if event.description:
                            with st.expander("Description"):
                                st.write(event.description)
                    
                    with col2:
                        # Dropdown for project selection
                        selected_project = st.selectbox(
                            "Project",
                            options=list(project_options.keys()),
                            format_func=lambda x: project_options[x],
                            key=f"project_select_{event.id}"
                        )
                        
                        # Button to save classification
                        if st.button("Classify", key=f"classify_btn_{event.id}"):
                            # We need the database ID, not the Google event ID
                            db_event = None
                            db = None
                            try:
                                # Get the database event ID
                                db = database.get_db_session()
                                db_event = db.query(database.EventModel).filter(
                                    database.EventModel.event_id == event.id
                                ).first()
                                
                                if db_event:
                                    success: bool = database.update_event_project(db_event.id, selected_project)
                                    if success:
                                        st.success(f"Event classified as '{project_options[selected_project]}'")
                                    else:
                                        st.error("Failed to update project.")
                                else:
                                    st.error(f"Could not find event with ID {event.id} in database")
                            except Exception as e:
                                st.error(f"Error classifying event: {e}")
                            finally:
                                if db:
                                    db.close()
                    
                    st.divider()
    
    elif classification_selection == "Auto-Classification":
        st.subheader("Automatic Event Classification")
        st.write("Use AI to automatically classify events based on their titles and descriptions.")
        
        # Check if OpenAI API key is configured
        openai_key = os.getenv("OPENAI_API_KEY", "")
        if not openai_key:
            st.warning("OpenAI API key not found in environment variables. Auto-classification requires this to be set.")
        else:
            # Button to trigger auto-classification
            if st.button("Run Auto-Classification", type="primary"):
                try:
                    with st.spinner("Classifying events..."):
                        # Get unclassified events
                        limit: int = 100
                        events_to_classify: List[CalendarEvent] = database.get_unclassified_events(limit, include_past=True)
                        
                        if not events_to_classify:
                            st.info("No unclassified events to process.")
                        else:
                            results: List[Tuple[str, Optional[int], str, float]] = auto_classify_events(limit)
                            st.success(f"Auto-classification completed! {len(results)} events processed.")
                            
                            # Display results
                            for event_id, project_id, title, confidence in results:
                                project_name = project_options.get(project_id, "Unknown Project")
                                
                                # Find the event in the list
                                event: Optional[CalendarEvent] = next((e for e in events_to_classify if e.id == event_id), None)
                                
                                if event:
                                    # Format the date
                                    try:
                                        formatted_date: str = event.start_dt.strftime("%a, %b %d, %Y %I:%M %p") if event.start_dt else "No date"
                                    except:
                                        formatted_date: str = str(event.start.date_time) if event.start else "No date"
                                    
                                    # Get calendar name - use calendar_id directly
                                    with st.container():
                                        st.write(f"**{title}** → {project_name} (Confidence: {confidence:.0%})")
                                        st.write(f"*{formatted_date}*")
                                        st.write(f"📅 {event.calendar_id or 'Unknown Calendar'}")
                                        st.divider()
                                else:
                                    st.write(f"**{title}** → {project_name} (Confidence: {confidence:.0%})")
                except Exception as e:
                    st.error(f"Error during auto-classification: {e}")
                    logger.error(f"Auto-classification error: {e}")
    
    elif classification_selection == "Classified Events":
        st.subheader("Classified Events")
        
        classified_events: List[CalendarEvent] = database.get_classified_events(100)
        
        if not classified_events:
            st.info("No classified events found. Use Manual or Auto-Classification to classify some events first.")
        else:
            st.write(f"Found {len(classified_events)} classified events.")
            
            # Group by project for better organization
            by_project: Dict[str, List[CalendarEvent]] = {}
            for event in classified_events:
                project_name: str = event.project_name or "Unassigned"
                if project_name not in by_project:
                    by_project[project_name] = []
                by_project[project_name].append(event)
            
            # Display events by project
            for project_name, events in by_project.items():
                with st.expander(f"{project_name} ({len(events)} events)"):
                    for event in events:
                        try:
                            formatted_date = event.start_dt.strftime("%a, %b %d, %Y %I:%M %p") if event.start_dt else "No date"
                        except:
                            formatted_date = str(event.start.date_time) if event.start else "No date"
                        
                        with st.container():
                            st.write(f"**{event.summary}**")
                            st.write(f"*{formatted_date}*")
                            # Display the calendar name
                            st.write(f"📅 {event.calendar_id or 'Unknown Calendar'}")
                            if event.description:
                                with st.expander("Description"):
                                    st.write(event.description)
                            st.divider()
    
    elif classification_selection == "MLflow Testing":
        st.subheader("MLflow Testing")
        st.write("Test the MLflow connection and view experiments.")
        
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("Test MLflow Connection", type="primary"):
                with st.spinner("Testing MLflow connection..."):
                    # Import the test_mlflow function from tests
                    from tests.test_classification import test_mlflow
                    # Call the test_mlflow function
                    if test_mlflow():
                        st.success("MLflow test successful! A test run has been created.")
                        # Create a link to view the test run
                        mlflow_url: str = classification.MLFLOW_TRACKING_URI
                        st.markdown(f"[View MLflow Dashboard]({mlflow_url})")
                    else:
                        st.error("MLflow test failed. Is the MLflow server running?")
                        st.info("Run the following command in a terminal to start MLflow:\n\n`mlflow ui`")
        
        with col2:
            if st.button("Create Test Experiment"):
                with st.spinner("Creating test experiment..."):
                    # Import the create_test_experiment function from tests
                    from tests.test_classification import create_test_experiment
                    # Call the create_test_experiment function
                    create_test_experiment()
                    st.success("Test experiment created!")
                    
                    # Create a link to view the experiment
                    experiment_id: str = classification.EXPERIMENT_NAME
                    mlflow_url: str = classification.MLFLOW_TRACKING_URI
                    st.markdown(f"[View Experiment: {experiment_id}]({mlflow_url}/#/experiments/)")

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
    projects: List[Project] = database.get_projects()
    
    # Create columns for project metrics
    col1, col2, col3 = st.columns(3)
    with col1:
        project_count: int = len(projects)
        st.metric("Total Projects", project_count)
    
    # New Project Creation Form
    with st.expander("Create New Project", expanded=False):
        st.write("Add a new project for classifying events")
        new_project_name: str = st.text_input("Project Name")
        new_project_hours: int = st.number_input("Estimated Weekly Hours", min_value=1, max_value=168, value=10)
        new_project_priority: int = st.number_input("Priority (1=highest)", min_value=1, max_value=10, value=3)
        new_project_desc: str = st.text_area("Description")
        
        if st.button("Create Project"):
            if new_project_name:
                try:
                    project_id: int = database.add_project(new_project_name, new_project_hours, new_project_priority, new_project_desc)
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
        df: pd.DataFrame = pd.DataFrame(projects, columns=['id', 'name', 'estimated_hours', 'priority', 'description'])
        
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