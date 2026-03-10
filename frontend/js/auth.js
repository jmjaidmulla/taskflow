// ============================================================
// auth.js — Login, Register (OTP), Forgot Password, Forgot Username
// All functions that run BEFORE the user is logged in.
// ============================================================


// ── Tab switching (Login ↔ Register) ─────────────────────
function switchTab(t) {
    document.querySelectorAll('.auth-tab').forEach((el, i) =>
        el.classList.toggle('active', t === 'login' ? i === 0 : i === 1)
    );
    // Hide all login-side panels (login form + all forgot steps)
    ['login-form', 'fp1', 'fp2', 'fp3', 'fu1', 'fu2', 'fu3'].forEach(id =>
        document.getElementById(id)?.classList.remove('active')
    );
    // Hide register steps
    document.getElementById('register-form').classList.remove('active');
    ['rg-s1', 'rg-s2'].forEach(id =>
        document.getElementById(id)?.classList.remove('active')
    );
    if (t === 'login') {
        document.getElementById('login-form').classList.add('active');
    } else {
        document.getElementById('register-form').classList.add('active');
        document.getElementById('rg-s1').classList.add('active');
    }
}


// ── Login ─────────────────────────────────────────────────
async function doLogin() {
    const u   = document.getElementById('li-u').value.trim();
    const p   = document.getElementById('li-p').value;
    const err = document.getElementById('li-err');
    err.textContent = '';
    if (!u || !p) { err.textContent = 'Please fill in all fields.'; return; }
    try {
        const res = await fetch(`${API}/login`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ username: u, password: p })
        });
        const d = await res.json();
        if (!res.ok) throw new Error(d.error || 'Login failed');
        token      = d.access_token;
        curUser    = d.username     || u;
        curDisplay = d.display_name || u;
        curMobile  = d.mobile       || '';
        curImg     = d.profile_image || '';
        saveLocal();
        showApp();
    } catch(e) { err.textContent = e.message; }
}


// ── Register — Step 1: send OTP ───────────────────────────
let _rgTimer = null;

async function rgSendOtp(isResend = false) {
    const u   = document.getElementById('rg-u').value.trim();
    const m   = document.getElementById('rg-m').value.trim();
    const p   = document.getElementById('rg-p').value;
    const err = document.getElementById('rg-err');
    err.textContent = '';
    if (!u || !m || !p)              { err.textContent = 'All fields are required.'; return; }
    if (u.length < 3)                { err.textContent = 'Username must be at least 3 characters.'; return; }
    if (!/^[a-zA-Z0-9_]+$/.test(u)) { err.textContent = 'Username: only letters, numbers, underscores.'; return; }
    if (!/^[0-9]{10}$/.test(m))     { err.textContent = 'Mobile must be exactly 10 digits.'; return; }
    if (p.length < 4)               { err.textContent = 'Password must be at least 4 characters.'; return; }
    try {
        const res = await fetch(`${API}/register/send-otp`, {
            method: 'POST', headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ username: u, mobile: m, password: p })
        });
        const d = await res.json();
        if (!res.ok) throw new Error(d.error || 'Failed to send OTP');
        const masked = '+91 ' + m.slice(0,2) + 'XXXXXX' + m.slice(-2);
        document.getElementById('rg-sent-lbl').textContent = d.dev
            ? '⚠️ DEV MODE — Check Flask terminal for OTP'
            : 'OTP sent to ' + masked;
        for (let i = 0; i < 6; i++) {
            const b = document.getElementById('rg-ob' + i);
            b.value = ''; b.classList.remove('done', 'shake');
        }
        document.getElementById('rg-err2').textContent = '';
        document.getElementById('rg-s1').classList.remove('active');
        document.getElementById('rg-s2').classList.add('active');
        rgStartTimer();
        showToast(d.dev ? '⚠️ Dev mode — check terminal for OTP' : 'OTP sent to ' + masked, d.dev ? 'info' : 'success');
        setTimeout(() => document.getElementById('rg-ob0').focus(), 80);
    } catch(e) { err.textContent = e.message; }
}

function rgGoBack() {
    clearInterval(_rgTimer);
    document.getElementById('rg-s2').classList.remove('active');
    document.getElementById('rg-s1').classList.add('active');
}

