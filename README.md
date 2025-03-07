# Lightweight Python Interview Scheduler – Project Plan
## Creating a Conda Environment

To set up the project in a new Conda environment, follow these steps:

1. **Create a new Conda environment:**
   Open your terminal and run:
   ```bash
   conda create -n interview_scheduler python=3.10
   ```

2. **Activate the environment:**
   ```bash
   conda activate interview_scheduler
   ```

3. **Install dependencies:**
   Make sure you have the `requirements.txt` file in the project directory, then run:
   ```bash
   pip install -r requirements.txt
   ```
   

4. **Set up environment variables:**
   Rename the `.env.example` file to `.env` and fill in your credentials as instructed.

5. **Run the application:**
   Start the Streamlit app by running:
   ```bash
   streamlit run app.py
   ```
## Extended Project Plan & Future Enhancements

This project is evolving into a comprehensive interview scheduling and project management tool. In addition to the initial Google Calendar integration and scheduling heuristics, we plan to implement the following features:

### 1. SQL Database & Schema
- **Database Setup:**  
  The project will use a SQLite database to store:
  - **Projects:** Project metadata (name, estimated weekly hours, priority, and description).
  - **Events:** Fetched calendar events, linked to projects.
  - **Proposed Events:** Suggested time slots for project work.
  - **Tracking:** User confirmations and tracking of completed sessions.
- **Initialization:**  
  Run the following command to initialize the database and create the necessary tables:
  ```bash
  python database.py
  ```


** 2. Event Classification with DSPy & OpenAI** 
	•	Classification Module:
A separate module (classification.py) uses OpenAI’s API via DSPy to classify calendar events into projects.
	•	Workflow:
	•	When an event is fetched, the classifier uses its title and description to suggest which project it belongs to.
	•	If the model is not confident or returns “Unknown”, you’ll be prompted to either assign the event to an existing project or create a new one.
	•	New projects are added to the database, and the event is stored with its associated project ID.
	•	Example Code:

```python

# Example: classify_event function in classification.py
project_id = classify_event(event_title, event_description)
```
If the classification is uncertain, the function will prompt you to create a new project.

3. Scheduling Optimization & Notifications (Future Work)
	•	Constraint-Based Scheduling:
In future iterations, we will implement a flexible scheduling system (using libraries like python-constraint and MiniZinc) that considers project priorities, estimated hours, and user preferences to allocate work slots.
	•	Notifications & Tracking:
A notification system will prompt you after scheduled sessions to confirm if the work was completed. Responses will be recorded in the database to refine future scheduling.

4. Integration with Project Management Systems

We plan to research and potentially integrate cloud-based project management tools (e.g., OpenProject, Redmine) for enhanced task tracking and collaboration via their APIs.

Prompts Log & Discussion

Initial Prompt

	I’m looking to build something simple that would allow me to more easily schedule interviews for tech companies, especially when they require more extensive preparation and scheduling of the preparation as well as the thing itself…

(Full initial prompt text is included here for reference.)

Discussion Highlights
	•	Google Calendar Integration & Secure Credential Storage:
The project uses OAuth 2.0 for secure access to Google Calendar, with credentials stored in a .env file.
	•	Heuristic-Based Scheduling:
A basic scheduling algorithm will allocate a fixed amount of preparation time (e.g., 40 hours) spread across multiple days before an interview.
	•	Database Schema:
A SQLite database will store projects, events, proposed events, and tracking data to enable project management and scheduling analytics.
	•	LLM-Based Event Classification:
Using DSPy and the OpenAI API, events will be classified into projects. If the classifier is uncertain, you’ll be prompted to assign or create a new project.
	•	Future Enhancements:
Plans include implementing a flexible constraint-based scheduler, notifications for session completion, and integration with external project management tools.

## Suggested project structure


```
interview_scheduler/
├── README.md
├── .gitignore
├── .env.example        # Template for environment variables
├── requirements.txt    # Python dependencies
├── app.py              # Streamlit application script
├── google_calendar.py  # Module handling Google Calendar API integration
├── scheduler.py        # Module for scheduling heuristic logic
├── database.py         # Module for database schema and initialization
├── classification.py   # Module for event classification using DSPy and OpenAI
└── data/               # Directory for token files and sample data

```

# Classification Module

Great! I’ll create the first version of the classification model using DSPy with OpenAI API and structure the project accordingly.
	•	SQL Schema & Database Setup:
	•	A new database.py module will be created to define and initialize the SQLite schema.
	•	This will include tables for projects, events, proposed events, and tracking.
	•	Instructions for initializing the database will be provided.
	•	Event Classification Module (classification.py):
	•	This will use DSPy to classify calendar events into projects.
	•	If an event doesn’t match any existing project with high certainty, it will be marked as "unknown" and prompt the user to create a new project.
	•	The classification model will be interactive, allowing the user to provide feedback and improve the suggestions over time.

