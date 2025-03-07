import os
import pickle
import datetime
import logging
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Define the OAuth scope (read-only in this case)
SCOPES = ['https://www.googleapis.com/auth/calendar.readonly']

def get_calendar_service():
    """
    Authenticate using desktop credentials and return the Google Calendar API service object.
    This uses a token.pickle file to cache the credentials.
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

def list_calendars(service):
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
        formatted_calendars = []
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

def fetch_events(service, max_results=10, calendar_ids=None):
    """
    Fetch upcoming events from the specified calendars.
    
    Args:
        service: Authenticated Google Calendar API service instance.
        max_results: Maximum number of events to return per calendar.
        calendar_ids: List of calendar IDs to fetch events from. If None, only primary calendar is used.
        
    Returns:
        A list of events from all specified calendars.
    """
    # If no calendar IDs provided, use primary calendar
    if not calendar_ids:
        calendar_ids = ['primary']
        logger.info("No calendar IDs provided, using primary calendar")
    else:
        logger.info(f"Fetching events from {len(calendar_ids)} calendars: {calendar_ids}")
    
    now = datetime.datetime.utcnow().isoformat() + 'Z'  # 'Z' indicates UTC time
    logger.info(f"Fetching events starting from {now}")
    
    all_events = []
    
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
            
            # Add calendar ID to each event for reference
            for event in events:
                event['calendarId'] = calendar_id
                event_id = event.get('id', 'unknown')
                summary = event.get('summary', 'No title')
                start = event['start'].get('dateTime', event['start'].get('date', 'unknown'))
                logger.debug(f"Event: {summary} at {start} (ID: {event_id})")
            
            all_events.extend(events)
        except Exception as e:
            logger.error(f"Error fetching events from calendar {calendar_id}: {e}")
            print(f"Error fetching events from calendar {calendar_id}: {e}")
    
    # Sort all events by start time
    all_events.sort(key=lambda x: x['start'].get('dateTime', x['start'].get('date')))
    logger.info(f"Total events fetched from all calendars: {len(all_events)}")
    
    return all_events

def get_calendar_name(service, calendar_id):
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