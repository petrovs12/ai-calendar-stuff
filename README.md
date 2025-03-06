# Lightweight Python Interview Scheduler – Project Plan

## Overview

This project aims to build a lightweight Python-based interview scheduling tool that helps schedule preparation time for interviews while integrating with calendar services. It will connect to Google Calendar to fetch events, schedule prep tasks with heuristics (ensuring ~30–50 hours of prep time before each interview), and provide a simple UI via Streamlit for visualization and management. The tool will prioritize ease of setup and future extensibility, including secure credential storage and potential expansion to other calendars (like Outlook). Key objectives include:
	•	Google Calendar Integration: Use Google’s Calendar API with the simplest authentication method (likely OAuth 2.0) to access multiple calendars and retrieve event data ￼ ￼.
https://endgrate.com/blog/how-to-get-calendar-events-with-the-google-calendar-api-in-python#:~:text=Before%20you%20can%20start%20interacting,the%20Google%20Calendar%20API%20securely
https://rollout.com/integration-guides/google-calendar/sdk/step-by-step-guide-to-building-a-google-calendar-api-integration-in-python
	•	Secure Credentials: Store API credentials and tokens in a .env file (or similar secure config) to keep secrets out of code and source control ￼.
    https://dev.to/jakewitcher/using-env-files-for-environment-variables-in-python-applications-55a1#:~:text=A%20,potentially%20sensitive%20information%20at%20risk
	•	Scheduling Heuristics: Implement a scheduling algorithm to allocate a fixed amount of preparation hours (e.g. 30–50 hours) before each interview, spread over several days (not last-minute).

	•	Open-Source Alternatives: Research existing open-source scheduling tools (e.g. “Atomic” – an open-source AI scheduler ￼) to see if they can be leveraged instead of building from scratch, or to draw inspiration.
    https://github.com/rush86999/atomic
	•	Streamlit UI: Provide a minimal web interface using Streamlit to visualize calendars and scheduled prep blocks, offering basic controls to manage the schedule.
	•	Future-Proofing: Design the system with flexibility for future improvements (better algorithms, additional calendar providers like Outlook ￼, etc.).
    https://dev.to/karanjot_s/connect-microsoft-outlook-calendar-to-django-application-561p#:~:text=Integrating%20Outlook%20Calendar%20with%20your,with%20the%20Outlook%20Calendar%20API

# 1. Google Calendar Integration

Approach: Leverage the Google Calendar API to connect to the user’s calendars and fetch event data. The integration will likely use Google’s official Python client libraries, which handle communication and data formatting. OAuth 2.0 will be used for authentication, as it’s the standard for Google APIs and ensures secure access ￼. (Using an API key alone is only viable for public calendars, so OAuth is the simplest secure method for private calendars.) Steps for integration:
https://rollout.com/integration-guides/google-calendar/sdk/step-by-step-guide-to-building-a-google-calendar-api-integration-in-python

	•	API Credentials: The user (or developer) must create a Google Cloud project and enable the Calendar API, then obtain OAuth 2.0 credentials (a client ID and secret) ￼. This process will be documented in the README. The credentials allow the app to request permission to read calendars on the user’s behalf.
https://dev.to/jakewitcher/using-env-files-for-environment-variables-in-python-applications-55a1#:~:text=A%20,potentially%20sensitive%20information%20at%20risk
	•	Consent Flow: On first run, the application will direct the user to Google’s consent page to grant access to their calendar. After authorization, an access token (and refresh token) is obtained for API calls. This token will be saved for reuse so that subsequent runs don’t require login every time.
	•	Multiple Calendars: The tool will fetch events from multiple calendars (e.g., both personal and team interview calendars). This can be done by querying the Calendar list via the API, then retrieving events from each calendar. Event data (title, start/end times, etc.) will be pulled and consolidated.
	•	Event Data Formatting: Retrieved events will be parsed into a Python-friendly structure (e.g., a list of events or a pandas DataFrame). Each event’s key details (date, time span, description, calendar source) will be available for analysis. This forms the “busy schedule” against which we’ll plan prep tasks.
	•	Analysis Prep: With events data available, the tool can analyze free time slots or identify the time window before each interview event. For example, if an interview event is on March 20 at 10 AM, the system will consider all free hours between “now” and that time for scheduling prep work.

# 2. Secure Credential Storage

