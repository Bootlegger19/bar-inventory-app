from functools import wraps
from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from models import db, Category, Item, Bar, Employee, ClosingTask, TaskCompletion

admin_bp = Blueprint("admin", __name__, template_folder="../templates/admin")

@admin_bp.after_request
def add_no_cache_headers(response):
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate"
    response.headers["Pragma"] = "no-cache"
    return response

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
    tasks = ClosingTask.query.filter_by(bar_id=bar.id).all()
    return render_template("dashboard.html", categories=categories, bar=bar, tasks=tasks)


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


@admin_bp.route("/add-category", methods=["POST"])
@pin_required
def add_category():
    name = request.form["name"].strip()
    bar = Bar.query.first()
    if name:
        db.session.add(Category(name=name, bar_id=bar.id))
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