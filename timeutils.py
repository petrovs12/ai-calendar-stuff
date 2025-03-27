from datetime import datetime
from enum import Enum
import json

class TimeOfDay(str, Enum):
    """Time of day categorization."""
    MORNING = "morning"
    AFTERNOON = "afternoon"
    EVENING = "evening"
    UNKNOWN = "unknown"


def get_time_of_day(dt: datetime) -> TimeOfDay:
    """
    Get time of day category based on hour.
    
    Args:
        dt: Datetime object
        
    Returns:
        TimeOfDay enum value
    """
    if not dt:
        return TimeOfDay.UNKNOWN
        
    hour = dt.hour
    if 5 <= hour < 12:
        return TimeOfDay.MORNING
    elif 12 <= hour < 17:
        return TimeOfDay.AFTERNOON
    else:
        return TimeOfDay.EVENING


# Custom JSON encoder for datetime objects
class DateTimeEncoder(json.JSONEncoder):
    """JSON encoder that handles datetime objects."""
    def default(self, obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        return super().default(obj)



