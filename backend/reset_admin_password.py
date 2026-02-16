from app import create_app
from db import db
from models import User

NEW_PASSWORD = "Admin@123"

def main():
    app = create_app()
    with app.app_context():
        u = User.query.filter_by(username="admin").first()
        if not u:
            u = User(
                username="admin",
                full_name="System Admin",
                role="admin",
                maintenance_dept=None,
            )
            # لو عندك emp_no
            if hasattr(u, "emp_no"):
                u.emp_no = "ADMIN"

            db.session.add(u)
            db.session.flush()

        # تأكيد تفعيل الحساب إن كان موجود
        if hasattr(u, "is_active"):
            u.is_active = True

        u.set_password(NEW_PASSWORD)
        db.session.commit()

        print(f"[OK] Admin password reset to: {NEW_PASSWORD}")

if __name__ == "__main__":
    main()
