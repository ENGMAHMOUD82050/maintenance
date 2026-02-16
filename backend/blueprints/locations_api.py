from flask import Blueprint, request, jsonify
from flask_login import login_required
from models import Building, Floor, HospitalSection, Room

bp = Blueprint("locations_api", __name__)

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
    if not building_id or not floor_id:
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
    if not building_id or not floor_id or not section_id:
        return jsonify([])
    rows = Room.query.filter_by(building_id=building_id, floor_id=floor_id, section_id=section_id)\
        .order_by(Room.name.asc()).all()
    return jsonify([{"id": r.id, "name": r.name} for r in rows])
