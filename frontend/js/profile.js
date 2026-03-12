// ============================================================
// profile.js — Edit Profile (name, photo, mobile OTP, password)
//              + Image Cropper
// ============================================================


// ── Load fresh profile data from server on every login ────
async function loadProfileFromServer() {
    try {
        const res = await api('/profile');
        if (!res.ok) return;
        const data = await res.json();
        curDisplay = data.display_name  || curUser;
        curMobile  = data.mobile        || '';
        curImg     = data.profile_image || '';
        saveLocal();
        updateUserUI();
        setGreeting();
    } catch(e) {}
}

// ── Update all avatar/name elements in the UI ─────────────
function updateUserUI() {
    const name = curDisplay || curUser || '?';
    const init = name.slice(0, 2).toUpperCase();

    const sbAv = document.getElementById('sb-av');
    sbAv.innerHTML = curImg ? `<img src="${curImg}" alt="av"/>` : init;
    document.getElementById('sb-name').textContent = name;

    const setAv = document.getElementById('set-av');
    setAv.innerHTML = curImg
        ? `<img src="${curImg}" alt="av"/><div class="s-av-ov">✏️</div>`
        : `${init}<div class="s-av-ov">✏️</div>`;
    document.getElementById('set-uname').textContent  = name;
    document.getElementById('set-mobile').textContent = curMobile || 'Not set';
}


// ============================================================
// MOBILE OTP — verify new number before saving
// ============================================================

let _mobTimer    = null;
let _mobVerified = '';   // number successfully OTP-verified this session
let _mobPending  = '';   // number currently being verified

// Called on every keystroke in the mobile field
function onProfMobileInput() {
    const val   = document.getElementById('prof-mobile').value.trim();
    const btn   = document.getElementById('mob-send-otp-btn');
    const badge = document.getElementById('mob-verified-badge');
    const panel = document.getElementById('mob-otp-panel');

    // If user edits the field while OTP panel is open, close it
    if (panel.classList.contains('open') && val !== _mobPending) {
        panel.classList.remove('open');
        stopMobTimer();
    }

    const isDifferent   = val !== (curMobile || '');
    const isFullNumber  = val.length === 10;
    const isVerified    = val === _mobVerified;

    btn.style.display   = (isDifferent && isFullNumber && !isVerified) ? 'inline-block' : 'none';
    badge.style.display = isVerified ? 'inline-flex' : 'none';
}

async function profMobileSendOtp(isResend) {
    const mob = document.getElementById('prof-mobile').value.trim();
    const err = document.getElementById('mob-otp-err');
    err.textContent = '';

    if (!/^[0-9]{10}$/.test(mob)) {
        err.textContent = 'Enter a valid 10-digit mobile number.';
        document.getElementById('mob-otp-panel').classList.add('open');
        return;
    }
    _mobPending = mob;

    try {
        const res = await api('/profile/mobile/send-otp', {
            method: 'POST',
            body: JSON.stringify({ mobile: mob })
        });
        const d = await res.json();
        if (!res.ok) throw new Error(d.error || 'Failed to send OTP');

        // Clear OTP boxes
        for (let i = 0; i < 6; i++) {
            const b = document.getElementById('mob-ob' + i);
            b.value = ''; b.classList.remove('done', 'shake');
        }
        const masked = '+91 ' + mob.slice(0, 2) + 'XXXXXX' + mob.slice(-2);
        document.getElementById('mob-otp-lbl').textContent = d.dev
            ? '⚠️ DEV MODE — check Flask terminal for OTP'
            : 'OTP sent to ' + masked;
        document.getElementById('mob-send-otp-btn').style.display = 'none';
        document.getElementById('mob-otp-panel').classList.add('open');
        startMobTimer();
        showToast(d.dev ? '⚠️ Dev mode — check terminal for OTP' : 'OTP sent to ' + masked,
                  d.dev ? 'info' : 'success');
        setTimeout(() => document.getElementById('mob-ob0').focus(), 80);

    } catch(e) {
        err.textContent = e.message;
        document.getElementById('mob-otp-panel').classList.add('open');
    }
}

