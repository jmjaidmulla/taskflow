# =============================================================================
# routes/auth_routes.py
# Handles: /api/login, /api/register (legacy direct register)
# =============================================================================

from flask import Blueprint, request, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from flask_jwt_extended import create_access_token
from database import get_connection

auth_bp = Blueprint("auth", __name__)


@auth_bp.route("/api/login", methods=["POST"])
def login():
    """
    POST /api/login
    Body: { "username": "...", "password": "..." }
    Returns: JWT access token + user profile fields
    """
    data = request.json
    if not data:
        return jsonify({"error": "No data provided"}), 400

    username = data.get("username", "").strip()
    password = data.get("password", "")

    if not username or not password:
        return jsonify({"error": "Username and password are required"}), 400

    conn   = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE username=?", (username,))
    user = cursor.fetchone()
    conn.close()

    if not user:
        print(f"[LOGIN] No user found: '{username}'")
        return jsonify({"error": "Invalid username or password"}), 401

    if not check_password_hash(user["password"], password):
        print(f"[LOGIN] Wrong password for: '{username}'")
        return jsonify({"error": "Invalid username or password"}), 401

    print(f"[LOGIN] Success: '{username}'")
    access_token = create_access_token(identity=str(user["id"]))

    return jsonify({
        "message":       "Login successful",
        "access_token":  access_token,
        "username":      user["username"],
        "display_name":  user["display_name"]  or username,
        "mobile":        user["mobile"]         or "",
        "profile_image": user["profile_image"]  or "",
    })