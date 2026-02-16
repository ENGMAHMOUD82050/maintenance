from app import create_app
from db import db
from models import User

DEFAULT_ADMIN_USER = "admin"
DEFAULT_ADMIN_PASSWORD = "admin123"

def main():
    app = create_app()
    with app.app_context():
        admin = User.query.filter_by(username=DEFAULT_ADMIN_USER).first()

        if not admin:
            admin = User(
                username=DEFAULT_ADMIN_USER,
                full_name="System Admin",
                role="admin",
                maintenance_dept=None,
                is_active=True
            )
            admin.set_password(DEFAULT_ADMIN_PASSWORD)
            db.session.add(admin)
            db.session.commit()
            print(f"[OK] Admin created: {DEFAULT_ADMIN_USER} / {DEFAULT_ADMIN_PASSWORD}")
        else:
            print("[OK] Admin exists (password unchanged)")

if __name__ == "__main__":
    main()