async function profMobileVerifyOtp() {
    const otp = [0,1,2,3,4,5].map(i => document.getElementById('mob-ob' + i).value).join('');
    const err = document.getElementById('mob-otp-err');
    err.textContent = '';

    if (otp.length < 6) { err.textContent = 'Enter the complete 6-digit OTP.'; return; }

    try {
        const res = await api('/profile/mobile/verify-otp', {
            method: 'POST',
            body: JSON.stringify({ mobile: _mobPending, otp })
        });
        const d = await res.json();
        if (!res.ok) throw new Error(d.error || 'Invalid OTP');

        // Mark verified and update local state immediately
        _mobVerified = _mobPending;
        curMobile    = _mobPending;
        saveLocal();

        stopMobTimer();
        document.getElementById('mob-otp-panel').classList.remove('open');
        document.getElementById('mob-send-otp-btn').style.display   = 'none';
        document.getElementById('mob-verified-badge').style.display = 'inline-flex';
        updateUserUI();
        showToast('✅ Mobile number verified and saved!', 'success');

    } catch(e) {
        err.textContent = e.message;
        [0,1,2,3,4,5].forEach(i => {
            const b = document.getElementById('mob-ob' + i);
            b.classList.add('shake');
            setTimeout(() => b.classList.remove('shake'), 1200);
        });
    }
}

function cancelMobOtp() {
    stopMobTimer();
    document.getElementById('mob-otp-panel').classList.remove('open');
    document.getElementById('prof-mobile').value            = curMobile || '';
    document.getElementById('mob-send-otp-btn').style.display = 'none';
    document.getElementById('mob-otp-err').textContent      = '';
    _mobPending = '';
}

function startMobTimer() {
    stopMobTimer();
    let s = 60;
    const tEl = document.getElementById('mob-otp-timer');
    const rEl = document.getElementById('mob-otp-resend');
    rEl.classList.add('off');
    tEl.textContent = 'Resend in 60s';
    _mobTimer = setInterval(() => {
        s--;
        tEl.textContent = s > 0 ? 'Resend in ' + s + 's' : '';
        if (s <= 0) { clearInterval(_mobTimer); rEl.classList.remove('off'); }
    }, 1000);
}

function stopMobTimer() {
    if (_mobTimer) { clearInterval(_mobTimer); _mobTimer = null; }
}

function mobOtpIn(i) {
    const b = document.getElementById('mob-ob' + i);
    b.value = b.value.replace(/[^0-9]/g, '').slice(-1);
    b.classList.toggle('done', !!b.value);
    b.classList.remove('shake');
    if (b.value && i < 5) document.getElementById('mob-ob' + (i + 1)).focus();
    if ([0,1,2,3,4,5].every(j => document.getElementById('mob-ob' + j).value)) profMobileVerifyOtp();
}

function mobOtpKey(e, i) {
    if (e.key === 'Backspace' && !document.getElementById('mob-ob' + i).value && i > 0)
        document.getElementById('mob-ob' + (i - 1)).focus();
}


// ============================================================
// OPEN / CLOSE / SAVE PROFILE
// ============================================================

function openEditProfile() {
    pendingImg   = null;
    _mobVerified = '';
    _mobPending  = '';

    document.getElementById('prof-err').textContent      = '';
    document.getElementById('prof-username').value       = curUser    || '';
    document.getElementById('prof-name').value           = curDisplay || curUser || '';
    document.getElementById('prof-mobile').value         = curMobile  || '';
    document.getElementById('prof-curr').value           = '';
    document.getElementById('prof-new').value            = '';
    document.getElementById('prof-conf').value           = '';

    // Reset OTP panel
    document.getElementById('mob-otp-panel').classList.remove('open');
    document.getElementById('mob-send-otp-btn').style.display   = 'none';
    document.getElementById('mob-verified-badge').style.display = 'none';
    document.getElementById('mob-otp-err').textContent           = '';
    for (let i = 0; i < 6; i++) {
        const b = document.getElementById('mob-ob' + i);
        if (b) { b.value = ''; b.classList.remove('done', 'shake'); }
    }
    stopMobTimer();

    refreshProfPreview();
    document.getElementById('profile-overlay').classList.add('open');
}

function closeEditProfile() {
    cancelMobOtp();
    _mobVerified = '';
    document.getElementById('profile-overlay').classList.remove('open');
}

function refreshProfPreview() {
    const prev = document.getElementById('prof-prev');
    const name = document.getElementById('prof-name').value.trim() || curDisplay || curUser || '?';
    const src  = pendingImg && pendingImg !== '__remove__'
        ? pendingImg
        : (pendingImg === '__remove__' ? null : curImg);
    prev.innerHTML = src ? `<img src="${src}" alt="preview"/>` : name.slice(0, 2).toUpperCase();
}

