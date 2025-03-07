# database.py
import sqlite3
import os

DB_PATH = "planner.db"

def init_db():
    """Initialize the database and create tables if they don't exist."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    # Create projects table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS projects (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            estimated_hours INTEGER,    -- estimated hours per week
            priority INTEGER,           -- e.g., priority rank or level
            description TEXT
        );
    """)
    # Create events table (each event may link to a project)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id INTEGER,                -- reference to projects.id (can be NULL if unclassified)
            title TEXT NOT NULL,               -- event title or summary
            description TEXT,                  -- event description/details
            start_time TEXT NOT NULL,          -- event start datetime (ISO format string)
            end_time TEXT NOT NULL,            -- event end datetime (ISO format string)
            event_id TEXT UNIQUE,              -- Google Calendar event ID for reference
            calendar_id TEXT,                  -- Google Calendar ID this event belongs to
            FOREIGN KEY(project_id) REFERENCES projects(id)
        );
    """)
    # Create proposed_events table (suggested time slots for projects)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS proposed_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id INTEGER NOT NULL,       -- reference to the project this slot is for
            proposed_start TEXT NOT NULL,      -- suggested start datetime
            proposed_end TEXT NOT NULL,        -- suggested end datetime
            FOREIGN KEY(project_id) REFERENCES projects(id)
        );
    """)
    # Create tracking table (user confirmations of completed work)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS tracking (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id INTEGER,               -- project that the work relates to
            event_id INTEGER,                 -- actual calendar event ID (if applicable)
            proposed_event_id INTEGER,        -- proposed event ID (if applicable)
            confirmed INTEGER DEFAULT 1,      -- 1 if completed (could be 0 for not completed)
            confirmation_time TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(project_id) REFERENCES projects(id),
            FOREIGN KEY(event_id) REFERENCES events(id),
            FOREIGN KEY(proposed_event_id) REFERENCES proposed_events(id)
        );
    """)
    conn.commit()
    conn.close()

def get_projects():
    """Retrieve all projects from the database."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT id, name, estimated_hours, priority, description FROM projects ORDER BY name;")
    projects = cursor.fetchall()
    conn.close()
    return projects

def add_project(name, estimated_hours=None, priority=None, description=None):
    """Add a new project to the database."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO projects (name, estimated_hours, priority, description) VALUES (?, ?, ?, ?);",
        (name, estimated_hours, priority, description)
    )
    new_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return new_id

# If run as a script, initialize the database
if __name__ == "__main__":
    init_db()
    print(f"Database initialized at {os.path.abspath(DB_PATH)}")
    
    # Add some sample projects if none exist
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM projects;")
    count = cursor.fetchone()[0]
    conn.close()
    
    if count == 0:
        print("Adding sample projects...")
        add_project("Interview Prep", 40, 1, "Preparation for technical interviews")
        add_project("Personal Development", 10, 2, "Skills development and learning")
        add_project("Work Meetings", None, 3, "Regular work-related meetings")
        print("Sample projects added.")
        
    print("Done. You can now run the application with 'streamlit run app.py'.")