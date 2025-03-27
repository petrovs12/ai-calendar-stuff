import os
import pickle
import datetime
from typing import List, Dict, Any, Optional, TypedDict, Union, Tuple
import logging
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from datetime import timezone

# Import our Pydantic models
from models import CalendarEvent
from timeutils import get_time_of_day, TimeOfDay
# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Define the OAuth scope (read-only in this case)
SCOPES = ['https://www.googleapis.com/auth/calendar.readonly']

# Type definitions for Google Calendar data
class CalendarDateTime(TypedDict):
    """Calendar date/time representation with native datetime as primary field."""
    native_dt: datetime.datetime  # Native Python datetime object (primary field)

class CalendarInfo(TypedDict):
    id: str
    summary: str
    primary: bool

# Simplified DateTimeComponents using just a datetime object
class DateTimeComponents(TypedDict):
    """Simplified datetime components extracted from an event."""
    dt: datetime.datetime  # Native Python datetime object
    time_of_day: str       # 'morning', 'afternoon', or 'evening'

def ensure_aware(dt: datetime.datetime) -> datetime.datetime:
    if dt.tzinfo is None or dt.tzinfo.utcoffset(dt) is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt

def parse_datetime(dt_str: str) -> datetime.datetime:
    """
    Parse a datetime string into a datetime object, handling different formats.
    
    Args:
        dt_str: DateTime string from Google Calendar API
        
    Returns:
        Python datetime object
    """
    if not dt_str:
        return datetime.datetime.now()
        
    try:
        # Remove timezone info for simplicity
        if 'Z' in dt_str:
            dt_str = dt_str.replace('Z', '+00:00')
            
        # Parse the datetime string
        return datetime.datetime.fromisoformat(dt_str)
    except Exception as e:
        logger.warning(f"Could not parse datetime string: {dt_str}, {e}")
        return datetime.datetime.now()

def extract_datetime_components(event: Dict[str, Any]) -> DateTimeComponents:
    """
    Extract datetime components from a calendar event.
    
    Args:
        event: Google Calendar event dictionary
        
    Returns:
        DateTimeComponents with native datetime object
    """
    # Get the datetime object for the event start
    dt = None
    
    if 'start_dt' in event:
        # Use pre-existing datetime if available
        dt = event['start_dt']
    elif 'start' in event:
        start = event['start']
        if 'native_dt' in start:
            # Use pre-existing native_dt if available
            dt = start['native_dt']
        elif 'dateTime' in start:
            # Parse from dateTime string
            dt = parse_datetime(start['dateTime'])
        elif 'date' in start:
            # Parse from date string
            dt = parse_datetime(start['date'])
    # Don't set a default time if we couldn't extract a valid datetime
    if not dt:
        dt = None
        logger.warning(f"Could not extract datetime from event")
    # Create the simplified components
    result: DateTimeComponents = {
        'dt': dt,
        'time_of_day': get_time_of_day(dt) if dt else ''
    }
    
    return result

def get_calendar_service():
    """
    Authenticate using desktop credentials and return the Google Calendar API service object.
    This uses a token.pickle file to cache the credentials.
    
    Returns:
        googleapiclient.discovery.Resource: The Google Calendar API service.
    """
    logger.info("Starting authentication process")
    creds = None
    # Check if token.pickle exists
    if os.path.exists('token.pickle'):
        logger.info("Found existing token.pickle file")
        with open('token.pickle', 'rb') as token:
            creds = pickle.load(token)
            logger.info("Loaded credentials from token.pickle")
    else:
        logger.info("No token.pickle file found")
    
    # If there are no (valid) credentials available, start the OAuth flow.
    if not creds or not creds.valid:
        logger.info("Credentials not valid, need to authenticate or refresh")
        if creds and creds.expired and creds.refresh_token:
            logger.info("Refreshing expired credentials")
            try:
                creds.refresh(Request())
                logger.info("Credentials refreshed successfully")
            except Exception as e:
                logger.error(f"Error refreshing credentials: {e}")
                # If refresh fails, proceed to new authentication
                creds = None
        else:
            logger.info("Starting new OAuth flow")
            try:
                # Look for credentials file
                credentials_file = 'credentials_desktop.json'
                if not os.path.exists(credentials_file):
                    logger.error(f"Credentials file not found: {credentials_file}")
                    raise FileNotFoundError(f"Credentials file not found: {credentials_file}")
                
                # Load desktop app credentials
                flow = InstalledAppFlow.from_client_secrets_file(credentials_file, SCOPES)
                logger.info(f"Starting local server for authentication")
                creds = flow.run_local_server(port=0)
                logger.info("Authentication successful")
            except Exception as e:
                logger.error(f"OAuth flow error: {e}")
                raise
        
        # Save the credentials for the next run
        try:
            with open('token.pickle', 'wb') as token:
                pickle.dump(creds, token)
            logger.info("Credentials saved to token.pickle")
        except Exception as e:
            logger.error(f"Error saving credentials: {e}")
    else:
        logger.info("Using existing valid credentials")
    
    # Build and return the Calendar API service object.
    try:
        service = build('calendar', 'v3', credentials=creds)
        logger.info("Google Calendar API service built successfully")
        return service
    except Exception as e:
        logger.error(f"Error building service: {e}")
        raise

