#!/usr/bin/env python3
"""
Debug script for testing the event classification with DSPy.
This script helps identify why the classification might be returning 'unknown' with 0% confidence.
"""

import os
import sys
import sqlite3
import logging
import json
from datetime import datetime
from dotenv import load_dotenv
import dspy
import mlflow

mlflow.set_experiment("DSPy Classification Debug")
mlflow.autolog()
# Load environment variables
load_dotenv()

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Configure DSPy with verbose logging
os.environ["DSPY_VERBOSE"] = "1"

# Import DSPy (with error handling in case it's not installed)
try:
    import dspy
    from dspy.predict import Predict
except ImportError:
    logger.error("DSPy not installed. Install with: pip install dspy-ai")
    sys.exit(1)

# Database connection
DB_PATH = "planner.db"

def fetch_projects_from_db():
    """Get all available projects from the database."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    try:
        cursor.execute("SELECT id, name, description FROM projects ORDER BY id")
        projects = cursor.fetchall()
        logger.info(f"Found {len(projects)} projects in the database")
        return projects
    except Exception as e:
        logger.error(f"Error fetching projects: {e}")
        return []
    finally:
        conn.close()

def get_sample_events():
    """Get a few sample events from the database for testing."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    try:
        cursor.execute("""
            SELECT id, title, description, start_time, end_time, calendar_id
            FROM events
            WHERE project_id IS NULL
            LIMIT 5
        """)
        events = cursor.fetchall()
        logger.info(f"Found {len(events)} sample events for testing")
        return events
    except Exception as e:
        logger.error(f"Error fetching sample events: {e}")
        return []
    finally:
        conn.close()
        
def setup_dspy():
    """Initialize DSPy with OpenAI."""
    # Configure OpenAI API
    openai_api_key = os.getenv("OPENAI_API_KEY")
    if not openai_api_key:
        logger.error("OPENAI_API_KEY not found in environment variables")
        sys.exit(1)
    
    logger.info("Setting up DSPy with OpenAI")
    # Set up the OpenAI API for DSPy
    openai_model = os.getenv("OPENAI_MODEL", "gpt-3.5-turbo")
    logger.info(f"Using OpenAI model: {openai_model}")
    
    # Configure DSPy to use OpenAI
    import dspy
    lm = dspy.LM('openai/gpt-4o-mini', api_key=openai_api_key)
    dspy.configure(lm=lm)
    logger.info(f"DSPy configured with OpenAI model: {openai_model}")
    
    # Define the DSPy signature for event classification
    class ClassifyEvent(dspy.Signature):
        """Classify calendar events into projects based on their title and description."""
        
        event_title = dspy.InputField(desc="The title of the calendar event")
        event_description = dspy.InputField(desc="The description of the calendar event (might be empty)")
        project_names = dspy.InputField(desc="List of available project names to classify the event into")
        
        project_name = dspy.OutputField(desc="The most likely project name for this event, or 'unknown' if it doesn't match any project")
        confidence = dspy.OutputField(desc="The confidence percentage (0-100) in this classification")
        explanation = dspy.OutputField(desc="A brief explanation of why this project was chosen")
    
    # Create a predictor using the signature
    predictor = dspy.Predict(ClassifyEvent)
    
    return predictor

def run_classification_tests(predictor, projects, events):
    """Run classification tests on sample events and log detailed results."""
    project_names = [p[1] for p in projects]
    
    if not project_names:
        logger.error("No projects available for classification")
        return
    
    logger.info(f"Projects available for classification: {', '.join(project_names)}")
    
    for i, event in enumerate(events):
        event_id, title, description, start_time, end_time, calendar_id = event
        
        logger.info(f"\n{'='*80}\nTesting event #{i+1}: {title}\n{'='*80}")
        logger.info(f"Description: {description or 'None'}")
        logger.info(f"Calendar: {calendar_id}")
        
        # Call the DSPy predictor
        try:
            logger.info("Calling DSPy classifier...")
            result = predictor(
                event_title=title,
                event_description=description or "",
                project_names=project_names
            )
            
            # Log the result
            logger.info(f"Classification result:")
            logger.info(f"Project: {result.project_name}")
            logger.info(f"Confidence: {result.confidence}")
            logger.info(f"Explanation: {result.explanation}")
            
            # Additional debugging
            if result.project_name == "unknown" or float(result.confidence.strip('%') if isinstance(result.confidence, str) else result.confidence) < 50:
                logger.warning("Low confidence classification detected - investigate prompt and response")
        
        except Exception as e:
            logger.error(f"Error during classification: {e}")