I’ll now begin implementing these changes and provide the necessary modifications for your repository.


## Implementation Steps
see planner.py for the initial implementation

1. Create a SQL Schema for the Database

First, set up a new module database.py that defines the database schema and initializes the tables. We will use a simple SQLite database (you can use any SQL database) to store four tables:
	•	projects – Stores project metadata (e.g., project name, estimated weekly hours, priority, etc.).
	•	events – Stores calendar events fetched from Google Calendar, each linked to a project (if classified).
	•	proposed_events – Stores suggested time slots for project work (proposed scheduling events).
	•	tracking – Stores user confirmations of completed work sessions, linking back to either actual events or proposed events.

Below is an example database.py implementing the schema and an initialization function. This script creates the tables with appropriate columns and relationships. Running this module (or calling init_db()) will initialize the database (here using a file planner.db for SQLite).

In this schema, the events table has a project_id foreign key linking to projects. This will allow us to associate each calendar event with a project once classified. The proposed_events table also links to projects (each suggested slot is for a specific project). The tracking table can reference either an actual event or a proposed event along with the project, and records a confirmation (for simplicity, a confirmed flag and timestamp when the confirmation is logged).

Initialization: To set up the database, ensure you have SQLite (or your chosen database) available. Running python database.py will create a new SQLite database file (e.g., planner.db) with all four tables. You can adjust the DB_PATH as needed (or modify the code to connect to a different DB server if not using SQLite).

2. Implement DSPy-Based Classification Module (classification.py)

Next, we create a classification.py module that uses OpenAI’s API in conjunction with the DSPy framework to classify events. The goal of this module is to take a calendar event (e.g., its title/description) and determine which project it belongs to, or mark it as “Unknown” if the model is not confident about any existing project. We will leverage DSPy to structure the prompt and response, ensuring the output includes a project name (or “Unknown”) and a confidence score.

Key points of the classification approach:
	•	We define a DSPy Signature class to describe the classification task, with input fields (event description, and optionally a list of existing project names) and output fields (predicted project and a confidence score). This structured approach lets DSPy format the prompt for the LLM (OpenAI) and parse its response.
	•	We use OpenAI’s GPT model via DSPy. You will need an OpenAI API key for this. In code, we’ll configure the DSPy OpenAI LLM with the desired model (e.g., GPT-3.5-Turbo or GPT-4).
	•	The classifier will attempt to match the event to one of the known projects. If the confidence is below a threshold or the model outputs “Unknown”, we treat the event as unclassified.
	•	If an event is unclassified (“Unknown”), the module will prompt the user (e.g., via console input) to decide if a new project should be created for this event. This is where user feedback comes in: the user can confirm creating a new project (which updates the database) or skip. This feedback loop ensures the system learns about new projects dynamically.
	•	All classification decisions are recorded: if a project is identified, the event will be tagged with that project’s ID in the database. New projects created on the fly are added to the projects table, so future similar events will be recognized. Over time, as more events are classified (and corrections are made), the system’s knowledge base grows, improving classification accuracy.