Goal: Keep sensitive information (API keys, OAuth client secrets, tokens) out of the source code and store them safely. The project will use a .env file (environment variables) to hold credentials, which is a common best practice ￼. Key points:
	•	A .env.example template will be provided, listing the required variables (e.g., GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET, and perhaps GOOGLE_REFRESH_TOKEN or path to a credentials JSON). Users should copy this to .env and fill in their actual values.
	•	The .env file will not be committed to version control (it will be listed in .gitignore). This ensures client secrets or tokens aren’t exposed in the repository ￼.
	•	The application will load these environment variables at runtime (using a library like python-dotenv or via the OS environment) to configure the Google API client. For example, the OAuth flow will use the client ID/secret from env variables.
	•	Token Storage: After the OAuth flow, the obtained access/refresh token will be stored securely. One simple approach is to save it in a local JSON file (e.g., token.json) that is also listed in .gitignore. Alternatively, the token can be stored in an environment variable or a secure key store. For initial simplicity, a local file or env var will suffice, with clear instructions to keep it private.
	•	The README will include instructions on how to obtain Google API credentials and where to put them. It will also stress the importance of keeping credentials secure (e.g., not sharing the .env file). The use of environment variables ensures that sensitive keys are isolated from the codebase, and they won’t be accidentally printed or uploaded to a repo 
    https://dev.to/jakewitcher/using-env-files-for-environment-variables-in-python-applications-55a1#:~:text=A%20,potentially%20sensitive%20information%20at%20risk
    ￼. (For those wanting an extra layer, we might mention options like encrypting the .env or using a secrets manager, but these are optional enhancements.)
	•	In summary, this section of the project safeguards user data by combining secure credential handling with user-friendly setup steps (so non-experts can still configure the tool without risking security).

# 3. Heuristic-Based Scheduling System

Objective: Implement a scheduling mechanism that allocates a fixed amount of preparation time before each interview, following certain rules. The heuristic will ensure, for example, that 40 hours (adjustable between 30–50) of prep work are scheduled leading up to an interview, distributed across multiple days rather than last-minute. Key design points for the scheduling algorithm:
	•	Identify Interview Events: The tool will identify which events in the calendar are interviews (perhaps by certain keywords or by the user marking them). For each upcoming interview, we then determine how much prep time is required (could default to 40 hours, or allow the user to set a value).
	•	Calculate Available Slots: Using the calendar data, determine the free time slots between now (or a starting point) and the interview event. This will involve subtracting existing events (meetings, etc.) from the working hours of each day. The user may define working hours (e.g., 9am-5pm) or times they can do prep. We will consider each day’s availability.
	•	Distribute Prep Hours: Allocate the required prep hours into the available slots evenly across days. The heuristic might be: don’t schedule more than X hours of prep in one day (to avoid burnout). For instance, if 40 hours of prep are needed and there are 10 weekdays before the interview, schedule about 4 hours each day. If there are fewer days, the daily prep might increase (e.g., ~5 hours/day for 8 days to reach 40).
	•	Greedy Algorithm: A simple greedy approach will start scheduling prep blocks on the earliest available days, ensuring the total adds up to the target hours. For each day before the interview (moving backwards or forwards in time), assign a block of prep time (say 2-4 hour blocks) until the daily limit or the total is met. Continue until the sum of all prep blocks equals the needed hours. This ensures a strict amount of prep time is allocated. For flexibility, the range 30–50 hours could mean the tool defaults to 40 but allows adjustments per interview (based on difficulty or user preference).
	•	Avoid Last-Minute Cramming: The heuristic will ideally schedule at least some prep on each of the days leading up to the interview, rather than allowing all 40 hours to fall on the final 2-3 days. For example, if time is short (interview in 5 days), it might allocate ~8 hours per day for 5 days. If the interview is far out (say 15 days away), it might allocate ~3 hours per day over 13-14 days, leaving some free days if possible.
	•	Calendar Event Creation: Once the schedule is determined, the tool could create “Interview Prep” events on the calendar via the API for each planned block. Initially, we might not auto-create them (just show to the user), but as a future feature, the app can insert these prep events into the user’s Google Calendar (using calendar write access).
	•	User Overrides: In this initial version, the heuristic will be simple. The user can review the suggested prep schedule in the UI. If needed, they might manually adjust (delete or move prep blocks) – though manual adjustments would likely be outside the algorithm, possibly by editing in Google Calendar or via the UI if we allow drag-and-drop in the future.
	•	Validation: Ensure the scheduled prep blocks do not conflict with existing events (the algorithm should only use free time). Also make sure the last prep block ends at least a certain buffer before the actual interview (e.g., at least an hour before the interview start, so the candidate has a rest period).

