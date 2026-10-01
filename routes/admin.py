from functools import wraps
from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from models import db, Category, Item, Bar, Employee

admin_bp = Blueprint("admin", __name__, template_folder="../templates/admin")


def pin_required(view_func):
    @wraps(view_func)
    def wrapper(*args, **kwargs):
        if not session.get("is_admin"):
            return redirect(url_for("admin.login"))
        return view_func(*args, **kwargs)
    return wrapper


@admin_bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        pin = request.form.get("pin", "")
        admin = Employee.query.join(Employee.role).filter_by(name="admin").first()
        if admin and admin.check_pin(pin):
            session["is_admin"] = True
            return redirect(url_for("admin.dashboard"))
        flash("Incorrect PIN")
    return render_template("login.html")


@admin_bp.route("/logout")
def logout():
    session.pop("is_admin", None)
    return redirect(url_for("admin.login"))


@admin_bp.route("/")
@pin_required
def dashboard():
    bar = Bar.query.first()
    categories = Category.query.filter_by(bar_id=bar.id).all()
    return render_template("dashboard.html", categories=categories, bar=bar)


@admin_bp.route("/add-category", methods=["POST"])
@pin_required
def add_category():
    name = request.form["name"].strip()
    bar = Bar.query.first()
    if name:
        db.session.add(Category(name=name, bar_id=bar.id))
        db.session.commit()
    return redirect(url_for("admin.dashboard"))