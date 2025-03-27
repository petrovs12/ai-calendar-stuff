#!/usr/bin/env python3
"""
Event classification module using DSPy and OpenAI to classify calendar events into projects.
"""

import os
import logging
from typing import List, Optional, Tuple, Dict, Any
import json
from datetime import datetime, timedelta

import dspy
import mlflow
import pickle
import streamlit as st

# Local imports
import database
from models import CalendarEvent, TimeOfDay, CalendarEventTime

# Directory for saving fine-tuned models
MODEL_DIR = "models"
os.makedirs(MODEL_DIR, exist_ok=True)

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# MLflow configuration
MLFLOW_TRACKING_URI = "http://127.0.0.1:5000"
EXPERIMENT_NAME = "DSPy Calendar Event Classification"

# Classification configuration
CONFIDENCE_THRESHOLD = 70.0  # Only accept classifications with confidence > 70%

# Define a DSPy Signature for enhanced event classification
class EventClassification(dspy.Signature):
    """Classify a calendar event into one of the given project names or 'Unknown'."""
    title: str = dspy.InputField(desc="The event title")
    description: str = dspy.InputField(desc="The event description")
    calendar_id: str = dspy.InputField(desc="The calendar ID of the event")
    day_of_week: str = dspy.InputField(desc="Day of the week (Monday, Tuesday, etc.)")
    time_of_day: str = dspy.InputField(desc="Time of day (Morning, Afternoon, Evening, Night)")
    attendees: str = dspy.InputField(desc="Comma-separated list of attendees' email addresses")
    projects: str = dspy.InputField(desc="Comma-separated list of existing project names")
    project: str = dspy.OutputField(desc="Predicted project name (or 'unknown' if it doesn't match any project)")
    confidence: float = dspy.OutputField(desc="Confidence percentage (0-100) in this classification")
    explanation: str = dspy.OutputField(desc="Brief explanation of why this project was selected")

# Define the DSPy module for classification
class ProjectClassifier(dspy.Module):
    """DSPy module for classifying events into projects."""
    
    def __init__(self):
        super().__init__()
        self.classifier = dspy.Predict("event_text -> project_name, confidence")
    
    def forward(self, event_text: str, project_names: List[str]):
        # Format project names as a string
        projects_str = ", ".join(project_names)
        
        # Create the full prompt with project names
        prompt = f"""Classify the following calendar event into one of these projects: {projects_str}.
        
Calendar Event:
{event_text}

Choose the most appropriate project from the list. If none seem appropriate, answer "Unknown".
Also provide a confidence score between 0 and 1, where 1 is completely confident.
"""
        
        # Add the project names to the context
        self.classifier.context = {"project_options": projects_str}
        
        # Classify the event
        prediction = self.classifier(event_text=prompt)
        
        # Try to parse the confidence as a number
        try:
            confidence = float(prediction.confidence)
            # Ensure confidence is in range 0-1
            confidence = max(0.0, min(1.0, confidence))
        except (ValueError, TypeError):
            # If parsing fails, default to a medium confidence
            confidence = 0.5
            
        return dspy.Prediction(
            project_name=prediction.project_name.strip(),
            confidence=confidence
        )

def initialize_experiment():
    """Initialize MLflow experiment for tracking."""
    # Set up MLflow tracking
    mlflow.set_tracking_uri(MLFLOW_TRACKING_URI)
    
    # Create or get the experiment
    try:
        experiment = mlflow.get_experiment_by_name(EXPERIMENT_NAME)
        if experiment is None:
            mlflow.create_experiment(EXPERIMENT_NAME)
            logger.info(f"Created new experiment: {EXPERIMENT_NAME}")
        else:
            logger.info(f"Found existing experiment: {EXPERIMENT_NAME} (ID: {experiment.experiment_id})")
    except Exception as e:
        logger.warning(f"Failed to initialize MLflow experiment: {e}")

