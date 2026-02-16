# backend/blueprints/printing_pdf.py
import os
from io import BytesIO
from datetime import datetime

from flask import Blueprint, send_file, abort
from flask_login import login_required

from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

import arabic_reshaper
from bidi.algorithm import get_display

from models import Ticket, Building, Floor, HospitalSection, Room, User

bp = Blueprint("printing_pdf", __name__)

def mm(v: float) -> float:
    return v * 2.83464567

def safe_str(x):
    return "" if x is None else str(x)

def get_attr(obj, name, default=None):
    if obj is None:
        return default
    return getattr(obj, name, default)

def ar(text: str) -> str:
    if not text:
        return ""
    reshaped = arabic_reshaper.reshape(str(text))
    return get_display(reshaped)

def static_path(*parts):
    base = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "static"))
    return os.path.join(base, *parts)

def register_fonts():
    """
    Prefer Arabic-friendly fonts from backend/static/fonts:
      - Cairo-Regular.ttf / Cairo-Bold.ttf
      - Amiri-Regular.ttf / Amiri-Bold.ttf
    Fallback to Helvetica if not found.
    """
    fonts_dir = static_path("fonts")
    candidates = [
        ("Cairo", os.path.join(fonts_dir, "Cairo-Regular.ttf"), os.path.join(fonts_dir, "Cairo-Bold.ttf")),
        ("Amiri", os.path.join(fonts_dir, "Amiri-Regular.ttf"), os.path.join(fonts_dir, "Amiri-Bold.ttf")),
    ]
    for base, reg, bold in candidates:
        if os.path.exists(reg) and os.path.exists(bold):
            pdfmetrics.registerFont(TTFont(base, reg))
            pdfmetrics.registerFont(TTFont(base + "-B", bold))
            return base, base + "-B"

    return "Helvetica", "Helvetica-Bold"

