#!/usr/bin/env python3
"""
Shared data models for the calendar application using Pydantic.

This module provides consistent, type-validated models for calendar events
and related data structures used throughout the application.
"""

from datetime import datetime, date, time
from typing import Dict, List, Optional, Union, Any, Literal
from enum import Enum
import json

from pydantic import BaseModel, Field, model_validator, field_validator, ConfigDict

from timeutils import TimeOfDay, get_time_of_day, DateTimeEncoder

class EventAttendee(BaseModel):
    """Model for a calendar event attendee."""
    model_config = ConfigDict(from_attributes=True, arbitrary_types_allowed=True)
    
    email: str
    response_status: Optional[str] = Field(None, alias="responseStatus")
    display_name: Optional[str] = Field(None, alias="displayName")
    is_self: Optional[bool] = Field(None, alias="self")
    is_organizer: Optional[bool] = Field(None, alias="organizer")
    is_resource: Optional[bool] = Field(None, alias="resource")


class CalendarEventTime(BaseModel):
    """
    Model for calendar event time information.
    Can handle both dateTime and date-only formats from Google Calendar.
    """
    model_config = ConfigDict(from_attributes=True, arbitrary_types_allowed=True)
    
    # Original string representations from Google Calendar API
    date_time: Optional[str] = Field(default=None, alias="dateTime")
    date_str: Optional[str] = Field(default=None, alias="date")
    
    # Native datetime object (derived from either date_time or date_str)
    dt: Optional[datetime] = Field(default=None)
    
    @model_validator(mode='after')
    def set_dt_after_validation(self):
        """Process datetime after validation."""
        # If dt is already set, keep it
        if self.dt is not None:
            return self
            
        # Try to parse date_time
        if self.date_time:
            try:
                # Handle 'Z' timezone marker
                dt_str = self.date_time
                if isinstance(dt_str, str) and 'Z' in dt_str:
                    dt_str = dt_str.replace('Z', '+00:00')
                self.dt = datetime.fromisoformat(dt_str)
            except Exception as e:
                print(f"Error parsing dateTime: {e}")
                
        # Try to parse date_str
        elif self.date_str:
            try:
                # For date-only events, use midnight
                date_obj = datetime.fromisoformat(self.date_str).date()
                self.dt = datetime.combine(date_obj, time())
            except Exception as e:
                print(f"Error parsing date: {e}")
                
        return self
    
    def model_dump(self, *args, **kwargs):
        """Custom dict method to always include the dt field."""
        result = super().model_dump(*args, **kwargs)
        # Convert datetime to ISO format for JSON serialization
        if self.dt:
            result["dt_iso"] = self.dt.isoformat()
            # Remove the non-serializable datetime object
            if "dt" in result:
                del result["dt"]
        return result
        
    @classmethod
    def from_google_dict(cls, event_time_dict: Dict[str, Any]) -> "CalendarEventTime":
        """Create a CalendarEventTime from a Google Calendar API datetime dictionary.
        
        Args:
            event_time_dict: Dictionary containing date or dateTime from Google Calendar
            
        Returns:
            CalendarEventTime instance
        """
        # Extract date_time and date fields from the Google API response
        date_time = event_time_dict.get('dateTime')
        date_str = event_time_dict.get('date')
        
        # Create CalendarEventTime instance
        return cls(
            dateTime=date_time,
            date=date_str
        )


