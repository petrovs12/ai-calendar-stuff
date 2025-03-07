#!/usr/bin/env python3
"""
Simplified classification module for calendar events.
This version focuses on improved prompting and better confidence score handling.
"""

import os
import logging
import sqlite3
from typing import List, Tuple, Dict, Optional
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Import DSPy (with error handling)
try:
    import dspy
    from dspy.predict import Predict
except ImportError:
    logger.error("DSPy not installed. Install with: pip install dspy-ai")
    raise

# Database connection
DB_PATH = "planner.db"

def init_dspy():
    """Initialize DSPy with OpenAI."""
    # Check for API key
    openai_api_key = os.getenv("OPENAI_API_KEY")
    if not openai_api_key:
        logger.error("OPENAI_API_KEY not found in environment variables")
        raise ValueError("Missing OpenAI API key")
    
    # Set up OpenAI for DSPy
    openai_model = os.getenv("OPENAI_MODEL", "gpt-3.5-turbo")
    logger.info(f"Initializing DSPy with model: {openai_model}")
    
    dspy.configure(
        lm=dspy.OpenAI(
            model=openai_model,
            api_key=openai_api_key,
        )
    )
    
    class ClassifyCalendarEvent(dspy.Signature):
        """
        Analyze a calendar event and determine which project it belongs to.
        """
        
        event_title = dspy.InputField(desc="Title of the calendar event")
        event_description = dspy.InputField(desc="Description of the calendar event (may be empty)")
        event_calendar = dspy.InputField(desc="The calendar where this event is stored (e.g., work calendar, personal calendar)")
        available_projects = dspy.InputField(desc="List of available project names to classify the event into")
        
        project_choice = dspy.OutputField(desc="The name of the project this event belongs to, exactly as written in available_projects, or 'unknown' if none match")
        confidence_score = dspy.OutputField(desc="A number from 0-100 representing your confidence in the classification")
        reasoning = dspy.OutputField(desc="Brief explanation of why this event belongs to the chosen project")
    
    # Create a custom module that provides better instructions
    class EventClassifier(dspy.Module):
        def __init__(self):
            super().__init__()
            self.predictor = dspy.Predict(ClassifyCalendarEvent)
            
        def forward(self, event_title, event_description, event_calendar, available_projects):
            # Add some guidance to make the model more decisive
            if isinstance(available_projects, list):
                projects_list = available_projects
            else:
                # Handle case where projects might be passed as string
                projects_list = available_projects.split(',') if ',' in available_projects else [available_projects]
            
            # Clean up projects list
            projects_list = [p.strip() for p in projects_list if p.strip()]
            
            # Call the predictor
            result = self.predictor(
                event_title=event_title,
                event_description=event_description or "",
                event_calendar=event_calendar,
                available_projects=projects_list
            )
            
            # Process the confidence score to ensure it's a number
            try:
                if isinstance(result.confidence_score, str):
                    # Remove any % signs and convert to float
                    confidence = result.confidence_score.strip('%').strip()
                    confidence = float(confidence)
                else:
                    confidence = float(result.confidence_score)
                
                # Ensure confidence is in the right range
                confidence = max(0, min(100, confidence))
            except (ValueError, TypeError):
                # Default to 0 if we couldn't parse the confidence
                logger.warning(f"Couldn't parse confidence score: {result.confidence_score}, defaulting to 0")
                confidence = 0
            
            # Ensure the project choice is valid - must be in the list or 'unknown'
            if result.project_choice not in projects_list and result.project_choice != 'unknown':
                logger.warning(f"Project choice '{result.project_choice}' not in available projects, setting to 'unknown'")
                project = 'unknown'
                confidence = 0
            else:
                project = result.project_choice
            
            # If confidence is very low, default to 'unknown'
            if confidence < 20 and project != 'unknown':
                logger.info(f"Low confidence ({confidence}%) for project '{project}', defaulting to 'unknown'")
                project = 'unknown'
                confidence = 0
            
            return {
                'project': project,
                'confidence': confidence,
                'reason': result.reasoning
            }
    
    return EventClassifier()

