from flask import Flask, render_template
import razorpay
from extensions import db, bcrypt, mail, login_manager
from models import User
from routes.users import users_bp
from routes.events import events_bp
from routes.bookings import bookings_bp
from config import Config
import os

def create_app():
    app = Flask(__name__, template_folder='templates', static_folder='static')
    app.config.from_object(Config)

    # Razorpay client
    app.razorpay_client = razorpay.Client(
        auth=(app.config["RAZORPAY_KEY_ID"], app.config["RAZORPAY_KEY_SECRET"])
    )

    # Initialize extensions
    db.init_app(app)
    bcrypt.init_app(app)
    mail.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = "users.login"

    # User loader
    @login_manager.user_loader
    def load_user(user_id):
        return db.session.get(User, int(user_id))

    # Register blueprints
    app.register_blueprint(users_bp, url_prefix="/users")
    app.register_blueprint(events_bp, url_prefix="/events")
    app.register_blueprint(bookings_bp, url_prefix="/bookings")
    
    # --- Frontend routes ---
    @app.route("/")
    def home():
        return render_template("index.html")

    @app.route("/login.html")
    def login_page():
        return render_template("login.html")

    @app.route("/register.html")
    def register_page():
        return render_template("register.html")

    @app.route("/dashboard.html")
    def dashboard_page():
        return render_template("dashboard.html")

    @app.route("/booking.html")
    def booking_page():
        return render_template("booking.html")

    @app.route("/organizer.html")
    def organizer_page():
        return render_template("organizer.html")
    
    @app.route("/create_event.html")
    def create_event_page():
        return render_template("create_event.html")

    @app.route("/event_bookings.html")
    def event_bookings_page():
        return render_template("event_bookings.html")

    @app.route("/edit_event.html")
    def edit_event_page():
        return render_template("edit_event.html")
    
    @app.route("/tickets.html")
    def tickets_page():
        return render_template("tickets.html")
    
    # Create tables
    with app.app_context():
        db.create_all()

    return app

if __name__ == "__main__":
    app = create_app()
    app.run(debug=True)