Below is an example of what classification.py might look like:
```python
# classification.py
import os
import openai
import dspy
from typing import List, Optional
import database  # Import the database module to access project data

# Configure OpenAI API for DSPy
openai.api_key = os.getenv("OPENAI_API_KEY", "")  # ensure your API key is set in the environment
# Set up the DSPy OpenAI language model (using GPT-3.5 in this example)
llm = dspy.OpenAI(model="gpt-3.5-turbo", api_key=openai.api_key)
dspy.settings.configure(lm=llm)

# Define a DSPy Signature for event classification
class EventClassification(dspy.Signature):
    """Classify a calendar event into one of the given project names or 'Unknown'."""
    event: str = dspy.InputField()        # The event title/description text
    projects: str = dspy.InputField()     # Comma-separated list of existing project names
    project: str = dspy.OutputField()     # Predicted project name (or "Unknown")
    confidence: float = dspy.OutputField()# Confidence score for the classification

# Create a DSPy module for prediction using the signature
classify_event_module = dspy.Predict(EventClassification)

# Optionally, define a confidence threshold for considering a classification "low confidence"
CONFIDENCE_THRESHOLD = 0.7

def classify_event(event_title: str, event_description: str = "") -> Optional[int]:
    """
    Classify a calendar event into a project. Returns the project ID if identified, 
    or None if unclassified. May prompt user to create a new project for unknown events.
    """
    # Fetch the list of current project names from the database
    projects = []
    conn = database.sqlite3.connect(database.DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT name FROM projects;")
    rows = cur.fetchall()
    conn.close()
    projects = [row[0] for row in rows]
    # Prepare input for classification
    event_text = event_title
    if event_description:
        event_text += " " + event_description
    projects_list = ", ".join(projects) if projects else ""  # join project names as a single string
    
    # If no projects exist yet, we will automatically treat as unknown (since there's nothing to classify against)
    predicted_project = "Unknown"
    confidence = 0.0
    if projects_list:
        # Call the DSPy classification module
        result = classify_event_module(event=event_text, projects=projects_list)
        predicted_project = result.project.strip()
        confidence = float(result.confidence) if result.confidence is not None else 0.0
    # If the model is not confident or doesn't match any known project, handle as unknown
    if (predicted_project.lower() == "unknown") or (confidence < CONFIDENCE_THRESHOLD) or (predicted_project not in projects):
        print(f"\n[Classification] The event \"{event_title}\" could not be confidently classified to an existing project (model suggestion: '{predicted_project}' with confidence {confidence:.2f}).")
        # Prompt the user to optionally create a new project
        choice = input("Would you like to create a new project for this event? (y/n): ").strip().lower()
        if choice == 'y':
            # Get new project details from user
            new_name = input("Enter a name for the new project: ").strip()
            if new_name:
                # Create the new project in the database
                conn = database.sqlite3.connect(database.DB_PATH)
                cur = conn.cursor()
                cur.execute("INSERT INTO projects (name) VALUES (?);", (new_name,))
                conn.commit()
                new_project_id = cur.lastrowid
                conn.close()
                print(f"[Classification] Created new project '{new_name}' (id={new_project_id}) and assigned the event to this project.")
                return new_project_id
    else:
        # We have a confident classification to an existing project
        proj_name = predicted_project
        # Find the project ID from the database
        conn = database.sqlite3.connect(database.DB_PATH)
        cur = conn.cursor()
        cur.execute("SELECT id FROM projects WHERE name = ?;", (proj_name,))
        row = cur.fetchone()
        conn.close()
        if row:
            project_id = row[0]
            print(f"[Classification] Event \"{event_title}\" classified as project \"{proj_name}\" (id={project_id}, confidence={confidence:.2f}).")
            return project_id
    # If we reach here, classification is unknown or user declined to create a project
    print(f"[Classification] Event \"{event_title}\" remains unclassified.")
    return None
```
In this code:
	•	We define EventClassification as a dspy.Signature with two input fields (event text and projects list) and two output fields (project and confidence). The projects input provides context to the model about which projects are available. The output project is expected to be one of those or "Unknown".
	•	The classify_event_module = dspy.Predict(EventClassification) sets up the classification module using the provided signature. DSPy will handle prompt creation and calling the OpenAI model.
	•	The function classify_event(event_title, event_description) is the main entry point to classify a single event. It retrieves all existing project names from the database to inform the model. If no projects exist yet, the function will skip calling the model and treat the event as unknown directly (since there are no categories to classify into).
	•	We concatenate the event title and description (if any) to form the text passed to the model. The list of projects is joined into a comma-separated string.
	•	After getting a result from the model, we interpret it:
	•	If the model’s predicted project is "Unknown" or the confidence is below our threshold (0.7 in this example) or the predicted name doesn’t match any existing project name, we consider the classification as uncertain/unknown.
	•	In the unknown case, the user is prompted via console (input) whether to create a new project for this event. If the user confirms, we ask for a project name and insert a new record into projects table. The new project’s ID is returned (which will be used to tag the event).
	•	If the user declines, or no name is given, we return None to indicate the event remains unclassified.
	•	If the model did return a known project with high confidence, we find that project’s ID in the database and return it. The event will be associated with this project.
	•	Throughout, we print some logging messages to the console for transparency (these could be replaced with proper logging in a real application).
	•	Refining classifications: Over time, this process improves as the database grows. New projects created from unknown events are added to the projects list, so future similar events will be correctly classified. If the model ever misclassifies an event (assigns the wrong project), the user can update it (for example, by editing the event’s project association in the database or via an interface). Such feedback could be used to further refine the classifier. For instance, one could maintain a history of corrected classifications and feed those as examples to DSPy (using techniques like few-shot examples or fine-tuning via DSPy’s optimization modules) to gradually improve the model’s accuracy. In our implementation, the primary learning mechanism is simply updating the project list and categories based on user input, which is an immediate form of feedback integration.