This heuristic approach is straightforward to implement and gives a satisfying guarantee of preparation time. It is not fully optimized (in a computational sense) but should meet the goal of front-loading adequate prep. In the future, we can refine this with more advanced techniques, but first we’ll focus on getting this rule-based system working reliably.

# 4. Exploring Open-Source Alternatives (Motion/Reclaim.ai Alternatives)

Before implementing everything from scratch, it’s wise to explore whether existing open-source projects could fulfill part of these requirements. Motion and Reclaim.ai are popular scheduling tools (proprietary) that automatically arrange tasks and meetings. We’ll research analogous open-source projects:
	•	Atomic – “An open-source priority-driven AI scheduler to solve your time problems”, branded as “an alternative to Motion, Clockwise, Cal.ai & Reclaim” ￼. This project aims to automate time management using AI (even allowing natural language input to schedule events). We will evaluate Atomic’s capabilities — for example, does it already integrate with Google Calendar and schedule tasks? If Atomic (or parts of it) can be used directly or via API, it might save development effort. However, since Atomic is a more comprehensive AI assistant, it might be heavyweight for our needs. At minimum, we can draw inspiration from its scheduling logic or features.
    https://github.com/rush86999/atomic
	•	Easy!Appointments – an open-source appointment scheduler often cited as an alternative to proprietary booking tools. It’s more focused on client appointment booking (like Calendly) rather than scheduling personal tasks, so it might not directly help with our use case.
	•	Cal.com (Calendso) – an open-source Calendly alternative for scheduling meetings. Again, this is oriented towards coordinating meeting times via links, not automatically planning tasks on a calendar. Not directly applicable to task scheduling but indicates available frameworks for calendar UI and scheduling if needed.
	•	Others: We will look for any libraries or smaller projects that handle “task scheduling on calendar”. There may be Python packages or scripts on GitHub that already place tasks given a set of events (similar to what we need for prep tasks). If found, we can assess if using them is easier.

Decision: After exploring, the plan will be to either (a) incorporate an existing solution or (b) proceed with our custom implementation if existing tools are unsuited or too complex. Given the specific nature of “interview prep scheduling” and our emphasis on a lightweight, tailored solution, we expect to implement the core logic ourselves, while borrowing ideas from these projects. For instance, Atomic’s approach to integrating with calendars and its use of priorities could inform our design. We may also keep the door open to potentially contribute our project or module back to the open-source community if it complements these tools.

Finally, documenting our findings in the README (or a separate document) would be useful. We can list the alternatives we researched, and note why we chose to build a new tool (e.g., simpler scope, more control, or educational purpose). This exploration ensures we aren’t reinventing the wheel and can justify the project’s direction.

# 5. Streamlit UI for Visualization and Management

The project will include a simple web-based interface built with Streamlit, allowing users to interact with their calendars and the generated schedule without dealing with code or CLI. Streamlit is chosen for its ease of use and ability to create a quick dashboard-like UI in pure Python. Key UI features and design:
	•	Calendar View: The UI will present the user’s calendar events (fetched from Google) in a readable format. This could be a list of upcoming events grouped by day, or a visual calendar grid. To keep it lightweight, we might start with a simple list or table of events for the relevant timeframe (e.g., “Today”, “This Week”, etc.). If time permits, we can incorporate a community component like streamlit-calendar to display a calendar view with events.
	•	Interview Identification: The app can highlight which events are identified as interviews. For example, it might list all events that match a certain keyword or calendar (like events on a calendar called “Interviews”). The user could also select an event and mark it as an interview if needed.
	•	Show Prep Schedule: Once the prep blocks are calculated by our heuristic, the UI will show the proposed schedule. This could be in a section like “Planned Interview Prep” with entries like “March 15, 2:00–5:00pm – Prep for Interview with Company X”. By visualizing alongside existing events, the user can verify that prep blocks don’t clash with meetings.
	•	Interactivity: We will include controls for the user to adjust parameters or trigger actions: for instance, a slider or input to set how many hours of prep to schedule, or a button to re-calculate the schedule. Another button might push the generated prep blocks to Google Calendar (creating the events) if the user approves.
	•	Running in Streamlit: The README will explain how to run streamlit run app.py to start the app. When launched, the user will navigate to a local URL in their browser to use the interface. Streamlit will handle serving the UI.
	•	Lightweight Design: We plan to keep the UI minimal. This is not a full-fledged web app with authentication flows (we rely on the local OAuth token from earlier). The focus is on demonstrating functionality. For example, one developer used Streamlit to visualize Google Calendar data (pulling events, processing them, and showing how time was spent) as a quick side project ￼, which validates the feasibility of our approach. We aim for a similar level of simplicity – it should feel like a basic dashboard where you can see events and suggested tasks.

