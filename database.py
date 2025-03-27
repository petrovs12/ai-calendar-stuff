"""
Database module using SQLAlchemy for ORM with Pydantic model integration.
"""
import os
import json
import logging
from typing import List, Optional, Dict, Any, Union
from datetime import datetime

from sqlalchemy import create_engine, Column, Integer, String, Text, ForeignKey, Boolean, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship, Session

# Import our Pydantic models
from models import CalendarEvent, Project, DateTimeEncoder, CalendarEventTime

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Database configuration
DB_PATH = "planner.db"
SQLALCHEMY_DATABASE_URL = f"sqlite:///{DB_PATH}"

# Create SQLAlchemy engine and session
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create base class for SQLAlchemy models
Base = declarative_base()

# Define SQLAlchemy models
class ProjectModel(Base):
    """SQLAlchemy model for projects."""
    __tablename__ = "projects"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, nullable=False)
    estimated_hours = Column(Integer, nullable=True)
    priority = Column(Integer, nullable=True)
    description = Column(Text, nullable=True)
    
    # Relationship to events
    events = relationship("EventModel", back_populates="project")
    proposed_events = relationship("ProposedEventModel", back_populates="project")
    
    def to_pydantic(self) -> Project:
        """Convert to Pydantic model."""
        return Project.model_validate(self, from_attributes=True)


class EventModel(Base):
    """SQLAlchemy model for events."""
    __tablename__ = "events"
    
    id = Column(Integer, primary_key=True)
    event_id = Column(String, unique=True, nullable=False)
    summary = Column(String)
    description = Column(String, nullable=True)
    location = Column(String, nullable=True)
    calendar_id = Column(String, nullable=True)
    start_time = Column(DateTime, nullable=True)
    end_time = Column(DateTime, nullable=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=True)
    
    # Relationships
    project = relationship("ProjectModel", back_populates="events")
    
    def to_pydantic(self) -> CalendarEvent:
        """Convert SQLAlchemy model to Pydantic model."""
        # Create start and end time objects
        start = CalendarEventTime(
            date_time=self.start_time.isoformat() if self.start_time else None,
            dt=self.start_time
        )
        
        end = CalendarEventTime(
            date_time=self.end_time.isoformat() if self.end_time else None,
            dt=self.end_time
        )
        
        # Get project name if available
        project_name = None
        if self.project:
            project_name = self.project.name
            
        # Create the CalendarEvent
        return CalendarEvent(
            id=self.event_id,
            summary=self.summary or "",
            description=self.description or "",
            location=self.location,
            calendar_id=self.calendar_id,
            start=start,
            end=end,
            project_id=self.project_id,
            project_name=project_name
        )


class ProposedEventModel(Base):
    """SQLAlchemy model for proposed events."""
    __tablename__ = "proposed_events"
    
    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)
    proposed_start = Column(String, nullable=False)
    proposed_end = Column(String, nullable=False)
    
    # Relationship to project
    project = relationship("ProjectModel", back_populates="proposed_events")


class TrackingModel(Base):
    """SQLAlchemy model for tracking user confirmations."""
    __tablename__ = "tracking"
    
    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=True)
    event_id = Column(Integer, ForeignKey("events.id"), nullable=True)
    proposed_event_id = Column(Integer, ForeignKey("proposed_events.id"), nullable=True)
    confirmed = Column(Boolean, default=True)
    confirmation_time = Column(String, nullable=True)


def init_db(db_path: str = DB_PATH) -> None:
    """Initialize the database and create tables if they don't exist."""
    logger.info(f"Initializing database: {os.path.basename(db_path)}")
    Base.metadata.create_all(bind=engine)
    logger.info(f"Database initialized at {os.path.abspath(db_path)}")


def get_db_session() -> Session:
    """Get a new database session."""
    return SessionLocal()


def get_projects() -> List[Project]:
    """
    Retrieve all projects from the database.
    
    Returns:
        List of Project objects
    """
    db = get_db_session()
    try:
        projects = db.query(ProjectModel).order_by(ProjectModel.name).all()
        return [project.to_pydantic() for project in projects]
    finally:
        db.close()


def add_project(name: str, estimated_hours: Optional[int] = None, 
               priority: Optional[int] = None, description: Optional[str] = None) -> int:
    """
    Add a new project to the database.
    
    Args:
        name: Project name
        estimated_hours: Optional estimated hours per week
        priority: Optional priority level
        description: Optional project description
        
    Returns:
        ID of the newly created project
    """
    db = get_db_session()
    try:
        project = ProjectModel(
            name=name,
            estimated_hours=estimated_hours,
            priority=priority,
            description=description
        )
        db.add(project)
        db.commit()
        db.refresh(project)
        return project.id
    finally:
        db.close()


def get_project_by_id(project_id: int) -> Optional[Project]:
    """
    Get a project by its ID.
    
    Args:
        project_id: Project ID
        
    Returns:
        Project object or None if not found
    """
    db = get_db_session()
    try:
        project = db.query(ProjectModel).filter(ProjectModel.id == project_id).first()
        if not project:
            return None
        return project.to_pydantic()
    finally:
        db.close()


