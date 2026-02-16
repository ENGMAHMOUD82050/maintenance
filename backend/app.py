import os
import sys
import sqlite3
from datetime import datetime

from flask import Flask, redirect, url_for, render_template
from flask_login import LoginManager, login_required

from db import db
from models import User, Ticket, Building, Floor, HospitalSection, Room

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)


def _import_bp(module_path: str):
    try:
        m = __import__(module_path, fromlist=["bp"])
        return getattr(m, "bp", None), None
    except Exception as e:
        return None, e


def _import_tr():
    try:
        m = __import__("i18n", fromlist=["t"])
        return getattr(m, "t", lambda x: x)
    except Exception:
        return lambda x: x


def _import_to_ar():
    try:
        m = __import__("translator", fromlist=["to_ar"])
        return getattr(m, "to_ar", lambda x: x)
    except Exception:
        return lambda x: x


_AR_MAP = {
    "basement": "القبو",
    "ground": "الأرضي",
    "ground floor": "الأرضي",
    "first floor": "الطابق الأول",
    "second floor": "الطابق الثاني",
    "third floor": "الطابق الثالث",
    "fourth floor": "الطابق الرابع",
}

tr = _import_tr()
_to_ar_core = _import_to_ar()


def to_ar(text):
    if text is None:
        return ""
    s = str(text).strip()
    if not s:
        return ""
    low = s.lower().strip()
    if low in _AR_MAP:
        return _AR_MAP[low]
    try:
        out = _to_ar_core(s)
        if out == s:
            parts = s.split()
            fixed = []
            for p in parts:
                k = p.strip(" ,./\\-_:;()[]{}").lower()
                fixed.append(_AR_MAP.get(k, p))
            return " ".join(fixed)
        return out
    except Exception:
        return s


def _sqlite_has_column(conn: sqlite3.Connection, table: str, col: str) -> bool:
    cur = conn.execute(f"PRAGMA table_info({table})")
    rows = cur.fetchall()
    return any(r[1] == col for r in rows)


def _sqlite_add_column(conn: sqlite3.Connection, table: str, col: str, coltype: str):
    conn.execute(f"ALTER TABLE {table} ADD COLUMN {col} {coltype}")


def _ensure_sqlite_columns(db_file: str):
    if not db_file or not os.path.exists(db_file):
        return

    conn = sqlite3.connect(db_file)
    try:
        # ticket table columns we rely on in dashboard/KPI
        needed = [
            ("assigned_at", "DATETIME"),
            ("first_response_at", "DATETIME"),
            ("last_status_at", "DATETIME"),
            ("spares_requested_at", "DATETIME"),
            ("started_at", "DATETIME"),
            ("ended_at", "DATETIME"),
            ("closed_at", "DATETIME"),
            ("closed_by", "INTEGER"),
            ("error_name", "VARCHAR(200)"),
            ("requester_extension", "VARCHAR(50)"),
        ]

        # If table doesn't exist yet, skip (create_all will handle)
        cur = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='ticket'")
        if not cur.fetchone():
            return

        for col, coltype in needed:
            if not _sqlite_has_column(conn, "ticket", col):
                _sqlite_add_column(conn, "ticket", col, coltype)

        conn.commit()
    finally:
        conn.close()