def get_projects_from_db() -> List[Tuple[int, str, str]]:
    """Get all projects from the database."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    try:
        cursor.execute("""
            SELECT id, name, description 
            FROM projects 
            ORDER BY name
        """)
        projects = cursor.fetchall()
        return projects
    except Exception as e:
        logger.error(f"Failed to fetch projects: {e}")
        return []
    finally:
        conn.close()

def classify_event(
    event_title: str,
    event_description: str = "",
    event_calendar: str = "",
    classifier = None
) -> Dict:
    """
    Classify a calendar event into a project.
    
    Args:
        event_title: The title of the event
        event_description: The description of the event (optional)
        event_calendar: The calendar ID or name (optional)
        classifier: An existing classifier instance (optional)
        
    Returns:
        Dict with keys: project_id, project_name, confidence, reason
    """
    # Get projects from the database
    projects = get_projects_from_db()
    if not projects:
        logger.warning("No projects found in the database, cannot classify event")
        return {
            'project_id': None,
            'project_name': 'unknown',
            'confidence': 0,
            'reason': 'No projects available'
        }
    
    # Extract project names
    project_names = [p[1] for p in projects]
    
    # Initialize DSPy if not provided
    if classifier is None:
        try:
            classifier = init_dspy()
        except Exception as e:
            logger.error(f"Failed to initialize DSPy: {e}")
            return {
                'project_id': None,
                'project_name': 'unknown',
                'confidence': 0,
                'reason': f'Error: {str(e)}'
            }
    
    # Add some context for empty description
    if not event_description:
        event_description = "(No description provided)"
    
    # Call the classifier
    try:
        logger.info(f"Classifying event: '{event_title}'")
        result = classifier(
            event_title=event_title,
            event_description=event_description,
            event_calendar=event_calendar,
            available_projects=project_names
        )
        
        # Map the project name back to ID if it's not unknown
        project_id = None
        if result['project'] != 'unknown':
            for p_id, p_name, _ in projects:
                if p_name == result['project']:
                    project_id = p_id
                    break
        
        return {
            'project_id': project_id,
            'project_name': result['project'],
            'confidence': result['confidence'],
            'reason': result['reason']
        }
    except Exception as e:
        logger.error(f"Classification failed: {e}")
        return {
            'project_id': None,
            'project_name': 'unknown',
            'confidence': 0,
            'reason': f'Error: {str(e)}'
        }

def auto_classify_events(limit=10):
    """
    Automatically classify unclassified events in the database.
    
    Args:
        limit: Maximum number of events to classify
        
    Returns:
        List of classification results
    """
    # Connect to the database
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    try:
        # Get unclassified events
        cursor.execute("""
            SELECT id, event_id, title, description, calendar_id
            FROM events
            WHERE project_id IS NULL
            ORDER BY start_time DESC
            LIMIT ?
        """, (limit,))
        events = cursor.fetchall()
        
        if not events:
            logger.info("No unclassified events found")
            return []
        
        logger.info(f"Found {len(events)} unclassified events")
        
        # Initialize the classifier once to reuse
        classifier = init_dspy()
        
        results = []
        for event in events:
            event_id, google_event_id, title, description, calendar_id = event
            
            # Classify the event
            result = classify_event(
                event_title=title,
                event_description=description or "",
                event_calendar=calendar_id,
                classifier=classifier
            )
            
            # Store the result
            results.append({
                'event_id': event_id,
                'title': title,
                'project_name': result['project_name'],
                'confidence': result['confidence'],
                'reason': result['reason']
            })
            
            # Update the database if we have a project match
            if result['project_id'] is not None:
                try:
                    cursor.execute("""
                        UPDATE events
                        SET project_id = ?
                        WHERE id = ?
                    """, (result['project_id'], event_id))
                    conn.commit()
                    logger.info(f"Event '{title}' classified as '{result['project_name']}' with {result['confidence']}% confidence")
                except Exception as e:
                    logger.error(f"Failed to update event {event_id}: {e}")
        
        return results
    except Exception as e:
        logger.error(f"Auto-classification failed: {e}")
        return []
    finally:
        conn.close()

if __name__ == "__main__":
    print("Testing simplified classification module...")
    
    # Sample project setup
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    try:
        # Create test projects if they don't exist
        test_projects = [
            ("Work", "Work-related activities and meetings", 40),
            ("Personal", "Personal tasks and appointments", 20),
            ("Learning", "Educational activities and courses", 15),
            ("Health", "Healthcare appointments and fitness", 10),
            ("Family", "Family events and responsibilities", 25)
        ]
        
        for project in test_projects:
            cursor.execute("""
                INSERT OR IGNORE INTO projects (name, description, estimated_hours) 
                VALUES (?, ?, ?)
            """, project)
        
        conn.commit()
        print(f"Ensured {len(test_projects)} test projects exist in the database")
    except Exception as e:
        print(f"Error setting up test projects: {e}")
    finally:
        conn.close()
    
    # Test with some sample events
    sample_events = [
        {
            "title": "Team Standup",
            "description": "Daily team meeting to discuss progress and blockers",
            "calendar": "work@example.com"
        },
        {
            "title": "Dentist Appointment",
            "description": "Regular checkup with Dr. Johnson",
            "calendar": "personal@example.com"
        },
        {
            "title": "Python Workshop",
            "description": "Learning advanced Python techniques",
            "calendar": "personal@example.com"
        },
        {
            "title": "Mom's Birthday",
            "description": "Celebration dinner at home",
            "calendar": "family@example.com"
        },
        {
            "title": "Gym Session",
            "description": "Weight training with personal trainer",
            "calendar": "fitness@example.com"
        }
    ]
    
    # Initialize classifier once
    classifier = init_dspy()
    
    # Test each event
    for event in sample_events:
        result = classify_event(
            event_title=event["title"],
            event_description=event["description"],
            event_calendar=event["calendar"],
            classifier=classifier
        )
        
        print(f"\nEvent: {event['title']}")
        print(f"Description: {event['description']}")
        print(f"Calendar: {event['calendar']}")
        print(f"Classification: {result['project_name']}")
        print(f"Confidence: {result['confidence']}%")
        print(f"Reason: {result['reason']}")
        print("-" * 50)
    
    # Now run auto-classification on actual database events
    print("\nRunning auto-classification on database events...")
    auto_results = auto_classify_events(limit=5)
    
    if auto_results:
        print(f"\nClassified {len(auto_results)} events from database:")
        for result in auto_results:
            print(f"Event: {result['title']}")
            print(f"Classification: {result['project_name']}")
            print(f"Confidence: {result['confidence']}%")
            print(f"Reason: {result['reason']}")
            print("-" * 50)
    else:
        print("No events were classified from the database")
    
    print("\nClassification test completed") 