function rgStartTimer() {
    clearInterval(_rgTimer);
    let s = 60;
    const tEl = document.getElementById('rg-timer');
    const rEl = document.getElementById('rg-resend');
    rEl.classList.add('off'); tEl.textContent = 'Resend in 60s';
    _rgTimer = setInterval(() => {
        s--;
        tEl.textContent = s > 0 ? 'Resend in ' + s + 's' : '';
        if (s <= 0) { clearInterval(_rgTimer); rEl.classList.remove('off'); }
    }, 1000);
}

function rgOtpIn(i) {
    const b = document.getElementById('rg-ob' + i);
    b.value = b.value.replace(/[^0-9]/g, '').slice(-1);
    b.classList.toggle('done', !!b.value);
    b.classList.remove('shake');
    if (b.value && i < 5) document.getElementById('rg-ob' + (i+1)).focus();
    const allFilled = [0,1,2,3,4,5].every(j => document.getElementById('rg-ob'+j).value);
    if (allFilled) rgVerifyAndCreate();
}

function rgOtpKey(e, i) {
    if (e.key === 'Backspace' && !document.getElementById('rg-ob'+i).value && i > 0)
        document.getElementById('rg-ob' + (i-1)).focus();
}


// ── Register — Step 2: verify OTP & create account ────────
async function rgVerifyAndCreate() {
    const otp = [0,1,2,3,4,5].map(i => document.getElementById('rg-ob'+i).value).join('');
    const err = document.getElementById('rg-err2');
    err.textContent = '';
    if (otp.length < 6) { err.textContent = 'Enter the complete 6-digit OTP.'; return; }
    const m = document.getElementById('rg-m').value.trim();
    try {
        const res = await fetch(`${API}/register/verify-otp`, {
            method: 'POST', headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ mobile: m, otp: otp })
        });
        const d = await res.json();
        if (!res.ok) throw new Error(d.error || 'Verification failed');
        clearInterval(_rgTimer);
        showToast('✅ Account created! Please sign in.', 'success');
        switchTab('login');
        document.getElementById('li-u').value = document.getElementById('rg-u').value.trim();
    } catch(e) {
        err.textContent = e.message;
        [0,1,2,3,4,5].forEach(i => {
            const b = document.getElementById('rg-ob'+i);
            b.classList.add('shake');
            setTimeout(() => b.classList.remove('shake'), 1200);
        });
    }
}


// ── Forgot Password — 3-step flow ─────────────────────────
let _fpMobile = '', _fpToken = '', _fpTimer = null;

// step: 0=back to login, 1=enter mobile, 2=OTP, 3=new password
function fpShow(step) {
    ['login-form','fp1','fp2','fp3','fu1','fu2','fu3'].forEach(id =>
        document.getElementById(id)?.classList.remove('active')
    );
    if (step === 0) document.getElementById('login-form').classList.add('active');
    else            document.getElementById('fp' + step).classList.add('active');
    document.getElementById('li-err').textContent = '';
    if (step === 1) setTimeout(() => document.getElementById('fp-mob').focus(), 80);
    if (step === 2) setTimeout(() => document.getElementById('fp-ob0').focus(), 80);
    if (step === 3) setTimeout(() => document.getElementById('fp-np').focus(), 80);
}

async function fpSendOtp(isResend = false) {
    const mob   = isResend ? _fpMobile : document.getElementById('fp-mob').value.trim();
    const errEl = document.getElementById('fp-err1');
    errEl.textContent = '';
    if (!/^[0-9]{10}$/.test(mob)) { errEl.textContent = 'Enter a valid 10-digit mobile number.'; return; }
    _fpMobile = mob;
    try {
        const res = await fetch(`${API}/forgot-password/send-otp`, {
            method: 'POST', headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ mobile: mob })
        });
        const d = await res.json();
        if (!res.ok) throw new Error(d.error || 'Failed to send OTP');
        const masked = '+91 ' + mob.slice(0,2) + 'XXXXXX' + mob.slice(-2);
        document.getElementById('fp-sent-lbl').textContent = d.dev
            ? '⚠️ DEV MODE — Check Flask terminal for OTP'
            : 'OTP sent to ' + masked;
        for (let i = 0; i < 6; i++) {
            const b = document.getElementById('fp-ob' + i);
            b.value = ''; b.classList.remove('done', 'shake');
        }
        document.getElementById('fp-err2').textContent = '';
        fpShow(2); fpStartTimer();
        showToast(d.dev ? '⚠️ Dev mode — check terminal for OTP' : 'OTP sent to ' + masked, d.dev ? 'info' : 'success');
    } catch(e) { document.getElementById('fp-err1').textContent = e.message; }
}

