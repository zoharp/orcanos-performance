import sqlite3, sys

conn = sqlite3.connect(r'C:\AI Projects\orcanos-performance\orcanos_performance.db')
cur = conn.cursor()

cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = [r[0] for r in cur.fetchall()]
print("Tables:", tables, file=sys.stderr)

statements = []

for table in tables:
    cur.execute(f"SELECT * FROM {table}")
    rows = cur.fetchall()
    if not rows:
        continue
    cur.execute(f"PRAGMA table_info({table})")
    cols = [r[1] for r in cur.fetchall()]
    print(f"{table}: {len(rows)} rows", file=sys.stderr)
    for row in rows:
        vals = []
        for v in row:
            if v is None:
                vals.append("NULL")
            elif isinstance(v, (int, float)):
                vals.append(str(v))
            else:
                vals.append("'" + str(v).replace("'", "''") + "'")
        col_list = ", ".join(cols)
        val_list = ", ".join(vals)
        statements.append(f"INSERT OR REPLACE INTO {table} ({col_list}) VALUES ({val_list});")

print("\n".join(statements))
conn.close()
