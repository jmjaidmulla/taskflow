from flask import Flask, request, jsonify, make_response
from flask_cors import CORS
from database import init_db, get_connection
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import timedelta
from flask_jwt_extended import (
    JWTManager, create_access_token, jwt_required, get_jwt_identity
)

app = Flask(__name__)

CORS(app)

app.config["JWT_SECRET_KEY"]           = "super-secret-taskflow-key-2024"
app.config["JWT_ACCESS_TOKEN_EXPIRES"] = timedelta(days=30)
app.config["JWT_ALGORITHM"]            = "HS256"
app.config["JWT_TOKEN_LOCATION"]       = ["headers"]
app.config["JWT_HEADER_NAME"]          = "Authorization"
app.config["JWT_HEADER_TYPE"]          = "Bearer"

jwt = JWTManager(app)

@app.after_request
def add_cors_headers(response):
    response.headers["Access-Control-Allow-Origin"]  = "*"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, PATCH, DELETE, OPTIONS"
    return response

@app.route("/api/<path:path>", methods=["OPTIONS"])
def options_handler(path):
    response = make_response()
    response.headers["Access-Control-Allow-Origin"]  = "*"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, PATCH, DELETE, OPTIONS"
    return response, 200

@jwt.unauthorized_loader
def unauthorized_callback(error):
    return jsonify({"error": "Missing or invalid token"}), 401

@jwt.invalid_token_loader
def invalid_token_callback(error):
    return jsonify({"error": "Invalid token"}), 422

@jwt.expired_token_loader
def expired_token_callback(jwt_header, jwt_payload):
    return jsonify({"error": "Token expired, please login again"}), 401


# ── TASKS ─────────────────────────────────────────────────────────────────────

@app.route("/api/tasks", methods=["GET"])
@jwt_required()
def get_tasks():
    user_id  = get_jwt_identity()
    conn     = get_connection()
    cursor   = conn.cursor()
    category = request.args.get("category")
    status   = request.args.get("status")
    search   = request.args.get("search")
    sort     = request.args.get("sort")
    query    = "SELECT * FROM tasks WHERE user_id=?"
    params   = [user_id]
    if category: query += " AND category=?"; params.append(category)
    if status == "done":    query += " AND is_done=1"
    elif status == "pending": query += " AND is_done=0"
    elif status == "today":   query += " AND due_date=date('now')"
    elif status == "overdue": query += " AND due_date < date('now') AND is_done=0"
    if search: query += " AND title LIKE ?"; params.append(f"%{search}%")
    if sort == "due_date":  query += " ORDER BY due_date ASC"
    elif sort == "priority": query += " ORDER BY CASE priority WHEN 'high' THEN 1 WHEN 'medium' THEN 2 WHEN 'low' THEN 3 END"
    elif sort == "newest":   query += " ORDER BY id DESC"
    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()
    return jsonify([dict(row) for row in rows])


@app.route("/api/tasks", methods=["POST"])
@jwt_required()
def add_task():
    user_id = get_jwt_identity()
    data    = request.json
    if not data or not data.get("title"):
        return jsonify({"error": "Title is required"}), 400
    conn   = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO tasks (title, description, category, priority, due_date, is_done, user_id)
        VALUES (?, ?, ?, ?, ?, 0, ?)
    """, (data["title"], data.get("description",""), data.get("category","personal"),
          data.get("priority","medium"), data.get("due_date"), user_id))
    conn.commit()
    new_id = cursor.lastrowid
    cursor.execute("SELECT * FROM tasks WHERE id=?", (new_id,))
    new_task = cursor.fetchone()
    conn.close()
    return jsonify(dict(new_task)), 201


@app.route("/api/tasks/<int:id>/done", methods=["PATCH"])
@jwt_required()
def toggle_done(id):
    user_id = get_jwt_identity()
    conn    = get_connection()
    cursor  = conn.cursor()
    cursor.execute("SELECT is_done FROM tasks WHERE id=? AND user_id=?", (id, user_id))
    task = cursor.fetchone()
    if not task: conn.close(); return jsonify({"error": "Task not found"}), 404
    new_status = 0 if task["is_done"] == 1 else 1
    cursor.execute("UPDATE tasks SET is_done=? WHERE id=? AND user_id=?", (new_status, id, user_id))
    conn.commit(); conn.close()
    return jsonify({"message": "Updated", "is_done": new_status})


@app.route("/api/tasks/<int:id>", methods=["DELETE"])
@jwt_required()
def delete_task(id):
    user_id = get_jwt_identity()
    conn    = get_connection()
    cursor  = conn.cursor()
    cursor.execute("DELETE FROM tasks WHERE id=? AND user_id=?", (id, user_id))
    if cursor.rowcount == 0: conn.close(); return jsonify({"error": "Task not found"}), 404
    conn.commit(); conn.close()
    return jsonify({"message": "Task deleted"})


@app.route("/api/tasks/<int:id>", methods=["PUT"])
@jwt_required()
def edit_task(id):
    user_id = get_jwt_identity()
    data    = request.json
    if not data or not data.get("title"):
        return jsonify({"error": "Title is required"}), 400
    conn   = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE tasks SET title=?, description=?, category=?, priority=?, due_date=?
        WHERE id=? AND user_id=?
    """, (data["title"], data.get("description",""), data.get("category","personal"),
          data.get("priority","medium"), data.get("due_date"), id, user_id))
    if cursor.rowcount == 0: conn.close(); return jsonify({"error": "Task not found"}), 404
    conn.commit()
    cursor.execute("SELECT * FROM tasks WHERE id=?", (id,))
    updated = cursor.fetchone(); conn.close()
    return jsonify(dict(updated))


