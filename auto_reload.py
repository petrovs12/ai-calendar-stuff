#!/usr/bin/env python3
"""
Auto-reloader for Streamlit apps.
Monitors Python files in the directory and restarts the Streamlit app when changes are detected.
"""

import os
import sys
import time
import subprocess
import signal
import glob
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

# Configuration
WATCH_EXTENSIONS = ['.py']  # File extensions to watch
STREAMLIT_COMMAND = ["streamlit", "run", "app.py"]  # Command to run Streamlit app
POLL_INTERVAL = 1  # Seconds between checks

class ChangeHandler(FileSystemEventHandler):
    """Watches for file changes and triggers app reload."""
    
    def __init__(self, app_process):
        self.app_process = app_process
        self.last_modified = time.time()
        # Prevent reacting to the same change multiple times
        self.cooldown = 1  # seconds
        
    def on_modified(self, event):
        if event.is_directory:
            return
            
        # Check if the file has a watched extension
        if any(event.src_path.endswith(ext) for ext in WATCH_EXTENSIONS):
            current_time = time.time()
            if (current_time - self.last_modified) > self.cooldown:
                self.last_modified = current_time
                print(f"\n🔄 Change detected in {event.src_path}. Reloading...")
                self.restart_app()
    
    def restart_app(self):
        """Terminate current Streamlit process and start a new one."""
        if self.app_process and self.app_process.poll() is None:
            # Send SIGTERM to main process group
            os.killpg(os.getpgid(self.app_process.pid), signal.SIGTERM)
            # Give it a moment to shutdown gracefully
            time.sleep(1)
            
        # Start a new Streamlit process
        self.app_process = self._start_streamlit()
        return self.app_process
    
    def _start_streamlit(self):
        """Start the Streamlit app process."""
        print("🚀 Starting Streamlit app...")
        # Create a new process group so we can kill the app and all its children
        process = subprocess.Popen(
            STREAMLIT_COMMAND, 
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            universal_newlines=True,
            preexec_fn=os.setsid
        )
        return process

def main():
    """Main entry point for the auto-reloader."""
    print("🔍 Auto-reloader starting. Watching for file changes...")
    
    # Start Streamlit app initially
    app_process = subprocess.Popen(
        STREAMLIT_COMMAND,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        universal_newlines=True,
        preexec_fn=os.setsid
    )
    
    # Set up file watcher
    event_handler = ChangeHandler(app_process)
    observer = Observer()
    
    # Watch current directory recursively
    observer.schedule(event_handler, path='.', recursive=True)
    observer.start()
    
    try:
        while True:
            # Process Streamlit output
            if app_process.poll() is None:  # If process is still running
                output = app_process.stdout.readline()
                if output:
                    print(output, end='')
            time.sleep(POLL_INTERVAL)
    except KeyboardInterrupt:
        print("\n🛑 Auto-reloader shutting down...")
        if app_process and app_process.poll() is None:
            os.killpg(os.getpgid(app_process.pid), signal.SIGTERM)
        observer.stop()
    
    observer.join()

if __name__ == "__main__":
    main() 