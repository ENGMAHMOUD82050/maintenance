from datetime import datetime
from flask import Blueprint, render_template, request, redirect, url_for, jsonify, flash
from flask_login import login_required, current_user
from sqlalchemy import func

from db import db
from models import (
    Building, Floor, HospitalSection, Room,
    Ticket, TicketUpdate, MAINT_DEPTS, PRIORITIES, STATUSES
)

bp = Blueprint("tickets", __name__)

# -------------------------
# Small JSON APIs for cascading dropdowns
# -------------------------
@bp.get("/api/locations/buildings")
@login_required
def api_buildings():
    rows = Building.query.order_by(Building.name.asc()).all()
    return jsonify([{"id": b.id, "name": b.name} for b in rows])

@bp.get("/api/locations/floors")
@login_required
def api_floors():
    building_id = request.args.get("building_id", type=int)
    if not building_id:
        return jsonify([])
    rows = Floor.query.filter_by(building_id=building_id).order_by(Floor.name.asc()).all()
    return jsonify([{"id": f.id, "name": f.name} for f in rows])

@bp.get("/api/locations/sections")
@login_required
def api_sections():
    building_id = request.args.get("building_id", type=int)
    floor_id = request.args.get("floor_id", type=int)
    if not (building_id and floor_id):
        return jsonify([])
    rows = HospitalSection.query.filter_by(building_id=building_id, floor_id=floor_id)\
        .order_by(HospitalSection.name.asc()).all()
    return jsonify([{"id": s.id, "name": s.name} for s in rows])

@bp.get("/api/locations/rooms")
@login_required
def api_rooms():
    building_id = request.args.get("building_id", type=int)
    floor_id = request.args.get("floor_id", type=int)
    section_id = request.args.get("section_id", type=int)
    if not (building_id and floor_id and section_id):
        return jsonify([])
    rows = Room.query.filter_by(building_id=building_id, floor_id=floor_id, section_id=section_id)\
        .order_by(Room.name.asc()).all()
    return jsonify([{"id": r.id, "name": r.name} for r in rows])


# -------------------------
# Create Ticket
# -------------------------
@bp.route("/tickets/create", methods=["GET", "POST"])
@login_required
def create_ticket():
    if request.method == "POST":
        requester_name = (request.form.get("requester_name") or "").strip()
        requester_extension = (request.form.get("requester_extension") or "").strip() or None

        building_id = request.form.get("building_id", type=int)
        floor_id = request.form.get("floor_id", type=int)
        section_id = request.form.get("section_id", type=int)
        room_id = request.form.get("room_id", type=int)

        maintenance_dept = (request.form.get("maintenance_dept") or "").strip().lower()
        priority = (request.form.get("priority") or "").strip().lower()
        error_name = (request.form.get("error_name") or "").strip() or None
        title = (request.form.get("title") or "").strip()
        description = (request.form.get("description") or "").strip()

        if not requester_name:
            flash("Requester Name is required.", "danger")
            return redirect(url_for("tickets.create_ticket"))

        if not all([building_id, floor_id, section_id, room_id]):
            flash("Please select Building, Floor, Section and Room.", "danger")
            return redirect(url_for("tickets.create_ticket"))

        if maintenance_dept not in MAINT_DEPTS:
            flash("Please select a valid Maintenance Department.", "danger")
            return redirect(url_for("tickets.create_ticket"))

        if priority not in PRIORITIES:
            flash("Please select a valid Priority.", "danger")
            return redirect(url_for("tickets.create_ticket"))

        if not title:
            flash("Title is required.", "danger")
            return redirect(url_for("tickets.create_ticket"))

        if not description:
            flash("Description is required.", "danger")
            return redirect(url_for("tickets.create_ticket"))

        b = Building.query.get(building_id)
        f = Floor.query.get(floor_id)
        s = HospitalSection.query.get(section_id)
        r = Room.query.get(room_id)
        if not b or not f or not s or not r:
            flash("Selected location is invalid. Please re-select.", "danger")
            return redirect(url_for("tickets.create_ticket"))

        last_no = db.session.query(func.max(Ticket.ticket_no)).scalar()
        next_no = 1 if last_no is None else int(last_no) + 1

        try:
            now = datetime.utcnow()
            t = Ticket(
                ticket_no=next_no,
                requester_user_id=current_user.id,
                requester_name=requester_name,
                requester_extension=requester_extension,
                building_id=building_id,
                floor_id=floor_id,
                section_id=section_id,
                room_id=room_id,
                maintenance_dept=maintenance_dept,
                priority=priority,
                error_name=error_name,
                title=title,
                description=description,
                status="new",
                created_at=now,
                last_status_at=now,
            )
            db.session.add(t)
            db.session.flush()

            db.session.add(TicketUpdate(
                ticket_id=t.id,
                action_type="created",
                note="Ticket created",
                old_value=None,
                new_value="new",
                created_by=current_user.id,
                created_at=now
            ))

            db.session.commit()

        except Exception as e:
            db.session.rollback()
            flash(f"Error while creating ticket: {e}", "danger")
            return redirect(url_for("tickets.create_ticket"))

        flash(f"Ticket #{t.ticket_no} created successfully.", "success")
        return redirect(url_for("tickets.ticket_detail", ticket_id=t.id))

    return render_template("ticket_create.html", maint_depts=MAINT_DEPTS, priorities=PRIORITIES)


