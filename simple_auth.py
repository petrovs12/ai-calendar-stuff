#!/usr/bin/env python3
"""
Simplified Google Calendar API Authentication Script
"""

import os
import json
import pickle
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request

# Define the scopes
SCOPES = ['https://www.googleapis.com/auth/calendar.readonly']

def main():
    print("=== Google Calendar API Authentication Helper ===")
    print("\nSTEP 1: Checking for existing credentials...")
    
    creds = None
    if os.path.exists('token.pickle'):
        print("Found existing token.pickle, attempting to use it...")
        with open('token.pickle', 'rb') as token:
            creds = pickle.load(token)
            
        if creds and creds.valid:
            print("✅ Existing credentials are valid!")
            return
    
    print("\nSTEP 2: Starting OAuth authentication flow...")
    print("\n⚠️  IMPORTANT BROWSER INSTRUCTIONS ⚠️")
    print("1. BEFORE opening the authorization URL, close ALL Google-related tabs")
    print("2. Clear your browser cookies or use incognito/private browsing")
    print("3. When the URL opens, you may need to sign in to your Google account")
    print("4. AFTER authorizing, if you get an error page saying:")
    print("   'This site can't be reached' or 'Connection refused'")
    print("   That's NORMAL! Look at THIS terminal for success message\n")
    
    input("Press ENTER when you're ready to continue...")
    
    print("\nSTEP 3: Creating OAuth flow...")
    try:
        # Use the credentials file
        flow = InstalledAppFlow.from_client_secrets_file('token.json', SCOPES)
        
        # Try a specific port
        print("Starting local server on port 8501...")
        creds = flow.run_local_server(port=8501)
        
        # Save the credentials for next time
        with open('token.pickle', 'wb') as token:
            pickle.dump(creds, token)
        
        print("\n✅ SUCCESS! Authentication complete.")
        print("📁 Credentials saved to 'token.pickle'")
        print("\nYou can now run your calendar script.")
    
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        print("\nTroubleshooting steps:")
        print("1. Make sure you've added all redirect URIs to Google Cloud Console")
        print("   Go to: https://console.cloud.google.com/apis/credentials")
        print("   Add: http://localhost:8501/")
        print("2. Make sure the Google Calendar API is enabled in your project")
        print("   Go to: https://console.cloud.google.com/apis/library/calendar-json.googleapis.com")
        print("3. Try using an incognito/private browser window")
        print("4. Check if port 8501 is already in use (close any Streamlit apps)")

if __name__ == "__main__":
    main() 