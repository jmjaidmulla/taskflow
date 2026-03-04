from flask import Flask, request, jsonify
from flask_cors import CORS
from database import init_db, get_connection

app = Flask(__name__)
CORS(app)

# ------------------ GET ALL TASKS ------------------

@app.route("/api/tasks", methods=["GET"])
def get_tasks():
    conn = get_connection()
    cursor = conn.cursor()

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

    cursor.execute(query, params)
    rows = cursor.fetchall()

    tasks = []
    for row in rows:
        tasks.append({
            "id": row[0],
            "title": row[1],
            "description": row[2],
            "category": row[3],
            "priority": row[4],
            "due_date": row[5],
            "is_done": row[6]
        })

    conn.close()
    return jsonify(tasks)


# ------------------ ADD TASK (POST) ------------------

@app.route("/api/tasks", methods=["POST"])
def add_task():
    data = request.json

    if not data.get("title"):
        return jsonify({"error": "Title required"}), 400

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO tasks (title, description, category, priority, due_date)
        VALUES (?, ?, ?, ?, ?)
    """, (
        data["title"],
        data.get("description", ""),
        data["category"],
        data["priority"],
        data["due_date"]
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


# ------------------ MAIN ------------------

if __name__ == "__main__":
    init_db()
    app.run(debug=True)