import streamlit as st
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Local module imports
import google_calendar
import scheduler

# Streamlit app layout
st.title("Interview Practice Scheduler")
st.write("Welcome! This app fetches your Google Calendar events and schedules interview practice sessions around them.")

# Button to trigger schedule generation
if st.button("Generate Schedule"):
    with st.spinner("Contacting Google Calendar and generating schedule..."):
        try:
            service = google_calendar.get_calendar_service()
        except Exception as e:
            st.error(f"Authentication failed: {e}")
        else:
            # Fetch upcoming events (e.g., next 2 weeks)
            events = google_calendar.fetch_events(service, max_results=100)
            # Compute schedule suggestions
            suggestions = scheduler.schedule_practice(events, duration_minutes=60, days_ahead=14)
            if suggestions:
                st.subheader("Suggested Practice Sessions")
                for start, end in suggestions:
                    st.write(f"- **{start.strftime('%a, %b %d %Y %I:%M %p')}** to **{end.strftime('%I:%M %p')}**")
            else:
                st.info("No free slots available for practice in the next two weeks. You might be fully booked!")