from flask import Flask, request, jsonify
from flask_cors import CORS
from database import init_db, get_connection

app = Flask(__name__)
CORS(app)

# ------------------ ROUTES START HERE ------------------

@app.route("/api/tasks", methods=["GET"])
def get_tasks():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM tasks")
    rows = cursor.fetchall()
    conn.close()
    return jsonify(rows)

# ------------------ ROUTES END HERE ------------------

if __name__ == "__main__":
    init_db()
    app.run(debug=True)