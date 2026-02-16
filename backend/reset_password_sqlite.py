# reset_password_sqlite.py
import os
import sqlite3
from werkzeug.security import generate_password_hash

# =======================
# عدّل هنا فقط
# =======================
TARGET_USERNAME = "admin"
NEW_PASSWORD = "admin123"

# =======================
# يحاول إيجاد maintenance.db تلقائياً
# =======================
def find_db_file():
    here = os.path.dirname(os.path.abspath(__file__))

    # أماكن شائعة
    candidates = [
        os.path.join(here, "maintenance.db"),
        os.path.join(here, "..", "maintenance.db"),
        os.path.join(here, "..", "..", "maintenance.db"),
        os.path.join(here, "instance", "maintenance.db"),
        os.path.join(here, "..", "instance", "maintenance.db"),
    ]

    # ابحث داخل المشروع (عمق محدود)
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
        print("[ERROR] لم أجد maintenance.db تلقائياً.")
        print("ضع maintenance.db بجانب هذا الملف أو داخل backend/instance/")
        return

    print("[OK] DB Found:", db_path)

    # Backup سريع
    backup_path = db_path + ".bak"
    if not os.path.exists(backup_path):
        try:
            with open(db_path, "rb") as fsrc, open(backup_path, "wb") as fdst:
                fdst.write(fsrc.read())
            print("[OK] Backup created:", backup_path)
        except Exception as e:
            print("[WARN] Backup failed:", e)

    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    # تأكد من وجود جدول user
    cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='user';")
    if not cur.fetchone():
        print("[ERROR] جدول user غير موجود في هذه القاعدة.")
        print("قد يكون اسم الجدول users أو شيء آخر.")
        # عرض الجداول للمساعدة
        cur.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = [r[0] for r in cur.fetchall()]
        print("Tables:", tables)
        conn.close()
        return

    # اعرض المستخدمين (للتأكد)
    try:
        cur.execute("SELECT username FROM user;")
        users = [r[0] for r in cur.fetchall()]
        print("[INFO] Users:", users)
    except Exception as e:
        print("[WARN] Can't list users:", e)

    # اعمل hash صحيح
    new_hash = generate_password_hash(NEW_PASSWORD)

    # حدّث كلمة المرور
    cur.execute("UPDATE user SET password_hash=? WHERE username=?;", (new_hash, TARGET_USERNAME))
    conn.commit()

    if cur.rowcount == 0:
        print(f"[ERROR] لم أجد المستخدم '{TARGET_USERNAME}' داخل جدول user.")
        conn.close()
        return

    print("[OK] Password updated successfully!")
    print("Username:", TARGET_USERNAME)
    print("Password:", NEW_PASSWORD)

    conn.close()


if __name__ == "__main__":
    main()
