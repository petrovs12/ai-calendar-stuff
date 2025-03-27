#!/usr/bin/env python3
"""
Event classification module using DSPy and OpenAI to classify calendar events into projects.
"""

import os
import logging
from typing import List, Optional, Tuple, Dict, Any
import sqlite3
from datetime import datetime, timedelta
import random
import threading

import dspy
import mlflow
import pickle
import streamlit as st

# Local imports
import database

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

# Define a DSPy Signature for event classification
class EventClassification(dspy.Signature):
    """Classify a calendar event into one of the given project names or 'Unknown'."""
    event: str = dspy.InputField(desc="The event title and description text")
    projects: str = dspy.InputField(desc="Comma-separated list of existing project names")
    project: str = dspy.OutputField(desc="Predicted project name (or 'unknown' if it doesn't match any project)")
    confidence: float = dspy.OutputField(desc="Confidence percentage (0-100) in this classification")
    explanation: str = dspy.OutputField(desc="Brief explanation of why this project was selected")

# Initialize MLflow
def init_mlflow():
    """
    Initialize MLflow configuration
    
    Returns:
        Boolean indicating if MLflow was successfully initialized
    """
    try:
        # Set the tracking URI to the MLflow server
        mlflow.set_tracking_uri(MLFLOW_TRACKING_URI)
        
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

# Configure OpenAI API for DSPy
api_key = os.getenv("OPENAI_API_KEY", "")
model_name = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

def configure_dspy(model_name: str = None, api_key: str = None):
    """
    Configure DSPy with OpenAI model. This function creates an LM and stores it in session state.
    
    Args:
        model_name: Optional model name to use. If None, uses the default from env.
        api_key: Optional API key to use. If None, uses the default from env.
        
    Returns:
        The LM object
    """
    # Use provided values or fall back to environment variables
    current_model = model_name or os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    current_api_key = api_key or os.getenv("OPENAI_API_KEY", "")
    
    
    logger.info(f"Creating LM with model: {current_model}")
    
    if not current_api_key:
        logger.warning("OpenAI API key not found. Classification will not work.")
        return None
    
    try:
        # Create the LM
        lm = dspy.LM(f'openai/{current_model}', api_key=current_api_key)
        
        # Store in session state
        st.session_state.dspy_lm = lm
        st.session_state.dspy_configured = True
        st.session_state.dspy_model_name = current_model
        
        logger.info(f"Created LM with OpenAI model: {current_model}")
        return lm
    except Exception as e:
        logger.error(f"Error creating LM: {e}")
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

