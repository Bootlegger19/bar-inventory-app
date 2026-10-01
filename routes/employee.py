from flask import Blueprint, render_template, request, redirect, url_for, session
from models import db, Category, Item, Employee, InventorySession, Count
from datetime import datetime

employee_bp = Blueprint("employee", __name__, template_folder="../templates/employee")


@employee_bp.route("/")
def home():
    categories = Category.query.all()
    return render_template("items.html", categories=categories)


@employee_bp.route("/add-item", methods=["POST"])
def add_item():
    name = request.form["name"].strip()
    category_id = int(request.form["category_id"])
    if name:
        db.session.add(Item(name=name, category_id=category_id))
        db.session.commit()
    return redirect(url_for("employee.home"))


@employee_bp.route("/start-closing", methods=["GET", "POST"])
def start_closing():
    if request.method == "POST":
        employee_id = int(request.form["employee_id"])
        employee = Employee.query.get(employee_id)
        new_session = InventorySession(bar_id=employee.bar_id, employee_id=employee_id)
        db.session.add(new_session)
        db.session.commit()
        session["inventory_session_id"] = new_session.id
        return redirect(url_for("employee.inventory_check"))

    employees = Employee.query.all()
    return render_template("start_closing.html", employees=employees)


@employee_bp.route("/inventory-check")
def inventory_check():
    session_id = session.get("inventory_session_id")
    if not session_id:
        return redirect(url_for("employee.start_closing"))

    current_session = InventorySession.query.get(session_id)
    categories = Category.query.filter_by(bar_id=current_session.bar_id).all()

    last_counts = {}
    previous_session = (
        InventorySession.query
        .filter_by(bar_id=current_session.bar_id, status="completed")
        .filter(InventorySession.id != session_id)
        .order_by(InventorySession.completed_at.desc())
        .first()
    )
    if previous_session:
        for c in previous_session.counts:
            last_counts[c.item_id] = c.quantity

    current_counts = {c.item_id: c.quantity for c in current_session.counts}

    return render_template(
        "inventory_check.html",
        categories=categories,
        last_counts=last_counts,
        current_counts=current_counts,
    )


@employee_bp.route("/submit-count", methods=["POST"])
def submit_count():
    session_id = session.get("inventory_session_id")
    item_id = int(request.form["item_id"])
    quantity = int(request.form["quantity"])

    existing = Count.query.filter_by(session_id=session_id, item_id=item_id).first()
    if existing:
        existing.quantity = quantity
    else:
        db.session.add(Count(session_id=session_id, item_id=item_id, quantity=quantity))
    db.session.commit()
    return redirect(url_for("employee.inventory_check"))


@employee_bp.route("/complete-inventory", methods=["POST"])
def complete_inventory():
    session_id = session.get("inventory_session_id")
    current_session = InventorySession.query.get(session_id)
    current_session.status = "completed"
    current_session.completed_at = datetime.utcnow()
    db.session.commit()
    session.pop("inventory_session_id", None)
    return redirect(url_for("employee.home"))