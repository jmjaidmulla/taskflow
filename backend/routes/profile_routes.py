# =============================================================================
# routes/profile_routes.py
# Handles: GET/PUT /api/profile, DELETE /api/account
# All routes require a valid JWT token.
# =============================================================================

import re
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from werkzeug.security import generate_password_hash, check_password_hash
from database import get_connection

profile_bp = Blueprint("profile", __name__)


@profile_bp.route("/api/profile", methods=["GET"])
@jwt_required()
def get_profile():
    """
    GET /api/profile
    Returns the logged-in user's profile data.
    """
    user_id = get_jwt_identity()
    conn    = get_connection()
    cursor  = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE id=?", (user_id,))
    user = cursor.fetchone()
    conn.close()

    if not user:
        return jsonify({"error": "User not found"}), 404

    return jsonify({
        "username":      user["username"],
        "display_name":  user["display_name"]  or user["username"],
        "mobile":        user["mobile"]         or "",
        "profile_image": user["profile_image"]  or "",
        "created_at":    user["created_at"],
    })



# Update profile fields. All fields optional.

@profile_bp.route("/api/profile", methods=["PUT"])
@jwt_required()
def update_profile():
    """
    PUT /api/profile
    Body (all fields optional):
      username, display_name, mobile,
      current_password + new_password (pair required to change password),
      profile_image (base64 data URL or "" to remove)
    Returns: updated profile fields
    """
    user_id = get_jwt_identity()
    data    = request.json

    if not data:
        return jsonify({"error": "No data provided"}), 400

    conn   = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE id=?", (user_id,))
    user = cursor.fetchone()

    if not user:
        conn.close()
        return jsonify({"error": "User not found"}), 404

    updates = []
    params  = []

    # ── Username ─────────────────────────────────────────────────────────────
    new_username = data.get("username", "").strip()
    if new_username:
        if len(new_username) < 3 or not re.match(r"^[a-zA-Z0-9_]+$", new_username):
            conn.close()
            return jsonify({"error": "Username: min 3 chars, letters/numbers/underscores only"}), 400
            
        cursor.execute("SELECT id FROM users WHERE username=? AND id!=?", (new_username, user_id))
        if cursor.fetchone():
            conn.close()
            return jsonify({"error": "Username already taken"}), 400
        updates.append("username=?"); params.append(new_username)

    # ── Display name ──────────────────────────────────────────────────────────
    display_name = data.get("display_name", "").strip()
    if display_name:
        updates.append("display_name=?"); params.append(display_name)

    # ── Mobile ────────────────────────────────────────────────────────────────
    mobile = data.get("mobile", "").strip()
    if mobile:
        if not mobile.isdigit() or len(mobile) != 10:
            conn.close()
            return jsonify({"error": "Mobile must be exactly 10 digits"}), 400
        cursor.execute("SELECT id FROM users WHERE mobile=? AND id!=?", (mobile, user_id))
        if cursor.fetchone():
            conn.close()
            return jsonify({"error": "Mobile already used by another account"}), 400
        updates.append("mobile=?"); params.append(mobile)

    # ── Password change ───────────────────────────────────────────────────────
    new_password = data.get("new_password", "")
    if new_password:
        current_password = data.get("current_password", "")
        if not current_password:
            conn.close()
            return jsonify({"error": "Current password required"}), 400
        if not check_password_hash(user["password"], current_password):
            conn.close()
            return jsonify({"error": "Current password is incorrect"}), 401
        if len(new_password) < 4:
            conn.close()
            return jsonify({"error": "New password must be at least 4 characters"}), 400
        updates.append("password=?"); params.append(generate_password_hash(new_password))

    # ── Profile image ─────────────────────────────────────────────────────────
    profile_image = data.get("profile_image", None)
    if profile_image is not None:
        if profile_image != "" and not profile_image.startswith("data:image/"):
            conn.close()
            return jsonify({"error": "Invalid image format"}), 400
        if len(profile_image) > 3_000_000: 
            conn.close()
            return jsonify({"error": "Image too large. Max ~2MB."}), 400
        updates.append("profile_image=?"); params.append(profile_image)

    if not updates:
        conn.close()
        return jsonify({"error": "No fields to update"}), 400

    params.append(user_id)
    cursor.execute(f"UPDATE users SET {', '.join(updates)} WHERE id=?", params)
    conn.commit()

    cursor.execute("SELECT * FROM users WHERE id=?", (user_id,))
    updated = cursor.fetchone()
    conn.close()

    return jsonify({
        "message":       "Profile updated successfully",
        "username":      updated["username"],
        "display_name":  updated["display_name"] or updated["username"],
        "mobile":        updated["mobile"]        or "",
        "profile_image": updated["profile_image"] or "",
    })