Technical implementation: Streamlit will allow us to write pure Python functions to render the calendar data. We’ll likely use the Google Calendar integration functions to fetch data when the app starts (or on user action) and then display results. We can use Streamlit widgets like st.button, st.selectbox (to choose a calendar or event), and st.write/st.table to output information. If advanced visualization is needed, libraries like Plotly or Altair could plot a Gantt-chart-like timeline of the schedule, but initially a textual display is sufficient.

Ensuring the UI is not overly complex will make it easier to maintain. It will serve as a foundation that can be extended as needed (for example, adding a login screen, theming, or more interactivity later on). Most importantly, it provides a user-friendly way to interact with the scheduling logic we implement.

6. Project Structure and Setup

Project Structure: The repository will be organized to separate concerns (API integration, scheduling logic, UI, etc.) and include configuration files for easy setup. A possible structure is:

```

https://github.com/rush86999/atomic interview_scheduler/
├── README.md
├── .gitignore
├── .env.example        # Template for environment variables
├── requirements.txt    # Python dependencies (streamlit, google-api-python-client, etc.)
├── app.py              # Streamlit application script
├── google_calendar.py  # Module handling Google Calendar API integration
├── scheduler.py        # Module for scheduling heuristic logic
├── utils.py            # (Optional) utility functions
└── data/               # (Optional) e.g., to store token.json or sample data
```

The README.md will contain comprehensive setup and usage instructions (detailed below) as well as an overview of the project.
	•	app.py: when run with Streamlit, this will bring up the UI. It will import functions from google_calendar.py to load events and from scheduler.py to compute prep schedules.
	•	google_calendar.py: contains functions to authenticate (perform OAuth flow or load saved credentials), fetch calendars, and fetch events. For example, a function get_events(calendar_ids, start_date, end_date) might return all events in the given calendars and time range.
	•	scheduler.py: contains the heuristic scheduling algorithm. For instance, a function schedule_prep(events, interview_event, hours_required) that returns a list of prep time blocks given the busy events and an interview to prepare for.
	•	We may also include a config file or section (could be just constants in Python or loaded from env) for things like default prep hours (40) and daily max prep hours.
	•	The requirements.txt will list required packages such as google-api-python-client, google-auth-httplib2, google-auth-oauthlib (for Google API), python-dotenv (for env files), and streamlit. This ensures anyone installing the project can get the correct dependencies.

Setup Instructions (for README):
To help users get started, the README will provide step-by-step guidance:
	1.	Prerequisites: Make sure Python 3.x is installed. It’s recommended to use a virtual environment.
	2.	Clone & Install Dependencies: Clone the repository and run pip install -r requirements.txt to install needed libraries.
	3.	Google API Setup: Go to Google Cloud Console and set up access to Google Calendar API:
	•	Create a new project (or use existing), enable the Google Calendar API ￼.
	•	Create OAuth credentials (type “Desktop App” for simplicity). Download the credentials.json file.
	•	Alternatively, you can obtain the Client ID and Secret from the API Credentials page.
	4.	Configure Environment Variables: Rename .env.example to .env. If you have a credentials.json, place it in the project directory (or a secure location) and add its path to the .env (e.g., GOOGLE_CREDENTIALS_FILE="credentials.json"). If using client ID/secret directly, put them in .env like GOOGLE_CLIENT_ID= and GOOGLE_CLIENT_SECRET=. Also set any other needed config (such as GOOGLE_CALENDAR_ID if a specific calendar is used, though by default we can use “primary” calendar or fetch all accessible calendars).
	•	Ensure no sensitive info is exposed – the README will remind the user not to commit their .env or credentials file.
	5.	Run the Application: Execute streamlit run app.py. This will launch the Streamlit app in your web browser.
	6.	Authorize Access: The first time, the app will prompt you to authenticate with Google. This might happen by opening a new browser tab to Google’s OAuth consent screen. After granting permission, the app will receive an authorization code and fetch tokens. The tokens will be saved (e.g., to token.json or in memory) for reuse. The README will detail this flow so the user knows to expect it.
	7.	Using the App: Once authenticated, the app will display your calendars and events. The README will give a quick walkthrough: for example, “Select an interview event from the dropdown to generate a prep schedule,” then “Click ‘Schedule Prep’ to see suggested prep blocks.” Also, how to confirm and actually add those prep events to your calendar (if implemented).
	8.	Troubleshooting: The README can include a section for common issues, e.g., dealing with OAuth token expiration (the tool should refresh tokens automatically, but if not, instruct how to delete the old token and re-auth), or ensuring the system time/timezone is correct, etc.

