from datetime import datetime
from decimal import Decimal, InvalidOperation

from flask import (Blueprint, flash, jsonify, redirect, render_template,
                   request, session, url_for)

from models import (db, Category, ClosingTask, CashCount, Count, Employee,
                    InventorySession, TaskCompletion)

employee_bp = Blueprint("employee", __name__, template_folder="../templates/employee")

# (label shown on screen, value in dollars). Edit this list to change currency.
DENOMINATIONS = [
    ("Bills", [("$100", "100"), ("$50", "50"), ("$20", "20"), ("$10", "10"), ("$5", "5")]),
    ("Coins", [("$2", "2"), ("$1", "1"), ("25¢", "0.25"), ("10¢", "0.10"), ("5¢", "0.05")]),
]


def get_current_session():
    """Return the closing session this browser is working on, or None."""
    session_id = session.get("inventory_session_id")
    if not session_id:
        return None
    return db.session.get(InventorySession, session_id)


@employee_bp.route("/")
def home():
    categories = Category.query.all()
    return render_template("items.html", categories=categories)


@employee_bp.route("/start-closing", methods=["GET", "POST"])
def start_closing():
    if request.method == "POST":
        employee = db.session.get(Employee, int(request.form["employee_id"]))
        if not employee:
            flash("Please select your name before starting.")
            return redirect(url_for("employee.start_closing"))
        new_session = InventorySession(bar_id=employee.bar_id, employee_id=employee.id)
        db.session.add(new_session)
        db.session.commit()
        session["inventory_session_id"] = new_session.id
        return redirect(url_for("employee.closing_hub"))

    employees = Employee.query.all()
    return render_template("start_closing.html", employees=employees)


@employee_bp.route("/closing")
def closing_hub():
    current = get_current_session()
    if not current:
        return redirect(url_for("employee.start_closing"))
    return render_template(
        "closing_hub.html",
        current=current,
        inventory_count=len(current.counts),
        cash=CashCount.query.filter_by(session_id=current.id).first(),
        total_tasks=ClosingTask.query.filter_by(bar_id=current.bar_id).count(),
        done_tasks=TaskCompletion.query.filter_by(session_id=current.id).count(),
    )


@employee_bp.route("/inventory-check")
def inventory_check():
    current = get_current_session()
    if not current:
        return redirect(url_for("employee.start_closing"))

    categories = Category.query.filter_by(bar_id=current.bar_id).all()

    previous = (
        InventorySession.query
        .filter_by(bar_id=current.bar_id, status="completed")
        .filter(InventorySession.id != current.id)
        .order_by(InventorySession.completed_at.desc())
        .first()
    )
    last_counts = {c.item_id: c.quantity for c in previous.counts} if previous else {}
    current_counts = {c.item_id: c.quantity for c in current.counts}

    return render_template(
        "inventory_check.html",
        categories=categories,
        last_counts=last_counts,
        current_counts=current_counts,
    )


@employee_bp.route("/submit-count-ajax", methods=["POST"])
def submit_count_ajax():
    current = get_current_session()
    if not current:
        return jsonify(success=False, error="No closing in progress"), 400
    try:
        item_id = int(request.form["item_id"])
        quantity = int(request.form["quantity"])
    except (KeyError, ValueError):
        return jsonify(success=False, error="Enter a whole number"), 400
    if quantity < 0:
        return jsonify(success=False, error="Count can't be negative"), 400

    existing = Count.query.filter_by(session_id=current.id, item_id=item_id).first()
    if existing:
        existing.quantity = quantity
    else:
        db.session.add(Count(session_id=current.id, item_id=item_id, quantity=quantity))
    db.session.commit()
    return jsonify(success=True)


@employee_bp.route("/cash-count", methods=["GET", "POST"])
def cash_count():
    current = get_current_session()
    if not current:
        return redirect(url_for("employee.start_closing"))
    existing = CashCount.query.filter_by(session_id=current.id).first()

    if request.method == "POST":
        total = Decimal("0")
        for _, group in DENOMINATIONS:
            for label, value in group:
                raw = request.form.get(f"d_{value}", "").strip() or "0"
                try:
                    quantity = int(raw)
                except ValueError:
                    flash(f"{label}: enter a whole number.")
                    return redirect(url_for("employee.cash_count"))
                if quantity < 0:
                    flash(f"{label}: can't be negative.")
                    return redirect(url_for("employee.cash_count"))
                total += Decimal(value) * quantity

        tip_raw = request.form.get("tip_pool", "").strip()
        try:
            tip = Decimal(tip_raw) if tip_raw else None
        except InvalidOperation:
            flash("Tip pool must be a number, like 42.50.")
            return redirect(url_for("employee.cash_count"))

        if existing:
            existing.total = total
            existing.tip_pool_total = tip
        else:
            db.session.add(CashCount(session_id=current.id, total=total, tip_pool_total=tip))
        db.session.commit()
        return redirect(url_for("employee.closing_hub"))

    return render_template("cash_count.html", denominations=DENOMINATIONS, existing=existing)


@employee_bp.route("/closing-tasks", methods=["GET", "POST"])
def closing_tasks():
    current = get_current_session()
    if not current:
        return redirect(url_for("employee.start_closing"))
    tasks = ClosingTask.query.filter_by(bar_id=current.bar_id).all()

    if request.method == "POST":
        checked_ids = {int(task_id) for task_id in request.form.getlist("task_ids")}
        TaskCompletion.query.filter_by(session_id=current.id).delete()
        for task in tasks:
            if task.id in checked_ids:
                db.session.add(TaskCompletion(session_id=current.id, task_id=task.id))
        db.session.commit()
        return redirect(url_for("employee.closing_hub"))

    done_ids = {tc.task_id for tc in TaskCompletion.query.filter_by(session_id=current.id)}
    return render_template("closing_tasks.html", tasks=tasks, done_ids=done_ids)


@employee_bp.route("/finish-closing", methods=["POST"])
def finish_closing():
    current = get_current_session()
    if not current:
        return redirect(url_for("employee.start_closing"))
    if not current.counts:
        flash("Enter at least one inventory count before finishing.")
        return redirect(url_for("employee.closing_hub"))

    current.status = "completed"
    current.completed_at = datetime.now()
    db.session.commit()
    session.pop("inventory_session_id", None)
    flash("Closing submitted. Good night!")
    return redirect(url_for("employee.home"))