# backend/blueprints/lang.py
from flask import Blueprint, redirect, url_for

bp = Blueprint("lang", __name__)

@bp.route("/lang/<code>")
def set_lang(code):
    # Arabic disabled temporarily => always redirect to dashboard in English
    return redirect(url_for("dashboard.dashboard"))
