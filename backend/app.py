# =============================================================================
# app.py — TaskFlow Flask Application Entry Point
#
# Registers all route blueprints and starts the server.
# Run with:  python app.py
# =============================================================================


from flask import Flask, make_response 
from flask_cors import CORS # (Cross Origin Resource Sharing)
from flask_jwt_extended import JWTManager # Verify the identity of the user after login
from datetime import timedelta  # For setting JWT token expiration time

from database import init_db 

# ── Import route blueprints ───────────────────────────────────────────────────
from routes.auth_routes    import auth_bp
from routes.task_routes    import task_bp
from routes.profile_routes import profile_bp
from routes.otp_routes     import otp_bp

# ── App setup ─────────────────────────────────────────────────────────────────
app = Flask(__name__)
CORS(app)

# ── JWT configuration ─────────────────────────────────────────────────────────
app.config["JWT_SECRET_KEY"]           = "super-secret-taskflow-key-2024"
app.config["JWT_ACCESS_TOKEN_EXPIRES"] = timedelta(days=30)
app.config["JWT_ALGORITHM"]            = "HS256"
app.config["JWT_TOKEN_LOCATION"]       = ["headers"]
app.config["JWT_HEADER_NAME"]          = "Authorization" 
app.config["JWT_HEADER_TYPE"]          = "Bearer"

jwt = JWTManager(app)

# ── JWT error handlers ────────────────────────────────────────────────────────
from flask import jsonify

@jwt.unauthorized_loader

def unauthorized_callback(error):
    return jsonify({"error": "Missing or invalid token"}), 401

@jwt.invalid_token_loader
def invalid_token_callback(error):
    return jsonify({"error": "Invalid token"}), 422

@jwt.expired_token_loader
def expired_token_callback(jwt_header, jwt_payload):
    return jsonify({"error": "Token expired, please login again"}), 401

# ── CORS headers on every response ───────────────────────────────────────────
@app.after_request
def add_cors_headers(response):
    response.headers["Access-Control-Allow-Origin"]  = "*"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, PATCH, DELETE, OPTIONS"
    return response

# Handle preflight OPTIONS requests for all API routes
@app.route("/api/<path:path>", methods=["OPTIONS"])
def options_handler(path):
    response = make_response()
    response.headers["Access-Control-Allow-Origin"]  = "*"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, PATCH, DELETE, OPTIONS"
    return response, 200


# ── Register blueprints ───────────────────────────────────────────────────────
app.register_blueprint(auth_bp)
app.register_blueprint(task_bp)
app.register_blueprint(profile_bp)
app.register_blueprint(otp_bp)

# ── Start server ──────────────────────────────────────────────────────────────
if __name__ == "__main__":
    init_db()                          # create tables / run migrations
    app.run(debug=True, port=5000)     # http://127.0.0.1:5000