Note: Make sure to install the required libraries (dspy and openai) and set your OPENAI_API_KEY. The classification module uses the OpenAI API, which will incur costs and require internet access. You can adjust the model (e.g., to GPT-4) or use a locally hosted model with DSPy if available. Also, the prompting here is basic; depending on your project naming, you might want to provide the model with more context or examples to improve accuracy (for example, if project names are not clearly related to event wording, the model might need descriptions of projects or example event-to-project mappings).

3. Integrate Classification into the Event Processing Pipeline

With the database and classification module in place, we integrate the classification step into your event ingestion pipeline. This pipeline is responsible for fetching events from Google Calendar and storing them in our database. We will modify it so that as each event is processed, it gets classified and linked to a project.

Integration steps:
	1.	Fetch new events – Use the Google Calendar API (or your existing code) to retrieve calendar events (e.g., for the upcoming week or a specified date range). This might return a list of event objects with fields like title (summary), description, start time, end time, etc.
	2.	Loop through events and classify – For each fetched event, call the classification.classify_event() function with the event’s title/description. This will return a project_id if the event was classified into a project, or None if it remained unknown (or the user chose not to create a project for it). During this step, if the event is not recognized, the user may be prompted to add a new project (as implemented above).
	3.	Store the event in the database – After classification, insert the event into the events table, including the project_id returned. If project_id is None (unclassified), you can insert it with project_id as NULL. The relevant fields to save would be the event’s title, description, start_time, end_time, and the project association. This way, the event is now recorded in our system with the classification result.
	4.	Repeat for all events – Continue classifying and storing each event from the fetch. By the end of this process, the events table will be up-to-date with new events and each will either be linked to a project or left unassigned if unknown.
	5.	(Optional) Handle tracking and proposed events – If your system suggests times to work on projects (populating proposed_events table) and later asks for confirmation, you would integrate those parts as well. For example, after inserting events and proposed events, you might have logic to prompt the user to confirm completion of a proposed work session, and then insert a record into tracking table. This step would typically occur after the time of the event or proposed slot has passed and the user indicates whether they did the work.

Here’s a pseudo-code example illustrating how the classification is integrated when processing events:
```python
# Pseudo-code for event ingestion with classification
import database
import classification
from google_calendar_api import fetch_upcoming_events  # hypothetical import

# Initialize database (ensure tables exist)
database.init_db()

# Fetch events from Google Calendar (this part depends on your Google API setup)
new_events = fetch_upcoming_events()  # returns a list of event dicts

# Open a database connection for inserting events
conn = database.sqlite3.connect(database.DB_PATH)
cur = conn.cursor()

for ev in new_events:
    title = ev.get('summary') or ev.get('title', '')
    desc = ev.get('description', '')
    start = ev.get('start_time')  # assume ISO string or datetime
    end = ev.get('end_time')
    # Classify the event to get a project ID (may prompt user if unknown)
    project_id = classification.classify_event(title, desc)
    # Insert the event into the events table with the obtained project_id
    cur.execute(
        "INSERT INTO events (project_id, title, description, start_time, end_time) VALUES (?, ?, ?, ?, ?);",
        (project_id, title, desc, start, end)
    )
    print(f"Stored event '{title}' with project_id={project_id}")
    
conn.commit()
conn.close()
```
In a real application, the fetching of events and the database insertion would be more robust (with proper date parsing, error handling, etc.), but the above outline shows where the classification fits in. Essentially, the classification function is called for each new event before saving it, so that when we save it, we already know which project (if any) it belongs to. This ensures the events table’s project_id field is filled for classified events.

After this pipeline runs, you can query the events table and see that each event has an associated project ID if it was recognized. Unclassified events will have project_id as NULL (unless you chose to create new projects for them during classification). Those new projects will appear in the projects table. Over time, as you run the ingestion regularly, the classification will leverage the growing projects table to categorize events, and prompt for new categories less frequently.


4. Provide Usage Instructions

