# backend/reset_password.py
from app import create_app
from models import db, User

# =========================
# EDIT THESE TWO VALUES
# =========================
TARGET_USERNAME = "admin"
NEW_PASSWORD = "admin123"   # ضع كلمة المرور الجديدة هنا

def main():
    app = create_app()
    with app.app_context():
        u = User.query.filter_by(username=TARGET_USERNAME).first()
        if not u:
            print(f"[ERROR] user '{TARGET_USERNAME}' not found in database.")
            return

        # ✅ hash password correctly using your model helper
        u.set_password(NEW_PASSWORD)
        db.session.commit()

        print("[OK] Password reset done.")
        print(f"Username: {TARGET_USERNAME}")
        print(f"New Password: {NEW_PASSWORD}")

if __name__ == "__main__":
    main()
