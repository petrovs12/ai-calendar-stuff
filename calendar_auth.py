#!/usr/bin/env python3
"""
Google Calendar Authentication Helper

This script helps you authenticate with Google Calendar API and creates a token.pickle
file that can be used by other scripts.
"""

from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
import pickle
import os

# Define the scopes
SCOPES = ['https://www.googleapis.com/auth/calendar.readonly']

def main():
    creds = None
    # Check if token.pickle exists
    if os.path.exists('token.pickle'):
        print("Found existing token.pickle, trying to use it...")
        with open('token.pickle', 'rb') as token:
            creds = pickle.load(token)
        
        if creds and creds.valid:
            print("Credentials are valid! You can now use them in your application.")
            return
        
        if creds and creds.expired and creds.refresh_token:
            print("Token expired, refreshing...")
            try:
                creds.refresh(Request())
                print("Token refreshed successfully!")
            except Exception as e:
                print(f"Error refreshing token: {e}")
                creds = None
    
    # If we don't have valid credentials, start the OAuth flow
    if not creds:
        print("Starting new OAuth flow...")
        try:
            # Clear browser cookies first
            print("\nIMPORTANT: For best results, please clear your browser cookies or use private/incognito mode when opening the auth URL.\n")
            
            # Create flow using client secrets file
            flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
            
            # Run local server - let it choose any available port
            creds = flow.run_local_server(port=63775)
            
            # Save the credentials for the next run
            with open('token.pickle', 'wb') as token:
                pickle.dump(creds, token)
            print(f"Authentication successful! Credentials saved to token.pickle")
        except Exception as e:
            print(f"Authentication error: {e}")
            return
    
    print("\nYou can now use these credentials in your application.")
    print("Example usage in your Python code:")
    print("-----------------------------------")
    print("from google.oauth2.credentials import Credentials")
    print("from googleapiclient.discovery import build")
    print("import pickle")
    print("")
    print("# Load credentials from file")
    print("with open('token.pickle', 'rb') as token:")
    print("    creds = pickle.load(token)")
    print("")
    print("# Build the service")
    print("service = build('calendar', 'v3', credentials=creds)")
    print("# Now you can use 'service' to interact with Google Calendar API")

if __name__ == "__main__":
    main() 