# Initialize MLflow
def init_mlflow():
    """
    Initialize MLflow configuration with autolog
    
    Returns:
        Boolean indicating if MLflow was successfully initialized
    """
    try:
        # Set the tracking URI to the MLflow server
        mlflow.set_tracking_uri(MLFLOW_TRACKING_URI)
        # Set up autologging for DSPy
        mlflow.dspy.autolog()
        
        # Create or get the experiment
        experiment = mlflow.get_experiment_by_name(EXPERIMENT_NAME)
        if experiment is None:
            logger.info(f"Creating new MLflow experiment: {EXPERIMENT_NAME}")
            experiment_id = mlflow.create_experiment(EXPERIMENT_NAME)
            logger.info(f"Created experiment with ID: {experiment_id}")
        else:
            logger.info(f"Found existing experiment: {EXPERIMENT_NAME} (ID: {experiment.experiment_id})")
            mlflow.set_experiment(EXPERIMENT_NAME)
        
        return True
    except Exception as e:
        logger.error(f"Error initializing MLflow: {e}")
        return False

# Initialize MLflow at module load time
init_mlflow()

# Configure OpenAI API for DSPy
api_key = os.getenv("OPENAI_API_KEY", "")
model_name = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

def configure_dspy(model_name: str = None, api_key: str = None) -> Optional[Any]:
    """
    Configure DSPy with the specified model and API key.
    
    Args:
        model_name: The name of the OpenAI model to use
        api_key: The OpenAI API key
        
    Returns:
        The configured language model or None if configuration failed
    """
    # Update global variables if provided
    global API_KEY, MODEL_NAME
    
    API_KEY = api_key or os.getenv("OPENAI_API_KEY", "")
    MODEL_NAME = model_name or os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    
    # Validate essential settings
    if not API_KEY:
        logger.error("OpenAI API key is required")
        return None
    
    try:
        # Create the language model
        lm = dspy.LM(model=f"openai/{MODEL_NAME}", api_key=API_KEY)
        logger.info(f"DSPy configured with model: {MODEL_NAME}")
        
        # Store the LM in the session state for future use
        if 'st' in globals():
            st.session_state.dspy_lm = lm
            st.session_state.dspy_configured = True
            st.session_state.dspy_model_name = MODEL_NAME
        
        return lm
    except Exception as e:
        logger.error(f"Error configuring DSPy: {e}")
        logger.exception(str(e))
        return None

def get_classify_module(lm=None):
    """
    Get a new classification module with the specified LM
    
    Args:
        lm: The language model to use. If None, uses the one from session state.
        
    Returns:
        A DSPy Predict module for event classification
    """
    # Use provided LM or get from session state
    if lm is None:
        if 'dspy_lm' not in st.session_state:
            logger.error("No LM found in session state. DSPy needs to be configured first.")
            return None
        lm = st.session_state.dspy_lm
    
    # Create a new module each time to avoid thread issues
    prediction_module = dspy.Predict(EventClassification)
    prediction_module.set_lm(lm)
    return prediction_module

def load_latest_model():
    """
    Load the most recent fine-tuned model if available.
    Returns the model or None if no saved models exist.
    """
    try:
        model_files = [f for f in os.listdir(MODEL_DIR) if f.startswith("classifier_") and f.endswith(".pkl")]
        if not model_files:
            logger.info("No fine-tuned models found. Using default model.")
            return None
            
        # Sort by timestamp (which is part of the filename)
        latest_model = sorted(model_files)[-1]
        model_path = os.path.join(MODEL_DIR, latest_model)
        
        logger.info(f"Loading fine-tuned model: {model_path}")
        with open(model_path, "rb") as f:
            model_state = pickle.load(f)
            
        logger.info(f"Successfully loaded model: {latest_model}")
        return model_state
    except Exception as e:
        logger.error(f"Error loading model: {e}")
        return None