function fpStartTimer() {
    clearInterval(_fpTimer);
    let s = 60;
    const tEl = document.getElementById('fp-timer');
    const rEl = document.getElementById('fp-resend');
    rEl.classList.add('off'); tEl.textContent = 'Resend in 60s';
    _fpTimer = setInterval(() => {
        s--;
        tEl.textContent = s > 0 ? 'Resend in ' + s + 's' : '';
        if (s <= 0) { clearInterval(_fpTimer); rEl.classList.remove('off'); }
    }, 1000);
}

function fpOtpIn(i) {
    const b = document.getElementById('fp-ob' + i);
    b.value = b.value.replace(/[^0-9]/g, '').slice(-1);
    b.classList.toggle('done', !!b.value);
    b.classList.remove('shake');
    if (b.value && i < 5) document.getElementById('fp-ob' + (i+1)).focus();
    const allFilled = [0,1,2,3,4,5].every(j => document.getElementById('fp-ob'+j).value);
    if (allFilled) fpVerifyOtp();
}

function fpOtpKey(e, i) {
    if (e.key === 'Backspace' && !document.getElementById('fp-ob'+i).value && i > 0)
        document.getElementById('fp-ob' + (i-1)).focus();
}

async function fpVerifyOtp() {
    const otp   = [0,1,2,3,4,5].map(i => document.getElementById('fp-ob'+i).value).join('');
    const errEl = document.getElementById('fp-err2');
    errEl.textContent = '';
    if (otp.length < 6) { errEl.textContent = 'Enter the complete 6-digit OTP.'; return; }
    try {
        const res = await fetch(`${API}/forgot-password/verify-otp`, {
            method: 'POST', headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ mobile: _fpMobile, otp: otp })
        });
        const d = await res.json();
        if (!res.ok) throw new Error(d.error || 'Invalid OTP');
        _fpToken = d.reset_token;
        clearInterval(_fpTimer);
        document.getElementById('fp-err3').textContent = '';
        document.getElementById('fp-ok3').textContent  = '';
        fpShow(3);
    } catch(e) {
        errEl.textContent = e.message;
        [0,1,2,3,4,5].forEach(i => {
            const b = document.getElementById('fp-ob'+i);
            b.classList.add('shake');
            setTimeout(() => b.classList.remove('shake'), 1200);
        });
    }
}

async function fpResetPass() {
    const np  = document.getElementById('fp-np').value;
    const cp  = document.getElementById('fp-cp').value;
    const err = document.getElementById('fp-err3');
    const ok  = document.getElementById('fp-ok3');
    err.textContent = ''; ok.textContent = '';
    if (!np)           { err.textContent = 'Enter a new password.'; return; }
    if (np.length < 4) { err.textContent = 'Password must be at least 4 characters.'; return; }
    if (np !== cp)     { err.textContent = 'Passwords do not match.'; return; }
    try {
        const res = await fetch(`${API}/forgot-password/reset`, {
            method: 'POST', headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ reset_token: _fpToken, new_password: np })
        });
        const d = await res.json();
        if (!res.ok) throw new Error(d.error || 'Reset failed');
        ok.textContent = '✅ Password reset! You can now sign in.';
        _fpToken = ''; _fpMobile = '';
        setTimeout(() => fpShow(0), 2000);
    } catch(e) { err.textContent = e.message; }
}


// ── Forgot Username — 3-step flow ─────────────────────────
let _fuMobile = '', _fuTimer = null;

// step: 0=back to login, 1=enter mobile, 2=OTP, 3=show username
function fuShow(step) {
    ['login-form','fp1','fp2','fp3','fu1','fu2','fu3'].forEach(id =>
        document.getElementById(id)?.classList.remove('active')
    );
    if (step === 0) document.getElementById('login-form').classList.add('active');
    else            document.getElementById('fu' + step).classList.add('active');
    if (step === 1) setTimeout(() => document.getElementById('fu-mob').focus(), 80);
    if (step === 2) setTimeout(() => document.getElementById('fu-ob0').focus(), 80);
}

