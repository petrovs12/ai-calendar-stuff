from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
import pickle
import os

def get_calendar_service():
    """Get an authorized Google Calendar API service instance."""
    # Check if token.pickle exists
    if not os.path.exists('token.pickle'):
        print("Error: token.pickle not found.")
        print("Please run calendar_auth.py first to authorize with Google Calendar.")
        return None
    
    # Load credentials from the saved token
    with open('token.pickle', 'rb') as token:
        creds = pickle.load(token)
    
    # Build and return the service
    return build('calendar', 'v3', credentials=creds)

def main():
    # Get the calendar service
    service = get_calendar_service()
    
    if not service:
        return
    
    print("Fetching calendar events...")
    
    # Call the Calendar API
    events_result = service.events().list(
        calendarId='primary',
        maxResults=10,
        singleEvents=True,
        orderBy='startTime'
    ).execute()
    
    events = events_result.get('items', [])
    
    # Print the events
    if not events:
        print('No upcoming events found.')
    else:
        print("\nUpcoming events:")
        for event in events:
            start = event['start'].get('dateTime', event['start'].get('date'))
            print(f"{start} - {event['summary']}")

if __name__ == "__main__":
    main()
