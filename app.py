from flask import Flask, render_template, request, redirect, url_for
from models import db, Category, Item

app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///inventory.db"
db.init_app(app)

with app.app_context():
    db.create_all()
    if Category.query.count() == 0:
        for name in ["Spirits", "Liqueurs", "Beer", "Cider"]:
            db.session.add(Category(name=name))
        db.session.commit()

@app.route("/")
def home():
    categories = Category.query.all()
    return render_template("items.html", categories=categories)

@app.route("/add-item", methods=["POST"])
def add_item():
    name = request.form["name"].strip()
    category_id = int(request.form["category_id"])
    if name:
        db.session.add(Item(name=name, category_id=category_id))
        db.session.commit()
    return redirect(url_for("home"))

if __name__ == "__main__":
    app.run(debug=True)