def create_test_project_if_needed():
    """Create a test project if no projects exist in the database."""
    projects = fetch_projects_from_db()
    if not projects:
        logger.info("No projects found, creating a test project")
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                INSERT INTO projects (name, description, estimated_hours)
                VALUES (?, ?, ?)
            """, ("Test Project", "This is a test project for classification debugging", 10))
            conn.commit()
            logger.info("Created test project 'Test Project'")
        except Exception as e:
            logger.error(f"Error creating test project: {e}")
        finally:
            conn.close()

def manual_classification_test():
    """Perform a manual classification test with hardcoded event and project data."""
    setup_dspy()
    
    # Sample project data
    projects = ["Work", "Personal", "Family", "Health", "Learning"]
    
    # Sample events for testing
    test_events = [
        {
            "title": "Meeting with Team",
            "description": "Weekly sync with the engineering team to discuss project status"
        },
        {
            "title": "Doctor Appointment",
            "description": "Annual checkup with Dr. Smith"
        },
        {
            "title": "Learn Python",
            "description": "Study DSPy library and finish classification tutorial"
        },
        {
            "title": "Family Dinner",
            "description": "Dinner with parents and siblings at Mom's house"
        }
    ]
    
    # Define the DSPy signature for event classification
    class ClassifyEvent(dspy.Signature):
        """Classify calendar events into projects based on their title and description."""
        
        event_title = dspy.InputField(desc="The title of the calendar event")
        event_description = dspy.InputField(desc="The description of the calendar event (might be empty)")
        project_names = dspy.InputField(desc="List of available project names to classify the event into")
        
        project_name = dspy.OutputField(desc="The most likely project name for this event, or 'unknown' if it doesn't match any project")
        confidence = dspy.OutputField(desc="The confidence percentage (0-100) in this classification")
        explanation = dspy.OutputField(desc="A brief explanation of why this project was chosen")
    
    # Create a predictor using the signature
    predictor = dspy.Predict(ClassifyEvent)
    
    for i, event in enumerate(test_events):
        logger.info(f"\n{'='*80}\nTesting manual event #{i+1}: {event['title']}\n{'='*80}")
        logger.info(f"Description: {event['description']}")
        
        # Call the DSPy predictor
        try:
            logger.info("Calling DSPy classifier...")
            result = predictor(
                event_title=event['title'],
                event_description=event['description'],
                project_names=projects
            )
            
            # Log the result
            logger.info(f"Classification result:")
            logger.info(f"Project: {result.project_name}")
            logger.info(f"Confidence: {result.confidence}")
            logger.info(f"Explanation: {result.explanation}")
            
        except Exception as e:
            logger.error(f"Error during classification: {e}")

def main():
    """Main function to run the debugging tests."""
    logger.info("Starting DSPy classification debug script")
    
    # Check if we can access the database
    if not os.path.exists(DB_PATH):
        logger.error(f"Database file {DB_PATH} not found")
        manual_classification_test()
        return
    
    # Create a test project if needed
    create_test_project_if_needed()
    
    # Get projects from the database
    projects = fetch_projects_from_db()
    if not projects:
        logger.error("No projects available in the database even after trying to create one")
        manual_classification_test()
        return
    
    # Get sample events
    events = get_sample_events()
    if not events:
        logger.error("No events available in the database for testing")
        return
    
    # Set up DSPy
    predictor = setup_dspy()
    
    # Run classification tests
    run_classification_tests(predictor, projects, events)
    
    # Also run manual test for comparison
    logger.info("\n\nRunning manual classification test for comparison...")
    manual_classification_test()
    
    logger.info("Classification debugging completed")

if __name__ == "__main__":
    main() 