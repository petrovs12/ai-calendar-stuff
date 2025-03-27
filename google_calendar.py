import os
import pickle
import datetime
from typing import List, Dict, Any, Optional, TypedDict, Union, Tuple
import logging
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Define the OAuth scope (read-only in this case)
SCOPES = ['https://www.googleapis.com/auth/calendar.readonly']

# Type definitions for Google Calendar data
class CalendarDateTime(TypedDict):
    """Calendar date/time representation with native datetime as primary field."""
    native_dt: datetime.datetime  # Native Python datetime object (primary field)

class CalendarEventAttendee(TypedDict):
    email: str
    responseStatus: Optional[str]
    displayName: Optional[str]
    self: Optional[bool]
    organizer: Optional[bool]
    resource: Optional[bool]

class CalendarEvent(TypedDict):
    """Google Calendar event with native datetime objects."""
    kind: str
    etag: str
    id: str
    status: str
    htmlLink: Optional[str]
    created: str
    updated: str
    summary: str
    description: Optional[str]
    location: Optional[str]
    creator: Dict[str, Any]
    organizer: Dict[str, Any]
    start: CalendarDateTime
    end: CalendarDateTime
    start_dt: datetime.datetime     # Native start datetime
    end_dt: datetime.datetime       # Native end datetime
    recurringEventId: Optional[str]
    originalStartTime: Optional[CalendarDateTime]
    iCalUID: str
    sequence: int
    attendees: Optional[List[CalendarEventAttendee]]
    extendedProperties: Optional[Dict[str, Any]]
    hangoutLink: Optional[str]
    conferenceData: Optional[Dict[str, Any]]
    reminders: Optional[Dict[str, Any]]
    eventType: str
    calendarId: Optional[str]  # Added by our code, not part of Google API

class CalendarInfo(TypedDict):
    id: str
    summary: str
    primary: bool

# Simplified DateTimeComponents using just a datetime object
class DateTimeComponents(TypedDict):
    """Simplified datetime components extracted from an event."""
    dt: datetime.datetime  # Native Python datetime object
    time_of_day: str       # 'morning', 'afternoon', or 'evening'

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

def get_time_of_day(dt: datetime.datetime) -> str:
    """
    Get time of day category based on hour.
    
    Args:
        dt: Datetime object
        
    Returns:
        String representing time of day: 'morning', 'afternoon', or 'evening'
    """
    hour = dt.hour
    if 5 <= hour < 12:
        return 'morning'
    elif 12 <= hour < 17:
        return 'afternoon'
    else:
        return 'evening'

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
        formatted_calendars.sort(key=lambda x: (not x.get('primary', False), x.get('summary', '')))
        
        return formatted_calendars
    except Exception as e:
        logger.error(f"Error listing calendars: {e}")
        raise

def fetch_events(service, max_results: int = 10, calendar_ids: Optional[List[str]] = None,days_lookahead: int = 60) -> List[CalendarEvent]:
    """
    Fetch upcoming events from the specified calendars.
    
    Args:
        service: Authenticated Google Calendar API service instance.
        max_results: Maximum number of events to return per calendar.
        calendar_ids: List of calendar IDs to fetch events from. If None, only primary calendar is used.
        
    Returns:
        A list of events from all specified calendars with native datetime objects.
    """
    # If no calendar IDs provided, use primary calendar
    if not calendar_ids:
        calendar_ids = ['primary']
        logger.info("No calendar IDs provided, using primary calendar")
    else:
        logger.info(f"Fetching events from {len(calendar_ids)} calendars: {calendar_ids}")
    
    now = datetime.datetime.utcnow().isoformat() + 'Z'  # 'Z' indicates UTC time
    logger.info(f"Fetching events starting from {now}")
    
    all_events: List[CalendarEvent] = []
    
    # Fetch events from each calendar
    for calendar_id in calendar_ids:
        logger.info(f"Fetching up to {max_results} events from calendar {calendar_id}")
        try:
            events_result = service.events().list(
                calendarId=calendar_id,
                timeMin=now,
                maxResults=max_results,
                singleEvents=True,
                orderBy='startTime'
            ).execute()
            
            events = events_result.get('items', [])
            logger.info(f"Found {len(events)} events in calendar {calendar_id}")
            
            # Add calendar ID and native datetime objects to each event
            for event in events:
                event['calendarId'] = calendar_id
                
                # Parse start time
                if 'start' in event:
                    start = event['start']
                    
                    # Extract the string representation
                    start_str = start.get('dateTime', start.get('date', ''))
                    
                    # Parse into a native datetime
                    start_dt = parse_datetime(start_str)
                    
                    # Add native datetime to both the start dict and event root
                    start['native_dt'] = start_dt
                    event['start_dt'] = start_dt
                
                # Parse end time
                if 'end' in event:
                    end = event['end']
                    
                    # Extract the string representation
                    end_str = end.get('dateTime', end.get('date', ''))
                    
                    # Parse into a native datetime
                    end_dt = parse_datetime(end_str)
                    
                    # Add native datetime to both the end dict and event root
                    end['native_dt'] = end_dt
                    event['end_dt'] = end_dt
                
                # Log the event
                event_id = event.get('id', 'unknown')
                summary = event.get('summary', 'No title')
                logger.debug(f"Event: {summary} at {event['start_dt']} (ID: {event_id})")
            
            all_events.extend(events)
        except Exception as e:
            logger.error(f"Error fetching events from calendar {calendar_id}: {e}")
            print(f"Error fetching events from calendar {calendar_id}: {e}")
    
    # Sort all events by start datetime
    # Ensure we're comparing datetimes with consistent timezone awareness
    # Use a timezone-naive datetime as default to avoid comparison issues
    default_dt = datetime.datetime.now().replace(tzinfo=None)
    # Sort events by start datetime (handling None values and timezone info)
    # all_events.sort(key=lambda x: x.get('start_dt', default_dt).replace(tzinfo=None) if x.get('start_dt') else default_dt)
    # logger.info(f"Total events fetched from all calendars: {len(all_events)}")
    
    # Filter events to only include those in the next 60 days
    max_date = default_dt + datetime.timedelta(days=days_lookahead)
    # Use list comprehension to filter future events
    filtered_events = [event for event in all_events 
                      if event.get('start_dt') and event.get('start_dt').replace(tzinfo=None) <= max_date]
    all_events = filtered_events
    return filtered_events

def get_calendar_name(service, calendar_id: str) -> str:
    """
    Get the name of a calendar by its ID.
    
    Args:
        service: Authenticated Google Calendar API service instance.
        calendar_id: ID of the calendar to look up.
        
    Returns:
        The name (summary) of the calendar, or the ID if not found.
    """
    logger.info(f"Looking up name for calendar ID: {calendar_id}")
    if calendar_id == 'primary':
        # For primary calendar, get the actual calendar details
        try:
            calendar = service.calendars().get(calendarId=calendar_id).execute()
            name = calendar.get('summary', calendar_id)
            logger.info(f"Primary calendar name: {name}")
            return name
        except Exception as e:
            logger.error(f"Error getting primary calendar details: {e}")
            return "Primary Calendar"
    
    try:
        calendar = service.calendarList().get(calendarId=calendar_id).execute()
        name = calendar.get('summary', calendar_id)
        logger.info(f"Calendar name for {calendar_id}: {name}")
        return name
    except Exception as e:
        logger.error(f"Error getting calendar name for {calendar_id}: {e}")
        return calendar_id