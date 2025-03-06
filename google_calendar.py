import os
import datetime
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

# OAuth scope for Google Calendar (read-only events access by default).
# If modifying this scope, delete any stored token.json to re-authenticate.
SCOPES = ["https://www.googleapis.com/auth/calendar.readonly"]

def get_calendar_service():
    """
    Authenticate with Google OAuth and return a Google Calendar API service object.
    Uses credentials from environment variables and token storage for reuse.
    """
    creds = None
    # Token file stores the user's access and refresh tokens, created after first auth.
    if os.path.exists("token.json"):
        creds = Credentials.from_authorized_user_file("token.json", SCOPES)
    # If no valid credentials available, initiate OAuth flow.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            # Refresh the expired token (no user intervention needed)
            creds.refresh(Request())
        else:
            # Load client secrets from environment variables
            client_config = {
                "installed": {
                    "client_id": os.getenv("GOOGLE_CLIENT_ID"),
                    "client_secret": os.getenv("GOOGLE_CLIENT_SECRET"),
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": "https://oauth2.googleapis.com/token",
                    "redirect_uris": ["http://localhost"]
                }
            }
            flow = InstalledAppFlow.from_client_config(client_config, SCOPES)
            creds = flow.run_local_server(port=0)  # Opens browser for authentication
        # Save the credentials for the next run
        with open("token.json", "w") as token_file:
            token_file.write(creds.to_json())
    # Build the Calendar API service
    service = build("calendar", "v3", credentials=creds)
    return service

def fetch_events(service, max_results=100):
    """
    Fetch upcoming events from the user's calendar.
    Returns a list of events occurring from now onwards.
    """
    now = datetime.datetime.utcnow().isoformat() + "Z"  # 'Z' indicates UTC time
    events_result = service.events().list(
        calendarId=os.getenv("GOOGLE_CALENDAR_ID", "primary"),
        timeMin=now,
        maxResults=max_results,
        singleEvents=True,
        orderBy="startTime"
    ).execute()
    events = events_result.get("items", [])
    return events