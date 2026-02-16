from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin
from db import db

MAINT_DEPTS = ["mechanical", "civil", "hvac", "electronics", "electrical"]
ROLES = ["admin", "supervisor", "technician", "requester"]
PRIORITIES = ["low", "medium", "high", "emergency"]
STATUSES = [
    "new",
    "processing",
    "waiting",
    "Needs Spare Parts",
    "executed",
    "cancelled",
    "closed",
]

class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    full_name = db.Column(db.String(200), nullable=False)
    emp_no = db.Column(db.String(50), nullable=True)
    role = db.Column(db.String(20), nullable=False)  # admin/supervisor/technician/requester
    maintenance_dept = db.Column(db.String(20), nullable=True)  # hvac/civil/..
    password_hash = db.Column(db.String(255), nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def set_password(self, pw: str):
        self.password_hash = generate_password_hash(pw)

    def check_password(self, pw: str) -> bool:
        return check_password_hash(self.password_hash, pw)

class Building(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), unique=True, nullable=False)

class Floor(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    building_id = db.Column(db.Integer, db.ForeignKey("building.id"), nullable=False)
    name = db.Column(db.String(120), nullable=False)

class HospitalSection(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    building_id = db.Column(db.Integer, db.ForeignKey("building.id"), nullable=False)
    floor_id = db.Column(db.Integer, db.ForeignKey("floor.id"), nullable=False)
    name = db.Column(db.String(200), nullable=False)

class Room(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    building_id = db.Column(db.Integer, db.ForeignKey("building.id"), nullable=False)
    floor_id = db.Column(db.Integer, db.ForeignKey("floor.id"), nullable=False)
    section_id = db.Column(db.Integer, db.ForeignKey("hospital_section.id"), nullable=False)
    name = db.Column(db.String(120), nullable=False)

class Ticket(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    ticket_no = db.Column(db.Integer, unique=True, index=True, nullable=False)

    requester_user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)

    requester_name = db.Column(db.String(200), nullable=False)
    requester_extension = db.Column(db.String(50), nullable=True)

    building_id = db.Column(db.Integer, db.ForeignKey("building.id"), nullable=False)
    floor_id = db.Column(db.Integer, db.ForeignKey("floor.id"), nullable=False)
    section_id = db.Column(db.Integer, db.ForeignKey("hospital_section.id"), nullable=False)
    room_id = db.Column(db.Integer, db.ForeignKey("room.id"), nullable=False)

    maintenance_dept = db.Column(db.String(20), nullable=False)
    priority = db.Column(db.String(20), nullable=False)
    error_name = db.Column(db.String(200), nullable=True)

    title = db.Column(db.String(300), nullable=False)
    description = db.Column(db.Text, nullable=False)

    # ✅ طول أكبر لأن "Needs Spare Parts" أطول من 20
    status = db.Column(db.String(50), default="new", nullable=False)

    assigned_technician_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=True)

    # Phase timestamps
    assigned_at = db.Column(db.DateTime, nullable=True)
    first_response_at = db.Column(db.DateTime, nullable=True)
    last_status_at = db.Column(db.DateTime, nullable=True)
    spares_requested_at = db.Column(db.DateTime, nullable=True)

    # ✅ مهمين للداشبورد والـ KPI
    started_at = db.Column(db.DateTime, nullable=True)
    ended_at = db.Column(db.DateTime, nullable=True)

    closed_by = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=True)
    closed_at = db.Column(db.DateTime, nullable=True)

    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class TicketUpdate(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    ticket_id = db.Column(db.Integer, db.ForeignKey("ticket.id"), nullable=False)
    action_type = db.Column(db.String(50), nullable=False)  # created/status_changed/assigned/closed/comment
    note = db.Column(db.Text, nullable=True)
    old_value = db.Column(db.String(200), nullable=True)
    new_value = db.Column(db.String(200), nullable=True)
    created_by = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

# SLA hours per priority
SLA_HOURS = {
    "emergency": 6,
    "high": 16,
    "medium": 24,
    "low": 48,
}
