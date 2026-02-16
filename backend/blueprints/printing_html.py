# backend/blueprints/printing_html.py
from datetime import datetime
from flask import Blueprint, render_template
from flask_login import login_required, current_user
from models import Ticket, Building, Floor, HospitalSection, Room

bp = Blueprint("printing_html", __name__)

# قاموس ترجمة ديناميكي (زوده وقت ما تحب)
AR_MAP = {
    "main building": "المبنى الرئيسي",
    "basement": "القبو",
    "ground": "الأرضي",
    "first floor": "الطابق الأول",
    "second floor": "الطابق الثاني",

    "hvac": "قسم التكييف",
    "mechanical": "قسم الميكانيكا",
    "civil": "قسم المدني",
    "electronics": "قسم الإلكترونيات",
    "electrical": "قسم الكهرباء",

    "new": "جديد",
    "processing": "تحت الإجراء",
    "waiting": "انتظار",
    "needs spare parts": "مطلوب قطع غيار",
    "needs_spares": "مطلوب قطع غيار",
    "executed": "تم التنفيذ",
    "cancelled": "ملغي",
    "closed": "تم الإغلاق",

    "high": "مرتفع",
    "medium": "متوسط",
    "low": "منخفض",
    "emergency": "طارئ",
    "other": "أخرى",
}

def to_ar(value: str) -> str:
    """ترجمة بسيطة تعتمد على AR_MAP مع fallback للقيمة نفسها."""
    if value is None:
        return ""
    text = str(value).strip()
    key = text.lower()
    return AR_MAP.get(key, text)

@bp.get("/print/work-order/<int:ticket_id>")
@login_required
def print_work_order(ticket_id: int):
    t = Ticket.query.get_or_404(ticket_id)

    building = Building.query.get(t.building_id)
    floor = Floor.query.get(t.floor_id)
    section = HospitalSection.query.get(t.section_id)
    room = Room.query.get(t.room_id)

    now = datetime.now()
    now_time = now.strftime("%I:%M %p")
    now_date = now.strftime("%d/%m/%Y")

    # ملاحظة: template بتستخدم current_user، فلازم يكون login_required موجود (وهو موجود)
    return render_template(
        "print_work_order.html",
        t=t,
        building=building,
        floor=floor,
        section=section,
        room=room,
        now_time=now_time,
        now_date=now_date,
        AR_MAP=AR_MAP,
        to_ar=to_ar  # ✅ مهم جدًا لأن template عندك بينادي to_ar(...) :contentReference[oaicite:0]{index=0}
    )
