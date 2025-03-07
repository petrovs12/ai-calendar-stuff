# Google Calendar API Integration Guide

This guide explains how to use the Google Calendar API scripts in this project and troubleshoot common authentication issues.

## Prerequisites

1. Python 3.6 or higher
2. Google Cloud project with Calendar API enabled
3. OAuth 2.0 credentials for a Desktop application

## Setup

1. Make sure you have the required Python packages:
   ```
   pip install google-api-python-client google-auth-httplib2 google-auth-oauthlib
   ```

2. Place your `credentials.json` file in the project root directory.

## Authentication Methods

This project provides two different ways to authenticate with the Google Calendar API:

### Method 1: Browser-based Authentication (test_client.py)

This method opens a browser window automatically to complete the OAuth flow:

```
python test_client.py
```

### Method 2: Manual Code Authentication (auth_with_code.py)

This method is useful when browser-based authentication doesn't work:

```
python auth_with_code.py
```

## Troubleshooting Authentication Issues

### "App Not Verified" Error

If you see a message like "This app isn't verified" or "Calendar has not completed the Google verification process", follow these steps:

1. **Add yourself as a test user:**
   - Go to the [Google Cloud Console](https://console.cloud.google.com/)
   - Select your project
   - Navigate to "APIs & Services" > "OAuth consent screen"
   - In the "Test users" section, click "Add Users"
   - Add your Google email address
   - Save the changes

2. **Use the "Advanced" option:**
   - When you see the warning screen, click "Advanced" at the bottom
   - Click "Go to [Your App Name] (unsafe)"
   - Continue with the authentication process

### Other Authentication Issues

1. **Delete existing tokens:**
   If you've changed scopes or are having authentication issues, delete the `token.pickle` file and try again.

2. **Check your credentials:**
   Make sure your `credentials.json` file is valid and contains the correct client ID and secret.

3. **Verify API is enabled:**
   Ensure the Google Calendar API is enabled in your Google Cloud project.

## Using the API

Once authenticated, the scripts will:
1. Fetch the next 10 events from your primary calendar
2. Display the start time and summary of each event

## Additional Resources

- [Google Calendar API Documentation](https://developers.google.com/calendar/api/guides/overview)
- [Google OAuth 2.0 for Desktop Apps](https://developers.google.com/identity/protocols/oauth2/native-app) 