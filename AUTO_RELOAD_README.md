# Streamlit Auto-Reloader

This utility automatically reloads your Streamlit app when Python files in the directory are modified.

## Usage

1. Make sure you have all the required packages installed:
   ```
   pip install -r requirements.txt
   ```

2. Run the auto-reloader script instead of running Streamlit directly:
   ```
   python auto_reload.py
   ```

3. Make changes to any Python file in your project, and the Streamlit app will automatically reload.

## How It Works

The script uses the `watchdog` library to monitor file changes in the current directory and its subdirectories. When a Python file is modified, it:

1. Terminates the current Streamlit process
2. Starts a new Streamlit process with your app.py
3. Displays the Streamlit output in the terminal

## Configuration

You can modify the following variables in `auto_reload.py` to customize the behavior:

- `WATCH_EXTENSIONS`: List of file extensions to monitor (default: ['.py'])
- `STREAMLIT_COMMAND`: Command to run your Streamlit app (default: ["streamlit", "run", "app.py"])
- `POLL_INTERVAL`: Time between checks in seconds (default: 1)

## Stopping the Auto-Reloader

Press Ctrl+C in the terminal to stop both the auto-reloader and the Streamlit app. 