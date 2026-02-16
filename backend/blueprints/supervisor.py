from datetime import datetime, timedelta
from flask import Blueprint, render_template, request, redirect, url_for, abort, flash
from flask_login import login_required, current_user
from sqlalchemy import func
from db import db
from models import Ticket, User, TicketUpdate, STATUSES, PRIORITIES, SLA_HOURS

bp = Blueprint("supervisor", __name__)

def supervisor_only():
    return current_user.role == "supervisor"

@bp.route("/supervisor/inbox", methods=["GET"])
@login_required
def inbox():
    if not supervisor_only():
        abort(403)

    status = request.args.get("status")
    priority = request.args.get("priority")
    q = request.args.get("q")

    query = Ticket.query.filter(
        Ticket.maintenance_dept == current_user.maintenance_dept
    )

    if status:
        query = query.filter(Ticket.status == status)

    if priority:
        query = query.filter(Ticket.priority == priority)

    if q:
        if q.isdigit():
            query = query.filter(Ticket.ticket_no == int(q))
        else:
            query = query.filter(Ticket.title.ilike(f"%{q}%"))

    tickets = query.order_by(Ticket.created_at.desc()).all()

    technicians = User.query.filter_by(
        role="technician",
        maintenance_dept=current_user.maintenance_dept,
        is_active=True
    ).order_by(User.full_name.asc()).all()

    tech_map = {tech.id: tech.full_name for tech in technicians}

    # ✅ SLA compute (naive datetime same as sqlite)
    now = datetime.now()
    sla_map = {}
    for t in tickets:
        pri = (t.priority or "").lower()
        hours = SLA_HOURS.get(pri, 24)
        due_at = t.created_at + timedelta(hours=hours)
        overdue = (t.status != "closed") and (now > due_at)
        remaining_min = int((due_at - now).total_seconds() // 60)
        sla_map[t.id] = {
            "hours": hours,
            "due_at": due_at,
            "overdue": overdue,
            "remaining_min": remaining_min
        }

    return render_template(
        "supervisor_inbox.html",
        tickets=tickets,
        technicians=technicians,
        tech_map=tech_map,
        statuses=STATUSES,
        priorities=PRIORITIES,
        sla_map=sla_map
    )

@bp.post("/supervisor/assign/<int:ticket_id>")
@login_required
def assign(ticket_id):
    if not supervisor_only():
        abort(403)

    t = Ticket.query.get_or_404(ticket_id)
    if t.maintenance_dept != current_user.maintenance_dept:
        abort(403)

    tech_id = request.form.get("technician_id", type=int)
    tech = User.query.get_or_404(tech_id)

    t.assigned_technician_id = tech.id
    if t.status == "new":
        t.status = "processing"

    upd = TicketUpdate(
        ticket_id=t.id,
        action_type="assigned",
        note=f"Assigned to {tech.full_name}",
        created_by=current_user.id
    )
    db.session.add(upd)
    db.session.commit()

    flash("Technician assigned successfully", "success")
    return redirect(url_for("supervisor.inbox"))

@bp.post("/supervisor/status/<int:ticket_id>")
@login_required
def change_status(ticket_id):
    if not supervisor_only():
        abort(403)

    t = Ticket.query.get_or_404(ticket_id)
    if t.maintenance_dept != current_user.maintenance_dept:
        abort(403)

    new_status = request.form.get("status")
    if new_status not in STATUSES:
        flash("Invalid status", "danger")
        return redirect(url_for("supervisor.inbox"))

    old_status = t.status
    t.status = new_status

    upd = TicketUpdate(
        ticket_id=t.id,
        action_type="status_changed",
        note=f"{old_status} → {new_status}",
        old_value=old_status,
        new_value=new_status,
        created_by=current_user.id
    )
    db.session.add(upd)
    db.session.commit()

    flash("Status updated", "success")
    return redirect(url_for("supervisor.inbox"))

@bp.post("/supervisor/close/<int:ticket_id>")
@login_required
def close(ticket_id):
    if not supervisor_only():
        abort(403)

    t = Ticket.query.get_or_404(ticket_id)
    if t.maintenance_dept != current_user.maintenance_dept:
        abort(403)

    t.status = "closed"
    t.closed_by = current_user.id
    t.closed_at = func.now()

    upd = TicketUpdate(
        ticket_id=t.id,
        action_type="closed",
        note="Ticket closed",
        created_by=current_user.id
    )
    db.session.add(upd)
    db.session.commit()

    flash("Ticket closed successfully", "success")
    return redirect(url_for("supervisor.inbox"))