By following the README, even a non-developer should be able to set up the tool locally. The language will be kept simple, and possibly screenshots (if allowed) might be added later for clarity (for example, showing where in Google Console to click). Additionally, the README will list the tested environment (OS, Python version) and how to report issues or contribute.

7. Roadmap and Future Enhancements

This project is intentionally scoped to be lightweight and focused, but there are many opportunities to expand or improve it over time. The roadmap for potential enhancements includes:
	•	Outlook Calendar Integration: Extend support to Microsoft Outlook/Office 365 calendars. This would involve connecting to the Microsoft Graph API in a similar way to Google’s. The code structure (using a separate module for calendar integration) will make it easier to plug in a new provider. In the future, a user could choose to connect their Outlook account in addition to or instead of Google. This opens the tool to more users and use-cases. Integrating Outlook via Graph API would similarly allow creating, reading, and managing events within the app ￼.
	•	Advanced Scheduling Optimization: Replace or augment the simple heuristic with more sophisticated algorithms. For example, using linear programming or constraint solvers to optimize prep scheduling (especially if juggling multiple interviews or other tasks). Google’s OR-Tools or other libraries could help to maximize efficiency (e.g., maybe minimize the number of days needed or schedule during optimal times of day). An AI-driven approach could even learn from the user’s habits or energy levels (though that’s beyond the initial scope).
	•	Task Priority and Tracking: Expand the tool to handle not just interview prep but any tasks that need scheduling. This moves it closer to what Reclaim.ai or Motion do – automatically slotting tasks (with deadlines or priorities) into the calendar. We could allow the user to input tasks (like “Complete project report – 5 hours by next Tuesday”) and have the tool schedule those. Interview prep could be just one type of task. This generalization would make the tool a personal scheduling assistant.
	•	User Interface Improvements: While Streamlit provides a quick start, we might consider a more polished UI in the future. This could involve using a JavaScript front-end for a snappier experience or adding drag-and-drop functionality for calendar events (perhaps via a library like FullCalendar). We could also add a calendar visualization to the UI so users can see their week at a glance with prep blocks colored differently.
	•	Collaboration and Sharing: In a multi-user scenario (like a team interview calendar), the tool could handle scheduling prep for multiple interviewers or coordinating panel interviews. Though our current scope is single-user, future versions might allow sharing an interview schedule with others or scheduling group prep sessions (if multiple people need to prepare together).
	•	Notifications and Integrations: Add features like sending email or Slack reminders about upcoming prep sessions or if an interview gets rescheduled (then the tool could prompt to reschedule prep accordingly). This would increase the tool’s usefulness as a proactive assistant.
	•	Out-of-Scope Task Management: For now, the focus is on scheduling and not on storing content of prep (like notes or resources). But a future enhancement could integrate with note-taking or task systems (for example, linking a Google Doc or Notion page for each interview’s prep). This would start to blend scheduling with content management.
	•	Testing and CI/CD: As the project grows, include automated tests for the scheduling logic (e.g., ensure that if an interview is X days away with Y free hours, the algorithm schedules the correct total prep hours without overlap). Also, setting up continuous integration to run tests and perhaps containerizing the app (Docker) to deploy it easily on a server if someone wants to host it.

Each of these enhancements can be added incrementally. The roadmap prioritizes first the core functionality (Google Calendar integration and basic scheduling), then usability (UI improvements), followed by additional features (other calendars, smarter algorithms). We will maintain the README’s roadmap section to reflect what has been done and what is planned, so users and contributors have a clear sense of direction.

⸻

References:
	•	Google Calendar API integration requires creating a Google Cloud project and OAuth credentials for secure access ￼. Using OAuth 2.0 ensures the app can access calendars safely with user consent ￼.
	•	Storing API keys and secrets in a .env file keeps them out of source control and safe from exposure ￼.
	•	Atomic is an example of an open-source AI scheduler positioned as an alternative to Motion and Reclaim ￼, indicating the interest in self-hosted scheduling tools.
	•	A developer demonstrated pulling Google Calendar data and visualizing it with Streamlit, showing that a lightweight calendar dashboard is feasible ￼.
	•	The design anticipates future Outlook Calendar support; integrating Outlook via Microsoft Graph API would similarly allow managing events within the app ￼.