def create_app():
    app = Flask(__name__)
    app.secret_key = os.environ.get("SECRET_KEY", "dev-secret-key")

    # ✅ ثابت: لو عايز كل النسخ تشوف نفس DB
    # مثال (ويندوز):
    # setx MAINT_DB_PATH "G:\Other computers\My Computer\Google Drive\maintenance_system\backend\maintenance.db"
    db_path = os.environ.get("MAINT_DB_PATH", "").strip()

    if not db_path:
        db_path = os.path.join(BASE_DIR, "maintenance.db")

    # ensure folder exists
    os.makedirs(os.path.dirname(db_path), exist_ok=True)

    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///" + db_path.replace("\\", "/")
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    try:
        print("========================================")
        print("[DB] Using:", app.config["SQLALCHEMY_DATABASE_URI"])
        print("========================================")
    except Exception:
        pass

    db.init_app(app)

    login_manager = LoginManager()
    login_manager.init_app(app)

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    @app.context_processor
    def inject_globals():
        return dict(tr=tr, to_ar=to_ar, zip=zip)

    # blueprints
    auth_bp, e1 = _import_bp("auth")
    if not auth_bp:
        auth_bp, e1 = _import_bp("blueprints.auth")

    users_bp, e2 = _import_bp("users")
    if not users_bp:
        users_bp, e2 = _import_bp("blueprints.users")

    tickets_bp, e3 = _import_bp("tickets")
    if not tickets_bp:
        tickets_bp, e3 = _import_bp("blueprints.tickets")

    kpi_bp, e4 = _import_bp("kpi")
    if not kpi_bp:
        kpi_bp, e4 = _import_bp("blueprints.kpi")

    dashboard_bp, e5 = _import_bp("dashboard")
    if not dashboard_bp:
        dashboard_bp, e5 = _import_bp("blueprints.dashboard")

    if auth_bp:
        app.register_blueprint(auth_bp)
        print("[OK] Imported blueprint: auth")
        login_manager.login_view = "auth.login"
    else:
        print("[ERROR] auth blueprint not found:", e1)
        login_manager.login_view = None

    if users_bp:
        app.register_blueprint(users_bp)
        print("[OK] Imported blueprint: users")
    else:
        print("[WARN] users blueprint not found:", e2)

    if tickets_bp:
        app.register_blueprint(tickets_bp)
        print("[OK] Imported blueprint: tickets")
    else:
        print("[WARN] tickets blueprint not found:", e3)

    if kpi_bp:
        app.register_blueprint(kpi_bp)
        print("[OK] Imported blueprint: kpi")
    else:
        print("[WARN] kpi blueprint not found:", e4)

    if dashboard_bp:
        app.register_blueprint(dashboard_bp)
        print("[OK] Imported blueprint: dashboard")
    else:
        print("[WARN] dashboard blueprint not found:", e5)

    printing_html_bp, ep1 = _import_bp("blueprints.printing_html")
    if printing_html_bp:
        app.register_blueprint(printing_html_bp)
        print("[OK] Imported blueprint: printing_html")
    else:
        print("[WARN] printing_html not loaded:", ep1)

    printing_pdf_bp, ep2 = _import_bp("blueprints.printing_pdf")
    if printing_pdf_bp:
        app.register_blueprint(printing_pdf_bp)
        print("[OK] Imported blueprint: printing_pdf")
    else:
        print("[SKIP] printing_pdf disabled:", ep2)

    @app.get("/")
    def home():
        try:
            return redirect(url_for("dashboard.dashboard"))
        except Exception:
            return redirect("/dashboard")

    # ✅ Create tables then ensure missing columns (SQLite)
    with app.app_context():
        db.create_all()
        # extract sqlite file from uri
        sqlite_file = db_path
        _ensure_sqlite_columns(sqlite_file)

    # PRINTING FALLBACK
    def _render_print(ticket_id: int):
        t = Ticket.query.get_or_404(ticket_id)

        building = Building.query.get(t.building_id)
        floor = Floor.query.get(t.floor_id)
        section = HospitalSection.query.get(t.section_id)
        room = Room.query.get(t.room_id)

        now = datetime.now()
        now_time = now.strftime("%I:%M %p")
        now_date = now.strftime("%d/%m/%Y")

        return render_template(
            "print_work_order.html",
            t=t,
            building=building,
            floor=floor,
            section=section,
            room=room,
            now_time=now_time,
            now_date=now_date,
            to_ar=to_ar,
            tr=tr,
        )

    @app.get("/print/<int:ticket_id>")
    @login_required
    def print_alias(ticket_id: int):
        return _render_print(ticket_id)

    @app.get("/print/work-order/<int:ticket_id>")
    @login_required
    def print_work_order(ticket_id: int):
        return _render_print(ticket_id)

    return app


if __name__ == "__main__":
    app = create_app()
    print("==========================================")
    print("[OK] Starting server...")
    print("Open: http://127.0.0.1:5000")
    print("==========================================")
    app.run(host="0.0.0.0", port=5000, debug=False)
