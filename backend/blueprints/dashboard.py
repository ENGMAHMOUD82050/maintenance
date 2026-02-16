from datetime import datetime, date, time, timedelta
from math import ceil
from urllib.parse import urlencode

from flask import Blueprint, render_template, request, jsonify
from flask_login import login_required, current_user
from sqlalchemy import func, or_

from models import (
    Ticket, Building, Floor, HospitalSection, Room,
    MAINT_DEPTS, STATUSES, SLA_HOURS
)

bp = Blueprint("dashboard", __name__)


def _parse_date(value: str):
    try:
        return date.fromisoformat(value)
    except Exception:
        return None


def _fmt_duration(delta: timedelta) -> str:
    if delta.total_seconds() < 0:
        delta = timedelta(seconds=0)
    mins = int(delta.total_seconds() // 60)
    h = mins // 60
    m = mins % 60
    if h <= 0:
        return f"{m}m"
    return f"{h}h {m:02d}m"


def _compute_over_sla(t: Ticket, now: datetime) -> bool:
    pri = (t.priority or "").lower().strip()
    hours = SLA_HOURS.get(pri)
    if not hours:
        return False
    end = t.ended_at or now
    if not t.created_at:
        return False
    elapsed = end - t.created_at
    return elapsed.total_seconds() > (hours * 3600)


def _build_query():
    today = date.today()
    now = datetime.utcnow()

    view = (request.args.get("view") or "open").strip().lower()
    if view not in ("open", "over_sla", "closed_today", "all"):
        view = "open"

    show_all = (request.args.get("all") == "1")
    date_from = _parse_date(request.args.get("from", "") or "") or today
    date_to = _parse_date(request.args.get("to", "") or "") or today
    dt_from = datetime.combine(date_from, time.min)
    dt_to = datetime.combine(date_to, time.max)

    selected_dept = (request.args.get("dept", "") or "").strip().lower()
    dept_locked = False
    if current_user.role in ("technician", "requester"):
        if current_user.maintenance_dept:
            selected_dept = current_user.maintenance_dept.lower()
        else:
            selected_dept = ""
        dept_locked = True

    valid_depts = [d.lower() for d in MAINT_DEPTS]
    if selected_dept and selected_dept not in valid_depts:
        selected_dept = ""

    q = (request.args.get("q", "") or "").strip()

    per_page = request.args.get("per", type=int) or 200
    per_page = max(20, min(per_page, 2000))
    page = request.args.get("page", type=int) or 1
    page = max(1, page)

    base_q = Ticket.query

    if selected_dept:
        base_q = base_q.filter(func.lower(Ticket.maintenance_dept) == selected_dept)

    if not show_all:
        base_q = base_q.filter(Ticket.created_at >= dt_from, Ticket.created_at <= dt_to)

    if q:
        terms = []
        if q.isdigit():
            terms.append(Ticket.ticket_no == int(q))
        like = f"%{q}%"
        terms.append(Ticket.requester_name.ilike(like))
        terms.append(Ticket.title.ilike(like))
        terms.append(Ticket.description.ilike(like))
        terms.append(Ticket.error_name.ilike(like))

        base_q = base_q.outerjoin(Building, Building.id == Ticket.building_id)\
                       .outerjoin(Floor, Floor.id == Ticket.floor_id)\
                       .outerjoin(HospitalSection, HospitalSection.id == Ticket.section_id)\
                       .outerjoin(Room, Room.id == Ticket.room_id)\
                       .filter(or_(
                           *terms,
                           Building.name.ilike(like),
                           Floor.name.ilike(like),
                           HospitalSection.name.ilike(like),
                           Room.name.ilike(like),
                       ))

    all_q = base_q
    open_q = all_q.filter(Ticket.status != "closed")
    closed_today_q = all_q.filter(
        Ticket.status == "closed",
        Ticket.closed_at >= datetime.combine(today, time.min),
        Ticket.closed_at <= datetime.combine(today, time.max),
    )

    # Over SLA scan (cap)
    over_sla_ids = []
    scan_rows = all_q.order_by(Ticket.created_at.desc()).limit(5000).all()
    for t in scan_rows:
        if t.status == "closed":
            continue
        if _compute_over_sla(t, now):
            over_sla_ids.append(t.id)

    over_sla_total = len(over_sla_ids)
    open_total = open_q.count()
    closed_today_total = closed_today_q.count()
    all_total = all_q.count()

    if view == "open":
        final_q = open_q
    elif view == "closed_today":
        final_q = closed_today_q
    elif view == "over_sla":
        final_q = all_q.filter(Ticket.id.in_(over_sla_ids)) if over_sla_ids else all_q.filter(Ticket.id == -1)
    else:
        final_q = all_q

    final_q = final_q.order_by(Ticket.created_at.desc())

    total = final_q.count()
    total_pages = max(1, ceil(total / per_page)) if total else 1
    if page > total_pages:
        page = total_pages

    rows = final_q.offset((page - 1) * per_page).limit(per_page).all()

    # maps
    building_map = {b.id: b.name for b in Building.query.all()}
    floor_map = {f.id: f.name for f in Floor.query.all()}
    section_map = {s.id: s.name for s in HospitalSection.query.all()}
    room_map = {r.id: r.name for r in Room.query.all()}

    items = []
    for t in rows:
        over_sla = (t.status != "closed") and _compute_over_sla(t, now)

        created_at = t.created_at or now
        age_minutes = int(max(0, (now - created_at).total_seconds() // 60))
        is_new = (age_minutes <= 15)

        if t.started_at and t.ended_at:
            duration_text = _fmt_duration(t.ended_at - t.started_at)
        elif t.started_at and not t.ended_at:
            duration_text = _fmt_duration(now - t.started_at)
        else:
            duration_text = _fmt_duration(now - created_at)

        started_hm = t.started_at.strftime("%H:%M") if t.started_at else None
        ended_hm = t.ended_at.strftime("%H:%M") if t.ended_at else None
        started_full = t.started_at.strftime("%Y-%m-%d %H:%M") if t.started_at else None
        ended_full = t.ended_at.strftime("%Y-%m-%d %H:%M") if t.ended_at else None

        can_close = (t.status in ("executed", "cancelled"))

        items.append({
            "id": t.id,
            "ticket_no": t.ticket_no,
            "caller": t.requester_name,
            "dept": (t.maintenance_dept or "").upper(),
            "priority": t.priority,
            "error_name": t.error_name,
            "status": t.status,
            "title": t.title,
            "building": building_map.get(t.building_id, "-"),
            "floor": floor_map.get(t.floor_id, "-"),
            "section": section_map.get(t.section_id, "-"),
            "room": room_map.get(t.room_id, "-"),
            "started_hm": started_hm,
            "ended_hm": ended_hm,
            "started_full": started_full,
            "ended_full": ended_full,
            "duration_text": duration_text,
            "over_sla": over_sla,
            "is_new": is_new,
            "age_minutes": age_minutes,
            "can_close": can_close,
        })

    status_choices = [(s, s) for s in STATUSES if s != "closed"]

    args = dict(request.args)
    args.pop("page", None)
    qs_no_page = urlencode(args, doseq=True)

    args_keep = dict(request.args)
    args_keep.pop("view", None)
    args_keep.pop("page", None)
    qs_keep = urlencode(args_keep, doseq=True)

    ctx = dict(
        today=today,
        view=view,

        q=q,
        show_all=show_all,
        date_from=str(date_from),
        date_to=str(date_to),

        maint_depts=valid_depts,
        selected_dept=selected_dept,
        dept_locked=dept_locked,

        per_page=per_page,
        page=page,
        total=total,
        total_pages=total_pages,
        has_prev=(page > 1),
        has_next=(page < total_pages),
        qs_no_page=qs_no_page,

        open_total=open_total,
        over_sla_total=over_sla_total,
        closed_today_total=closed_today_total,
        all_total=all_total,
        qs_keep=qs_keep,

        recent_tickets=items,
        status_choices=status_choices,
    )

    return ctx


@bp.route("/dashboard")
@login_required
def dashboard():
    ctx = _build_query()
    return render_template("dashboard.html", **ctx)


@bp.get("/api/dashboard/tickets")
@login_required
def api_dashboard_tickets():
    ctx = _build_query()
    return jsonify({
        "total": ctx["total"],
        "page": ctx["page"],
        "total_pages": ctx["total_pages"],
        "items": ctx["recent_tickets"],
    })