def store_events(events: List[Union[CalendarEvent, Dict[str, Any]]], db_path: str = DB_PATH) -> int:
    """
    Store events in the database.
    
    Args:
        events: List of CalendarEvent objects or dictionaries
        db_path: Path to the database file
        
    Returns:
        Number of events stored
    """
    logger.info(f"Storing {len(events)} events in database: {os.path.basename(db_path)}")
    
    try:
        # Initialize database
        init_db(db_path)
        
        # Get session
        db = get_db_session()
        
        count = 0
        for event in events:
            try:
                # Convert dict to Pydantic model if needed
                if isinstance(event, dict):
                    try:
                        calendar_id = event.get('calendar_id', '')
                        event = CalendarEvent.from_google_dict(event, calendar_id=calendar_id)
                    except Exception as e:
                        logger.error(f"Error converting dict to CalendarEvent: {e}")
                        continue
                
                # Check if event already exists
                existing = db.query(EventModel).filter(EventModel.event_id == event.id).first()
                
                if existing:
                    # Update existing event
                    existing.summary = event.summary
                    existing.description = event.description
                    existing.location = event.location
                    existing.calendar_id = event.calendar_id
                    
                    # Handle datetime conversion
                    if event.start.dt:
                        existing.start_time = event.start.dt
                    elif event.start.date_time:
                        try:
                            existing.start_time = datetime.fromisoformat(event.start.date_time.replace('Z', '+00:00'))
                        except Exception as e:
                            logger.warning(f"Could not parse start_time: {e}")
                            existing.start_time = None
                    
                    if event.end.dt:
                        existing.end_time = event.end.dt
                    elif event.end.date_time:
                        try: 
                            existing.end_time = datetime.fromisoformat(event.end.date_time.replace('Z', '+00:00'))
                        except Exception as e:
                            logger.warning(f"Could not parse end_time: {e}")
                            existing.end_time = None
                            
                    db.commit()
                    logger.debug(f"Updated existing event: {event.id}")
                else:
                    # Create new event
                    start_time = None
                    if event.start.dt:
                        start_time = event.start.dt
                    elif event.start.date_time:
                        try:
                            start_time = datetime.fromisoformat(event.start.date_time.replace('Z', '+00:00'))
                        except Exception as e:
                            logger.warning(f"Could not parse start_time: {e}")
                    
                    end_time = None
                    if event.end.dt:
                        end_time = event.end.dt
                    elif event.end.date_time:
                        try:
                            end_time = datetime.fromisoformat(event.end.date_time.replace('Z', '+00:00'))
                        except Exception as e:
                            logger.warning(f"Could not parse end_time: {e}")
                    
                    new_event = EventModel(
                        event_id=event.id,
                        summary=event.summary,
                        description=event.description,
                        location=event.location,
                        calendar_id=event.calendar_id,
                        start_time=start_time,
                        end_time=end_time
                    )
                    db.add(new_event)
                    db.commit()
                    logger.debug(f"Created new event: {event.id}")
                count += 1
            except Exception as e:
                logger.error(f"Error storing event {getattr(event, 'id', 'unknown')}: {e}")
                db.rollback()
                continue
                
        db.close()
        logger.info(f"Successfully stored {count} events")
        return count
    except Exception as e:
        logger.error(f"Error storing events in database: {e}")
        return 0


def get_unclassified_events(limit: int = 100, include_past: bool = False) -> List[CalendarEvent]:
    """
    Get events that haven't been classified yet.
    
    Args:
        limit: Maximum number of events to return
        include_past: Whether to include past events
        
    Returns:
        List of unclassified events
    """
    db = get_db_session()
    try:
        query = db.query(EventModel).filter(EventModel.project_id.is_(None))
        
        # Filter out past events if requested
        if not include_past:
            now = datetime.now()
            query = query.filter(EventModel.start_time >= now)
            
        # Order by start time
        query = query.order_by(EventModel.start_time.asc())
        
        # Limit the number of results
        query = query.limit(limit)
        
        # Convert to Pydantic models
        events = []
        for event in query.all():
            events.append(event.to_pydantic())
            
        return events
    finally:
        db.close()


def get_classified_events(limit: int = 1000) -> List[CalendarEvent]:
    """
    Get events that have been classified, with their project info.
    
    Args:
        limit: Maximum number of events to return
        
    Returns:
        List of classified events
    """
    db = get_db_session()
    try:
        # Query events that have a project_id
        query = db.query(EventModel).filter(
            EventModel.project_id.isnot(None)
        ).order_by(EventModel.start_time.desc())
        
        # Limit the number of results
        query = query.limit(limit)
        
        # Convert to Pydantic models
        events = []
        for event in query.all():
            events.append(event.to_pydantic())
            
        return events
    finally:
        db.close()


def update_event_project(event_id: int, project_id: int) -> bool:
    """
    Update an event's project classification.
    
    Args:
        event_id: Database ID of the event (not the Google Calendar event ID)
        project_id: ID of the project to classify this event as
        
    Returns:
        True if successful, False otherwise
    """
    db = get_db_session()
    try:
        # Get the event by its database ID
        event = db.query(EventModel).filter(EventModel.id == event_id).first()
        if not event:
            logger.error(f"Event with ID {event_id} not found")
            return False
            
        # Update the project ID
        event.project_id = project_id
        db.commit()
        logger.info(f"Event {event.event_id} classified as project {project_id}")
        return True
    except Exception as e:
        logger.error(f"Error updating event project: {e}")
        db.rollback()
        return False
    finally:
        db.close()


# If run as a script, initialize the database
if __name__ == "__main__":
    init_db()
    
    # Add some sample projects if none exist
    db = get_db_session()
    project_count = db.query(ProjectModel).count()
    db.close()
    
    if project_count == 0:
        print("Adding sample projects...")
        add_project("Personal Development", 10, 2, "Skills development and learning")
        add_project("Work", None, 3, "Regular work")
        add_project("Family & Friends", None, 3, "Activities related to family, friends, or household")
        print("Sample projects added.")
        
    print("Done. You can now run the application with 'streamlit run app.py'.")