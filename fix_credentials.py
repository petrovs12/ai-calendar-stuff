#!/usr/bin/env python3
"""
This script adds additional redirect URIs to your Google OAuth credentials file.
"""

import json
import os

def main():
    # Path to credentials file
    creds_file = 'token.json'
    
    # Check if the file exists
    if not os.path.exists(creds_file):
        print(f"Error: {creds_file} not found.")
        return
    
    # Load the credentials file
    with open(creds_file, 'r') as f:
        creds = json.load(f)
    
    # Print current redirect URIs
    if 'web' in creds and 'redirect_uris' in creds['web']:
        print("Current redirect URIs:")
        for uri in creds['web']['redirect_uris']:
            print(f"  - {uri}")
    else:
        print("No redirect URIs found in credentials file.")
        return
    
    # Add new redirect URIs
    new_uris = [
        "http://localhost:63775/",  # The port from the error message
        "http://127.0.0.1:63775/",
        "http://localhost:0/",      # Wildcard port
        "http://127.0.0.1:0/"
    ]
    
    # Check if URIs already exist
    for uri in new_uris:
        if uri in creds['web']['redirect_uris']:
            print(f"URI already exists: {uri}")
        else:
            creds['web']['redirect_uris'].append(uri)
            print(f"Added new URI: {uri}")
    
    # Also add to javascript_origins if it exists
    if 'javascript_origins' in creds['web']:
        js_origins = [
            "http://localhost:63775",
            "http://127.0.0.1:63775",
            "http://localhost:0",
            "http://127.0.0.1:0"
        ]
        
        for origin in js_origins:
            if origin in creds['web']['javascript_origins']:
                print(f"Origin already exists: {origin}")
            else:
                creds['web']['javascript_origins'].append(origin)
                print(f"Added new origin: {origin}")
    
    # Save the updated credentials file
    with open(creds_file, 'w') as f:
        json.dump(creds, f)
    
    print("\nCredentials file updated successfully!")
    print("IMPORTANT: You need to also add these redirect URIs to your Google Cloud Console:")
    for uri in new_uris:
        print(f"  - {uri}")
    print("\nGo to https://console.cloud.google.com/apis/credentials")
    print("Select your OAuth 2.0 Client ID")
    print("Add the URIs to 'Authorized redirect URIs' section")
    print("Save the changes\n")
    print("After updating in Google Cloud Console, try running your script again.")

if __name__ == "__main__":
    main() 