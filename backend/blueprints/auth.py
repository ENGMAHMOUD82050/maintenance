from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import check_password_hash

from models import User
from db import db

bp = Blueprint("auth", __name__)

def _get_login_fields():
    username = (
        (request.form.get("username") or "").strip()
        or (request.form.get("user") or "").strip()
        or (request.form.get("login") or "").strip()
        or (request.form.get("email") or "").strip()
    )
    password = (request.form.get("password") or "") or (request.form.get("pass") or "")
    return username, password

def _looks_like_hash(s: str) -> bool:
    if not s:
        return False
    # werkzeug hashes usually contain ":" and are long
    return (":" in s) and (len(s) > 20)

@bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("dashboard.dashboard"))

    if request.method == "POST":
        username, password = _get_login_fields()

        if not username or not password:
            flash("Please enter username and password.", "danger")
            print("[LOGIN] missing username/password")
            return render_template("login.html")

        user = User.query.filter_by(username=username).first()
        if not user:
            flash("User not found.", "danger")
            print(f"[LOGIN] user not found: {username}")
            return render_template("login.html")

        # safe debug
        ph = (getattr(user, "password_hash", "") or "").strip()
        print(f"[LOGIN] username={username} hash_len={len(ph)} hash_prefix={ph[:18]}...")

        # 1) normal hashed check
        ok = False
        try:
            ok = user.check_password(password)
        except Exception as e:
            print(f"[LOGIN] check_password exception: {e}")
            ok = False

        # 2) fallback: DB contains plaintext password OR weird old value
        if not ok:
            try:
                if ph and (not _looks_like_hash(ph)) and ph == password:
                    ok = True
                    # upgrade to hashed
                    user.set_password(password)
                    db.session.commit()
                    print(f"[LOGIN] plaintext password detected -> upgraded for {username}")
            except Exception as e:
                print(f"[LOGIN] plaintext fallback failed: {e}")

        # 3) extra fallback: if ph looks like hash but werkzeug check failed (rare)
        # try check_password_hash directly
        if not ok:
            try:
                if ph and _looks_like_hash(ph) and check_password_hash(ph, password):
                    ok = True
            except Exception as e:
                print(f"[LOGIN] check_password_hash direct failed: {e}")

        if ok:
            login_user(user)
            next_page = request.args.get("next")
            print(f"[LOGIN] SUCCESS -> redirect to {next_page or '/dashboard'}")
            return redirect(next_page or url_for("dashboard.dashboard"))

        flash("Invalid password.", "danger")
        print(f"[LOGIN] invalid password for {username}")
        return render_template("login.html")

    return render_template("login.html")


@bp.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("auth.login"))
