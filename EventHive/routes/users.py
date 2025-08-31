from flask import Blueprint, request, jsonify
from extensions import db, bcrypt
from models import User
from flask_login import login_user as flask_login_user, logout_user, current_user, login_required

users_bp = Blueprint("users", __name__)

# ----------------- Register User -----------------
@users_bp.route("/register", methods=["POST"])
def register_user():
    data = request.json
    name = data.get("name")
    email = data.get("email")
    phone = data.get("phone")
    password = data.get("password")
    role = data.get("role", "attendee")

    # Check if user already exists
    if User.query.filter_by(email=email).first():
        return jsonify({"error": "Email already registered"}), 400
    if User.query.filter_by(phone=phone).first():
        return jsonify({"error": "Phone already registered"}), 400

    # Hash password
    hashed_pw = bcrypt.generate_password_hash(password).decode("utf-8")

    # Create user
    new_user = User(name=name, email=email, phone=phone, password=hashed_pw, role=role)
    db.session.add(new_user)
    db.session.commit()

    return jsonify({"message": "User registered successfully", "user_id": new_user.id}), 201

# ----------------- Login User -----------------
@users_bp.route("/login", methods=["POST"])
def login():
    data = request.json
    email = data.get("email")
    password = data.get("password")

    user = User.query.filter_by(email=email).first()
    if not user:
        return jsonify({"error": "User not found"}), 404

    if not bcrypt.check_password_hash(user.password, password):
        return jsonify({"error": "Invalid password"}), 401

    # Create login session
    flask_login_user(user)

    return jsonify({
        "message": "Login successful",
        "user_id": user.id,
        "name": user.name,
        "role": user.role
    })

# ----------------- Logout User -----------------
@users_bp.route("/logout", methods=["POST"])
@login_required
def logout():
    logout_user()
    return jsonify({"message": "Logged out successfully"})

# ----------------- Get Current User Profile -----------------
@users_bp.route("/profile", methods=["GET"])
@login_required
def profile():
    return jsonify({
        "user_id": current_user.id,
        "name": current_user.name,
        "email": current_user.email,
        "phone": current_user.phone,
        "role": current_user.role
    })

# ----------------- Get User by ID -----------------
@users_bp.route("/<int:user_id>", methods=["GET"])
def get_user(user_id):
    user = User.query.get(user_id)
    if not user:
        return jsonify({"error": "User not found"}), 404

    return jsonify({
        "user_id": user.id,
        "name": user.name,
        "email": user.email,
        "phone": user.phone,
        "role": user.role
    })