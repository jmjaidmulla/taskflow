from flask import Flask, request, jsonify
from flask_cors import CORS
from database import init_db, get_connection
from werkzeug.security import generate_password_hash, check_password_hash
from flask_jwt_extended import (
    JWTManager,
    create_access_token,
    jwt_required,
    get_jwt_identity
)

app = Flask(__name__)
CORS(app)

app.config["JWT_SECRET_KEY"] = "super-secret-key"  # change later in production
jwt = JWTManager(app)

# ------------------ GET ALL TASKS ------------------

@app.route("/api/tasks", methods=["GET"])
def get_tasks():
    conn = get_connection()
    cursor = conn.cursor()
    sort = request.args.get("sort")

    category = request.args.get("category")
    status = request.args.get("status")
    search = request.args.get("search")

    query = "SELECT * FROM tasks WHERE 1=1"
    params = []

    if category:
        query += " AND category=?"
        params.append(category)

    if status == "done":
        query += " AND is_done=1"
    elif status == "pending":
        query += " AND is_done=0"
    elif status == "today":
        query += " AND due_date=date('now')"
    elif status == "overdue":
        query += " AND due_date < date('now') AND is_done=0"

    if search:
        query += " AND title LIKE ?"
        params.append(f"%{search}%")

        # -------- SORTING --------
    if sort == "due_date":
        query += " ORDER BY due_date ASC"
    elif sort == "priority":
        query += " ORDER BY priority DESC"
    elif sort == "newest":
        query += " ORDER BY id DESC"


    cursor.execute(query, params)
    rows = cursor.fetchall()

    tasks = []
    for row in rows:
        tasks.append({
            "id": row["id"],
            "title": row["title"],
            "description": row["description"],
            "category": row["category"],
            "priority": row["priority"],
            "due_date": row["due_date"],
            "is_done": row["is_done"],
            "user_id": row["user_id"]
        })

    conn.close()
    return jsonify(tasks)


# ------------------ ADD TASK (POST) ------------------

@app.route("/api/tasks", methods=["POST"])
def add_task():
    data = request.json

    # 🔥 NEW: Get user_id
    user_id = data.get("user_id")

    if not data.get("title") or not user_id:
        return jsonify({"error": "Title and user_id required"}), 400

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO tasks (title, description, category, priority, due_date, user_id)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (
        data["title"],
        data.get("description", ""),
        data.get("category"),
        data.get("priority"),
        data.get("due_date"),
        user_id   # 🔥 NEW FIELD
    ))

    conn.commit()
    new_id = cursor.lastrowid
    conn.close()

    return jsonify({"id": new_id}), 201


# ------------------ TOGGLE DONE (PATCH) ------------------

@app.route("/api/tasks/<int:id>/done", methods=["PATCH"])
def toggle_done(id):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT is_done FROM tasks WHERE id=?", (id,))
    current = cursor.fetchone()

    if not current:
        conn.close()
        return jsonify({"error": "Task not found"}), 404

    new_status = 0 if current[0] == 1 else 1

    cursor.execute("UPDATE tasks SET is_done=? WHERE id=?", (new_status, id))
    conn.commit()
    conn.close()

    return jsonify({"message": "Updated successfully"})


# ------------------ DELETE TASK ------------------

@app.route("/api/tasks/<int:id>", methods=["DELETE"])
def delete_task(id):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("DELETE FROM tasks WHERE id=?", (id,))
    conn.commit()
    conn.close()

    return jsonify({"message": "Task deleted successfully"})


# ------------------ EDIT TASK (PUT) ------------------

@app.route("/api/tasks/<int:id>", methods=["PUT"])
def edit_task(id):
    data = request.json

    if not data.get("title"):
        return jsonify({"error": "Title required"}), 400

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        UPDATE tasks
        SET title=?, description=?, category=?, priority=?, due_date=?
        WHERE id=?
    """, (
        data["title"],
        data.get("description", ""),
        data["category"],
        data["priority"],
        data["due_date"],
        id
    ))

    conn.commit()
    conn.close()

    return jsonify({"message": "Task updated successfully"})


# ------------------ STATS API ------------------

@app.route("/api/stats", methods=["GET"])
def get_stats():
    conn = get_connection()
    cursor = conn.cursor()

    # Total tasks
    cursor.execute("SELECT COUNT(*) FROM tasks")
    total = cursor.fetchone()[0]

    # Completed tasks
    cursor.execute("SELECT COUNT(*) FROM tasks WHERE is_done=1")
    completed = cursor.fetchone()[0]

    # Pending tasks
    cursor.execute("SELECT COUNT(*) FROM tasks WHERE is_done=0")
    pending = cursor.fetchone()[0]

    # Today's tasks
    cursor.execute("SELECT COUNT(*) FROM tasks WHERE due_date=date('now')")
    today = cursor.fetchone()[0]

    # Overdue tasks
    cursor.execute("SELECT COUNT(*) FROM tasks WHERE due_date < date('now') AND is_done=0")
    overdue = cursor.fetchone()[0]

    conn.close()

    # ------------------ PROGRESS CALCULATION ------------------

    progress = 0

    if total > 0:
        progress = round((completed / total) * 100, 2)

    return jsonify({
        "total": total,
        "completed": completed,
        "pending": pending,
        "today": today,
        "overdue": overdue,
        "progress": progress
    })


# ------------------ REGISTER ------------------

@app.route("/api/register", methods=["POST"])
def register():
    data = request.json

    username = data.get("username")
    password = data.get("password")

    if not username or not password:
        return jsonify({"error": "Username and password required"}), 400

    hashed_password = generate_password_hash(password)

    conn = get_connection()
    cursor = conn.cursor()

    try:
        cursor.execute(
            "INSERT INTO users (username, password) VALUES (?, ?)",
            (username, hashed_password)
        )
        conn.commit()
    except:
        conn.close()
        return jsonify({"error": "Username already exists"}), 400

    conn.close()

    return jsonify({"message": "User registered successfully"})


# ------------------ LOGIN ------------------

@app.route("/api/login", methods=["POST"])
def login():
    data = request.json

    username = data.get("username")
    password = data.get("password")

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM users WHERE username=?", (username,))
    user = cursor.fetchone()
    conn.close()

    if user and check_password_hash(user["password"], password):

        # 🔥 Create JWT token
        access_token = create_access_token(identity=user["id"])

        return jsonify({
            "message": "Login successful",
            "access_token": access_token
        })

    return jsonify({"error": "Invalid credentials"}), 401

# ------------------ MAIN ------------------

if __name__ == "__main__":
    init_db()
    app.run(debug=True)