# -------------------------
# Ticket Detail
# -------------------------
@bp.get("/tickets/<int:ticket_id>")
@login_required
def ticket_detail(ticket_id: int):
    # دعم الطباعة بدون تغيير أي JS
    if request.args.get("print") == "1":
        return redirect(url_for("printing_html.print_work_order", ticket_id=ticket_id))

    t = Ticket.query.get_or_404(ticket_id)

    building = Building.query.get(t.building_id)
    floor = Floor.query.get(t.floor_id)
    section = HospitalSection.query.get(t.section_id)
    room = Room.query.get(t.room_id)

    return render_template(
        "ticket_detail.html",
        t=t,
        building=building,
        floor=floor,
        section=section,
        room=room
    )

@bp.get("/tickets/<int:ticket_id>/print")
@login_required
def ticket_print_alias(ticket_id: int):
    return redirect(url_for("printing_html.print_work_order", ticket_id=ticket_id))


# -------------------------
# Status logic (desktop-like timing)
# -------------------------
def _apply_auto_times_on_status_change(t: Ticket, old_status: str, new_status: str, now: datetime):
    t.last_status_at = now

    # first response: first time leaving new
    if (old_status == "new") and (new_status != "new") and (t.first_response_at is None):
        t.first_response_at = now

    # start time
    if new_status == "processing" and t.started_at is None:
        t.started_at = now

    if new_status in ("waiting", "Needs Spare Parts") and t.started_at is None:
        t.started_at = now

    # spares timestamp
    if (new_status == "Needs Spare Parts") and (t.spares_requested_at is None):
        t.spares_requested_at = now

    # end time
    if new_status in ("executed", "cancelled") and t.ended_at is None:
        t.ended_at = now


def _can_update_ticket(t: Ticket) -> bool:
    # admin/supervisor always
    if current_user.role in ("admin", "supervisor"):
        return True

    # technician: only his dept
    if current_user.role == "technician":
        if not current_user.maintenance_dept:
            return False
        return (t.maintenance_dept or "").lower() == current_user.maintenance_dept.lower()

    return False