@app.route("/api/stats", methods=["GET"])
@jwt_required()
def get_stats():
    user_id = get_jwt_identity()
    conn    = get_connection()
    cursor  = conn.cursor()
    def count(q): cursor.execute(q, (user_id,)); return cursor.fetchone()[0]
    total     = count("SELECT COUNT(*) FROM tasks WHERE user_id=?")
    completed = count("SELECT COUNT(*) FROM tasks WHERE is_done=1 AND user_id=?")
    pending   = count("SELECT COUNT(*) FROM tasks WHERE is_done=0 AND user_id=?")
    today     = count("SELECT COUNT(*) FROM tasks WHERE due_date=date('now') AND user_id=?")
    overdue   = count("SELECT COUNT(*) FROM tasks WHERE due_date < date('now') AND is_done=0 AND user_id=?")
    conn.close()
    progress = round((completed / total) * 100, 2) if total > 0 else 0
    return jsonify({"total":total,"completed":completed,"pending":pending,"today":today,"overdue":overdue,"progress":progress})


# ── AUTH ──────────────────────────────────────────────────────────────────────

@app.route("/api/register", methods=["POST"])
def register():
    data = request.json
    if not data: return jsonify({"error": "No data provided"}), 400
    username = data.get("username","").strip()
    password = data.get("password","")
    mobile   = data.get("mobile","").strip()
    if not username or not password or not mobile:
        return jsonify({"error": "Username, password and mobile are required"}), 400
    if len(password) < 4:
        return jsonify({"error": "Password must be at least 4 characters"}), 400
    if not mobile.isdigit() or len(mobile) != 10:
        return jsonify({"error": "Mobile number must be exactly 10 digits"}), 400
    conn   = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM users WHERE mobile=?", (mobile,))
    if cursor.fetchone(): conn.close(); return jsonify({"error": "This mobile number is already registered"}), 400
    hashed = generate_password_hash(password)
    try:
        cursor.execute("INSERT INTO users (username, display_name, password, mobile) VALUES (?,?,?,?)",
                       (username, username, hashed, mobile))
        conn.commit()
    except Exception:
        conn.close(); return jsonify({"error": "Username already exists"}), 400
    conn.close()
    return jsonify({"message": "Account created successfully"}), 201


@app.route("/api/login", methods=["POST"])
def login():
    data = request.json
    if not data: return jsonify({"error": "No data provided"}), 400
    username = data.get("username","").strip()
    password = data.get("password","")
    if not username or not password:
        return jsonify({"error": "Username and password are required"}), 400
    conn   = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE username=?", (username,))
    user = cursor.fetchone(); conn.close()
    if not user:
        print(f"[LOGIN] No user found: '{username}'")
        return jsonify({"error": "Invalid username or password"}), 401
    if not check_password_hash(user["password"], password):
        print(f"[LOGIN] Wrong password for: '{username}'")
        return jsonify({"error": "Invalid username or password"}), 401
    print(f"[LOGIN] Success: '{username}'")
    access_token = create_access_token(identity=str(user["id"]))
    try: display_name  = user["display_name"]  or username
    except: display_name = username
    try: mobile        = user["mobile"]        or ""
    except: mobile = ""
    try: profile_image = user["profile_image"] or ""
    except: profile_image = ""
    return jsonify({"message":"Login successful","access_token":access_token,
                    "username":username,"display_name":display_name,
                    "mobile":mobile,"profile_image":profile_image})


