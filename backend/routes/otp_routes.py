# =============================================================================
# routes/otp_routes.py
# Handles all OTP-based flows:
#   - Register with OTP  (/api/register/send-otp, /api/register/verify-otp)
#   - Forgot Password    (/api/forgot-password/send-otp, verify-otp, reset)
#   - Forgot Username    (/api/forgot-username/send-otp, verify-otp)
# =============================================================================

import re
from flask import Blueprint, request, jsonify
from werkzeug.security import generate_password_hash    # For hashing passwords
from database import get_connection
from utils.otp_helper import (  
    make_otp, send_sms,
    store_otp, verify_otp, consume_otp,
    issue_reset_token, verify_reset_token, consume_reset_token,
)

otp_bp = Blueprint("otp", __name__)



# =============================================================================
# REGISTER WITH OTP
# =============================================================================



##-------  Send OTP and store registration data -------##

@otp_bp.route("/api/register/send-otp", methods=["POST"])   # Send OTP for registration
def reg_send_otp():
    """
    Step 1: Validate fields, check for duplicates, send OTP to mobile.  
    Body: { username, mobile, password }
    """
    data     = request.json or {}
    username = data.get("username", "").strip()
    mobile   = data.get("mobile",   "").strip()
    password = data.get("password", "")

    # Validate inputs
    if not username or not mobile or not password:
        return jsonify({"error": "All fields are required"}), 400
    if len(username) < 3 or not re.match(r"^[a-zA-Z0-9_]+$", username):
        return jsonify({"error": "Username: min 3 chars, letters/numbers/underscores only"}), 400
    if not mobile.isdigit() or len(mobile) != 10:
        return jsonify({"error": "Mobile must be exactly 10 digits"}), 400
    if len(password) < 4:
        return jsonify({"error": "Password must be at least 4 characters"}), 400


    # Check for existing username or mobile before sending SMS
    conn   = get_connection()   # Open DB
    cursor = conn.cursor()  # Create cursor for DB operations
    cursor.execute("SELECT id FROM users WHERE username=?", (username,))
    if cursor.fetchone():
        conn.close()
        return jsonify({"error": "Username already taken"}), 400
    cursor.execute("SELECT id FROM users WHERE mobile=?", (mobile,))
    if cursor.fetchone():
        conn.close()
        return jsonify({"error": "Mobile number already registered"}), 400
    conn.close()

    # Generate and store OTP (10-minute expiry), carry registration data
    otp = make_otp()
    store_otp("reg_" + mobile, otp, ttl_seconds=600,
              username=username, mobile=mobile, password=password)

    ok, err = send_sms(mobile, otp)
    if not ok:
        print(f"[REG OTP] SMS failed: {err}")
        print(f"[REG OTP] *** DEV OTP for {mobile}: {otp} ***")
        return jsonify({"message": "OTP ready", "dev": True}), 200

    print(f"[REG OTP] Sent OTP to {mobile}")
    return jsonify({"message": "OTP sent to your mobile number"}), 200  # OTP sent successfully




##-------  Verify OTP and create account -------##

@otp_bp.route("/api/register/verify-otp", methods=["POST"]) # Verify OTP and create account
def reg_verify_otp():
    """
    Step 2: Verify OTP and create the account.
    Body: { mobile, otp }
    """
    data   = request.json or {}
    mobile = data.get("mobile", "").strip()
    otp    = data.get("otp",    "").strip()

    ok, err, stored = verify_otp("reg_" + mobile, otp)
    if not ok:
        return jsonify({"error": err}), 400

    username = stored["username"]
    password = stored["password"]
    consume_otp("reg_" + mobile)

    # Re-check uniqueness (guard against race condition)
    conn   = get_connection()   # Open DB
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM users WHERE username=?", (username,))
    if cursor.fetchone():
        conn.close()    
        return jsonify({"error": "Username was just taken. Go back and choose another."}), 400
    cursor.execute("SELECT id FROM users WHERE mobile=?", (mobile,))
    if cursor.fetchone():
        conn.close()
        return jsonify({"error": "Mobile number was just registered."}), 400


    try:    # Create the user account in DB
        cursor.execute( 
            "INSERT INTO users (username, display_name, password, mobile) VALUES (?,?,?,?)",
            (username, username, generate_password_hash(password), mobile)
        )
        conn.commit()   # Save changes to DB

    except Exception as e:  # Handle DB errors
        conn.close()
        return jsonify({"error": "Account creation failed: " + str(e)}), 400
    conn.close()

    print(f"[REG] Account created: {username} / {mobile}")
    return jsonify({"message": "Account created successfully"}), 201


# =============================================================================
# FORGOT PASSWORD — 3-step flow
# =============================================================================

