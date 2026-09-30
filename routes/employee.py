from flask import Blueprint, render_template, request, redirect, url_for
from models import db, Category, Item

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