# ── PROFILE ───────────────────────────────────────────────────────────────────

@app.route("/api/profile", methods=["GET"])
@jwt_required()
def get_profile():
    user_id = get_jwt_identity()
    conn    = get_connection()
    cursor  = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE id=?", (user_id,))
    user = cursor.fetchone(); conn.close()
    if not user: return jsonify({"error": "User not found"}), 404
    return jsonify({
        "username":      user["username"],
        "display_name":  user["display_name"]  or user["username"],
        "mobile":        user["mobile"]         or "",
        "profile_image": user["profile_image"]  or "",
        "created_at":    user["created_at"]
    })


@app.route("/api/profile", methods=["PUT"])
@jwt_required()
def update_profile():
    user_id = get_jwt_identity()
    data    = request.json
    if not data: return jsonify({"error": "No data provided"}), 400
    conn   = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE id=?", (user_id,))
    user = cursor.fetchone()
    if not user: conn.close(); return jsonify({"error": "User not found"}), 404
    updates = []; params = []
    display_name = data.get("display_name","").strip()
    if display_name: updates.append("display_name=?"); params.append(display_name)
    mobile = data.get("mobile","").strip()
    if mobile:
        if not mobile.isdigit() or len(mobile) != 10:
            conn.close(); return jsonify({"error": "Mobile must be exactly 10 digits"}), 400
        cursor.execute("SELECT id FROM users WHERE mobile=? AND id!=?", (mobile, user_id))
        if cursor.fetchone(): conn.close(); return jsonify({"error": "Mobile already used by another account"}), 400
        updates.append("mobile=?"); params.append(mobile)
    new_password = data.get("new_password","")
    if new_password:
        current_password = data.get("current_password","")
        if not current_password: conn.close(); return jsonify({"error": "Current password required"}), 400
        if not check_password_hash(user["password"], current_password):
            conn.close(); return jsonify({"error": "Current password is incorrect"}), 401
        if len(new_password) < 4: conn.close(); return jsonify({"error": "New password min 4 characters"}), 400
        updates.append("password=?"); params.append(generate_password_hash(new_password))
    profile_image = data.get("profile_image", None)
    if profile_image is not None:
        if profile_image != "" and not profile_image.startswith("data:image/"):
            conn.close(); return jsonify({"error": "Invalid image format"}), 400
        if len(profile_image) > 3_000_000:
            conn.close(); return jsonify({"error": "Image too large. Max 2MB."}), 400
        updates.append("profile_image=?"); params.append(profile_image)
    if not updates: conn.close(); return jsonify({"error": "No fields to update"}), 400
    params.append(user_id)
    cursor.execute(f"UPDATE users SET {', '.join(updates)} WHERE id=?", params)
    conn.commit()
    cursor.execute("SELECT * FROM users WHERE id=?", (user_id,))
    updated = cursor.fetchone(); conn.close()
    return jsonify({"message":"Profile updated successfully",
                    "username":updated["username"],
                    "display_name":updated["display_name"] or updated["username"],
                    "mobile":updated["mobile"] or "",
                    "profile_image":updated["profile_image"] or ""})


# ── DELETE ACCOUNT ────────────────────────────────────────────────────────────

@app.route("/api/account", methods=["DELETE"])
@jwt_required()
def delete_account():
    user_id = get_jwt_identity()
    data    = request.json
    if not data or not data.get("password"):
        return jsonify({"error": "Password confirmation is required"}), 400
    conn   = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE id=?", (user_id,))
    user = cursor.fetchone()
    if not user: conn.close(); return jsonify({"error": "User not found"}), 404
    if not check_password_hash(user["password"], data["password"]):
        conn.close(); return jsonify({"error": "Incorrect password"}), 401
    cursor.execute("DELETE FROM tasks WHERE user_id=?", (user_id,))
    cursor.execute("DELETE FROM users WHERE id=?", (user_id,))
    conn.commit(); conn.close()
    return jsonify({"message": "Account permanently deleted"})


if __name__ == "__main__":
    init_db()
    app.run(debug=True, port=5000)