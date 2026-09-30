from flask import Flask
from models import db, Bar, Category

app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///inventory.db"
db.init_app(app)

with app.app_context():
    db.create_all()
    if Bar.query.count() == 0:
        bar = Bar(name="Main Bar")
        db.session.add(bar)
        db.session.commit()
        for name in ["Spirits", "Liqueurs", "Beer", "Cider"]:
            db.session.add(Category(name=name, bar_id=bar.id))
        db.session.commit()

from routes.employee import employee_bp
app.register_blueprint(employee_bp)

if __name__ == "__main__":
    app.run(debug=True)