Finally, here are instructions on how to use this system, from setup to running the classification:
	1.	Install Requirements: Make sure you have the necessary Python packages installed. You will need sqlite3 (built into Python), OpenAI’s openai package, and DSPy. Install DSPy and OpenAI API client via pip:
	```bash
	pip install openai dspy
	```
	2.	Create a .env file: Copy the .env.example template to .env and fill in your actual values.
	```bash
	cp .env.example .env
	```
	3.	Add OpenAI API key: Add your OpenAI API key to the .env file.
	```bash
	OPENAI_API_KEY=<your_openai_api_key>
	```
	4. initialize the db:
	```bash
	python database.py
```
	5.	Use Proposed Events and Tracking (if applicable): If your system suggests time slots for you to work on projects (populating the proposed_events table), those would be generated based on project settings (e.g., based on each project’s priority or remaining hours for the week). After you act on a proposed event (for example, you actually spend that time to work on the project), you would mark it as completed. The application could prompt you to confirm (“Did you work on Project X from 3-4pm as suggested?”) and then record a entry in the tracking table. Each tracking entry links the work session (actual or proposed event) to the project and notes it as completed. This allows you to later analyze how much time was spent on each project versus the plan. (Implementing the full suggestion logic and confirmation prompts is beyond the scope of this question, but the schema supports it.)
	6.	Refining the Classifier: As you use the system, the classification of events should improve:
	•	New Projects: Whenever an event doesn’t match any existing project, adding a new project through the prompt means the system learns a new category. Future events with similar titles/descriptions will likely be classified into this new project.
	•	Correcting Mistakes: If an event was misclassified (e.g., the system assigned it to Project A but it actually belonged to Project B), you should update it. You can manually edit the events.project_id in the database or through whatever interface your application provides. This feedback isn’t automatically fed back into the AI model in our simple implementation, but it does ensure your stored data is correct. In a more advanced setup, you could use these corrections to retrain or adjust the classifier (for example, by adding the misclassified event text and the correct project as a training example in DSPy, or fine-tuning the model). Over time, accumulating such examples could allow you to programmatically improve the prompt or even fine-tune a model via DSPy’s optimization features.
	•	Reviewing Classifications: It’s a good practice to periodically review how events are being categorized (especially early on). The console logs from the classification step show the model’s chosen category and confidence. If you notice consistently low confidence or incorrect assignments, you might refine the prompt or provide the model with additional context (like project descriptions or keywords) to help it make better decisions.
	7.	Running the System: In summary, to run the full system:
	•	Ensure the database is initialized and up-to-date.
	•	Run the event fetching and classification script (which integrates the classification module). This could be done manually or as a scheduled job (e.g., daily) to keep your events table in sync with your calendar.
	•	Respond to any prompts for new project creation during the run.
	•	After classification, use your data (projects, events, tracking) as needed — e.g., generate reports of hours per project, see what’s planned for each project, etc.

All these instructions should be documented in the repository’s README for easy reference. By following the above steps, you can set up the system, classify incoming calendar events into projects (with the help of an AI model), and continuously improve the classification as you provide feedback.


## Overview -first prompt

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

# 6. Project Structure and Setup

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

# 7. Roadmap and Future Enhancements

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
	•	The design anticipates future Outlook Calendar support; integrating Outlook via Microsoft Graph API would similarly allow managing events within the app.


# Parking Lot 
## Initial Prompt

I'm looking to build something simple that would allow me to more easily schedule interviews for tech companies, especially when they require more extensive preparation and scheduling of the preparation as well as the thing itself. So, to do that, I would like as a first step to connect somehow to Google Calendar and maybe Outlook. I want to connect to multiple calendars if possible, download them, and then try to find the appropriate date to conduct my interview, given that I have specified some calendars and I want, for example, a given time between them. So, for example, maybe I want to prepare for 30 hours or for 50 hours before the full interview loop and so on. So, as a first step, I would like you to write down a plan of how to conduct this project. So, maybe the first step would be something like calendar connectivity and downloads, overall project structure, where I want it to be quite lightweight, but still kind of robust enough so I can download multiple calendars and connect to them and see my existing commitments and then try to fit things the best. So, as a first step, I would like you to write a project plan with a README that would be used in further steps. So, it might be that I want to download these calendars or have access to the API, maybe, possibly. You have to also tell me what credentials I need, how do I put them in the .env environmental file and things like that. So, maybe the first step would be just kind of this document setup where we outline the steps we're going to take. So, first this part and then start thinking about the scheduling problem itself, how to fit it into my day and weeks and so on. Could you start on this? Basically, this is the project I want to build; help me plan it and start executing it. I want to implement it in Python. It would be like, feel free to think about also what kind of optimization libraries we you can use for the scheduling part if needed or just have some simple algorithm for scheduling to start with. And regarding the UI, I want to use Streamlit to just make it simple and easy to start with. but if you have better options also tell me. Just don't over complicate things but make it comprehensive and easy for me to get started with it. a like some some tools which are kind of comparable or for example motion I think I think there is something called reclaim.ai and... Yeah, maybe you can also look for kind of open source alternatives to Motion that I can integrate but the main use case would be to sort of try to schedule interviews while planning and flexibly some some kind of preparation time for for interviews without scheduling it explicitly. it's more like I just need to have a bunch of time for the preparation as a buffer before the interview itself.