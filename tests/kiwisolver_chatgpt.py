import pandas as pd
import kiwisolver as kiwi

# ------------------------------------------------------------------------------
# EXAMPLE DATA
# ------------------------------------------------------------------------------
# DataFrame of "fixed" calendar events
fixed_events_data = [
    {"event": "Team Meeting", "start": 9.0, "end": 10.0, "project": "Project A"},
    {"event": "Client Call",  "start": 14.0, "end": 15.0, "project": "Project B"}
]
fixed_events_df = pd.DataFrame(fixed_events_data)

# DataFrame of projects with total hours needed in the week
projects_data = [
    {"project": "Project A", "priority": "high",   "total_hours_needed": 2.0, "deadline": "2025-03-15"},
    {"project": "Project B", "priority": "medium", "total_hours_needed": 2.0, "deadline": "2025-03-20"},
    {"project": "Project C", "priority": "low",    "total_hours_needed": 2.0, "deadline": "2025-03-30"},
]
projects_df = pd.DataFrame(projects_data)

# Create "focus blocks" of 1 hour each for these projects.
focus_blocks = []
for idx, row in projects_df.iterrows():
    project = row["project"]
    needed = int(row["total_hours_needed"])
    for i in range(needed):
        focus_blocks.append({
            "block_name": f"{project}_Block_{i+1}",
            "project": project,
            "priority": row["priority"]
        })
focus_blocks_df = pd.DataFrame(focus_blocks)
print(f"Input data for the focus blocks: {focus_blocks_df}")

# ------------------------------------------------------------------------------
# KIWI SOLVER SETUP
# ------------------------------------------------------------------------------
solver = kiwi.Solver()

# Dictionary to store Kiwi Variables for each block.
start_vars = {}

WORKDAY_START = 9.0
WORKDAY_END   = 21.0
BLOCK_DURATION = 1.0

# Create variables and basic time constraints for each block.
for _, row in focus_blocks_df.iterrows():
    block_name = row["block_name"]
    var = kiwi.Variable(block_name)
    
    # Required constraints: WORKDAY_START <= var <= WORKDAY_END - BLOCK_DURATION
    solver.addConstraint(var >= WORKDAY_START)
    solver.addConstraint(var <= WORKDAY_END - BLOCK_DURATION)
    
    # For high priority, we add an edit variable and suggest a value (soft constraint)
    if row["priority"] == "high":
        solver.addEditVariable(var, kiwi.strength.strong)
        solver.suggestValue(var, WORKDAY_START)
    
    start_vars[block_name] = var

# Impose ordering: each block (sorted by name) starts at least 1 hour after the previous one ends.
sorted_block_names = sorted(start_vars.keys())
for i in range(len(sorted_block_names) - 1):
    current_block = sorted_block_names[i]
    next_block    = sorted_block_names[i+1]
    solver.addConstraint(start_vars[next_block] - start_vars[current_block] >= BLOCK_DURATION)

# Avoid overlap with fixed events:
# Push all new blocks to start after the last fixed event's end.
latest_end_of_fixed = max(fixed_events_df["end"])
for var in start_vars.values():
    solver.addConstraint(var >= latest_end_of_fixed)

# ------------------------------------------------------------------------------
# SOLVE & PRINT RESULTS
# ------------------------------------------------------------------------------
solver.updateVariables()

# Collect the schedule (start/end) for each block.
schedule_rows = []
for _, row in focus_blocks_df.iterrows():
    block_name = row["block_name"]
    project    = row["project"]
    priority   = row["priority"]
    start_time = start_vars[block_name].value()
    end_time   = start_time + BLOCK_DURATION
    
    schedule_rows.append({
        "block_name": block_name,
        "project": project,
        "priority": priority,
        "start": round(start_time, 2),
        "end": round(end_time, 2)
    })

schedule_df = pd.DataFrame(schedule_rows)

print("\n--- Optimized Focus Blocks ---")
print(schedule_df)

print("\n--- Fixed Calendar Events ---")
print(fixed_events_df)