# reset_password_sqlite_FAST.py
import os
import sqlite3
from werkzeug.security import generate_password_hash

# =======================
# عدّل هنا فقط
# =======================
TARGET_USERNAME = "admin"      # غيّرها حسب قائمة المستخدمين التي ستظهر لك
NEW_PASSWORD = "admin123"      # كلمة المرور الجديدة

def find_db_file():
    here = os.path.dirname(os.path.abspath(__file__))

    candidates = [
        os.path.join(here, "instance", "maintenance.db"),
        os.path.join(here, "maintenance.db"),
        os.path.join(here, "..", "instance", "maintenance.db"),
        os.path.join(here, "..", "maintenance.db"),
        os.path.join(here, "..", "..", "instance", "maintenance.db"),
        os.path.join(here, "..", "..", "maintenance.db"),
    ]

    # ابحث داخل المشروع (عمق بسيط)
    root = os.path.abspath(os.path.join(here, ".."))
    for dirpath, _, filenames in os.walk(root):
        if "maintenance.db" in filenames:
            candidates.insert(0, os.path.join(dirpath, "maintenance.db"))

    for p in candidates:
        p = os.path.abspath(p)
        if os.path.exists(p):
            return p
    return None

def main():
    db_path = find_db_file()
    if not db_path:
        print("[ERROR] لم أجد maintenance.db داخل المشروع.")
        return

    print("[OK] DB PATH USED:", db_path)

    # Backup
    try:
        bak = db_path + ".bak"
        if not os.path.exists(bak):
            with open(db_path, "rb") as fsrc, open(bak, "wb") as fdst:
                fdst.write(fsrc.read())
            print("[OK] Backup:", bak)
    except Exception as e:
        print("[WARN] Backup failed:", e)

    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    # تأكد من جدول user
    cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='user';")
    if not cur.fetchone():
        print("[ERROR] جدول user غير موجود. (قد يكون اسمه users)")
        cur.execute("SELECT name FROM sqlite_master WHERE type='table';")
        print("Tables:", [r[0] for r in cur.fetchall()])
        conn.close()
        return

    # اطبع قائمة المستخدمين
    cur.execute("SELECT id, username, full_name, role FROM user ORDER BY id;")
    rows = cur.fetchall()
    print("\n[INFO] USERS IN DB:")
    for r in rows:
        print(" -", r)

    # حدّث كلمة المرور
    new_hash = generate_password_hash(NEW_PASSWORD)
    cur.execute("UPDATE user SET password_hash=? WHERE username=?;", (new_hash, TARGET_USERNAME))
    conn.commit()

    if cur.rowcount == 0:
        print(f"\n[ERROR] لم أجد username='{TARGET_USERNAME}' داخل قاعدة البيانات.")
        print("=> غيّر TARGET_USERNAME لقيمة موجودة في القائمة أعلاه ثم أعد التشغيل.")
        conn.close()
        return

    print("\n[OK] Password updated successfully!")
    print("Username:", TARGET_USERNAME)
    print("Password:", NEW_PASSWORD)

    conn.close()

if __name__ == "__main__":
    main()
