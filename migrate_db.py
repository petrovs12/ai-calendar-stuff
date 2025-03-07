#!/usr/bin/env python3
"""
Database migration script to handle schema changes.
This script will:
1. First attempt to add missing columns to the events table
2. If that fails, delete the database and re-initialize it
"""

import os
import sqlite3
import logging
import database

# Configure logging
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

DB_PATH = "planner.db"

def migrate_database():
    """Attempt to migrate the database by adding missing columns."""
    if not os.path.exists(DB_PATH):
        logger.info(f"Database file {DB_PATH} doesn't exist. Nothing to migrate.")
        return False
    
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Check if event_id column exists
        cursor.execute("PRAGMA table_info(events)")
        columns = [column[1] for column in cursor.fetchall()]
        
        if "event_id" not in columns:
            logger.info("Adding event_id column to events table...")
            cursor.execute("ALTER TABLE events ADD COLUMN event_id TEXT UNIQUE")
        
        if "calendar_id" not in columns:
            logger.info("Adding calendar_id column to events table...")
            cursor.execute("ALTER TABLE events ADD COLUMN calendar_id TEXT")
        
        conn.commit()
        logger.info("Migration successful!")
        return True
    except Exception as e:
        logger.error(f"Migration failed: {e}")
        return False
    finally:
        if 'conn' in locals():
            conn.close()

def delete_and_reinitialize():
    """Delete the database file and re-initialize it."""
    try:
        if os.path.exists(DB_PATH):
            logger.info(f"Deleting database file {DB_PATH}...")
            os.remove(DB_PATH)
            logger.info(f"Database file deleted.")
        
        logger.info("Initializing new database...")
        database.init_db()
        logger.info("Database initialized with current schema.")
        return True
    except Exception as e:
        logger.error(f"Error during delete and re-initialize: {e}")
        return False

if __name__ == "__main__":
    logger.info("Starting database migration...")
    
    if migrate_database():
        logger.info("Migration completed successfully.")
    else:
        logger.info("Migration failed, proceeding with delete and re-initialize...")
        if delete_and_reinitialize():
            logger.info("Delete and re-initialize completed successfully.")
        else:
            logger.error("Database operations failed. Please check the errors above.") 