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

import dspy
from dspy.predict import Predict
import mlflow
import pickle
import streamlit as st

mlflow.set_experiment("DSPy Calendar Event Classification")

# Local imports
import database

# Directory for saving fine-tuned models
MODEL_DIR = "models"
os.makedirs(MODEL_DIR, exist_ok=True)

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Configure OpenAI API for DSPy
api_key = os.getenv("OPENAI_API_KEY", "")
model_name = os.getenv("OPENAI_MODEL", "gpt-3.5-turbo")
import dspy
lm = dspy.LM('openai/gpt-4o-mini', api_key=api_key, cache=None)
dspy.configure(lm=lm)

try:
    if not api_key:
        logger.warning("OpenAI API key not found in environment variables. Classification will not work.")
    else:
        # Set up the LLM
        llm = dspy.OpenAI(model=model_name, api_key=api_key, cache=None)
        dspy.settings.configure(lm=llm)
        logger.info(f"DSPy configured with OpenAI model: {model_name}")
except Exception as e:
    logger.error(f"Error configuring DSPy with OpenAI: {e}")

# Define a DSPy Signature for event classification
class EventClassification(dspy.Signature):
    """Classify a calendar event into one of the given project names or 'Unknown'."""
    event: str = dspy.InputField(desc="The event title and description text")
    projects: str = dspy.InputField(desc="Comma-separated list of existing project names")
    project: str = dspy.OutputField(desc="Predicted project name (or 'unknown' if it doesn't match any project)")
    confidence: float = dspy.OutputField(desc="Confidence percentage (0-100) in this classification")
    explanation: str = dspy.OutputField(desc="Brief explanation of why this project was selected")

# Create a DSPy module for prediction using the signature
classify_event_module = dspy.Predict(EventClassification)

# Constants
CONFIDENCE_THRESHOLD = 70.0  # Minimum confidence to accept a classification

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
            
        # Apply the model state to the classifier module
        # This assumes the DSPy module has a load_state method
        classify_event_module.load_state(model_state)
        logger.info(f"Successfully loaded model: {latest_model}")
        return model_state
    except Exception as e:
        logger.error(f"Error loading model: {e}")
        return None

def fine_tune_classifier():
    """
    Fine-tune the DSPy classification model using manually classified events from the database.
    Uses events with a non-null project_id as training examples.
    
    Returns:
        Boolean indicating success or failure
    """
    try:
        # Check if DSPy module supports training
        if not hasattr(classify_event_module, 'train'):
            logger.warning("DSPy module doesn't support fine-tuning with the 'train' method.")
            return False
        
        # Retrieve labeled examples from the events table
        conn = database.sqlite3.connect(database.DB_PATH)
        cur = conn.cursor()
        
        # Query all classified events
        logger.info("Retrieving classified events for fine-tuning...")
        cur.execute("""
            SELECT e.title, e.description, p.name 
            FROM events e
            JOIN projects p ON e.project_id = p.id
            WHERE e.project_id IS NOT NULL
            LIMIT 200
        """)
        examples = cur.fetchall()
        conn.close()
        
        if not examples:
            logger.info("No labeled examples found. Skipping fine-tuning.")
            return False
        
        # Prepare training data in the format that DSPy expects
        logger.info(f"Preparing {len(examples)} examples for fine-tuning...")
        training_data = []
        for title, desc, project_name in examples:
            # Format the input text the same way we do during prediction
            input_text = title
            if desc:
                input_text += f" {desc}"
            
            # Create a training example
            training_data.append({
                "event": input_text,
                "projects": project_name,  # For training, we can simplify to just the correct project
                "project": project_name,
                "confidence": 100.0  # High confidence for training examples
            })
        
        if not training_data:
            logger.info("No valid training data extracted. Skipping fine-tuning.")
            return False
        
        logger.info(f"Fine-tuning classifier on {len(training_data)} examples...")
        
        # Progress tracking for Streamlit if available
        progress_callback = None
        if 'st' in globals():
            try:
                progress_bar = st.progress(0)
                status_text = st.empty()
                status_text.text("Fine-tuning progress: 0%")
                
                def update_progress(step, total):
                    progress = int((step / total) * 100)
                    progress_bar.progress(progress)
                    status_text.text(f"Fine-tuning progress: {progress}%")
                
                progress_callback = update_progress
            except Exception as e:
                logger.error(f"Could not set up Streamlit progress tracking: {e}")
        
        # Fine-tune the model
        try:
            # Create an MLflow run for tracking
            with mlflow.start_run(run_name="event_classifier_fine_tuning"):
                # Log parameters
                mlflow.log_param("num_examples", len(training_data))
                mlflow.log_param("epochs", 1)
                
                # Perform the fine-tuning
                logger.info("Starting DSPy fine-tuning...")
                
                # This is a simplified approach - in reality, we might need to adapt to DSPy's API
                # since different DSPy versions have different training interfaces
                classify_event_module.train(
                    training_data=training_data,
                    epochs=1,
                    # Add callback for progress if available
                    progress_callback=progress_callback if progress_callback else None
                )
                
                # Update progress
                if 'st' in globals():
                    try:
                        progress_bar.progress(100)
                        status_text.text("Fine-tuning progress: 100%")
                    except:
                        pass
                
                # Save the fine-tuned model with versioning
                import time
                version = int(time.time())
                model_path = os.path.join(MODEL_DIR, f"classifier_{version}.pkl")
                
                if hasattr(classify_event_module, 'get_state'):
                    with open(model_path, "wb") as f:
                        model_state = classify_event_module.get_state()
                        pickle.dump(model_state, f)
                    
                    # Log the model path in MLflow
                    mlflow.log_artifact(model_path)
                    
                    logger.info(f"Fine-tuning complete and model saved to {model_path}")
                    return True
                else:
                    logger.error("The classification module doesn't support state saving")
                    return False
                
        except Exception as e:
            logger.error(f"Error during fine-tuning: {e}", exc_info=True)
            
            # Log the error in MLflow
            mlflow.log_param("error", str(e))
            
            return False
            
    except Exception as e:
        logger.error(f"Error setting up fine-tuning: {e}", exc_info=True)
        return False