def get_project_data() -> Tuple[Dict[str, int], List[str]]:
    """
    Get project data from the database.
    
    Returns:
        tuple containing:
        - dict[str, int]: Mapping of project names (lowercase) to their IDs
        - list[str]: List of project names
    """
    # Use the database module to get projects
    projects = database.get_projects()
    
    if not projects:
        logger.warning("No projects found in database. Cannot classify event.")
        return {}, []
    
    # Create a mapping of project names to IDs (case-insensitive)
    project_ids = {}
    project_names = []
    
    for project in projects:
        if project.id is not None and project.name:
            project_ids[project.name.lower()] = project.id
            project_names.append(project.name)
    
    return project_ids, project_names

def classify_event(
    event: CalendarEvent,
    project_names: List[str],
    project_ids: Dict[str, int],
    lm: Optional[Any] = None
) -> Tuple[Optional[int], float]:
    """
    Classify a CalendarEvent into a project using DSPy.
    
    Args:
        event: CalendarEvent object to classify
        project_names: List of project names
        project_ids: Mapping of lowercase project names to IDs
        lm: Optional language model to use
        
    Returns:
        Tuple of (project_id, confidence)
    """
    # Validate inputs
    if not event.summary and not event.description:
        logger.warning("Both title and description are empty. Cannot classify.")
        return None, 0.0
    
    if not project_names:
        logger.warning("No projects available for classification")
        return None, 0.0
    
    # Get the classification module
    classifier = get_classify_module(lm)
    if not classifier:
        logger.error("Failed to create classification module")
        return None, 0.0
    
    # Initialize MLflow tracking if needed
    initialize_experiment()
    
    # Wrap API calls in try-except for robustness
    try:
        # Extract day of week if available
        day_of_week = ""
        if event.start_dt:
            day_of_week = event.start_dt.strftime("%A")
        
        # Get time of day
        time_of_day = event.time_of_day.name if event.time_of_day else "UNKNOWN"
        
        # Get attendees if available
        attendees = ", ".join(event.attendee_emails) if hasattr(event, 'attendee_emails') else ""
        
        # Run inference with the classifier
        result = classifier(
            title=event.summary,
            description=event.description or "",
            calendar_id=event.calendar_id or "",
            day_of_week=day_of_week,
            time_of_day=time_of_day,
            attendees=attendees,
            projects=", ".join(project_names)
        )
        
        # Get the project ID from the predicted name
        predicted = result.project.lower()
        confidence = result.confidence / 100.0  # Convert from percentage to 0-1 scale
        
        # Find the closest matching project - first check for exact match
        if predicted in project_ids:
            project_id = project_ids[predicted]
            logger.info(f"Classified event to project: {predicted} (ID: {project_id}, Confidence: {confidence:.0%})")
            return project_id, confidence
            
        # If no exact match, try to find the closest name
        # This is useful for handling minor differences in text
        closest_name = find_closest_name(predicted, list(project_ids.keys()))
        if closest_name:
            project_id = project_ids[closest_name]
            logger.info(f"Using closest match: '{closest_name}' for '{predicted}' (ID: {project_id})")
            return project_id, confidence
            
        # No match found
        logger.warning(f"No matching project found for '{predicted}'")
        return None, confidence
        
    except Exception as e:
        # Log the error
        logger.error(f"Classification error: {e}")
        return None, 0.0

def batch_classify_events(events: List[CalendarEvent], lm: Optional[Any] = None, run_name: Optional[str] = None) -> Dict[str, Tuple[Optional[int], float]]:
    """
    Batch classify events using MLflow for tracking.
    
    Args:
        events: List of CalendarEvent objects to classify
        lm: Optional language model to use
        run_name: Name for the MLflow run
        
    Returns:
        Dictionary mapping event IDs to (project_id, confidence) tuples
    """
    logger.info(f"Batch classifying {len(events)} events")
    
    # Initialize MLflow experiment and tracking
    initialize_experiment()
    
    # Initialize results
    results: Dict[str, Tuple[Optional[int], float]] = {}
    
    # Get project data
    project_ids, project_names = get_project_data()
    
    # Check if we have projects to classify events
    if not project_names:
        logger.warning("No projects available for classification")
        return results
    
    # Process each event in the batch
    for idx, event in enumerate(events):
        event_id = event.id
        
        try:
            # Call classify_event with the event data
            project_id, confidence = classify_event(
                event,
                project_names,
                project_ids,
                lm=lm
            )
            
            # Update the database with the classification result
            if project_id is not None:
                update_event_with_classification(event_id, project_id, confidence)
            
            # Store the result
            results[event_id] = (project_id, confidence)
            
        except Exception as e:
            logger.error(f"Error classifying event {event_id}: {e}")
            results[event_id] = (None, 0.0)
    
    # Log overall results
    classified_count = sum(1 for pid, _ in results.values() if pid is not None)
    logger.info(f"Batch classification complete: {classified_count}/{len(events)} events classified")
    return results

