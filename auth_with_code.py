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
    """Shows basic usage of the Google Calendar API using manual authorization code entry.
    This is useful when automatic browser authentication doesn't work.
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
            print("\n=== Google Calendar API Manual Authentication ===")
            print("This script uses manual code entry instead of automatic browser authentication.")
            
            try:
                # Create the flow using the client secrets file
                flow = InstalledAppFlow.from_client_secrets_file(
                    'credentials.json', SCOPES)
                
                # Tell the user to go to the authorization URL
                auth_url, _ = flow.authorization_url(
                    access_type='offline',
                    include_granted_scopes='true')
                
                print("\n1. Go to this URL in your browser:")
                print(f"{auth_url}")
                print("\n2. If you see a warning about 'unverified app':")
                print("   - Click 'Advanced' and then 'Go to [app name] (unsafe)'")
                print("3. Sign in with your Google account")
                print("4. Grant the requested permissions")
                print("5. You'll be redirected to a page that says 'The authentication flow has completed.'")
                print("6. Copy the entire URL from your browser's address bar")
                
                # Get the authorization code from the user
                code = input('\nEnter the URL you were redirected to: ').strip()
                
                # If the user entered the full redirect URL, extract just the code
                if "code=" in code:
                    code = code.split("code=")[1].split("&")[0]
                
                # Exchange the authorization code for credentials
                flow.fetch_token(code=code)
                creds = flow.credentials
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
    now = datetime.datetime.utcnow().isoformat() + 'Z'  # 'Z' indicates UTC time
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