@otp_bp.route("/api/forgot-password/send-otp", methods=["POST"])
def fp_send_otp():
    """
    Step 1: Verify mobile is registered, send OTP.
    Body: { mobile }
    """
    data   = request.json or {}
    mobile = data.get("mobile", "").strip()

    if not mobile.isdigit() or len(mobile) != 10:
        return jsonify({"error": "Enter a valid 10-digit mobile number"}), 400

    conn   = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM users WHERE mobile=?", (mobile,))
    if not cursor.fetchone():
        conn.close()
        return jsonify({"error": "No account found with this mobile number"}), 404
    conn.close()

    otp = make_otp()
    store_otp(mobile, otp, ttl_seconds=600)

    ok, err = send_sms(mobile, otp)
    if not ok:
        print(f"[FP OTP] SMS failed: {err}")
        print(f"[FP OTP] *** DEV OTP for {mobile}: {otp} ***")
        return jsonify({"message": "OTP ready", "dev": True}), 200

    print(f"[FP OTP] Sent OTP to {mobile}")
    return jsonify({"message": "OTP sent to your mobile number"}), 200

# Verify OTP and reset password.

@otp_bp.route("/api/forgot-password/verify-otp", methods=["POST"])
def fp_verify_otp():
    """
    Step 2: Verify OTP, issue a short-lived reset token.
    Body: { mobile, otp }
    Returns: { reset_token }
    """
    data   = request.json or {}
    mobile = data.get("mobile", "").strip()
    otp    = data.get("otp",    "").strip()

    ok, err, _ = verify_otp(mobile, otp)
    if not ok:
        return jsonify({"error": err}), 400

    consume_otp(mobile)
    reset_token = issue_reset_token(mobile, ttl_seconds=300)  # 5-min window

    return jsonify({"message": "OTP verified", "reset_token": reset_token}), 200




@otp_bp.route("/api/forgot-password/reset", methods=["POST"])
def fp_reset_password():
    """
    Step 3: Use the reset token to set a new password.
    Body: { reset_token, new_password }
    """
    data         = request.json or {}
    reset_token  = data.get("reset_token",  "").strip()
    new_password = data.get("new_password", "")

    if not reset_token or not new_password:
        return jsonify({"error": "Missing required fields"}), 400
    if len(new_password) < 4:
        return jsonify({"error": "Password must be at least 4 characters"}), 400

    ok, err, mobile = verify_reset_token(reset_token) # Verify the reset token and get the associated mobile number.
    if not ok:
        return jsonify({"error": err}), 400 

    conn   = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE users SET password=? WHERE mobile=?",
        (generate_password_hash(new_password), mobile)
    )
    conn.commit()
    conn.close()
    consume_reset_token(reset_token)

    print(f"[FP] Password reset for mobile: {mobile}")
    return jsonify({"message": "Password reset successfully"}), 200


# =============================================================================
# FORGOT USERNAME — 2-step flow
# =============================================================================

@otp_bp.route("/api/forgot-username/send-otp", methods=["POST"])
def fu_send_otp():
    """
    Step 1: Verify mobile is registered, send OTP.
    Body: { mobile }
    """
    data   = request.json or {}
    mobile = data.get("mobile", "").strip()

    if not mobile.isdigit() or len(mobile) != 10:
        return jsonify({"error": "Enter a valid 10-digit mobile number"}), 400

    conn   = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM users WHERE mobile=?", (mobile,))
    if not cursor.fetchone():
        conn.close()
        return jsonify({"error": "No account found with this mobile number"}), 404
    conn.close()

    otp = make_otp()
    store_otp("fu_" + mobile, otp, ttl_seconds=600)

    ok, err = send_sms(mobile, otp)
    if not ok:
        print(f"[FU OTP] SMS failed: {err}")
        print(f"[FU OTP] *** DEV OTP for {mobile}: {otp} ***")
        return jsonify({"message": "OTP ready", "dev": True}), 200

    print(f"[FU OTP] Sent OTP to {mobile}")
    return jsonify({"message": "OTP sent to your mobile number"}), 200
 

 
# Verify OTP and return the username.

@otp_bp.route("/api/forgot-username/verify-otp", methods=["POST"])
def fu_verify_otp():
    """
    Step 2: Verify OTP and return the username.
    Body: { mobile, otp }
    Returns: { username }
    """
    data   = request.json or {}
    mobile = data.get("mobile", "").strip()
    otp    = data.get("otp",    "").strip()

    ok, err, _ = verify_otp("fu_" + mobile, otp)
    if not ok:
        return jsonify({"error": err}), 400

    consume_otp("fu_" + mobile)

    conn   = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT username FROM users WHERE mobile=?", (mobile,))
    row = cursor.fetchone()
    conn.close()

    if not row:
        return jsonify({"error": "Account not found"}), 404

    print(f"[FU] Username retrieved for mobile: {mobile}")
    return jsonify({"message": "Verified", "username": row["username"]}), 200