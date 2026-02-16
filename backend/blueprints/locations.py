# backend/blueprints/locations.py
from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from sqlalchemy import func

from models import db, Building, Floor, HospitalSection, Room

bp = Blueprint("locations", __name__)

def _admin_only():
    return getattr(current_user, "role", "") == "admin"


@bp.get("/locations")
@login_required
def locations_home():
    if not _admin_only():
        flash("Admin only.", "danger")
        return redirect(url_for("dashboard.dashboard"))

    buildings = Building.query.order_by(Building.name.asc()).all()

    building_id = request.args.get("building_id", type=int)
    floor_id = request.args.get("floor_id", type=int)
    section_id = request.args.get("section_id", type=int)

    floors = []
    sections = []
    rooms = []

    if building_id:
        floors = Floor.query.filter_by(building_id=building_id).order_by(Floor.name.asc()).all()

    if building_id and floor_id:
        sections = HospitalSection.query.filter_by(building_id=building_id, floor_id=floor_id)\
            .order_by(HospitalSection.name.asc()).all()

    if building_id and floor_id and section_id:
        rooms = Room.query.filter_by(building_id=building_id, floor_id=floor_id, section_id=section_id)\
            .order_by(Room.name.asc()).all()

    return render_template(
        "locations.html",
        buildings=buildings,
        floors=floors,
        sections=sections,
        rooms=rooms,
        building_id=building_id,
        floor_id=floor_id,
        section_id=section_id
    )


# -------------------------
# Add building / floor / section / room
# -------------------------
@bp.post("/locations/buildings/add")
@login_required
def add_building():
    if not _admin_only():
        flash("Admin only.", "danger")
        return redirect(url_for("dashboard.dashboard"))

    name = (request.form.get("name") or "").strip()
    if not name:
        flash("Building name is required.", "danger")
        return redirect(url_for("locations.locations_home"))

    if Building.query.filter(func.lower(Building.name) == name.lower()).first():
        flash("Building already exists.", "warning")
        return redirect(url_for("locations.locations_home"))

    db.session.add(Building(name=name))
    db.session.commit()
    flash("Building added.", "success")
    return redirect(url_for("locations.locations_home"))


@bp.post("/locations/floors/add")
@login_required
def add_floor():
    if not _admin_only():
        flash("Admin only.", "danger")
        return redirect(url_for("dashboard.dashboard"))

    building_id = request.form.get("building_id", type=int)
    name = (request.form.get("name") or "").strip()

    if not building_id or not name:
        flash("Building + Floor name are required.", "danger")
        return redirect(url_for("locations.locations_home"))

    if not Building.query.get(building_id):
        flash("Invalid building.", "danger")
        return redirect(url_for("locations.locations_home"))

    exists = Floor.query.filter_by(building_id=building_id)\
        .filter(func.lower(Floor.name) == name.lower()).first()
    if exists:
        flash("Floor already exists in this building.", "warning")
        return redirect(url_for("locations.locations_home", building_id=building_id))

    db.session.add(Floor(building_id=building_id, name=name))
    db.session.commit()
    flash("Floor added.", "success")
    return redirect(url_for("locations.locations_home", building_id=building_id))


@bp.post("/locations/sections/add")
@login_required
def add_section():
    if not _admin_only():
        flash("Admin only.", "danger")
        return redirect(url_for("dashboard.dashboard"))

    building_id = request.form.get("building_id", type=int)
    floor_id = request.form.get("floor_id", type=int)
    name = (request.form.get("name") or "").strip()

    if not building_id or not floor_id or not name:
        flash("Building + Floor + Section name are required.", "danger")
        return redirect(url_for("locations.locations_home"))

    if not (Building.query.get(building_id) and Floor.query.get(floor_id)):
        flash("Invalid building/floor.", "danger")
        return redirect(url_for("locations.locations_home", building_id=building_id))

    exists = HospitalSection.query.filter_by(building_id=building_id, floor_id=floor_id)\
        .filter(func.lower(HospitalSection.name) == name.lower()).first()
    if exists:
        flash("Section already exists.", "warning")
        return redirect(url_for("locations.locations_home", building_id=building_id, floor_id=floor_id))

    db.session.add(HospitalSection(building_id=building_id, floor_id=floor_id, name=name))
    db.session.commit()
    flash("Section added.", "success")
    return redirect(url_for("locations.locations_home", building_id=building_id, floor_id=floor_id))


@bp.post("/locations/rooms/add")
@login_required
def add_room():
    if not _admin_only():
        flash("Admin only.", "danger")
        return redirect(url_for("dashboard.dashboard"))

    building_id = request.form.get("building_id", type=int)
    floor_id = request.form.get("floor_id", type=int)
    section_id = request.form.get("section_id", type=int)
    name = (request.form.get("name") or "").strip()

    if not building_id or not floor_id or not section_id or not name:
        flash("Building + Floor + Section + Room name are required.", "danger")
        return redirect(url_for("locations.locations_home"))

    if not (Building.query.get(building_id) and Floor.query.get(floor_id) and HospitalSection.query.get(section_id)):
        flash("Invalid location chain.", "danger")
        return redirect(url_for("locations.locations_home", building_id=building_id, floor_id=floor_id))

    exists = Room.query.filter_by(building_id=building_id, floor_id=floor_id, section_id=section_id)\
        .filter(func.lower(Room.name) == name.lower()).first()
    if exists:
        flash("Room already exists.", "warning")
        return redirect(url_for("locations.locations_home", building_id=building_id, floor_id=floor_id, section_id=section_id))

    db.session.add(Room(building_id=building_id, floor_id=floor_id, section_id=section_id, name=name))
    db.session.commit()
    flash("Room added.", "success")
    return redirect(url_for("locations.locations_home", building_id=building_id, floor_id=floor_id, section_id=section_id))


@bp.post("/locations/delete")
@login_required
def delete_location():
    if not _admin_only():
        flash("Admin only.", "danger")
        return redirect(url_for("dashboard.dashboard"))

    kind = (request.form.get("kind") or "").strip()
    item_id = request.form.get("id", type=int)

    if kind not in ("building", "floor", "section", "room") or not item_id:
        flash("Invalid delete request.", "danger")
        return redirect(url_for("locations.locations_home"))

    model = {"building": Building, "floor": Floor, "section": HospitalSection, "room": Room}[kind]
    obj = model.query.get(item_id)
    if not obj:
        flash("Item not found.", "warning")
        return redirect(url_for("locations.locations_home"))

    try:
        db.session.delete(obj)
        db.session.commit()
        flash("Deleted.", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"Cannot delete (maybe used by tickets). {e}", "danger")

    return redirect(url_for("locations.locations_home"))