def get_project_data() -> tuple[dict[str, int], list[str]]:
    """
    Get project data from the database.
    
    Returns:
        tuple containing:
        - dict[str, int]: Mapping of project names (lowercase) to their IDs
        - list[str]: List of project names
    """
    conn = database.sqlite3.connect(database.DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT id, name FROM projects")
    project_data = cursor.fetchall()
    conn.close()

    if not project_data:
        logger.warning("No projects found in database. Cannot classify event.")
        return {}, []

    # Create a mapping of project names to IDs (case-insensitive)
    project_ids = {}
    for pid, pname in project_data:
        project_ids[pname.lower()] = pid

    project_names = [name for _, name in project_data]
    
    return project_ids, project_names

def classify_event(event_title: str, event_description: str = "", event_calendar: str = "", lm=None) -> Tuple[Optional[int], float]:
    """
    Classify a calendar event into a project based on its title and description.
    
    Args:
        event_title: The title of the event
        event_description: The description of the event (optional)
        event_calendar: The calendar ID the event belongs to (optional)
        lm: The language model to use (optional, defaults to session state LM)
        
    Returns:
        Tuple of (project_id, confidence) where project_id is None if classification failed
    """
    # Check if LM is available
    if lm is None:
        if 'dspy_lm' not in st.session_state:
            logger.warning("No LM available. Please configure DSPy first.")
            return None, 0.0
        lm = st.session_state.dspy_lm
    
    # Get a new classification module with the LM
    classify_module = get_classify_module(lm)
    if classify_module is None:
        logger.error("Failed to create classification module.")
        return None, 0.0
    
    # Get project data from database
    project_ids, project_names = get_project_data()
    
    if not project_names:
        return None, 0.0
    
    logger.info(f"Classifying event '{event_title}' against {len(project_names)} projects")
    
    # Prepare input for the classifier
    input_text = f"{event_title}"
    if event_description:
        input_text += f" {event_description}"
    
    # Define projects_list for the classification
    projects_list = ", ".join(project_names)
    
    try:
        # Initialize MLflow
        init_mlflow()
        
        # Start an MLflow run
        run_name = f"classify_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        with mlflow.start_run(run_name=run_name,nested=True):
            # Log parameters to MLflow
            mlflow.log_param("event_title", event_title)
            if event_description:
                mlflow.log_param("has_description", True)
            mlflow.log_param("model", st.session_state.get('dspy_model_name', 'unknown'))
            
            # Make the prediction
            logger.info(f"Sending classification request to OpenAI with {len(project_names)} projects")
            
            # Log the exact input being sent to the model
            logger.debug(f"Classification input: event='{input_text}', projects='{projects_list}'")
            
            # Make the prediction
            result = classify_module(event=input_text, projects=projects_list)
            
            # Log the raw result for debugging
            logger.debug(f"Raw classification result: {result}")
            
            # Extract project name and confidence
            predicted_project = result.project.strip() if hasattr(result, 'project') else "unknown"
            
            # Parse confidence with better error handling
            confidence = 0.0
            try:
                if hasattr(result, 'confidence'):
                    confidence_str = str(result.confidence).strip()
                    # Remove any % signs
                    confidence_str = confidence_str.replace('%', '')
                    confidence = float(confidence_str)
                    
                    # If confidence is in 0-1 range, convert to 0-100
                    if 0 <= confidence <= 1:
                        confidence *= 100
                
                # Ensure confidence is within 0-100 range
                confidence = max(0, min(100, confidence))
            except (ValueError, TypeError, AttributeError) as e:
                logger.warning(f"Could not parse confidence score: {e}. Using 0.0")
                confidence = 0.0
            
            # Log prediction to MLflow
            mlflow.log_param("predicted_project", predicted_project)
            mlflow.log_metric("confidence", confidence)
            if hasattr(result, 'explanation'):
                mlflow.log_text(result.explanation, "explanation.txt")
            
            logger.info(f"Model returned project '{predicted_project}' with confidence {confidence:.2f}")
            
            # Check if prediction is reliable
            if predicted_project.lower() == "unknown" or confidence < CONFIDENCE_THRESHOLD:
                logger.info(f"Classification uncertain: project='{predicted_project}', confidence={confidence:.2f}")
                mlflow.log_metric("classification_success", 0)
                return None, confidence
            
            # Find the project ID by name (case-insensitive)
            project_id = None
            for name, pid in project_ids.items():
                if name == predicted_project.lower():
                    project_id = pid
                    break
            
            if project_id:
                logger.info(f"Classified event as project ID {project_id} with confidence {confidence:.2f}")
                mlflow.log_metric("classification_success", 1)
                mlflow.log_param("project_id", project_id)
                return project_id, confidence
            else:
                logger.warning(f"Predicted project '{predicted_project}' not found in database")
                mlflow.log_metric("classification_success", 0)
                return None, confidence
    except Exception as e:
        logger.error(f"Error during prediction: {e}")
        logger.exception(str(e))
        try:
            with mlflow.start_run(run_name=f"error_{datetime.now().strftime('%Y%m%d_%H%M%S')}",nested=True):
                mlflow.log_param("error", str(e))
                mlflow.log_param("event_title", event_title)
                mlflow.log_metric("classification_success", 0)
        except Exception as mlflow_e:
            logger.error(f"Error logging to MLflow: {mlflow_e}")
        return None, 0.0

def batch_classify_events(event_list, lm=None, run_name=None):
    """
    Classify a batch of events
    
    Args:
        event_list: List of event dictionaries with title, description (optional), and calendar_id (optional)
        lm: The language model to use (optional, defaults to session state LM)
        run_name: Optional custom name for the parent run
        
    Returns:
        Dictionary of results with event IDs as keys and (project_id, confidence) as values
    """
    # Check if LM is available
    if lm is None:
        if 'dspy_lm' not in st.session_state:
            logger.warning("No LM available. Please configure DSPy first.")
            return {}
        lm = st.session_state.dspy_lm
    
    # Generate a run name if not provided
    if not run_name:
        run_name = f"batch_classify_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    results = {}
    
    # Initialize MLflow
    init_mlflow()
    
    # Create a parent run for all classifications in this batch
    with mlflow.start_run(run_name=run_name,nested=True):
        # Log batch information
        mlflow.log_param("batch_size", len(event_list))
        mlflow.log_param("model", st.session_state.get('dspy_model_name', 'unknown'))
        mlflow.log_param("timestamp", datetime.now().isoformat())
        
        # Classify each event
        for i, event in enumerate(event_list):
            if i > 2:
                break
            title = event.get('title', '')
            description = event.get('description', '')
            calendar_id = event.get('calendar_id', '')
            event_id = event.get('id', i)
            
            # Classify the event using the same LM
            project_id, confidence = classify_event(
                title, 
                description, 
                calendar_id, 
                lm=lm
            )
            
            # Store the result
            results[event_id] = (project_id, confidence)
        
        # Log summary metrics
        classified_count = sum(1 for _, (pid, _) in results.items() if pid is not None)
        mlflow.log_metric("total_classified", classified_count)
        mlflow.log_metric("classification_rate", classified_count / len(event_list) if event_list else 0)
    
    return results

def update_event_with_classification(event_id: int, project_id: int) -> bool:
    """
    Update an event in the database with its classification result.
    
    Args:
        event_id: The ID of the event to update
        project_id: The ID of the project to assign
        
    Returns:
        Boolean indicating success
    """
    try:
        conn = sqlite3.connect(database.DB_PATH)
        cursor = conn.cursor()
        
        # Update the event with the project ID
        cursor.execute("""
            UPDATE events
            SET project_id = ?
            WHERE id = ?
        """, (project_id, event_id))
        
        conn.commit()
        conn.close()
        
        logger.info(f"Updated event {event_id} with project ID {project_id}")
        return True
    except Exception as e:
        logger.error(f"Error updating event with classification: {e}")
        return False

def init_db():
    """Initialize the database."""
    database.init_db()

# Add a test invocation at the end to run when the script is executed directly
if __name__ == "__main__":
    # Initialize the database if running standalone
    init_db()
    
    # Test the classification with a sample event
    test_event = "Weekly team meeting with engineering"
    print(f"Classifying test event: '{test_event}'")
    
    # Need to configure DSPy before calling classify_event
    lm = configure_dspy()
    if lm:
        project_id, confidence = classify_event(test_event, lm=lm)
        
        if project_id is not None:
            print(f"Classification result: Project ID {project_id}, Confidence {confidence:.2f}%")
        else:
            print(f"Classification result: Unknown (no project assigned), Confidence {confidence:.2f}%")
    else:
        print("Failed to configure DSPy. Cannot classify event.")