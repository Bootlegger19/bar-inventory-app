from datetime import datetime, timedelta
from functools import wraps

from flask import (Blueprint, flash, redirect, render_template, request,
                   session, url_for)

from models import (db, Bar, Category, ClosingTask, Employee, Item, TaskCompletion)

admin_bp = Blueprint("admin", __name__, template_folder="../templates/admin")

# --- Security settings: change them here, nowhere else ---
PIN_MIN_LENGTH = 4
PIN_MAX_LENGTH = 8
LOCKOUT_THRESHOLD = 5   # failed attempts before locking
LOCKOUT_MINUTES = 5


def get_admin():
    return Employee.query.join(Employee.role).filter_by(name="admin").first()


def validate_new_pin(pin):
    """Return an error message if the PIN is unacceptable, else None."""
    if not pin.isdigit():
        return "PIN must contain digits only."
    if not PIN_MIN_LENGTH <= len(pin) <= PIN_MAX_LENGTH:
        return f"PIN must be {PIN_MIN_LENGTH} to {PIN_MAX_LENGTH} digits long."
    if len(set(pin)) == 1:
        return "PIN can't be a single repeated digit."
    if pin in "0123456789" or pin in "9876543210":
        return "PIN can't be a simple sequence like 1234."
    return None


def register_failed_attempt(admin):
    """Count a wrong PIN. Returns True if this attempt triggered a lockout."""
    admin.failed_attempts += 1
    locked = admin.failed_attempts >= LOCKOUT_THRESHOLD
    if locked:
        admin.failed_attempts = 0
        admin.locked_until = datetime.now() + timedelta(minutes=LOCKOUT_MINUTES)
        session.pop("is_admin", None)
    db.session.commit()
    return locked


def pin_required(view_func):
    @wraps(view_func)
    def wrapper(*args, **kwargs):
        if not session.get("is_admin"):
            return redirect(url_for("admin.login"))
        admin = get_admin()
        if admin and admin.must_change_pin and request.endpoint != "admin.change_pin":
            flash("Please set a new PIN before continuing.")
            return redirect(url_for("admin.change_pin"))
        return view_func(*args, **kwargs)
    return wrapper


@admin_bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        admin = get_admin()
        now = datetime.now()

        if admin and admin.locked_until and admin.locked_until > now:
            minutes_left = int((admin.locked_until - now).total_seconds() // 60) + 1
            flash(f"Too many failed attempts. Try again in {minutes_left} minute(s).")
            return render_template("login.html")

        if admin and admin.check_pin(request.form.get("pin", "")):
            admin.failed_attempts = 0
            admin.locked_until = None
            db.session.commit()
            session["is_admin"] = True
            return redirect(url_for("admin.dashboard"))

        if admin:
            if register_failed_attempt(admin):
                flash(f"Too many failed attempts. Locked for {LOCKOUT_MINUTES} minutes.")
            else:
                left = LOCKOUT_THRESHOLD - admin.failed_attempts
                flash(f"Incorrect PIN. {left} attempt(s) left.")
        else:
            flash("Incorrect PIN.")
    return render_template("login.html")


@admin_bp.route("/logout")
def logout():
    session.pop("is_admin", None)
    return redirect(url_for("admin.login"))


@admin_bp.route("/change-pin", methods=["GET", "POST"])
@pin_required
def change_pin():
    admin = get_admin()
    if request.method == "POST":
        current_pin = request.form.get("current_pin", "")
        new_pin = request.form.get("new_pin", "")
        confirm_pin = request.form.get("confirm_pin", "")

        if not admin.check_pin(current_pin):
            if register_failed_attempt(admin):
                flash(f"Too many failed attempts. Locked for {LOCKOUT_MINUTES} minutes.")
                return redirect(url_for("admin.login"))
            flash("Current PIN is incorrect.")
        elif new_pin != confirm_pin:
            flash("New PIN and confirmation don't match.")
        elif new_pin == current_pin:
            flash("New PIN must be different from the current one.")
        else:
            error = validate_new_pin(new_pin)
            if error:
                flash(error)
            else:
                admin.set_pin(new_pin)
                admin.must_change_pin = False
                db.session.commit()
                flash("PIN updated.")
                return redirect(url_for("admin.dashboard"))
        return redirect(url_for("admin.change_pin"))

    return render_template("change_pin.html", forced=admin.must_change_pin,
                           min_len=PIN_MIN_LENGTH, max_len=PIN_MAX_LENGTH)


@admin_bp.route("/")
@pin_required
def dashboard():
    bar = Bar.query.first()
    categories = Category.query.filter_by(bar_id=bar.id).all()
    tasks = ClosingTask.query.filter_by(bar_id=bar.id).all()
    return render_template("dashboard.html", categories=categories, bar=bar, tasks=tasks)


@admin_bp.route("/add-category", methods=["POST"])
@pin_required
def add_category():
    name = request.form["name"].strip()
    if name:
        db.session.add(Category(name=name, bar_id=Bar.query.first().id))
        db.session.commit()
    return redirect(url_for("admin.dashboard"))


@admin_bp.route("/add-item", methods=["POST"])
@pin_required
def add_item():
    name = request.form["name"].strip()
    category_id = int(request.form["category_id"])
    if name:
        db.session.add(Item(name=name, category_id=category_id))
        db.session.commit()
    return redirect(url_for("admin.dashboard"))


@admin_bp.route("/delete-item/<int:item_id>", methods=["POST"])
@pin_required
def delete_item(item_id):
    item = Item.query.get_or_404(item_id)
    db.session.delete(item)
    db.session.commit()
    return redirect(url_for("admin.dashboard"))


@admin_bp.route("/delete-category/<int:category_id>", methods=["POST"])
@pin_required
def delete_category(category_id):
    category = Category.query.get_or_404(category_id)
    if category.items:
        flash(f"Can't delete '{category.name}' — it still has items in it.")
        return redirect(url_for("admin.dashboard"))
    db.session.delete(category)
    db.session.commit()
    return redirect(url_for("admin.dashboard"))


@admin_bp.route("/add-task", methods=["POST"])
@pin_required
def add_task():
    description = request.form["description"].strip()
    if description:
        db.session.add(ClosingTask(bar_id=Bar.query.first().id, description=description))
        db.session.commit()
    return redirect(url_for("admin.dashboard"))


@admin_bp.route("/delete-task/<int:task_id>", methods=["POST"])
@pin_required
def delete_task(task_id):
    task = ClosingTask.query.get_or_404(task_id)
    TaskCompletion.query.filter_by(task_id=task.id).delete()
    db.session.delete(task)
    db.session.commit()
    return redirect(url_for("admin.dashboard"))