function removeProfileImg() {
    pendingImg = '__remove__';
    document.getElementById('prof-prev').innerHTML = (curDisplay || curUser || '?').slice(0, 2).toUpperCase();
    showToast('Photo will be removed on save.');
}

async function saveProfile() {
    const err = document.getElementById('prof-err');
    err.textContent = '';

    const new_username = document.getElementById('prof-username').value.trim();
    const display_name = document.getElementById('prof-name').value.trim();
    const mobile       = document.getElementById('prof-mobile').value.trim();
    const curr_pass    = document.getElementById('prof-curr').value;
    const new_pass     = document.getElementById('prof-new').value;
    const conf_pass    = document.getElementById('prof-conf').value;

    if (new_username && new_username.length < 3)               { err.textContent = 'Username must be at least 3 characters.'; return; }
    if (new_username && !/^[a-zA-Z0-9_]+$/.test(new_username)) { err.textContent = 'Username: only letters, numbers and underscores.'; return; }
    if (mobile && !/^\d{10}$/.test(mobile))                    { err.textContent = 'Mobile must be exactly 10 digits.'; return; }

    // Block save if mobile changed but OTP not yet verified
    if (mobile && mobile !== (curMobile || '') && mobile !== _mobVerified) {
        err.textContent = 'Please verify your new mobile number with OTP before saving.';
        document.getElementById('mob-send-otp-btn').style.display = 'inline-block';
        document.getElementById('prof-mobile').focus();
        return;
    }

    if (new_pass && new_pass !== conf_pass) { err.textContent = 'New passwords do not match.'; return; }
    if (new_pass && !curr_pass)             { err.textContent = 'Current password is required to set a new password.'; return; }
    if (new_pass && new_pass.length < 4)    { err.textContent = 'New password must be at least 4 characters.'; return; }

    const payload = {};
    if (new_username && new_username !== curUser) payload.username = new_username;
    if (display_name)  payload.display_name = display_name;
    // Mobile is saved directly by the verify-otp endpoint — don't send it here again
    if (new_pass) { payload.new_password = new_pass; payload.current_password = curr_pass; }
    if (pendingImg === '__remove__') payload.profile_image = '';
    else if (pendingImg)             payload.profile_image = pendingImg;

    // Only mobile was changed (already saved via OTP verify)
    if (Object.keys(payload).length === 0) {
        closeEditProfile();
        showToast('✅ Profile updated!', 'success');
        return;
    }

    try {
        const res  = await api('/profile', { method: 'PUT', body: JSON.stringify(payload) });
        const data = await res.json();
        if (!res.ok) throw new Error(data.error || 'Update failed');

        if (data.username) { curUser = data.username; localStorage.setItem('tf_user', curUser); }
        curDisplay = data.display_name  || display_name || curDisplay;
        curImg     = data.profile_image !== undefined ? data.profile_image : curImg;
        saveLocal();
        closeEditProfile();
        updateUserUI();
        setGreeting();
        showToast('✅ Profile updated successfully!', 'success');
    } catch(e) { err.textContent = e.message; }
}


// ============================================================
// IMAGE FILE INPUT → open cropper
// ============================================================

function onImgSelect(e) {
    const file = e.target.files[0]; if (!file) return;
    if (file.size > 10 * 1024 * 1024) { showToast('Image must be under 10MB', 'error'); return; }
    const reader = new FileReader();
    reader.onload = ev => { cropImgSrc = ev.target.result; openCropper(); };
    reader.readAsDataURL(file);
    e.target.value = '';
}


// ============================================================
// IMAGE CROPPER
// ============================================================

function openCropper() {
    const img   = document.getElementById('crop-img');
    const stage = document.getElementById('crop-stage');
    img.src     = cropImgSrc;
    img.onload  = () => {
        const sw = stage.offsetWidth, sh = stage.offsetHeight;
        const iw = img.naturalWidth,  ih = img.naturalHeight;
        cropScale = Math.min(sw / iw, sh / ih, 1);
        cropImgX  = (sw - iw * cropScale) / 2;
        cropImgY  = (sh - ih * cropScale) / 2;
        const size = Math.min(sw, sh) * 0.65;
        cropX = (sw - size) / 2; cropY = (sh - size) / 2;
        cropW = size; cropH = size;
        document.getElementById('zoom-sl').value        = 100;
        document.getElementById('zoom-pct').textContent = '100%';
        renderCrop();
    };
    document.getElementById('cropper-overlay').classList.add('open');
}

function closeCropper() {
    document.getElementById('cropper-overlay').classList.remove('open');
}

