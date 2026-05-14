import sqlite3

conn = sqlite3.connect('orcanos_performance.db')
print("=== Recent Test Runs ===")
runs = conn.execute('SELECT id, status, started_at, completed_at FROM test_runs ORDER BY id DESC LIMIT 5').fetchall()
for row in runs:
    print(f"Run {row[0]}: status={row[1]}, started={row[2]}, completed={row[3]}")

print("\n=== Recent Step Results ===")
steps = conn.execute('SELECT run_id, step_name, status, duration_seconds FROM step_results ORDER BY id DESC LIMIT 10').fetchall()
for row in steps:
    print(f"Run {row[0]}: {row[1]} - {row[2]} ({row[3]}s)")

conn.close()
