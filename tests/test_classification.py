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
    """
    Test the classification system with a few sample events.
    This function is meant to be run manually for testing purposes.
    """
    logger.info("===== TESTING CLASSIFICATION SYSTEM =====")
    
    # First, ensure the database is initialized
    database.init_db()
    
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
    fine_tune_result = classification.fine_tune_classifier()
    
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
        project_id, confidence = classification.classify_event(test_event)
        
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
    Test the MLflow configuration by creating a test run.
    This helps validate that MLflow is properly set up.
    """
    logger.info("Testing MLflow configuration...")
    
    # Initialize MLflow
    if not classification.init_mlflow():
        logger.error("Failed to initialize MLflow")
        return False
    
    # Create a test run
    with classification.mlflow.start_run(run_name=f"test_run_{datetime.now().strftime('%Y%m%d_%H%M%S')}"):
        # Log some test parameters and metrics
        classification.mlflow.log_param("test_param", "test_value")
        classification.mlflow.log_metric("test_metric", 1.0)
        classification.mlflow.log_text("This is a test run to validate MLflow configuration.", "test_note.txt")
        
        # Log run info
        run_id = classification.mlflow.active_run().info.run_id
        experiment_id = classification.mlflow.active_run().info.experiment_id
        
        logger.info(f"Created test run with ID: {run_id} in experiment: {experiment_id}")
        logger.info(f"MLflow UI URL: {classification.MLFLOW_TRACKING_URI}")
        
        return True

def create_test_experiment():
    """
    Create a test experiment with a sample run to validate MLflow configuration.
    This can be called manually to ensure the MLflow UI shows experiments.
    """
    # Initialize MLflow
    if not classification.init_mlflow():
        logger.error("Failed to initialize MLflow")
        return
    
    # Get or create the experiment
    try:
        experiment = classification.mlflow.get_experiment_by_name(classification.EXPERIMENT_NAME)
        if experiment is None:
            experiment_id = classification.mlflow.create_experiment(classification.EXPERIMENT_NAME)
            logger.info(f"Created experiment with ID: {experiment_id}")
        else:
            experiment_id = experiment.experiment_id
            logger.info(f"Using existing experiment with ID: {experiment_id}")
        
        # Set the experiment as active
        classification.mlflow.set_experiment(classification.EXPERIMENT_NAME)
        
        # Create a test run
        with classification.mlflow.start_run(run_name=f"manual_test_run_{datetime.now().strftime('%Y%m%d_%H%M%S')}"):
            # Log some test parameters
            classification.mlflow.log_param("test_source", "manual_test")
            classification.mlflow.log_param("timestamp", datetime.now().isoformat())
            
            # Log a test metric
            classification.mlflow.log_metric("test_value", 100)
            
            # Log a test artifact
            import tempfile
            with tempfile.NamedTemporaryFile(suffix=".txt", mode="w", delete=False) as f:
                f.write(f"Test artifact created at {datetime.now().isoformat()}")
                f.flush()
                classification.mlflow.log_artifact(f.name, "test_artifacts")
            
            # Get the run ID
            run_id = classification.mlflow.active_run().info.run_id
            logger.info(f"Created test run with ID: {run_id}")
            logger.info(f"View this run at: {classification.MLFLOW_TRACKING_URI}")
    
    except Exception as e:
        logger.error(f"Error creating test experiment: {e}")

class TestClassification(unittest.TestCase):
    """Unit tests for the classification module."""
    
    def setUp(self):
        """Set up test resources."""
        # Configure DSPy if needed
        if not classification.st.session_state.get('dspy_configured', False):
            classification.configure_dspy()
    
    def test_batch_classification(self):
        """Test batch classification functionality."""
        # Create test data
        test_events = [
            {'id': 1, 'title': 'Team Meeting about Website Design', 'description': 'Weekly sync with the design team'},
            {'id': 2, 'title': 'Dentist Appointment', 'description': 'Regular checkup'},
        ]
        
        # Run batch classification
        results = classification.batch_classify_events(test_events)
        
        # Verify results
        self.assertIsInstance(results, dict)
        self.assertEqual(len(results), len(test_events))
        
        # Check each result
        for event_id, (project_id, confidence) in results.items():
            self.assertIn(event_id, [1, 2])
            self.assertIsInstance(confidence, float)
            # We don't assert on project_id because it might be None if classification is uncertain

if __name__ == "__main__":
    # If run directly, execute the test system
    test_classification_system() 