function renderCrop() {
    const img = document.getElementById('crop-img');
    const box = document.getElementById('crop-box');
    img.style.transform = `translate(${cropImgX}px,${cropImgY}px) scale(${cropScale})`;
    box.style.cssText   = `left:${cropX}px;top:${cropY}px;width:${cropW}px;height:${cropH}px;position:absolute;border:2px solid #fff;box-shadow:0 0 0 9999px rgba(0,0,0,.5);cursor:move;box-sizing:border-box;`;
}

function setZoom(val) {
    const pct   = parseInt(val) / 100;
    const stage = document.getElementById('crop-stage');
    const img   = document.getElementById('crop-img');
    const sw = stage.offsetWidth, sh = stage.offsetHeight;
    const base  = Math.min(sw / img.naturalWidth, sh / img.naturalHeight, 1);
    cropScale = base * pct;
    cropImgX  = (sw - img.naturalWidth  * cropScale) / 2;
    cropImgY  = (sh - img.naturalHeight * cropScale) / 2;
    document.getElementById('zoom-pct').textContent = val + '%';
    renderCrop();
}

function cropDown(e) {
    if (e.target.classList.contains('crop-corner')) return;
    const sr = document.getElementById('crop-stage').getBoundingClientRect();
    const mx = e.clientX - sr.left, my = e.clientY - sr.top;
    if (mx >= cropX && mx <= cropX + cropW && my >= cropY && my <= cropY + cropH)
        _drag = { type:'box', startMx:mx, startMy:my, startX:cropX, startY:cropY };
}

function cropCorner(e, corner) {
    e.stopPropagation();
    const sr = document.getElementById('crop-stage').getBoundingClientRect();
    _drag = { type:'corner', corner, startMx:e.clientX-sr.left, startMy:e.clientY-sr.top,
              startX:cropX, startY:cropY, startW:cropW, startH:cropH };
}

function cropMove(e) {
    if (!_drag) return;
    const sr = document.getElementById('crop-stage').getBoundingClientRect();
    const mx = e.clientX - sr.left, my = e.clientY - sr.top;
    const dx = mx - _drag.startMx, dy = my - _drag.startMy;
    const sw = sr.width, sh = sr.height;
    if (_drag.type === 'box') {
        cropX = Math.max(0, Math.min(sw - cropW, _drag.startX + dx));
        cropY = Math.max(0, Math.min(sh - cropH, _drag.startY + dy));
    } else {
        const c = _drag.corner, minS = 40;
        let x = _drag.startX, y = _drag.startY, w = _drag.startW, h = _drag.startH;
        const d = Math.abs(dx) > Math.abs(dy) ? dx : dy;
        if (c==='br') { w=Math.max(minS,w+d); h=w; }
        if (c==='bl') { w=Math.max(minS,w-d); h=w; x=_drag.startX+_drag.startW-w; }
        if (c==='tr') { w=Math.max(minS,w+d); h=w; y=_drag.startY+_drag.startH-h; }
        if (c==='tl') { w=Math.max(minS,w-d); h=w; x=_drag.startX+_drag.startW-w; y=_drag.startY+_drag.startH-h; }
        cropX = Math.max(0, x); cropY = Math.max(0, y);
        cropW = Math.min(w, sw - cropX); cropH = Math.min(h, sh - cropY);
    }
    renderCrop();
}

function cropUp()    { _drag = null; }

function cropWheel(e) {
    e.preventDefault();
    const sl = document.getElementById('zoom-sl');
    const v  = Math.max(50, Math.min(300, parseInt(sl.value) + (e.deltaY < 0 ? 5 : -5)));
    sl.value = v; setZoom(v);
}


function applyCrop() {
    const canvas = document.createElement('canvas');
    const OUT = 300; canvas.width = OUT; canvas.height = OUT;
    const ctx = canvas.getContext('2d');
    const img = document.getElementById('crop-img');
    const srcX = (cropX - cropImgX) / cropScale;
    const srcY = (cropY - cropImgY) / cropScale;
    const srcW = cropW / cropScale;
    const srcH = cropH / cropScale;
    ctx.beginPath(); ctx.arc(OUT/2, OUT/2, OUT/2, 0, Math.PI*2); ctx.clip();
    ctx.drawImage(img, srcX, srcY, srcW, srcH, 0, 0, OUT, OUT);
    pendingImg = canvas.toDataURL('image/jpeg', 0.85);
    closeCropper();
    refreshProfPreview();
    showToast('Photo cropped! Click "Save Changes" to apply.', 'success');
}