#!/usr/bin/env python3
"""
Tests for the classification module.
"""

import os
import sqlite3
import logging
import random
from datetime import datetime, timedelta
import sys
import unittest

# Add the parent directory to the path so we can import modules from there
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import the modules we want to test
import database
import classification

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_classification_system():
    """Test the classification system with sample events."""
    logger.info("===== STARTING CLASSIFICATION SYSTEM TEST =====")
    
    # 1. Initialize database
    logger.info("Initializing database...")
    classification.init_db()
    
    # 2. Create test projects if they don't exist
    conn = sqlite3.connect(database.DB_PATH)
    cursor = conn.cursor()
    
    test_projects = [
        ("Work", 40, 1, "Work-related activities"),
        ("Health", 5, 2, "Health and fitness activities"),
        ("Learning", 10, 3, "Learning and education activities"),
        ("Personal", 5, 4, "Personal activities"),
        ("Family", 10, 5, "Family-related activities")
    ]
    
    for name, hours, priority, desc in test_projects:
        cursor.execute("SELECT id FROM projects WHERE name = ?", (name,))
        if not cursor.fetchone():
            cursor.execute("""
                INSERT INTO projects (name, estimated_hours, priority, description)
                VALUES (?, ?, ?, ?)
            """, (name, hours, priority, desc))
            logger.info(f"Created test project: {name}")
    
    conn.commit()
    
    # 3. Create test events if none exist
    cursor.execute("SELECT COUNT(*) FROM events")
    if cursor.fetchone()[0] == 0:
        logger.info("No events found, creating test events")
        test_events = [
            ("Team Meeting", "Weekly team sync with engineering team", "Work", "2024-03-20T10:00:00"),
            ("Dentist Appointment", "Routine checkup with Dr. Smith", "Health", "2024-03-21T14:00:00"),
            ("Python Course", "Advanced Python programming webinar", "Learning", "2024-03-22T19:00:00"),
            ("Grocery Shopping", "Buy weekly groceries from Whole Foods", "Personal", "2024-03-23T09:00:00"),
            ("Family Dinner", "Dinner with parents at their house", "Family", "2024-03-24T18:00:00")
        ]
        
        # Insert test events
        for title, desc, project_name, start_time in test_events:
            # Get project ID
            cursor.execute("SELECT id FROM projects WHERE name = ?", (project_name,))
            project_id = cursor.fetchone()[0]
            
            # Create event
            start_dt = datetime.fromisoformat(start_time)
            end_time = start_dt + timedelta(hours=1)
            
            cursor.execute("""
                INSERT INTO events 
                (title, description, start_time, end_time, project_id, calendar_id) 
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                title, 
                desc, 
                start_dt.isoformat(), 
                end_time.isoformat(), 
                project_id,
                "test-calendar@example.com"
            ))
            
            logger.info(f"Created test event: {title} (Project: {project_name})")
        
        conn.commit()
    
    # 4. Test classification with new events
    logger.info("Testing classification with new events...")
    test_classifications = [
        ("Quarterly Business Review with leadership team", "2024-03-25T10:00:00"),
        ("Yoga class at the gym", "2024-03-26T07:00:00"),
        ("Meeting with Python Study Group", "2024-03-27T19:00:00"),
        ("Birthday party for Mom", "2024-03-28T18:00:00"),
        ("Doctor appointment for annual physical", "2024-03-29T14:00:00")
    ]
    
    # Configure DSPy first
    lm = classification.configure_dspy()
    if not lm:
        logger.error("Failed to configure DSPy. Test cannot continue.")
        return
    
    for test_event, start_time in test_classifications:
        project_id, confidence = classification.classify_event(
            test_event,
            event_start_time=start_time,
            event_calendar="test-calendar@example.com",
            lm=lm
        )
        
        if project_id:
            cursor.execute("SELECT name FROM projects WHERE id = ?", (project_id,))
            project_name = cursor.fetchone()[0]
            logger.info(f"Classified '{test_event}' as '{project_name}' with {confidence:.1f}% confidence")
        else:
            logger.info(f"Could not classify '{test_event}' with sufficient confidence ({confidence:.1f}%)")
    
    # Close connection
    conn.close()
    
    logger.info("===== CLASSIFICATION SYSTEM TEST COMPLETE =====")

def test_mlflow():
    """
    Test that MLflow is configured and autologging is enabled.
    """
    logger.info("Testing MLflow configuration...")
    
    try:
        # Verify MLflow tracking URI is set
        tracking_uri = classification.mlflow.get_tracking_uri()
        logger.info(f"MLflow tracking URI is set to: {tracking_uri}")
        
        # Verify experiment exists
        experiment = classification.mlflow.get_experiment_by_name(classification.EXPERIMENT_NAME)
        if experiment:
            logger.info(f"Found experiment '{classification.EXPERIMENT_NAME}' with ID: {experiment.experiment_id}")
        else:
            logger.warning(f"Experiment '{classification.EXPERIMENT_NAME}' not found. It will be created when needed.")
        
        # Make a simple prediction to test autologging
        lm = classification.configure_dspy()
        if lm:
            test_result = classification.classify_event("Test event for MLflow", lm=lm)
            logger.info(f"Test prediction completed: {test_result}")
            return True
        else:
            logger.error("Failed to configure DSPy")
            return False
    except Exception as e:
        logger.error(f"Error testing MLflow: {e}")
        return False

def create_test_experiment():
    """
    Create a simple test to verify MLflow autologging works.
    """
    logger.info("Creating test experiment...")
    
    # Configure DSPy
    lm = classification.configure_dspy()
    if not lm:
        logger.error("Failed to configure DSPy. Test cannot continue.")
        return
    
    # Run a few classifications to generate logged data
    test_events = [
        "Team meeting about product roadmap",
        "Dentist appointment for annual cleaning",
        "Python study group session"
    ]
    
    for event in test_events:
        result = classification.classify_event(event, lm=lm)
        logger.info(f"Classified '{event}': {result}")
    
    logger.info(f"Test complete. Check MLflow at {classification.MLFLOW_TRACKING_URI} for results.")

class TestClassification(unittest.TestCase):
    """Unit tests for the classification module."""
    
    def setUp(self):
        """Set up test resources."""
        # Configure DSPy for testing
        self.lm = classification.configure_dspy()
        self.assertIsNotNone(self.lm, "Failed to configure DSPy")
    
    def test_batch_classification(self):
        """Test batch classification functionality."""
        # Create test data
        test_events = [
            {'id': 1, 'title': 'Team Meeting about Website Design', 'description': 'Weekly sync with the design team'},
            {'id': 2, 'title': 'Dentist Appointment', 'description': 'Regular checkup'},
        ]
        
        # Run batch classification
        results = classification.batch_classify_events(test_events, lm=self.lm)
        
        # Verify results
        self.assertIsInstance(results, dict)
        self.assertLessEqual(len(results), len(test_events))  # May be less due to limit in batch_classify_events
        
        # Check each result
        for event_id, (project_id, confidence) in results.items():
            self.assertIn(event_id, [1, 2])
            self.assertIsInstance(confidence, float)
            # We don't assert on project_id because it might be None if classification is uncertain

if __name__ == "__main__":
    # If run directly, execute the test system
    test_classification_system() 