def classify_event(event_title: str, event_description: str = "", event_calendar: str = "") -> Tuple[Optional[int], float]:
    """
    Classify a calendar event into a project based on its title and description.
    
    Args:
        event_title: The title of the event
        event_description: The description of the event (optional)
        event_calendar: The calendar ID the event belongs to (optional)
        
    Returns:
        Tuple of (project_id, confidence) where project_id is None if classification failed
    """
    # Load the latest model if we haven't already
    if 'st' in globals() and not hasattr(st.session_state, 'model_loaded'):
        load_latest_model()
        st.session_state.model_loaded = True
    
    # Get all project names from the database
    conn = database.sqlite3.connect(database.DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT id, name FROM projects")
    project_data = cursor.fetchall()
    conn.close()
    
    if not project_data:
        logger.warning("No projects found in database. Cannot classify event.")
        return None, 0.0
    
    # Create a mapping of project names to IDs (case-insensitive)
    project_ids = {}
    for pid, pname in project_data:
        project_ids[pname.lower()] = pid
    
    project_names = [name for _, name in project_data]
    logger.info(f"Classifying event '{event_title}' against {len(project_names)} projects")
    
    # Prepare input for the classifier
    input_text = f"{event_title}"
    if event_description:
        input_text += f" {event_description}"
    
    try:
        # Call the DSPy classification module
        logger.info(f"Sending classification request to OpenAI with {len(project_names)} projects")
        projects_list = ", ".join(project_names)
        
        # Log the exact input being sent to the model
        logger.debug(f"Classification input: event='{input_text}', projects='{projects_list}'")
        
        # Make the prediction
        result = classify_event_module(event=input_text, projects=projects_list)
        
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
        
        logger.info(f"Model returned project '{predicted_project}' with confidence {confidence:.2f}")
        
        # Log project matches for debugging
        matched_projects = [p for p in project_names if p.lower() == predicted_project.lower()]
        if matched_projects:
            logger.debug(f"Project '{predicted_project}' matched with existing projects: {matched_projects}")
        else:
            logger.debug(f"Project '{predicted_project}' did not match any existing projects")
        
        # Check if prediction is reliable
        if predicted_project.lower() == "unknown" or confidence < CONFIDENCE_THRESHOLD:
            logger.info(f"Classification uncertain: project='{predicted_project}', confidence={confidence:.2f}")
            return None, confidence
        
        # Find the project ID by name (case-insensitive)
        project_id = None
        for name, pid in project_ids.items():
            if name == predicted_project.lower():
                project_id = pid
                break
        
        if project_id:
            logger.info(f"Classified event as project ID {project_id} with confidence {confidence:.2f}")
            
            # Update the fine-tuning counter in session state
            if 'st' in globals():
                if not hasattr(st.session_state, 'auto_classify_counter'):
                    st.session_state.auto_classify_counter = 0
                
                st.session_state.auto_classify_counter += 1
                
                # Trigger fine-tuning after every 5 successful classifications
                if st.session_state.auto_classify_counter >= 5:
                    logger.info("Triggering fine-tuning after 5 successful classifications")
                    fine_tune_classifier()
                    st.session_state.auto_classify_counter = 0
                    
            return project_id, confidence
        else:
            logger.warning(f"Predicted project '{predicted_project}' not found in database")
        return None, confidence
        
    except Exception as e:
        logger.error(f"Error during classification: {e}", exc_info=True)
        return None, 0.0

def create_new_project(project_name: str) -> Optional[int]:
    """
    Create a new project in the database.
    
    Args:
        project_name: The name of the new project
        
    Returns:
        The ID of the newly created project, or None if creation failed
    """
    try:
        conn = database.sqlite3.connect(database.DB_PATH)
        cur = conn.cursor()
        cur.execute("INSERT INTO projects (name) VALUES (?);", (project_name,))
        conn.commit()
        new_project_id = cur.lastrowid
        conn.close()
        
        logger.info(f"Created new project '{project_name}' (id={new_project_id})")
        
        # Update the fine-tuning counter
        if 'st' in globals():
            if not hasattr(st.session_state, 'auto_classify_counter'):
                st.session_state.auto_classify_counter = 0
                
            st.session_state.auto_classify_counter += 1
            
            # Trigger fine-tuning after every 5 successful classifications
            if st.session_state.auto_classify_counter >= 5:
                fine_tune_classifier()
                st.session_state.auto_classify_counter = 0
            
        return new_project_id
    except Exception as e:
        logger.error(f"Error creating new project: {e}")
        return None

def auto_classify_events(limit=10):
    """
    Automatically classify unclassified events from the database.
    
    Args:
        limit: Maximum number of events to classify
        
    Returns:
        Number of successfully classified events
    """
    logger.info(f"Starting auto-classification of up to {limit} events")
    
    # First check if we have trained a model
    if not os.path.exists(MODEL_DIR) or not any(f.startswith("classifier_") and f.endswith(".pkl") for f in os.listdir(MODEL_DIR)):
        logger.warning("No fine-tuned model available. Results may be less accurate.")
    
    conn = database.sqlite3.connect(database.DB_PATH)
    cursor = conn.cursor()
    
    # Get unclassified events
    try:
        cursor.execute("""
            SELECT id, title, description, calendar_id 
            FROM events 
            WHERE project_id IS NULL
            ORDER BY start_time DESC
            LIMIT ?
        """, (limit,))
        
        unclassified_events = cursor.fetchall()
        
        if not unclassified_events:
            logger.info("No unclassified events found.")
            conn.close()
            return 0
        
        logger.info(f"Found {len(unclassified_events)} unclassified events to process")
        
        classified_count = 0
        low_confidence_count = 0
        
        # Track fine-tuning counter
        fine_tune_counter = 0
        
        for event_id, title, description, calendar_id in unclassified_events:
            # Try to classify the event
            try:
                project_id, confidence = classify_event(title, description, calendar_id)
                
                if project_id:
                    # Update the event with the classified project
                    cursor.execute("""
                        UPDATE events
                        SET project_id = ?
                        WHERE id = ?
                    """, (project_id, event_id))
                    
                    classified_count += 1
                    fine_tune_counter += 1
                    
                    # Get project name for logging
                    cursor.execute("SELECT name FROM projects WHERE id = ?", (project_id,))
                    project_name = cursor.fetchone()[0] if cursor.fetchone() else f"ID:{project_id}"
                    
                    logger.info(f"Classified event '{title[:30]}...' as '{project_name}' with {confidence:.1f}% confidence")
                else:
                    low_confidence_count += 1
                    logger.info(f"Could not classify event '{title[:30]}...' with sufficient confidence ({confidence:.1f}%)")
            except Exception as e:
                logger.error(f"Error classifying event '{title[:30]}...': {e}")
        
        # Commit all changes
        conn.commit()
        
        # Log the results
        logger.info(f"Auto-classification complete: {classified_count} classified, {low_confidence_count} low confidence")
        
        # Check if we should trigger fine-tuning based on the total number of events classified
        if classified_count > 0:
            if fine_tune_counter >= 5:
                logger.info(f"Triggering fine-tuning after {fine_tune_counter} successful classifications")
                fine_tune_classifier()
        
        return classified_count
    except Exception as e:
        logger.error(f"Error during auto-classification: {e}", exc_info=True)
        return 0
    finally:
        try:
            conn.close()
        except:
            pass

# Initialize by loading the latest model
if 'st' in globals() and not hasattr(st.session_state, 'model_loaded'):
    load_latest_model()
    st.session_state.model_loaded = True

def init_db():
    """Initialize the database."""
    database.init_db()

def test_classification_system():
    """
    Test the classification system with a few sample events.
    This function is meant to be run manually for testing purposes.
    """
    logger.info("===== TESTING CLASSIFICATION SYSTEM =====")
    
    # First, ensure the database is initialized
    init_db()
    
    # 1. Check for existing projects
    conn = sqlite3.connect(database.DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT id, name FROM projects")
    existing_projects = cursor.fetchall()
    
    # Create test projects if none exist
    if not existing_projects:
        logger.info("No projects found, creating test projects")
        test_projects = [
            ("Work", "Work related activities and meetings"),
            ("Personal", "Personal appointments and events"),
            ("Learning", "Educational activities and courses"),
            ("Health", "Health and fitness related activities"),
            ("Family", "Family events and commitments")
        ]
        
        for name, desc in test_projects:
            cursor.execute("INSERT INTO projects (name, description) VALUES (?, ?)", (name, desc))
            logger.info(f"Created test project: {name}")
        
        conn.commit()
        cursor.execute("SELECT id, name FROM projects")
        existing_projects = cursor.fetchall()
    
    logger.info(f"Found {len(existing_projects)} projects in database")
    
    # 2. Create some test events if we don't have any
    cursor.execute("SELECT COUNT(*) FROM events")
    event_count = cursor.fetchone()[0]
    
    if event_count == 0:
        logger.info("No events found, creating test events")
        test_events = [
            ("Team Meeting", "Weekly team sync with engineering team", "Work"),
            ("Dentist Appointment", "Routine checkup with Dr. Smith", "Health"),
            ("Python Course", "Advanced Python programming webinar", "Learning"),
            ("Grocery Shopping", "Buy weekly groceries from Whole Foods", "Personal"),
            ("Family Dinner", "Dinner with parents at their house", "Family")
        ]
        
        # Insert test events
        for title, desc, project_name in test_events:
            # Get project ID
            cursor.execute("SELECT id FROM projects WHERE name = ?", (project_name,))
            project_id = cursor.fetchone()[0]
            
            # Create event
            start_time = datetime.now() + timedelta(days=random.randint(1, 30))
            end_time = start_time + timedelta(hours=1)
            
            cursor.execute("""
                INSERT INTO events 
                (title, description, start_time, end_time, project_id, calendar_id) 
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                title, 
                desc, 
                start_time.isoformat(), 
                end_time.isoformat(), 
                project_id,
                "test-calendar@example.com"
            ))
            
            logger.info(f"Created test event: {title} (Project: {project_name})")
        
        conn.commit()
    
    # 3. Test fine-tuning
    logger.info("Testing fine-tuning functionality...")
    fine_tune_result = fine_tune_classifier()
    
    if fine_tune_result:
        logger.info("Fine-tuning completed successfully!")
    else:
        logger.warning("Fine-tuning did not complete successfully")
    
    # 4. Test classification with new events
    logger.info("Testing classification with new events...")
    test_classifications = [
        "Quarterly Business Review with leadership team",
        "Yoga class at the gym",
        "Meeting with Python Study Group",
        "Birthday party for Mom",
        "Doctor appointment for annual physical"
    ]
    
    for test_event in test_classifications:
        project_id, confidence = classify_event(test_event)
        
        if project_id:
            cursor.execute("SELECT name FROM projects WHERE id = ?", (project_id,))
            project_name = cursor.fetchone()[0]
            logger.info(f"Classified '{test_event}' as '{project_name}' with {confidence:.1f}% confidence")
        else:
            logger.info(f"Could not classify '{test_event}' with sufficient confidence ({confidence:.1f}%)")
    
    # Close connection
    conn.close()
    
    logger.info("===== CLASSIFICATION SYSTEM TEST COMPLETE =====")

# This is only run when the script is executed directly
if __name__ == "__main__":
    # Initialize the database if running standalone
    init_db()
    
    # Test the classification system if environment variable is set
    if os.getenv("TEST_CLASSIFICATION") == "1":
        test_classification_system()
    else:
        # Test the classification with a sample event
        test_event = "Weekly team meeting with engineering"
        print(f"Classifying test event: '{test_event}'")
        project_id, confidence = classify_event(test_event)
        
        if project_id is not None:
            print(f"Classification result: Project ID {project_id}, Confidence {confidence:.2f}%")
        else:
            print(f"Classification result: Unknown (no project assigned), Confidence {confidence:.2f}%")