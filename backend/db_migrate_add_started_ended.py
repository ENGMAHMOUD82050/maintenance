import os
import sqlite3

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "maintenance.db")

def column_exists(cur, table, col):
    cur.execute(f"PRAGMA table_info({table})")
    cols = [r[1] for r in cur.fetchall()]
    return col in cols

def main():
    if not os.path.exists(DB_PATH):
        print("DB not found:", DB_PATH)
        return

    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()

    # Ensure table exists
    cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='ticket'")
    if not cur.fetchone():
        print("Table 'ticket' not found.")
        con.close()
        return

    changes = 0

    if not column_exists(cur, "ticket", "started_at"):
        cur.execute("ALTER TABLE ticket ADD COLUMN started_at DATETIME")
        changes += 1
        print("Added column: started_at")

    if not column_exists(cur, "ticket", "ended_at"):
        cur.execute("ALTER TABLE ticket ADD COLUMN ended_at DATETIME")
        changes += 1
        print("Added column: ended_at")

    con.commit()
    con.close()

    if changes == 0:
        print("No changes needed. Columns already exist.")
    else:
        print("Migration done successfully.")

if __name__ == "__main__":
    main()