# -------------------------
# Single Quick Update (Status / Close)
# -------------------------
@bp.post("/tickets/<int:ticket_id>/quick-update")
@login_required
def ticket_quick_update(ticket_id: int):
    t = Ticket.query.get_or_404(ticket_id)

    if not _can_update_ticket(t):
        flash("Not allowed.", "danger")
        return redirect(url_for("dashboard.dashboard"))

    return_to = (request.form.get("return_to") or "").strip() or url_for("dashboard.dashboard")
    action = (request.form.get("action") or "update").strip().lower()
    new_status = (request.form.get("status") or "").strip()

    now = datetime.utcnow()

    try:
        if action == "close":
            # Allowed when executed/cancelled only
            if t.status not in ("executed", "cancelled"):
                flash("Close allowed only when status is Executed or Cancelled.", "danger")
                return redirect(return_to)

            old = t.status
            t.status = "closed"
            t.closed_at = now
            t.closed_by = current_user.id
            t.last_status_at = now

            db.session.add(TicketUpdate(
                ticket_id=t.id,
                action_type="closed",
                note="Ticket closed",
                old_value=old,
                new_value="closed",
                created_by=current_user.id,
                created_at=now
            ))
            db.session.commit()
            flash("Ticket closed.", "success")
            return redirect(return_to)

        # action == update
        if new_status not in STATUSES:
            flash("Invalid status.", "danger")
            return redirect(return_to)

        if new_status == t.status:
            flash("No changes.", "secondary")
            return redirect(return_to)

        old = t.status
        t.status = new_status

        _apply_auto_times_on_status_change(t, old, new_status, now)

        db.session.add(TicketUpdate(
            ticket_id=t.id,
            action_type="status_changed",
            note=f"Status changed: {old} -> {new_status}",
            old_value=old,
            new_value=new_status,
            created_by=current_user.id,
            created_at=now
        ))

        db.session.commit()
        flash("Status updated.", "success")
        return redirect(return_to)

    except Exception as e:
        db.session.rollback()
        flash(f"Update error: {e}", "danger")
        return redirect(return_to)


# -------------------------
# ✅ Bulk Update (Status / Close / Print list)
# -------------------------
@bp.post("/tickets/bulk-update")
@login_required
def tickets_bulk_update():
    ids_raw = (request.form.get("ids") or "").strip()
    action = (request.form.get("action") or "").strip().lower()
    status = (request.form.get("status") or "").strip()
    return_to = (request.form.get("return_to") or "").strip() or url_for("dashboard.dashboard")

    if not ids_raw:
        flash("No tickets selected.", "warning")
        return redirect(return_to)

    try:
        ids = [int(x) for x in ids_raw.split(",") if x.strip().isdigit()]
    except Exception:
        ids = []

    if not ids:
        flash("No tickets selected.", "warning")
        return redirect(return_to)

    # load tickets
    tickets = Ticket.query.filter(Ticket.id.in_(ids)).all()

    # permission: all must be allowed
    for t in tickets:
        if not _can_update_ticket(t):
            flash("Not allowed to update one or more selected tickets.", "danger")
            return redirect(return_to)

    now = datetime.utcnow()

    try:
        if action == "status":
            if status not in STATUSES:
                flash("Invalid status.", "danger")
                return redirect(return_to)

            changed = 0
            for t in tickets:
                if t.status == status:
                    continue
                old = t.status
                t.status = status
                _apply_auto_times_on_status_change(t, old, status, now)
                db.session.add(TicketUpdate(
                    ticket_id=t.id,
                    action_type="status_changed",
                    note=f"Bulk status: {old} -> {status}",
                    old_value=old,
                    new_value=status,
                    created_by=current_user.id,
                    created_at=now
                ))
                changed += 1

            db.session.commit()
            flash(f"Bulk status updated ({changed}).", "success")
            return redirect(return_to)

        if action == "close":
            closed = 0
            skipped = 0
            for t in tickets:
                if t.status not in ("executed", "cancelled"):
                    skipped += 1
                    continue
                old = t.status
                t.status = "closed"
                t.closed_at = now
                t.closed_by = current_user.id
                t.last_status_at = now
                db.session.add(TicketUpdate(
                    ticket_id=t.id,
                    action_type="closed",
                    note="Bulk close",
                    old_value=old,
                    new_value="closed",
                    created_by=current_user.id,
                    created_at=now
                ))
                closed += 1

            db.session.commit()
            if skipped:
                flash(f"Closed {closed} (skipped {skipped} not executed/cancelled).", "warning")
            else:
                flash(f"Closed {closed}.", "success")
            return redirect(return_to)

        flash("Invalid bulk action.", "danger")
        return redirect(return_to)

    except Exception as e:
        db.session.rollback()
        flash(f"Bulk update error: {e}", "danger")
        return redirect(return_to)
