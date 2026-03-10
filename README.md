# TaskManager

A full-stack task management app — Flask REST API + vanilla JS frontend.

## Project Structure

```
TaskManager/
├── Frontend/               ← Open index.html in browser
│   ├── index.html          ← Main HTML (structure only)
│   ├── css/
│   │   └── style.css       ← All styles (16 sections)
│   └── js/
│       ├── config.js       ← API URL + global state variables
│       ├── auth.js         ← Login, Register, Forgot Password/Username
│       ├── tasks.js        ← Task CRUD, filters, search, stats, categories
│       ├── profile.js      ← Edit profile + image cropper
│       ├── notifications.js← Push notifications (Service Worker)
│       └── ui.js           ← Navigation, dark mode, helpers, keyboard shortcuts
│
└── Backend/                ← Run with: python app.py
    ├── app.py              ← Flask entry point — registers all blueprints
    ├── database.py         ← SQLite setup + migrations
    ├── routes/
    │   ├── auth_routes.py      ← POST /api/login
    │   ├── task_routes.py      ← CRUD + stats for /api/tasks
    │   ├── profile_routes.py   ← GET/PUT /api/profile, DELETE /api/account
    │   └── otp_routes.py       ← Register OTP, Forgot Password, Forgot Username
    └── utils/
        └── otp_helper.py       ← OTP store, SMS sender (Fast2SMS), reset tokens
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