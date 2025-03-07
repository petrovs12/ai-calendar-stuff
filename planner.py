import sqlite3

conn = sqlite3.connect("planner.db")
cursor = conn.cursor()

# List all tables
cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
tables = cursor.fetchall()
print("Tables in the database:", tables)

# For each table, show its structure
for table in tables:
    table_name = table[0]
    cursor.execute(f"PRAGMA table_info({table_name})")
    columns = cursor.fetchall()
    print(f"\nStructure of table '{table_name}':")
    for column in columns:
        print(column)

conn.close()