// ============================================================
// config.js — API base URL, global state variables
// ============================================================

// Base URL for all API calls (change this if Flask runs on a different port)
const API = 'http://127.0.0.1:5000/api';

// ── Auth state ──────────────────────────────────────────
let token      = localStorage.getItem('tf_token')   || null;    // JWT authentication token
let curUser    = localStorage.getItem('tf_user')    || null;    // Username
let curDisplay = localStorage.getItem('tf_display') || null;    // Display name
let curMobile  = localStorage.getItem('tf_mobile')  || null;    // Mobile number
let curImg     = localStorage.getItem('tf_img')     || null;    // Profile image URL


// ── Task list state ──────────────────────────────────────
let tasks = [], editingId = null, deleteTaskId = null;  
let selPri = 'high', curFilter = 'all', curCat = '', curSort = '', searchQ = '';    //


// ── UI state ─────────────────────────────────────────────
let darkMode = localStorage.getItem('tf_dark') === 'true';  // Dark mode state


// ── Notification state ───────────────────────────────────
let _notifEnabled  = localStorage.getItem('tf_notif') !== 'off';
let _notifInterval = null;
let _notifFired    = JSON.parse(localStorage.getItem('tf_notif_fired') || '{}');


// ── Image cropper state ──────────────────────────────────
let cropImgSrc = null, cropX = 80, cropY = 60, cropW = 160, cropH = 160;    // Crop box position and size 
let cropImgX = 0, cropImgY = 0, cropScale = 1, _drag = null;    


// ── Profile pending image ────────────────────────────────
let pendingImg = null;  // Newly selected profile image, waiting for cropper

// ── Helper: persist auth state to localStorage ───────────
function saveLocal() {
    localStorage.setItem('tf_token',   token);
    localStorage.setItem('tf_user',    curUser);
    localStorage.setItem('tf_display', curDisplay);
    localStorage.setItem('tf_mobile',  curMobile);
    localStorage.setItem('tf_img',     curImg);
}

// ── Helper: authenticated fetch wrapper ──────────────────
// Automatically adds JWT header; logs out on 401
function hdr() { return { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` }; }
async function api(path, opts = {}) {
    const res = await fetch(API + path, { ...opts, headers: hdr() });
    if (res.status === 401) { doLogout(); throw new Error('Session expired'); }
    return res;
}