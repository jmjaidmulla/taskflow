# =============================================================================
# routes/task_routes.py
# Handles: GET/POST /api/tasks, PUT/DELETE/PATCH /api/tasks/<id>, GET /api/stats
# All routes require a valid JWT token.
# =============================================================================

from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from database import get_connection

task_bp = Blueprint("tasks", __name__)


@task_bp.route("/api/tasks", methods=["GET"])
@jwt_required()
def get_tasks():
    """
    GET /api/tasks
    Query params: category, status (done/pending/today/overdue), search, sort
    Returns: list of task objects belonging to the logged-in user
    """
    user_id  = get_jwt_identity()
    conn     = get_connection()
    cursor   = conn.cursor()

    category = request.args.get("category")
    status   = request.args.get("status")
    search   = request.args.get("search")
    sort     = request.args.get("sort")

    query  = "SELECT * FROM tasks WHERE user_id=?"
    params = [user_id]

    # Filters
    if category:
        query += " AND category=?"
        params.append(category)

    if status == "done":
        query += " AND is_done=1"

    elif status == "pending":
        query += " AND is_done=0"

    # ✅ FIXED TODAY FILTER
    elif status == "today":
        query += " AND substr(due_date,1,10) = date('now','localtime')"

    elif status == "overdue":
        query += """
        AND due_date < strftime('%Y-%m-%dT%H:%M', 'now', 'localtime')
        AND is_done=0
        """

    if search:
        query += " AND title LIKE ?"
        params.append(f"%{search}%")

    # Sorting
    if sort == "due_date":
        query += " ORDER BY due_date ASC"

    elif sort == "priority":
        query += """
        ORDER BY CASE priority
        WHEN 'high' THEN 1
        WHEN 'medium' THEN 2
        WHEN 'low' THEN 3
        END
        """

    elif sort == "newest":
        query += " ORDER BY id DESC"

    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()

    return jsonify([dict(row) for row in rows])


@task_bp.route("/api/tasks", methods=["POST"])
@jwt_required()
def add_task():
    """
    POST /api/tasks
    Body: { title, description?, category?, priority?, due_date? }
    Returns: the newly created task object
    """
    user_id = get_jwt_identity()
    data    = request.json

    if not data or not data.get("title"):
        return jsonify({"error": "Title is required"}), 400

    conn   = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO tasks (title, description, category, priority, due_date, is_done, user_id)
        VALUES (?, ?, ?, ?, ?, 0, ?)
    """, (
        data["title"],
        data.get("description", ""),
        data.get("category", "personal"),
        data.get("priority", "medium"),
        data.get("due_date"),
        user_id
    ))

    conn.commit()
    new_id = cursor.lastrowid

    cursor.execute("SELECT * FROM tasks WHERE id=?", (new_id,))
    new_task = cursor.fetchone()

    conn.close()

    return jsonify(dict(new_task)), 201


@task_bp.route("/api/tasks/<int:id>", methods=["PUT"])
@jwt_required()
def edit_task(id):
    """
    PUT /api/tasks/<id>
    Body: { title, description?, category?, priority?, due_date? }
    Returns: updated task object
    """
    user_id = get_jwt_identity()
    data    = request.json

    if not data or not data.get("title"):
        return jsonify({"error": "Title is required"}), 400

    conn   = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        UPDATE tasks
        SET title=?, description=?, category=?, priority=?, due_date=?
        WHERE id=? AND user_id=?
    """, (
        data["title"],
        data.get("description", ""),
        data.get("category", "personal"),
        data.get("priority", "medium"),
        data.get("due_date"),
        id,
        user_id
    ))

    if cursor.rowcount == 0:
        conn.close()
        return jsonify({"error": "Task not found"}), 404

    conn.commit()

    cursor.execute("SELECT * FROM tasks WHERE id=?", (id,))
    updated = cursor.fetchone()

    conn.close()

    return jsonify(dict(updated))


@task_bp.route("/api/tasks/<int:id>", methods=["DELETE"])
@jwt_required()
def delete_task(id):
    """
    DELETE /api/tasks/<id>
    Permanently removes the task.
    """
    user_id = get_jwt_identity()

    conn    = get_connection()
    cursor  = conn.cursor()

    cursor.execute("DELETE FROM tasks WHERE id=? AND user_id=?", (id, user_id))

    if cursor.rowcount == 0:
        conn.close()
        return jsonify({"error": "Task not found"}), 404

    conn.commit()
    conn.close()

    return jsonify({"message": "Task deleted"})


@task_bp.route("/api/tasks/<int:id>/done", methods=["PATCH"])
@jwt_required()
def toggle_done(id):
    """
    PATCH /api/tasks/<id>/done
    Toggles the is_done flag between 0 and 1.
    """
    user_id = get_jwt_identity()

    conn   = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT is_done FROM tasks WHERE id=? AND user_id=?", (id, user_id))
    task = cursor.fetchone()

    if not task:
        conn.close()
        return jsonify({"error": "Task not found"}), 404

    new_status = 0 if task["is_done"] == 1 else 1

    cursor.execute("""
        UPDATE tasks
        SET is_done=?
        WHERE id=? AND user_id=?
    """, (new_status, id, user_id))

    conn.commit()
    conn.close()

    return jsonify({
        "message": "Updated",
        "is_done": new_status
    })


@task_bp.route("/api/stats", methods=["GET"])
@jwt_required()
def get_stats():
    """
    GET /api/stats
    Returns task counts and completion percentage for the logged-in user.
    """
    user_id = get_jwt_identity()

    conn    = get_connection()
    cursor  = conn.cursor()

    def count(q):
        cursor.execute(q, (user_id,))
        return cursor.fetchone()[0]

    total     = count("SELECT COUNT(*) FROM tasks WHERE user_id=?")
    completed = count("SELECT COUNT(*) FROM tasks WHERE is_done=1 AND user_id=?")
    pending   = count("SELECT COUNT(*) FROM tasks WHERE is_done=0 AND user_id=?")

    # ✅ FIXED TODAY STATS
    today = count("""
    SELECT COUNT(*) FROM tasks
    WHERE substr(due_date,1,10) = date('now','localtime')
    AND user_id=?
    """)

    overdue = count("""
    SELECT COUNT(*) FROM tasks
    WHERE due_date < strftime('%Y-%m-%dT%H:%M', 'now', 'localtime')
    AND is_done=0
    AND user_id=?
    """)

    conn.close()

    progress = round((completed / total) * 100, 2) if total > 0 else 0

    return jsonify({
        "total": total,
        "completed": completed,
        "pending": pending,
        "today": today,
        "overdue": overdue,
        "progress": progress
    })