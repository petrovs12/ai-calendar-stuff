from datetime import datetime, timedelta, timezone

def schedule_practice(events, duration_minutes=60, days_ahead=14):
    """
    Simple heuristic-based scheduling for interview practice sessions.
    Finds one free slot per day (up to 'days_ahead' days from now) for a session.
    
    :param events: List of Google Calendar events (each a dict with 'start' and 'end' times).
    :param duration_minutes: Length of each practice session in minutes.
    :param days_ahead: How many days ahead to look for free slots.
    :return: List of (start_datetime, end_datetime) tuples for scheduled practice sessions.
    """
    # Convert Google events into a list of (start_datetime, end_datetime)
    busy_times = {}  # dict with date as key and list of (start, end) datetimes as value
    for event in events:
        start_str = event['start'].get('dateTime', event['start'].get('date'))
        end_str = event['end'].get('dateTime', event['end'].get('date'))
        if not start_str or not end_str:
            continue  # skip if no start or end (shouldn't happen in normal cases)
        # Parse date/time strings into datetime objects
        # Handle all-day events (date without time) and adjust end for all-day.
        if len(start_str) == 10:  # format 'YYYY-MM-DD', an all-day event
            # Treat all-day events as busy for the whole day
            start_dt = datetime.fromisoformat(start_str)  # at midnight
            end_dt = start_dt + timedelta(days=1)         # next midnight
        else:
            # Replace 'Z' with '+00:00' for UTC times, for datetime parsing
            if start_str.endswith('Z'):
                start_str = start_str.replace('Z', '+00:00')
            if end_str.endswith('Z'):
                end_str = end_str.replace('Z', '+00:00')
            start_dt = datetime.fromisoformat(start_str)
            end_dt = datetime.fromisoformat(end_str)
        # Only consider events within the next 'days_ahead' days
        # Ensure we're comparing timezone-aware datetimes by making now timezone-aware
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        if start_dt.tzinfo is not None:
            # If start_dt has a timezone, make it timezone-naive for consistent comparison
            start_dt = start_dt.replace(tzinfo=None)
        if end_dt.tzinfo is not None:
            # If end_dt has a timezone, make it timezone-naive for consistent comparison
            end_dt = end_dt.replace(tzinfo=None)
            
        if start_dt.date() > now.date() + timedelta(days=days_ahead):
            continue
        day = start_dt.date()
        busy_times.setdefault(day, []).append((start_dt, end_dt))
    # Sort busy intervals for each day
    for day in busy_times:
        busy_times[day].sort(key=lambda x: x[0])
    # Define workday hours for scheduling (could be adjusted or made configurable)
    work_start = timedelta(hours=9)   # 9:00 AM
    work_end   = timedelta(hours=17)  # 5:00 PM
    session_dur = timedelta(minutes=duration_minutes)
    suggestions = []
    today = datetime.now().date()
    for i in range(days_ahead + 1):  # include today + days_ahead
        day = today + timedelta(days=i)
        # Skip if it's a weekend (optional heuristic, can be removed if weekend practice is okay)
        # if day.weekday() >= 5: 
        #     continue
        day_start = datetime.combine(day, datetime.min.time()) + work_start
        day_end = datetime.combine(day, datetime.min.time()) + work_end
        if day not in busy_times:
            # No events this day, schedule at day_start
            if day_start + session_dur <= day_end:
                suggestions.append((day_start, day_start + session_dur))
        else:
            # There are events; find a gap before, between, or after events
            current_time = day_start
            for (ev_start, ev_end) in busy_times[day]:
                # If there's free time between current_time and the next event start
                if ev_start > current_time and (ev_start - current_time) >= session_dur:
                    # Schedule a session starting at current_time
                    suggestions.append((current_time, current_time + session_dur))
                    break  # only one session per day
                # Move the pointer past this event if it overlaps or touches current_time
                if ev_end > current_time:
                    current_time = ev_end
            else:
                # After checking all events, if there's space at end of day
                if current_time + session_dur <= day_end:
                    suggestions.append((current_time, current_time + session_dur))
        # Stop if we've collected enough suggestions (one per day up to days_ahead)
    return suggestions