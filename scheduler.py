"""
Scheduler module for planning interview practice sessions based on calendar events.
"""
from datetime import datetime, timedelta, timezone
from typing import List, Tuple, Dict, Any, Optional

# Other imports if needed
try:
    from models import CalendarEvent, TimeOfDay
except ImportError:
    # For backward compatibility
    CalendarEvent = None
    TimeOfDay = None

def schedule_practice(events, duration_minutes=60, days_ahead=14):
    """
    Schedule practice sessions based on available time slots.
    
    Args:
        events: List of events (can be dictionaries or CalendarEvent objects)
        duration_minutes: Duration of practice sessions in minutes
        days_ahead: Number of days ahead to schedule
        
    Returns:
        List of (start_time, end_time) tuples for suggested practice sessions
    """
    # Constants
    PRACTICE_DURATION = timedelta(minutes=duration_minutes)
    START_HOUR = 9  # 9 AM
    END_HOUR = 22   # 10 PM
    
    # Create a set of busy times from the events
    busy_times = []
    
    for event in events:
        # Handle both dictionary and Pydantic model formats
        if isinstance(event, dict):
            # Event is a dictionary from Google Calendar API
            start_str = event.get('start', {}).get('dateTime')
            end_str = event.get('end', {}).get('dateTime')
            
            if start_str and end_str:
                # Convert to datetime objects
                try:
                    # Handle 'Z' timezone marker
                    if 'Z' in start_str:
                        start_str = start_str.replace('Z', '+00:00')
                    if 'Z' in end_str:
                        end_str = end_str.replace('Z', '+00:00')
                        
                    start_time = datetime.fromisoformat(start_str)
                    end_time = datetime.fromisoformat(end_str)
                    
                    # Convert to naive datetime if timezone-aware
                    if start_time.tzinfo is not None:
                        start_time = start_time.replace(tzinfo=None)
                    if end_time.tzinfo is not None:
                        end_time = end_time.replace(tzinfo=None)
                        
                    busy_times.append((start_time, end_time))
                except Exception as e:
                    print(f"Error parsing event times: {e}")
        else:
            # Event is a CalendarEvent Pydantic model
            start_dt = getattr(event, 'start_dt', None)
            end_dt = getattr(event, 'end_dt', None)
            
            if start_dt and end_dt:
                # Convert to naive datetime if timezone-aware
                if start_dt.tzinfo is not None:
                    start_dt = start_dt.replace(tzinfo=None)
                if end_dt.tzinfo is not None:
                    end_dt = end_dt.replace(tzinfo=None)
                    
                busy_times.append((start_dt, end_dt))
    
    # Sort busy times by start time
    busy_times.sort()
    
    # Define the range to check for available slots
    now = datetime.now().replace(tzinfo=None)  # Ensure now is naive
    end_date = now + timedelta(days=days_ahead)
    
    # Generate potential practice slots
    available_slots = []
    current_date = now.replace(hour=START_HOUR, minute=0, second=0, microsecond=0)
    
    # If we've already passed START_HOUR for today, start from tomorrow
    if now.hour >= START_HOUR:
        current_date += timedelta(days=1)
    
    while current_date < end_date:
        day_end = current_date.replace(hour=END_HOUR, minute=0, second=0, microsecond=0)
        slot_start = current_date
        
        # Check each potential slot against busy times
        while slot_start + PRACTICE_DURATION <= day_end:
            slot_end = slot_start + PRACTICE_DURATION
            
            # Check if slot overlaps with any busy time
            is_available = True
            for busy_start, busy_end in busy_times:
                # Check for overlap
                if (slot_start < busy_end and slot_end > busy_start):
                    is_available = False
                    # Move to the end of this busy period
                    slot_start = busy_end
                    break
            
            if is_available:
                available_slots.append((slot_start, slot_end))
                slot_start += PRACTICE_DURATION
            else:
                # If not available, slot_start has already been updated
                # to the end of the overlapping busy period
                pass
        
        # Move to the next day
        current_date = current_date + timedelta(days=1)
    
    return available_slots