@bp.get("/tickets/<int:ticket_id>/print.pdf")
@login_required
def print_ticket_pdf(ticket_id: int):
    t = Ticket.query.get(ticket_id)
    if not t:
        abort(404)

    # ---- Location objects (safe) ----
    building = Building.query.get(get_attr(t, "building_id"))
    floor = Floor.query.get(get_attr(t, "floor_id"))
    section = HospitalSection.query.get(get_attr(t, "section_id"))
    room = Room.query.get(get_attr(t, "room_id"))

    # ---- Requester fields (support both names) ----
    requester_name = get_attr(t, "requester_name")
    if not requester_name:
        requester_name = get_attr(t, "caller_name", "")  # fallback قديم
    requester_name = requester_name or ""

    requester_extension = get_attr(t, "requester_extension")
    if requester_extension is None:
        requester_extension = get_attr(t, "requester_ext")
    requester_extension = requester_extension or ""

    # ---- Ticket No ----
    ticket_no = get_attr(t, "ticket_no")
    if ticket_no is None:
        ticket_no = get_attr(t, "ticket_number")
    if ticket_no is None:
        ticket_no = get_attr(t, "ticket_id")
    if ticket_no is None:
        ticket_no = get_attr(t, "id", "")

    # ---- Times ----
    created_at = get_attr(t, "created_at")
    job_time = created_at.strftime("%I:%M %p") if created_at else ""
    job_date = created_at.strftime("%d/%m/%Y") if created_at else ""

    now = datetime.now()
    print_time = now.strftime("%I:%M %p")
    print_date = now.strftime("%d/%m/%Y")

    # ---- Other fields ----
    maintenance_dept = safe_str(get_attr(t, "maintenance_dept", ""))
    error_name = safe_str(get_attr(t, "error_name", ""))
    priority = safe_str(get_attr(t, "priority", ""))
    status = safe_str(get_attr(t, "status", ""))
    description = safe_str(get_attr(t, "description", ""))

    # ---- Fonts ----
    FONT_REG, FONT_BOLD = register_fonts()

    # ---- PDF canvas ----
    buf = BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    W, H = A4

    margin = mm(8)
    x0, y0 = margin, margin
    x1, y1 = W - margin, H - margin

    # Border
    c.setLineWidth(2)
    c.rect(x0, y0, x1 - x0, y1 - y0)

    # Header image (optional)
    y = y1
    header_h = mm(22)
    header_path = static_path("header.png")
    if os.path.exists(header_path):
        try:
            img = ImageReader(header_path)
            c.drawImage(img, x0, y1 - header_h, width=(x1 - x0), height=header_h,
                        preserveAspectRatio=True, anchor='sw')
            c.setLineWidth(1)
            c.line(x0, y1 - header_h, x1, y1 - header_h)
            y = y1 - header_h
        except:
            y = y1 - mm(10)
    else:
        y = y1 - mm(10)

    def box(x, top, w, h, lw=1):
        c.setLineWidth(lw)
        c.rect(x, top - h, w, h)

    def draw_center(x, top, w, h, text, size=11, bold=False, rtl=False, dy=0):
        c.setFont(FONT_BOLD if bold else FONT_REG, size)
        s = ar(text) if rtl else safe_str(text)
        c.drawCentredString(x + w/2, (top - h/2) - 4 + dy, s)

    def draw_left(x, top, w, h, text, size=11, bold=False, dy=0):
        c.setFont(FONT_BOLD if bold else FONT_REG, size)
        c.drawString(x + mm(2), (top - h/2) - 4 + dy, safe_str(text))

    def draw_right(x, top, w, h, text, size=11, bold=False, rtl=False, dy=0):
        c.setFont(FONT_BOLD if bold else FONT_REG, size)
        s = ar(text) if rtl else safe_str(text)
        c.drawRightString(x + w - mm(2), (top - h/2) - 4 + dy, s)

    # ===== Row 1 (Print + Title) =====
    row_h = mm(22)
    col_w = (x1 - x0) / 3

    # left
    box(x0, y, col_w, row_h)
    c.setFont(FONT_BOLD, 11)
    c.drawString(x0 + mm(2), y - mm(6), "Print Time")
    c.drawRightString(x0 + col_w - mm(2), y - mm(6), print_time)
    c.drawString(x0 + mm(2), y - mm(14), "Print Date")
    c.drawRightString(x0 + col_w - mm(2), y - mm(14), print_date)

    # center title
    box(x0 + col_w, y, col_w, row_h)
    c.setFillColorRGB(0.83, 0.47, 0.0)
    c.setFont(FONT_BOLD, 16)
    c.drawCentredString(x0 + col_w + col_w/2, y - mm(9), "General Maintenance")
    c.setFont(FONT_BOLD, 14)
    c.drawCentredString(x0 + col_w + col_w/2, y - mm(16), ar("الصيانة العامة"))
    c.setFillColorRGB(0, 0, 0)

    # right
    box(x0 + 2*col_w, y, col_w, row_h)
    c.setFont(FONT_BOLD, 11)
    c.drawRightString(x0 + 3*col_w - mm(2), y - mm(6), ar("وقت الطباعة"))
    c.drawString(x0 + 2*col_w + mm(2), y - mm(6), print_time)
    c.drawRightString(x0 + 3*col_w - mm(2), y - mm(14), ar("تاريخ الطباعة"))
    c.drawString(x0 + 2*col_w + mm(2), y - mm(14), print_date)

    y -= row_h

    # ===== Row 2 (Job info) =====
    row_h = mm(18)
    col = (x1 - x0) / 5
    heads = [
        ("Job Time", "وقت البلاغ", job_time),
        ("Job Date", "تاريخ البلاغ", job_date),
        ("Job No", "رقم أمر العمل", ticket_no),
        ("Emp No", "الرقم الوظيفي", ""),     # لو لاحقاً تربطه من User
        ("Requestor #", "التحويلة", requester_extension),
    ]

    for i, (en, ar_lbl, val) in enumerate(heads):
        x = x0 + i * col
        box(x, y, col, row_h)
        c.setFont(FONT_BOLD, 10)
        c.drawCentredString(x + col/2, y - mm(6), en)
        c.drawCentredString(x + col/2, y - mm(10), ar(ar_lbl))
        if i == 2:
            c.setFont(FONT_BOLD, 18)
            c.drawCentredString(x + col/2, y - mm(15), safe_str(val))
        else:
            c.setFont(FONT_REG, 11)
            c.drawCentredString(x + col/2, y - mm(15), safe_str(val))

    y -= row_h

    # ===== Row 3 (User name) =====
    row_h = mm(14)
    box(x0, y, x1-x0, row_h)
    c.setFont(FONT_BOLD, 11)
    c.drawCentredString((x0+x1)/2, y - mm(6), "User Name / " + ar("اسم المستخدم"))
    c.setFont(FONT_BOLD, 14)
    c.drawCentredString((x0+x1)/2, y - mm(12), safe_str(requester_name))
    y -= row_h

    # ===== Main table =====
    row_h = mm(10)
    w1 = (x1-x0) * 0.20
    w2 = (x1-x0) * 0.35
    w3 = (x1-x0) * 0.25
    w4 = (x1-x0) * 0.20

    def row(en_label, en_val, ar_val, ar_label, center_values=False):
        nonlocal y
        box(x0, y, w1, row_h)
        box(x0+w1, y, w2, row_h)
        box(x0+w1+w2, y, w3, row_h)
        box(x0+w1+w2+w3, y, w4, row_h)

        draw_left(x0, y, w1, row_h, en_label, 10, True)

        if center_values:
            draw_center(x0+w1, y, w2, row_h, en_val, 10, False)
            draw_center(x0+w1+w2, y, w3, row_h, ar_val, 10, False, rtl=True)
        else:
            draw_center(x0+w1, y, w2, row_h, en_val, 10, False)
            draw_right(x0+w1+w2, y, w3, row_h, ar_val, 10, False, rtl=True)

        draw_right(x0+w1+w2+w3, y, w4, row_h, ar_label, 10, True, rtl=True)
        y -= row_h

    row("Caller Name", requester_name, requester_name, "اسم طالب الصيانة")
    row("Caller Location", get_attr(building, "name", ""), get_attr(building, "name", ""), "موقع طالب الصيانة")
    row("Section Name", get_attr(section, "name", ""), get_attr(section, "name", ""), "اسم القسم")
    row("Floor Number", get_attr(floor, "name", ""), get_attr(floor, "name", ""), "رقم الطابق")
    row("Office No / Name", get_attr(room, "name", ""), get_attr(room, "name", ""), "رقم / اسم المكتب")
    row("Maintenance Type", maintenance_dept, maintenance_dept, "نوع الصيانة")
    row("Error Name", error_name, error_name, "اسم العطل / المشكلة")
    row("Job Priority", priority, priority, "درجة الأهمية")
    row("Job Status", status, status, "حالة أمر العمل")

    # ✅ Error Desc centered
    row("Error Desc", description, description, "وصف العطل", center_values=True)

    # ===== Spare parts (numbers start from TOP-LEFT) =====
    spare_h = mm(30)
    box(x0, y, x1-x0, spare_h)
    c.setFont(FONT_BOLD, 12)
    c.drawCentredString((x0+x1)/2, y - mm(6), ar("قطع الغيار المطلوبة"))

    start_y = y - mm(10)   # top alignment
    gap = mm(4.6)

    num_x = x0 + mm(6)
    line_start = x0 + mm(20)
    line_end = x1 - mm(6)

    for i in range(6):
        yy = start_y - i * gap
        c.setFont(FONT_BOLD, 11)
        c.drawString(num_x, yy - mm(1.6), f"{i+1} -")
        c.setLineWidth(1.1)
        c.setDash(1, 2)
        c.line(line_start, yy, line_end, yy)
        c.setDash()

    y -= spare_h

    # ===== Technician report (bigger writing space, still A4) =====
    tech_h = mm(38)
    box(x0, y, x1-x0, tech_h)
    c.setFont(FONT_BOLD, 12)
    c.drawCentredString((x0+x1)/2, y - mm(6), "Technician Report / " + ar("التقرير الفني"))

    # Bigger spacing between lines
    start_y = y - mm(14)
    gap = mm(10)
    for i in range(3):
        yy = start_y - i * gap
        c.setLineWidth(1.1)
        c.setDash(1, 2)
        c.line(x0 + mm(6), yy, x1 - mm(6), yy)
        c.setDash()

    y -= tech_h

    # ===== Signatures =====
    sig_h = mm(18)
    col = (x1-x0) / 4
    sigs = ["رئيس قسم الصيانة العامة", "مشرف قسم الصيانة العامة", "مسؤول القسم", "الفني المختص"]
    for i, lab in enumerate(sigs):
        box(x0 + i * col, y, col, sig_h)
        c.setFont(FONT_BOLD, 10)
        c.drawCentredString(x0 + i * col + col/2, y - sig_h/2 - 4, ar(lab))

    c.showPage()
    c.save()

    buf.seek(0)
    return send_file(
        buf,
        mimetype="application/pdf",
        as_attachment=False,
        download_name=f"work_order_{ticket_id}.pdf"
    )
