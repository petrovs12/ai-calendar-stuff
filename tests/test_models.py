#!/usr/bin/env python3
"""
Test script to verify the Pydantic models and classification functions work correctly.
"""

import os
import sys
import json
import logging
from datetime import datetime
import unittest

# Add the parent directory to the path so we can import modules from there
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import the models module
from models import (
    CalendarEvent, 
    CalendarEventTime, 
    EventAttendee, 
    Project, 
)
from timeutils import TimeOfDay, get_time_of_day


# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class TestModels(unittest.TestCase):
    """Test the Pydantic models and classification functions."""
    
    def test_calendar_event_time(self):
        """Test the CalendarEventTime model."""
        # Test with dateTime
        event_time = CalendarEventTime(dateTime="2023-04-01T14:30:00+01:00")
        self.assertIsNotNone(event_time.dt)
        self.assertEqual(event_time.dt.hour, 14)
        self.assertEqual(event_time.dt.minute, 30)
        
        # Test with date
        event_date = CalendarEventTime(date="2023-04-01")
        self.assertIsNotNone(event_date.dt)
        self.assertEqual(event_date.dt.day, 1)
        self.assertEqual(event_date.dt.month, 4)
        self.assertEqual(event_date.dt.hour, 0)  # Midnight
        
        # Test with direct datetime
        now = datetime.now()
        direct_dt = CalendarEventTime(dt=now)
        self.assertEqual(direct_dt.dt, now)
    
    def test_time_of_day(self):
        """Test the get_time_of_day function."""
        morning = datetime.now().replace(hour=8, minute=0)
        afternoon = datetime.now().replace(hour=14, minute=0)
        evening = datetime.now().replace(hour=20, minute=0)
        
        self.assertEqual(get_time_of_day(morning), TimeOfDay.MORNING)
        self.assertEqual(get_time_of_day(afternoon), TimeOfDay.AFTERNOON)
        self.assertEqual(get_time_of_day(evening), TimeOfDay.EVENING)
    
    def test_event_attendee(self):
        """Test the EventAttendee model."""
        attendee = EventAttendee(
            email="test@example.com",
            responseStatus="accepted",
            displayName="Test User",
            self=True,
            organizer=False,
            resource=False
        )
        
        self.assertEqual(attendee.email, "test@example.com")
        self.assertEqual(attendee.response_status, "accepted")
        self.assertEqual(attendee.display_name, "Test User")
        self.assertTrue(attendee.is_self)
        self.assertFalse(attendee.is_organizer)
        self.assertFalse(attendee.is_resource)
    
    def test_calendar_event(self):
        """Test the CalendarEvent model."""
        # Create a simple event
        event = CalendarEvent(
            id="event123",
            summary="Test Event",
            description="This is a test event",
            start=CalendarEventTime(dateTime="2023-04-01T10:00:00"),
            end=CalendarEventTime(dateTime="2023-04-01T11:00:00"),
            calendar_id="primary"
        )
        
        # Test basic properties
        self.assertEqual(event.id, "event123")
        self.assertEqual(event.summary, "Test Event")
        self.assertEqual(event.calendar_id, "primary")
        
        # Test datetime accessors
        self.assertIsNotNone(event.start_dt)
        self.assertEqual(event.start_dt.hour, 10)
        self.assertEqual(event.end_dt.hour, 11)
        
        # Test time_of_day auto-assignment
        self.assertEqual(event.time_of_day, TimeOfDay.MORNING)
        
        # Test to_db_dict method
        db_dict = event.to_db_dict()
        self.assertEqual(db_dict["event_id"], "event123")
        self.assertEqual(db_dict["title"], "Test Event")
        self.assertTrue("raw_event_data" in db_dict)
        
        # Test JSON serialization
        event_json = json.dumps(event.model_dump())
        self.assertIsInstance(event_json, str)
        
        # Test to_classification_input method
        classification_input = event.to_classification_input()
        self.assertEqual(classification_input["event"], "Test Event This is a test event")
        self.assertEqual(classification_input["calendar"], "primary")
        self.assertEqual(classification_input["time_of_day"], TimeOfDay.MORNING)
    
    def test_project(self):
        """Test the Project model."""
        project = Project(
            id=1,
            name="Test Project",
            estimated_hours=40,
            priority=2,
            description="This is a test project"
        )
        
        self.assertEqual(project.id, 1)
        self.assertEqual(project.name, "Test Project")
        
        # Test to_db_dict method
        db_dict = project.to_db_dict()
        self.assertEqual(db_dict["id"], 1)
        self.assertEqual(db_dict["name"], "Test Project")
    
    def test_event_serialization(self):
        """Test that events can be serialized and deserialized correctly."""
        # Create a test event
        original_event = CalendarEvent(
            id="test-event-123",
            summary="Test Serialization",
            description="Testing serialization of events",
            start=CalendarEventTime(dateTime=datetime.now().isoformat()),
            end=CalendarEventTime(dateTime=datetime.now().replace(hour=datetime.now().hour+1).isoformat()),
            calendar_id="test-calendar"
        )
        
        # Serialize to JSON
        event_json = json.dumps(original_event.model_dump())
        
        # Deserialize from JSON
        event_dict = json.loads(event_json)
        deserialized_event = CalendarEvent.model_validate(event_dict)

        # Verify the event was preserved
        self.assertEqual(deserialized_event.id, original_event.id)
        self.assertEqual(deserialized_event.summary, original_event.summary)
        self.assertEqual(deserialized_event.description, original_event.description)
        
        # Time will be deserialized as a string that needs to be parsed
        # We just check basic properties are there
        self.assertIsNotNone(deserialized_event.start)
        self.assertIsNotNone(deserialized_event.end)
    
    def test_database_conversion(self):
        """Test conversion to and from database format."""
        # Create a test event
        event = CalendarEvent(
            id="db-test-123",
            summary="Database Test",
            description="Testing database conversion",
            start=CalendarEventTime(dateTime=datetime.now().isoformat()),
            end=CalendarEventTime(dateTime=datetime.now().replace(hour=datetime.now().hour+1).isoformat()),
            calendar_id="test-db-calendar",
            project_id=5,
            project_name="Test Project"
        )
        
        # Convert to database dict
        db_dict = event.to_db_dict()
        
        # Verify database dict contains correct values
        self.assertEqual(db_dict["event_id"], "db-test-123")
        self.assertEqual(db_dict["title"], "Database Test")
        self.assertEqual(db_dict["project_id"], 5)
        
        # Create event from database dict with raw_event_data
        from_db = CalendarEvent.from_db_dict(db_dict)
        
        # Verify event was reconstructed correctly
        self.assertEqual(from_db.id, event.id)
        self.assertEqual(from_db.summary, event.summary)
        self.assertEqual(from_db.project_id, event.project_id)

if __name__ == "__main__":
    unittest.main() 