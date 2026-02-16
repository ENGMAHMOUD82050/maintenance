from flask import Blueprint, render_template, request, redirect, url_for, abort, flash
from flask_login import login_required, current_user
from db import db
from models import User, ROLES, MAINT_DEPTS

bp = Blueprint("users", __name__)

def admin_only():
    return current_user.role == "admin"

@bp.route("/users", methods=["GET", "POST"])
@login_required
def users():
    if not admin_only():
        abort(403)

    # =======================
    # POST
    # =======================
    if request.method == "POST":
        action = request.form.get("action")

        if action == "create":
            username = (request.form.get("username") or "").strip()
            full_name = (request.form.get("full_name") or "").strip()
            emp_no = (request.form.get("emp_no") or "").strip() or None
            role = request.form.get("role")
            dept = request.form.get("maintenance_dept") or None
            password = request.form.get("password") or ""

            if not username or not full_name or not password:
                flash("Username, Full Name and Password are required.", "danger")
                return redirect(url_for("users.users"))

            if role not in ROLES:
                flash("Invalid role.", "danger")
                return redirect(url_for("users.users"))

            if role in ("supervisor", "technician"):
                if dept not in MAINT_DEPTS:
                    flash("Dept is required for supervisor/technician.", "danger")
                    return redirect(url_for("users.users"))
            else:
                dept = None

            if User.query.filter_by(username=username).first():
                flash("Username already exists.", "danger")
                return redirect(url_for("users.users"))

            u = User(
                username=username,
                full_name=full_name,
                emp_no=emp_no,
                role=role,
                maintenance_dept=dept,
                is_active=True
            )
            u.set_password(password)
            db.session.add(u)
            db.session.commit()

            flash("User created successfully.", "success")
            return redirect(url_for("users.users"))

        elif action == "update":
            user_id = request.form.get("user_id", type=int)
            u = User.query.get_or_404(user_id)

            full_name = (request.form.get("full_name") or "").strip()
            emp_no = (request.form.get("emp_no") or "").strip() or None
            role = request.form.get("role")
            dept = request.form.get("maintenance_dept") or None

            if not full_name:
                flash("Full name is required.", "danger")
                return redirect(url_for("users.users"))

            if role not in ROLES:
                flash("Invalid role.", "danger")
                return redirect(url_for("users.users"))

            if role in ("supervisor", "technician"):
                if dept not in MAINT_DEPTS:
                    flash("Dept is required for supervisor/technician.", "danger")
                    return redirect(url_for("users.users"))
            else:
                dept = None

            u.full_name = full_name
            u.emp_no = emp_no
            u.role = role
            u.maintenance_dept = dept
            db.session.commit()

            flash("User updated.", "success")
            return redirect(url_for("users.users"))

        elif action == "reset_password":
            user_id = request.form.get("user_id", type=int)
            new_password = request.form.get("new_password") or ""

            if len(new_password) < 4:
                flash("Password must be at least 4 characters.", "danger")
                return redirect(url_for("users.users"))

            u = User.query.get_or_404(user_id)
            u.set_password(new_password)
            db.session.commit()

            flash("Password updated.", "success")
            return redirect(url_for("users.users"))

        elif action == "toggle":
            user_id = request.form.get("user_id", type=int)
            u = User.query.get_or_404(user_id)

            if u.username == "admin":
                flash("Admin user cannot be disabled.", "danger")
                return redirect(url_for("users.users"))

            u.is_active = not u.is_active
            db.session.commit()

            flash("User status updated.", "success")
            return redirect(url_for("users.users"))

        flash("Unknown action.", "danger")
        return redirect(url_for("users.users"))

    # =======================
    # GET
    # =======================
    search = (request.args.get("search") or "").strip()
    role_filter = request.args.get("role") or ""
    dept_filter = request.args.get("dept") or ""

    query = User.query
    if search:
        query = query.filter(
            (User.full_name.ilike(f"%{search}%")) |
            (User.username.ilike(f"%{search}%"))
        )
    if role_filter:
        query = query.filter(User.role == role_filter)
    if dept_filter:
        query = query.filter(User.maintenance_dept == dept_filter)

    users_list = query.order_by(User.created_at.desc()).all()

    return render_template(
        "users.html",
        users=users_list,
        roles=ROLES,
        depts=MAINT_DEPTS,
        search=search,
        role_filter=role_filter,
        dept_filter=dept_filter
    )
