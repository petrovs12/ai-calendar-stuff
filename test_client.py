from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
import os.path
import pickle
import datetime
import sys

# If modifying these SCOPES, delete the file token.pickle.
SCOPES = ['https://www.googleapis.com/auth/calendar.readonly']

def main():
    """Shows basic usage of the Google Calendar API.
    Lists the next 10 events on the user's calendar.
    """
    creds = None
    # The file token.pickle stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first
    # time.
    if os.path.exists('token.pickle'):
        with open('token.pickle', 'rb') as token:
            creds = pickle.load(token)
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            print("\n=== Google Calendar API Authentication ===")
            print("1. A browser window should open automatically.")
            print("2. If you see a warning about 'unverified app', click 'Advanced' and then 'Go to [app name] (unsafe)'")
            print("3. Sign in with your Google account that has access to the calendar.")
            print("4. Grant the requested permissions.\n")
            
            try:
                flow = InstalledAppFlow.from_client_secrets_file(
                    'credentials_desktop.json', SCOPES)
                creds = flow.run_local_server(port=0)
                print("Authentication successful!")
            except Exception as e:
                print(f"Authentication error: {e}")
                print("\nIf you're seeing 'app not verified' errors, you need to:")
                print("1. Go to Google Cloud Console: https://console.cloud.google.com/")
                print("2. Select your project")
                print("3. Go to 'APIs & Services' > 'OAuth consent screen'")
                print("4. Add your email as a test user")
                sys.exit(1)
                
        # Save the credentials for the next run
        with open('token.pickle', 'wb') as token:
            pickle.dump(creds, token)

    service = build('calendar', 'v3', credentials=creds)

    # Call the Calendar API
    now = datetime.datetime.utcnow().isoformat() + 'Z' # 'Z' indicates UTC time
    print('Getting the upcoming 10 events')
    events_result = service.events().list(calendarId='primary', timeMin=now,
                                          maxResults=10, singleEvents=True,
                                          orderBy='startTime').execute()
    events = events_result.get('items', [])

    if not events:
        print('No upcoming events found.')
    for event in events:
        start = event['start'].get('dateTime', event['start'].get('date'))
        print(start, event['summary'])

if __name__ == '__main__':
    main()