def update_event_with_classification(event_id: str, project_id: int, confidence: Optional[float] = None) -> bool:
    """
    Update an event with its classification result.
    
    Args:
        event_id: The event ID to update
        project_id: The project ID to assign to the event
        confidence: Optional confidence score for the classification
        
    Returns:
        bool: True if the update was successful, False otherwise
    """
    try:
        # Get the event from the database to get its internal ID
        db = database.get_db_session()
        event = db.query(database.EventModel).filter(
            database.EventModel.event_id == event_id
        ).first()
        
        if not event:
            logger.warning(f"Event with ID {event_id} not found in database")
            db.close()
            return False
            
        # Use the database function to update the event
        db.close()
        return database.update_event_project(event.id, project_id)
    except Exception as e:
        logger.error(f"Error updating event classification: {e}")
        return False

def find_closest_name(target: str, options: List[str], threshold: float = 0.8) -> Optional[str]:
    """
    Find the closest matching string from a list of options using fuzzy matching.
    
    Args:
        target: The target string to match
        options: List of strings to compare against
        threshold: Similarity threshold (0-1) for considering a match
        
    Returns:
        The closest matching string, or None if no good match found
    """
    try:
        # Simple case - direct substring match
        for option in options:
            if target in option or option in target:
                return option
                
        # Try fuzzy matching with difflib
        from difflib import SequenceMatcher
        
        best_match = None
        best_ratio = 0
        
        for option in options:
            ratio = SequenceMatcher(None, target.lower(), option.lower()).ratio()
            if ratio > best_ratio:
                best_ratio = ratio
                best_match = option
                
        # Return the best match if it's above the threshold
        if best_ratio >= threshold:
            return best_match
            
        return None
    except Exception as e:
        logger.error(f"Error in find_closest_name: {e}")
        return None

# Add a test invocation at the end to run when the script is executed directly
if __name__ == "__main__":
    # Initialize the database if running standalone
    database.init_db()
    
    # Test the classification with a sample event
    test_event_title = "Weekly team meeting with engineering"
    print(f"Creating test event with title: '{test_event_title}'")
    
    # Create a test CalendarEvent object
    from models import CalendarEventTime
    now = datetime.now()
    test_event = CalendarEvent(
        id="test_event_123",
        summary=test_event_title,
        description="Weekly sync-up with the engineering team to discuss progress",
        start=CalendarEventTime(dateTime=now.isoformat(), dt=now),
        end=CalendarEventTime(dateTime=(now + timedelta(hours=1)).isoformat(), dt=now + timedelta(hours=1)),
        calendar_id="primary"
    )
    
    # Need to configure DSPy before calling classify_event
    lm = configure_dspy()
    if lm:
        # Get project data for classification
        project_ids, project_names = get_project_data()
        
        project_id, confidence = classify_event(
            test_event,
            project_names,
            project_ids,
            lm=lm
        )
        
        if project_id is not None:
            print(f"Classification result: Project ID {project_id}, Confidence {confidence:.2f}%")
        else:
            print(f"Classification result: Unknown (no project assigned), Confidence {confidence:.2f}%")
    else:
        print("Failed to configure DSPy. Cannot classify event.")