# delete account permanently and all associated tasks. Requires password confirmation.

@profile_bp.route("/api/account", methods=["DELETE"]) # Delete account route
@jwt_required()
def delete_account():
    """
    DELETE /api/account
    Body: { "password": "..." }
    Permanently deletes the user and all their tasks.
    """
    user_id = get_jwt_identity()
    data    = request.json

    if not data or not data.get("password"):
        return jsonify({"error": "Password confirmation is required"}), 400

    conn   = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE id=?", (user_id,))
    user = cursor.fetchone()

    if not user:
        conn.close()
        return jsonify({"error": "User not found"}), 404

    if not check_password_hash(user["password"], data["password"]):
        conn.close()
        return jsonify({"error": "Incorrect password"}), 401

    cursor.execute("DELETE FROM tasks WHERE user_id=?", (user_id,))
    cursor.execute("DELETE FROM users WHERE id=?", (user_id,))
    conn.commit()
    conn.close()

    return jsonify({"message": "Account permanently deleted"})


# =============================================================================
# MOBILE OTP VERIFICATION
# Two-step: send OTP → verify OTP (which also saves the new mobile in the DB)
# =============================================================================

import random # For generating OTPs
import time # For OTP expiration timing

_mob_otp_store = {}   # "uid_mobile" → { otp, expires_at }


@profile_bp.route("/api/profile/mobile/send-otp", methods=["POST"])
@jwt_required()
def profile_mobile_send_otp():
    """
    POST /api/profile/mobile/send-otp
    Body: { "mobile": "9876543210" }
    Validates the number is not already taken, then sends a 6-digit OTP via SMS.
    """
    from utils.otp_helper import make_otp, send_sms

    user_id = get_jwt_identity()
    data    = request.json or {}
    mobile  = data.get("mobile", "").strip()

    if not mobile.isdigit() or len(mobile) != 10:
        return jsonify({"error": "Enter a valid 10-digit mobile number"}), 400

    # Ensure number is not already used by another account
    conn   = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM users WHERE mobile=? AND id!=?", (mobile, user_id))
    if cursor.fetchone():
        conn.close()
        return jsonify({"error": "This mobile number is already registered to another account"}), 400
    conn.close()

    otp = make_otp()
    _mob_otp_store[user_id + "_" + mobile] = {
        "otp":        otp,
        "expires_at": time.time() + 600,    # 10 minutes
    }

    ok, err = send_sms(mobile, otp)
    if not ok:
        print(f"[MOB OTP] SMS failed: {err}")
        print(f"[MOB OTP] *** DEV OTP for {mobile}: {otp} ***")
        return jsonify({"message": "OTP ready", "dev": True}), 200

    print(f"[MOB OTP] Sent to {mobile}")
    return jsonify({"message": "OTP sent to your mobile number"}), 200



@profile_bp.route("/api/profile/mobile/verify-otp", methods=["POST"])
@jwt_required()
def profile_mobile_verify_otp():
    """
    POST /api/profile/mobile/verify-otp
    Body: { "mobile": "9876543210", "otp": "123456" }
    Verifies OTP and immediately saves the new mobile in the database.
    """
    user_id = get_jwt_identity()
    data    = request.json or {}
    mobile  = data.get("mobile", "").strip()
    otp     = data.get("otp",    "").strip()

    key    = user_id + "_" + mobile
    stored = _mob_otp_store.get(key)

    if not stored:
        return jsonify({"error": "OTP expired or not sent. Click Send OTP again."}), 400
    if time.time() > stored["expires_at"]:
        del _mob_otp_store[key]
        return jsonify({"error": "OTP has expired. Click Send OTP again."}), 400
    if stored["otp"] != otp:
        return jsonify({"error": "Incorrect OTP. Please try again."}), 400

    # OTP correct — save new mobile to DB
    del _mob_otp_store[key]
    conn   = get_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET mobile=? WHERE id=?", (mobile, user_id))
    conn.commit()
    conn.close()

    print(f"[MOB OTP] Mobile updated: user {user_id} → {mobile}")
    return jsonify({"message": "Mobile number verified and updated", "mobile": mobile}), 200