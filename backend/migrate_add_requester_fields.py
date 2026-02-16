import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent / "maintenance.db"

def column_exists(conn, table: str, col: str) -> bool:
    cur = conn.execute(f"PRAGMA table_info({table})")
    cols = [r[1] for r in cur.fetchall()]  # r[1] = column name
    return col in cols

def main():
    if not DB_PATH.exists():
        print(f"[ERROR] DB not found: {DB_PATH}")
        print("Start the server once to create DB, then run migration again.")
        return

    conn = sqlite3.connect(str(DB_PATH))
    try:
        # Ticket table name in SQLAlchemy default is "ticket"
        table = "ticket"

        # Add requester_name (NOT NULL) safely:
        # SQLite cannot add NOT NULL without default, so we add it with DEFAULT '' first,
        # then you can keep it as required at app-level.
        if not column_exists(conn, table, "requester_name"):
            print("[ADD] requester_name")
            conn.execute("ALTER TABLE ticket ADD COLUMN requester_name VARCHAR(120) NOT NULL DEFAULT ''")

        # Add requester_extension (nullable)
        if not column_exists(conn, table, "requester_extension"):
            print("[ADD] requester_extension")
            conn.execute("ALTER TABLE ticket ADD COLUMN requester_extension VARCHAR(20)")

        conn.commit()
        print("[OK] Migration completed successfully.")
        print("Now restart server and create a new ticket.")
    finally:
        conn.close()

if __name__ == "__main__":
    main()