async function fuSendOtp(isResend = false) {
    const mob   = isResend ? _fuMobile : document.getElementById('fu-mob').value.trim();
    const errEl = document.getElementById('fu-err1');
    errEl.textContent = '';
    if (!/^[0-9]{10}$/.test(mob)) { errEl.textContent = 'Enter a valid 10-digit mobile number.'; return; }
    _fuMobile = mob;
    try {
        const res = await fetch(`${API}/forgot-username/send-otp`, {
            method: 'POST', headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ mobile: mob })
        });
        const d = await res.json();
        if (!res.ok) throw new Error(d.error || 'Failed to send OTP');
        const masked = '+91 ' + mob.slice(0,2) + 'XXXXXX' + mob.slice(-2);
        document.getElementById('fu-sent-lbl').textContent = d.dev
            ? '⚠️ DEV MODE — Check Flask terminal for OTP'
            : 'OTP sent to ' + masked;
        for (let i = 0; i < 6; i++) {
            const b = document.getElementById('fu-ob' + i);
            b.value = ''; b.classList.remove('done', 'shake');
        }
        document.getElementById('fu-err2').textContent = '';
        fuShow(2); fuStartTimer();
        showToast(d.dev ? '⚠️ Dev mode — check terminal for OTP' : 'OTP sent to ' + masked, d.dev ? 'info' : 'success');
    } catch(e) { document.getElementById('fu-err1').textContent = e.message; }
}

function fuStartTimer() {
    clearInterval(_fuTimer);
    let s = 60;
    const tEl = document.getElementById('fu-timer');
    const rEl = document.getElementById('fu-resend');
    rEl.classList.add('off'); tEl.textContent = 'Resend in 60s';
    _fuTimer = setInterval(() => {
        s--;
        tEl.textContent = s > 0 ? 'Resend in ' + s + 's' : '';
        if (s <= 0) { clearInterval(_fuTimer); rEl.classList.remove('off'); }
    }, 1000);
}

function fuOtpIn(i) {
    const b = document.getElementById('fu-ob' + i);
    b.value = b.value.replace(/[^0-9]/g, '').slice(-1);
    b.classList.toggle('done', !!b.value);
    b.classList.remove('shake');
    if (b.value && i < 5) document.getElementById('fu-ob' + (i+1)).focus();
    const allFilled = [0,1,2,3,4,5].every(j => document.getElementById('fu-ob'+j).value);
    if (allFilled) fuVerifyOtp();
}

function fuOtpKey(e, i) {
    if (e.key === 'Backspace' && !document.getElementById('fu-ob'+i).value && i > 0)
        document.getElementById('fu-ob' + (i-1)).focus();
}

async function fuVerifyOtp() {
    const otp   = [0,1,2,3,4,5].map(i => document.getElementById('fu-ob'+i).value).join('');
    const errEl = document.getElementById('fu-err2');
    errEl.textContent = '';
    if (otp.length < 6) { errEl.textContent = 'Enter the complete 6-digit OTP.'; return; }
    try {
        const res = await fetch(`${API}/forgot-username/verify-otp`, {
            method: 'POST', headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ mobile: _fuMobile, otp: otp })
        });
        const d = await res.json();
        if (!res.ok) throw new Error(d.error || 'Invalid OTP');
        clearInterval(_fuTimer);
        document.getElementById('fu-result').textContent = d.username;
        document.getElementById('fu-ok3').textContent = '✅ Verified! Use this username to sign in.';
        fuShow(3);
    } catch(e) {
        errEl.textContent = e.message;
        [0,1,2,3,4,5].forEach(i => {
            const b = document.getElementById('fu-ob'+i);
            b.classList.add('shake');
            setTimeout(() => b.classList.remove('shake'), 1200);
        });
    }
}

// Auto-fill the recovered username into the login field
function fuGoLogin() {
    const username = document.getElementById('fu-result').textContent;
    fuShow(0);
    document.getElementById('li-u').value = username;
    document.getElementById('li-p').focus();
    _fuMobile = '';
}