class CalendarEvent(BaseModel):
    """
    Comprehensive model for a Google Calendar event.
    
    This model serves as the central data structure for calendar events
    throughout the application, providing consistent validation and serialization.
    """
    # Configuration for ORM mode
    model_config = ConfigDict(from_attributes=True, arbitrary_types_allowed=True)
    
    # Core Google Calendar fields
    id: str
    kind: Optional[str] = Field(default=None)
    etag: Optional[str] = Field(default=None)
    status: Optional[str] = Field(default=None)
    html_link: Optional[str] = Field(default=None, alias="htmlLink")
    created: Optional[str] = Field(default=None)
    updated: Optional[str] = Field(default=None)
    summary: str
    description: Optional[str] = Field(default=None)
    location: Optional[str] = Field(default=None)
    calendar_id: Optional[str] = Field(default=None, alias="calendar_id")
    
    # Time information
    start: CalendarEventTime
    end: CalendarEventTime
    
    # Participant information
    creator: Optional[Dict[str, Any]] = Field(default=None)
    organizer: Optional[Dict[str, Any]] = Field(default=None)
    attendees: Optional[List[Dict[str, Any]]] = Field(default=None)
    
    # Recurrence information
    recurring_event_id: Optional[str] = Field(default=None, alias="recurringEventId")
    original_start_time: Optional[CalendarEventTime] = Field(default=None, alias="originalStartTime")
    
    # Additional Google Calendar fields
    ical_uid: Optional[str] = Field(default=None, alias="iCalUID")
    sequence: Optional[int] = Field(default=None)
    extended_properties: Optional[Dict[str, Any]] = Field(default=None, alias="extendedProperties")
    hangout_link: Optional[str] = Field(default=None, alias="hangoutLink")
    conference_data: Optional[Dict[str, Any]] = Field(default=None, alias="conferenceData")
    reminders: Optional[Dict[str, Any]] = Field(default=None)
    event_type: Optional[str] = Field(default=None, alias="eventType")
    
    # Classification fields (added by our application)
    project_id: Optional[int] = Field(default=None)
    project_name: Optional[str] = Field(default=None)
    classification_confidence: Optional[float] = Field(default=None)
    time_of_day: Optional[TimeOfDay] = Field(default=None)
    
    @model_validator(mode='after')
    def set_derived_fields(self):
        """Set derived fields based on other values."""
        # Set time_of_day based on start time
        if self.start and self.start.dt:
            self.time_of_day = get_time_of_day(self.start.dt)
        return self
    
    @property
    def start_dt(self) -> Optional[datetime]:
        """Convenient accessor for start datetime."""
        return self.start.dt if self.start else None
        
    @property
    def end_dt(self) -> Optional[datetime]:
        """Convenient accessor for end datetime."""
        return self.end.dt if self.end else None
    
    @property
    def creator_email(self) -> Optional[str]:
        """Extract creator email."""
        return self.creator.get("email") if self.creator else None
    
    @property
    def organizer_email(self) -> Optional[str]:
        """Extract organizer email."""
        return self.organizer.get("email") if self.organizer else None
    
    @property
    def attendee_emails(self) -> List[str]:
        """Extract list of attendee emails."""
        if not self.attendees:
            return []
        return [a.get("email", "") for a in self.attendees]
    
    @property
    def has_reminders(self) -> bool:
        """Check if event has reminders."""
        if not self.reminders:
            return False
        return bool(self.reminders.get("useDefault", False) or 
                   self.reminders.get("overrides", []))
    
    def to_classification_input(self) -> Dict[str, Any]:
        """
        Convert to a dictionary suitable for classification input.
        
        Returns:
            Dict with required fields for the classification process
        """
        return {
            "event": f"{self.summary} {self.description or ''}".strip(),
            "calendar": self.calendar_id or "",
            "iso_time": self.start_dt.isoformat() if self.start_dt else "",
            "day_of_week": self.start_dt.strftime("%A") if self.start_dt else "",
            "time_of_day": self.time_of_day or TimeOfDay.UNKNOWN,
            "created": self.created or "",
            "updated": self.updated or "",
            "creator": self.creator_email or "",
            "organizer": self.organizer_email or "",
            "attendees": ", ".join(self.attendee_emails),
            "has_reminders": "Yes" if self.has_reminders else "No",
            "event_type": self.event_type or "default"
        }
    
    def model_dump(self, *args, **kwargs):
        """Custom model_dump method to handle datetime objects."""
        data = super().model_dump(*args, **kwargs)
        
        # Process nested datetime objects
        if 'start' in data and 'dt' in data['start']:
            if data['start']['dt']:
                data['start']['dt_iso'] = data['start']['dt'].isoformat()
            del data['start']['dt']
            
        if 'end' in data and 'dt' in data['end']:
            if data['end']['dt']:
                data['end']['dt_iso'] = data['end']['dt'].isoformat()
            del data['end']['dt']
            
        return data
    
    @classmethod
    def from_google_dict(cls, event_dict: Dict[str, Any], calendar_id: Optional[str] = None) -> 'CalendarEvent':
        """Create a CalendarEvent from a Google Calendar API event dictionary.
        
        Args:
            event_dict: Dictionary from Google Calendar API
            calendar_id: Calendar ID, if not included in the event dictionary
            
        Returns:
            CalendarEvent instance
        """
        # Create start and end time objects
        start = CalendarEventTime.from_google_dict(event_dict.get('start', {}))
        end = CalendarEventTime.from_google_dict(event_dict.get('end', {}))
        
        # Use provided calendar_id or the one in event_dict
        cal_id = calendar_id or event_dict.get('calendar_id') or event_dict.get('calendarId')
        
        # Create the event with required fields
        return cls(
            id=event_dict.get('id', ''),
            summary=event_dict.get('summary', 'Untitled Event'),
            start=start,
            end=end,
            
            # Optional fields with proper defaults
            kind=event_dict.get('kind'),
            etag=event_dict.get('etag'),
            status=event_dict.get('status'),
            html_link=event_dict.get('htmlLink'),
            created=event_dict.get('created'),
            updated=event_dict.get('updated'),
            description=event_dict.get('description'),
            location=event_dict.get('location'),
            calendar_id=cal_id,
            creator=event_dict.get('creator'),
            organizer=event_dict.get('organizer'),
            attendees=event_dict.get('attendees'),
            recurring_event_id=event_dict.get('recurringEventId'),
            original_start_time=CalendarEventTime.from_google_dict(event_dict.get('originalStartTime', {})) if event_dict.get('originalStartTime') else None,
            ical_uid=event_dict.get('iCalUID'),
            sequence=event_dict.get('sequence'),
            extended_properties=event_dict.get('extendedProperties'),
            hangout_link=event_dict.get('hangoutLink'),
            conference_data=event_dict.get('conferenceData'),
            reminders=event_dict.get('reminders'),
            event_type=event_dict.get('eventType')
        )


