// ============================================================
// ui.js — Navigation, Dark Mode, Logout, Delete Account,
//         Overview greeting, Toast notifications, Helpers
// ============================================================


// ── App boot: called after successful login ───────────────
function showApp() {
    startNotifIfEnabled();
    document.getElementById('auth-screen').style.display = 'none';
    document.getElementById('app').classList.add('visible');
    updateUserUI();
    loadTasks();
    loadStats();
    setGreeting();
    loadProfileFromServer(); // always pull fresh data from DB
}


// ── Navigation between views ──────────────────────────────
function goView(name, navEl) {
    document.querySelectorAll('.view').forEach(v => v.classList.remove('active'));
    document.querySelectorAll('.nav-item').forEach(n => n.classList.remove('active'));
    document.getElementById('view-' + name).classList.add('active');
    if (navEl) navEl.classList.add('active');
    if (name === 'overview')   { loadStats(); loadTodayTasks(); setGreeting(); }
    if (name === 'categories') { loadCategories(); }
}

// Refresh whichever secondary view is currently open
function refreshViews() {
    if (document.getElementById('view-overview').classList.contains('active'))   { loadStats(); loadTodayTasks(); }
    if (document.getElementById('view-categories').classList.contains('active')) { loadCategories(); }
}


// ── Overview: greeting + date ─────────────────────────────
function setGreeting() {
    const h = new Date().getHours();
    const g = h < 12 ? 'Good morning' : h < 17 ? 'Good afternoon' : 'Good evening';
    document.getElementById('ov-greet').textContent =
        `${g}, ${curDisplay || curUser} 👋`;
    document.getElementById('ov-date').textContent =
        new Date().toLocaleDateString('en-US', { weekday:'long', year:'numeric', month:'long', day:'numeric' });
}


// ── Dark mode ─────────────────────────────────────────────
function toggleDark() {
    darkMode = !darkMode;
    localStorage.setItem('tf_dark', darkMode);
    applyDark();
}
function applyDark() {
    document.documentElement.setAttribute('data-theme', darkMode ? 'dark' : 'light');
    const t = document.getElementById('dark-tog');
    if (t) t.classList.toggle('on', darkMode);
}


// ── Logout ────────────────────────────────────────────────
function openLogout()  { document.getElementById('logout-overlay').classList.add('open'); }
function closeLogout() { document.getElementById('logout-overlay').classList.remove('open'); }
function doLogout() {
    token = null; curUser = null; curDisplay = null; curMobile = null; curImg = null;
    localStorage.clear();
    document.getElementById('app').classList.remove('visible');
    document.getElementById('auth-screen').style.display = 'flex';
    document.getElementById('logout-overlay').classList.remove('open');
    showToast('Logged out successfully.');
}


// ── Delete Account ────────────────────────────────────────
function openDelAcc() {
    document.getElementById('del-pass').value         = '';
    document.getElementById('del-err').textContent    = '';
    document.getElementById('del-acc-overlay').classList.add('open');
    setTimeout(() => document.getElementById('del-pass').focus(), 80);
}
function closeDelAcc() {
    document.getElementById('del-acc-overlay').classList.remove('open');
}
async function doDeleteAccount() {
    const pass = document.getElementById('del-pass').value;
    const err  = document.getElementById('del-err');
    err.textContent = '';
    if (!pass) { err.textContent = 'Please enter your password to confirm.'; return; }
    try {
        const res = await api('/account', { method: 'DELETE', body: JSON.stringify({ password: pass }) });
        const d   = await res.json();
        if (!res.ok) throw new Error(d.error || 'Failed');
        localStorage.clear();
        document.getElementById('del-acc-overlay').classList.remove('open');
        document.getElementById('app').classList.remove('visible');
        document.getElementById('auth-screen').style.display = 'flex';
        showToast('Account permanently deleted.', 'info');
    } catch(e) { err.textContent = e.message; }
}


// ── Toast message ─────────────────────────────────────────
// type: 'info' | 'success' | 'error'
let toastT;
function showToast(msg, type = 'info') {
    const el = document.getElementById('toast');
    el.textContent = msg;
    el.className   = `show ${type}`;
    clearTimeout(toastT);
    toastT = setTimeout(() => el.className = '', 3000);
}


// ── Utility helpers ───────────────────────────────────────

// Returns CSS class for a task due date badge
function dueCls(d, done) {
    if (!d || done) return 'normal';
    const now      = new Date();
    const date     = new Date(d);
    const todayStr = now.toISOString().split('T')[0];
    const dStr     = d.split('T')[0];
    if (date < now)        return 'overdue';
    if (dStr === todayStr) return 'today';
    return 'normal';
}

// Returns true if a task is overdue and not done
function isOver(d, done) {
    if (!d || done) return false;
    return new Date(d) < new Date();
}

// Returns a human-readable due date string
function fmtDue(d) {
    if (!d) return '';
    const now     = new Date();
    const date    = new Date(d);
    const today   = now.toISOString().split('T')[0];
    const dDay    = d.split('T')[0];
    const timeStr = date.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' });
    if (dDay === today) return `Today ${timeStr}`;
    return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' }) + ' ' + timeStr;
}

// Escape HTML special characters (prevents XSS in task titles/descriptions)
function esc(s) {
    return String(s || '')
        .replace(/&/g,'&amp;').replace(/</g,'&lt;')
        .replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}

// Capitalise first letter
function cap(s) { return s ? s[0].toUpperCase() + s.slice(1) : ''; }


// ── Keyboard shortcuts ────────────────────────────────────
document.addEventListener('keydown', e => {
    // Esc closes any open modal/overlay
    if (e.key === 'Escape') {
        closeModal(); closeDelTask(); closeLogout();
        closeDelAcc(); closeEditProfile(); closeCropper();
    }
    // Ctrl+K / Cmd+K → focus search
    if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
        e.preventDefault();
        document.getElementById('search-inp').focus();
    }
    // Ctrl+N / Cmd+N → open Add Task modal
    if ((e.ctrlKey || e.metaKey) && e.key === 'n') {
        e.preventDefault();
        openModal();
    }
});


// Enter key shortcuts on the login form
document.getElementById('li-p').addEventListener('keydown', e => { if (e.key === 'Enter') doLogin(); });
document.getElementById('li-u').addEventListener('keydown', e => { if (e.key === 'Enter') document.getElementById('li-p').focus(); });