def list_calendars(service) -> List[CalendarInfo]:
    """
    List all calendars available in the user's account.
    
    Args:
        service: Authenticated Google Calendar API service instance.
        
    Returns:
        A list of dictionaries containing calendar information (id, summary, primary).
    """
    logger.info("Fetching list of available calendars")
    try:
        calendars_result = service.calendarList().list().execute()
        calendars = calendars_result.get('items', [])
        logger.info(f"Found {len(calendars)} calendars")
        
        # Format the calendar information
        formatted_calendars: List[CalendarInfo] = []
        for calendar in calendars:
            calendar_id = calendar['id']
            calendar_summary = calendar.get('summary', 'Unnamed Calendar')
            is_primary = calendar.get('primary', False)
            
            formatted_calendars.append({
                'id': calendar_id,
                'summary': calendar_summary,
                'primary': is_primary
            })
            
            logger.info(f"Calendar: {calendar_summary} (ID: {calendar_id}, Primary: {is_primary})")
        
        # Sort calendars to put primary calendar first
        formatted_calendars.sort(key=lambda c: (not c['primary'], c['summary']))
        return formatted_calendars
    except Exception as e:
        logger.error(f"Error listing calendars: {e}")
        return []

def fetch_events(service: Any, max_results: int = 100, calendar_ids: Optional[List[str]] = None, days_lookahead: int = 90) -> List[CalendarEvent]:
    """Fetch events from specified calendars."""
    if not calendar_ids:
        calendar_ids = ['primary']
    
    # Calculate time bounds
    now = datetime.datetime.utcnow().isoformat() + 'Z'  # 'Z' indicates UTC time
    future = (datetime.datetime.utcnow() + datetime.timedelta(days=days_lookahead)).isoformat() + 'Z'
    
    # Fetch events from all specified calendars
    all_events = []
    
    for calendar_id in calendar_ids:
        try:
            logger.info(f"Fetching events from calendar: {calendar_id}")
            
            events_result = service.events().list(
                calendarId=calendar_id,
                timeMin=now,
                timeMax=future,
                maxResults=max_results,
                singleEvents=True,
                orderBy='startTime'
            ).execute()
            
            events = events_result.get('items', [])
            logger.info(f"Found {len(events)} events in calendar {calendar_id}")
            
            # Process each event
            for event in events:
                # Add calendar ID to the event
                event['calendar_id'] = calendar_id
                # Create a CalendarEvent using the Pydantic model
                calendar_event = CalendarEvent.from_google_dict(event)
                all_events.append(calendar_event)
                
        except Exception as e:
            logger.error(f"Error fetching events from calendar {calendar_id}: {e}")
            logger.exception(e)
    
    # Sort all events by start time
    if all_events:
        # Sort CalendarEvent objects by their start_dt property
        all_events.sort(key=lambda e: e.start_dt or datetime.datetime.max)
            
    return all_events

def get_calendar_name(service, calendar_id: str) -> str:
    """
    Get the name of a calendar from its ID.
    
    Args:
        service: Authenticated Google Calendar API service.
        calendar_id: The ID of the calendar.
        
    Returns:
        The name of the calendar, or the ID if not found.
    """
    try:
        calendar = service.calendarList().get(calendar_id=calendar_id).execute()
        return calendar.get('summary', calendar_id)
    except Exception as e:
        logger.error(f"Error getting calendar info for {calendar_id}: {e}")
        return calendar_id