class Project(BaseModel):
    """Model for a project."""
    # Configuration for ORM mode
    model_config = ConfigDict(from_attributes=True, arbitrary_types_allowed=True)
    
    id: Optional[int] = None
    name: str
    estimated_hours: Optional[int] = None
    priority: Optional[int] = None
    description: Optional[str] = None
    
    def to_db_dict(self) -> Dict[str, Any]:
        """Convert to a dictionary suitable for database storage."""
        return {
            "id": self.id,
            "name": self.name,
            "estimated_hours": self.estimated_hours,
            "priority": self.priority,
            "description": self.description
        }
    
    @classmethod
    def from_db_dict(cls, db_dict: Dict[str, Any]) -> "Project":
        """Create a Project from database dictionary."""
        return cls(
            id=db_dict.get("id"),
            name=db_dict.get("name", ""),
            estimated_hours=db_dict.get("estimated_hours"),
            priority=db_dict.get("priority"),
            description=db_dict.get("description", "")
        )


class EventClassificationResult(BaseModel):
    """Model for event classification results."""
    event_id: str
    project: str
    confidence: float
    explanation: Optional[str] = None
    
    @property
    def is_confident(self) -> bool:
        """Check if classification confidence is above threshold."""
        # Default threshold (can be made configurable)
        THRESHOLD = 70.0
        return self.confidence >= THRESHOLD

    model_config = ConfigDict(from_attributes=True, arbitrary_types_allowed=True)