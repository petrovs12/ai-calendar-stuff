#!/usr/bin/env python3
"""
Desktop-based Google Calendar API Authentication
Uses InstalledAppFlow with a manual copy-paste approach
"""

import os
import pickle
from google_auth_oauthlib.flow import InstalledAppFlow

# Define the scopes
SCOPES = ['https://www.googleapis.com/auth/calendar.readonly']

def main():
    print("=== Google Calendar Desktop Authentication ===")
    
    # Create flow
    flow = InstalledAppFlow.from_client_secrets_file(
        'token.json', SCOPES,
        # Force manual authentication mode
        redirect_uri='urn:ietf:wg:oauth:2.0:oob'
    )
    
    # Generate auth URL for user
    auth_url, _ = flow.authorization_url(prompt='consent')
    
    print("\nSTEP 1: Go to this URL in your browser:")
    print(f"\n{auth_url}\n")
    print("STEP 2: Sign in and authorize the app")
    print("STEP 3: Copy the authorization code from the browser")
    
    # Get authorization code from user
    code = input("\nEnter the authorization code: ").strip()
    
    # Exchange code for credentials
    flow.fetch_token(code=code)
    creds = flow.credentials
    
    # Save credentials
    with open('token.pickle', 'wb') as f:
        pickle.dump(creds, f)
    
    print("\n✅ SUCCESS! Authentication complete.")
    print("📁 Credentials saved to 'token.pickle'")
    print("You can now run your calendar script.")

if __name__ == "__main__":
    main() 