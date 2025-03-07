#!/usr/bin/env python3
"""
Event classification module using DSPy and OpenAI to classify calendar events into projects.
"""

import os
import logging
from typing import List, Optional, Tuple, Dict, Any

import dspy
from dspy.predict import Predict
import mlflow

mlflow.set_experiment("DSPy Calendar Event Classification")

# Local imports
import database

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Configure OpenAI API for DSPy
api_key = os.getenv("OPENAI_API_KEY", "")
model_name = os.getenv("OPENAI_MODEL", "gpt-3.5-turbo")
import dspy
lm = dspy.LM('openai/gpt-4o-mini', api_key=api_key)
dspy.configure(lm=lm)

try:
    if not api_key:
        logger.warning("OpenAI API key not found in environment variables. Classification will not work.")
    else:
        # Set up the LLM
        llm = dspy.OpenAI(model=model_name, api_key=api_key)
        dspy.settings.configure(lm=llm)
        logger.info(f"DSPy configured with OpenAI model: {model_name}")
except Exception as e:
    logger.error(f"Error configuring DSPy with OpenAI: {e}")

# Define a DSPy Signature for event classification
class EventClassification(dspy.Signature):
    """Classify a calendar event into one of the given project names or 'Unknown'."""
    event: str = dspy.InputField()        # The event title/description text
    projects: str = dspy.InputField()     # Comma-separated list of existing project names
    project: str = dspy.OutputField()     # Predicted project name (or "Unknown")
    confidence: float = dspy.OutputField()# Confidence score for the classification

# Create a DSPy module for prediction using the signature
classify_event_module = dspy.Predict(EventClassification)

# Confidence threshold for considering a classification reliable
CONFIDENCE_THRESHOLD = 0.7

def classify_event(event_title: str, event_description: str = "") -> Tuple[Optional[int], float]:
    """
    Classify a calendar event into a project. 
    
    Args:
        event_title: The title or summary of the event
        event_description: Optional description of the event
    
    Returns:
        Tuple of (project_id, confidence_score). 
        Project ID is None if classification fails or confidence is low.
    """
    logger.info(f"Classifying event: {event_title}")
    
    # Check if OpenAI API is configured
    if not api_key:
        logger.error("OpenAI API key not set. Cannot classify event.")
        return None, 0.0
    
    # Fetch the list of current project names from the database
    projects = []
    try:
        conn = database.sqlite3.connect(database.DB_PATH)
        cur = conn.cursor()
        cur.execute("SELECT id, name FROM projects;")
        rows = cur.fetchall()
        conn.close()
        
        if not rows:
            logger.warning("No projects found in database. Cannot classify event.")
            return None, 0.0
            
        projects = {row[0]: row[1] for row in rows}  # Dict of id: name
        logger.info(f"Found {len(projects)} projects for classification")
    except Exception as e:
        logger.error(f"Error fetching projects from database: {e}")
        return None, 0.0
    
    # Prepare input for classification
    event_text = event_title
    if event_description:
        event_text += " " + event_description
    
    projects_list = ", ".join(projects.values())
    print(f"Projects list: {projects_list}")
    
    try:
        # Call the DSPy classification module
        logger.info(f"Sending classification request to OpenAI with {len(projects)} projects")
        result = classify_event_module(event=event_text, projects=projects_list)
        print(f"Result: {result}")
        
        predicted_project = result.project.strip()
        confidence = 0.0
        
        try:
            confidence = float(result.confidence)
            logger.info(f"Model returned project '{predicted_project}' with confidence {confidence:.2f}")
        except (ValueError, TypeError):
            logger.warning(f"Could not parse confidence score: {result.confidence}")
            confidence = 0.0
        
        # Check if prediction is reliable
        if predicted_project.lower() == "unknown" or confidence < CONFIDENCE_THRESHOLD:
            logger.info(f"Classification uncertain: project='{predicted_project}', confidence={confidence:.2f}")
            return None, confidence
        
        # Find the project ID by name
        project_id = None
        for pid, pname in projects.items():
            if pname.lower() == predicted_project.lower():
                project_id = pid
                break
        
        if project_id:
            logger.info(f"Classified event as project ID {project_id} with confidence {confidence:.2f}")
            return project_id, confidence
        else:
            logger.warning(f"Predicted project '{predicted_project}' not found in database")
            return None, confidence
            
    except Exception as e:
        logger.error(f"Error during classification: {e}")
        return None, 0.0

def init_db():
    """Initialize the database."""
    database.init_db()

if __name__ == "__main__":
    # Initialize the database if running standalone
    init_db()
    
    # Test the classification with a sample event
    test_event = "Weekly team meeting with engineering"
    print(f"Classifying test event: '{test_event}'")
    project_id, confidence = classify_event(test_event)
    
    if project_id is not None:
        print(f"Classification result: Project ID {project_id}, Confidence {confidence:.2f}")
    else:
        print("Classification result: Unknown (no project assigned)")