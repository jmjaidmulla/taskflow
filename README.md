# TaskManager

A full-stack task management app — Flask REST API + vanilla JS frontend.

## Project Structure

```
TaskFlow/
├── .postman/                     ← Stores API collections for testing with Postman
│
├── .venv/                        ← Python virtual environment for project dependencies
│
├── .vscode/                      ← VS Code workspace settings and configuration
│
├── backend/                      ← Backend server (Run using: python app.py)
│   ├── __pycache__/              ← Python compiled cache files (auto-generated)
│   │
│   ├── routes/                   ← API route modules (Flask Blueprints)
│   │   ├── __pycache__/          ← Compiled Python cache
│   │   ├── auth_routes.py        ← Authentication APIs
│   │   │                             POST /api/login
│   │   │                             POST /api/register
│   │   │                             Handles user authentication
│   │   │
│   │   ├── otp_routes.py         ← OTP verification APIs
│   │   │                             Send OTP
│   │   │                             Verify OTP
│   │   │                             Password reset OTP
│   │   │
│   │   ├── profile_routes.py     ← Profile management APIs
│   │   │                             GET /api/profile
│   │   │                             PUT /api/profile
│   │   │                             Update user details
│   │   │
│   │   └── task_routes.py        ← Task management APIs
│   │                                 GET /api/tasks
│   │                                 POST /api/tasks
│   │                                 PUT /api/tasks/{id}
│   │                                 DELETE /api/tasks/{id}
│   │
│   ├── utils/                    ← Utility/helper functions
│   │   ├── __pycache__/          ← Python compiled cache
│   │   └── otp_helper.py         ← OTP generation and verification helper functions
│   │
│   ├── venv/                     ← Local backend virtual environment (optional)
│   │
│   ├── app.py                    ← Main Flask application entry point
│   │                                 Initializes Flask server
│   │                                 Registers API routes
│   │                                 Enables CORS
│   │
│   ├── database.py               ← Database connection and query helper functions
│   │
│   └── database.db               ← SQLite database file storing users and tasks
│
├── frontend/                     ← Frontend user interface (Open index.html)
│   ├── css/
│   │   └── style.css             ← All UI styling, layout design, and responsiveness
│   │
│   ├── js/
│   │   ├── auth.js               ← Authentication logic
│   │   │                             Login
│   │   │                             Register
│   │   │                             Logout
│   │   │
│   │   ├── config.js             ← Backend API URL and global configuration variables
│   │   │
│   │   ├── notifications.js      ← Notification and reminder system
│   │   │                             Task deadline alerts
│   │   │
│   │   ├── profile.js            ← Profile management functions
│   │   │                             Load profile
│   │   │                             Update user information
│   │   │
│   │   ├── tasks.js              ← Task management logic
│   │   │                             Create task
│   │   │                             Edit task
│   │   │                             Delete task
│   │   │                             Mark task complete
│   │   │
│   │   └── ui.js                 ← UI interaction controller
│   │                                 Navigation handling
│   │                                 Theme toggle
│   │                                 UI utilities
│   │
│   └── index.html                ← Main application interface (Task dashboard)
│
├── postman/                      ← Additional API testing files
│
└── README.md                     ← Project documentation
```

## Setup

### Backend

```bash
cd Backend

# Install dependencies
pip install flask flask-cors flask-jwt-extended werkzeug

# Run the server
python app.py
# → Running on http://127.0.0.1:5000
```

### Frontend

Just open `Frontend/index.html` in your browser.
No build step needed — plain HTML + CSS + JS.

> Make sure the Flask server is running on port 5000 before using the app.

## SMS (OTP)

OTPs are sent via **Fast2SMS**.
1. Get a free API key at https://fast2sms.com → Dev API
2. Paste it into `Backend/utils/otp_helper.py` → `FAST2SMS_KEY`

**Dev mode:** If the SMS fails (wrong key, no internet), the OTP is printed
to the Flask terminal instead so you can still test locally.

## API Endpoints

| Method | URL | Auth | Description |
|--------|-----|------|-------------|
| POST | /api/login | ✗ | Login |
| POST | /api/register/send-otp | ✗ | Register step 1 |
| POST | /api/register/verify-otp | ✗ | Register step 2 |
| POST | /api/forgot-password/send-otp | ✗ | Forgot password step 1 |
| POST | /api/forgot-password/verify-otp | ✗ | Forgot password step 2 |
| POST | /api/forgot-password/reset | ✗ | Forgot password step 3 |
| POST | /api/forgot-username/send-otp | ✗ | Forgot username step 1 |
| POST | /api/forgot-username/verify-otp | ✗ | Forgot username step 2 |
| GET | /api/tasks | ✓ JWT | List tasks |
| POST | /api/tasks | ✓ JWT | Create task |
| PUT | /api/tasks/:id | ✓ JWT | Update task |
| DELETE | /api/tasks/:id | ✓ JWT | Delete task |
| PATCH | /api/tasks/:id/done | ✓ JWT | Toggle done |
| GET | /api/stats | ✓ JWT | Task statistics |
| GET | /api/profile | ✓ JWT | Get profile |
| PUT | /api/profile | ✓ JWT | Update profile |
| DELETE | /api/account | ✓ JWT | Delete account |
