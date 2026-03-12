// ============================================================
// notifications.js — Push notifications (5-min warning + on-time)
// Uses the Service Worker API for background delivery.
// ============================================================



// ── Register a Service Worker via blob URL ────────────────
// This lets notifications appear even when the tab is not focused.
if ('serviceWorker' in navigator) {
    const swCode = `
self.addEventListener('message', e => {
    if (e.data && e.data.type === 'SHOW_NOTIF') {
        self.registration.showNotification(e.data.title, {
            body: e.data.body,
            icon: e.data.icon || '/favicon.ico',
            tag:  e.data.tag,
            requireInteraction: false,
            vibrate: [200, 100, 200]
        });
    }
});
self.addEventListener('notificationclick', e => {
    e.notification.close();
    e.waitUntil(clients.matchAll({ type: 'window' }).then(cs => {
        if (cs.length) cs[0].focus(); else clients.openWindow('/');
    }));
});`;
    const swBlob = new Blob([swCode], { type: 'text/javascript' });
    navigator.serviceWorker.register(URL.createObjectURL(swBlob))
        .then(reg => { window._swReg = reg; })
        .catch(() => {});
}


// ── Send a native notification ────────────────────────────
// Uses the Service Worker if available, falls back to direct Notification API.
function _showNotif(title, body, tag) {
    if (Notification.permission !== 'granted') return;
    const icon = 'data:image/svg+xml,<svg xmlns=%22http://www.w3.org/2000/svg%22 viewBox=%220 0 100 100%22><text y=%22.9em%22 font-size=%2290%22>✅</text></svg>';
    if (window._swReg && window._swReg.active) {
        window._swReg.active.postMessage({ type: 'SHOW_NOTIF', title, body, tag, icon });
    } else {
        new Notification(title, { body, tag, icon });
    }
}


// ── Check all tasks and fire any due notifications ────────
// Called on load and every 30 seconds by the scheduler.
function checkTaskNotifications() {
    if (!_notifEnabled || Notification.permission !== 'granted') return;
    const now    = new Date();
    const fiveMs = 5 * 60 * 1000;       // 5 minutes in ms
    const win    = 35_000;              // ±35s window around the exact moment

    // Clean up fired keys for tasks that are now done or deleted
    Object.keys(_notifFired).forEach(key => {
        const id = parseInt(key.split('_')[0]);
        const t  = tasks.find(x => x.id === id);
        if (!t || t.is_done) delete _notifFired[key];
    });

    tasks.forEach(t => {
        if (!t.due_date || t.is_done) return;
        const due    = new Date(t.due_date);
        const diff   = due - now;
        const label  = t.title.length > 40 ? t.title.slice(0, 37) + '...' : t.title;
        const dueStr = due.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' });

        // Fire "5 minutes left" warning
        const key5 = t.id + '_5min';
        if (!_notifFired[key5] && diff > 0 && diff <= fiveMs + win && diff >= fiveMs - win) {
            _showNotif('⏰ Due in 5 minutes!', `"${label}" is due at ${dueStr}`, key5);
            _notifFired[key5] = true;
            localStorage.setItem('tf_notif_fired', JSON.stringify(_notifFired));
        }

        // Fire "due right now" alert
        const keyNow = t.id + '_ontime';
        if (!_notifFired[keyNow] && diff > -win && diff <= win) {
            _showNotif('🚨 Task Due Now!', `"${label}" was due at ${dueStr}. Mark it done!`, keyNow);
            _notifFired[keyNow] = true;
            localStorage.setItem('tf_notif_fired', JSON.stringify(_notifFired));
        }
    });
}


// ── Scheduler: check every 30 seconds ─────────────────────
function startNotifScheduler() {
    stopNotifScheduler();
    checkTaskNotifications();
    _notifInterval = setInterval(checkTaskNotifications, 30_000);
}

function stopNotifScheduler() {
    if (_notifInterval) { clearInterval(_notifInterval); _notifInterval = null; }
}


// ── On app load: quietly start scheduler if already allowed ─
function startNotifIfEnabled() {
    const tog = document.getElementById('notif-tog');
    if (!_notifEnabled) { if (tog) tog.classList.remove('on'); return; }
    if (tog) tog.classList.add('on');
    if (Notification.permission === 'granted') startNotifScheduler();
    // If permission is 'denied', silently disable the feature
    if (Notification.permission === 'denied') {
        _notifEnabled = false;
        localStorage.setItem('tf_notif', 'off');
        if (tog) tog.classList.remove('on');
    }
}


// ── Settings toggle: user enables/disables notifications ──
async function toggleNotifications() {
    const tog = document.getElementById('notif-tog');
    if (_notifEnabled) {
        // Turn off
        _notifEnabled = false;
        localStorage.setItem('tf_notif', 'off');
        if (tog) tog.classList.remove('on');
        stopNotifScheduler();
        showToast('🔕 Notifications disabled.', 'info');
    } else {
        // Turn on — request browser permission if not yet granted
        if (!('Notification' in window)) {
            showToast('Your browser does not support notifications.', 'error'); return;
        }
        if (Notification.permission === 'denied') {
            showToast('Notifications blocked — enable them in browser settings.', 'error'); return;
        }
        const perm = Notification.permission === 'granted'
            ? 'granted'
            : await Notification.requestPermission();
        if (perm !== 'granted') {
            showToast('Permission denied. Enable notifications in browser settings.', 'error'); return;
        }
        _notifEnabled = true;
        localStorage.setItem('tf_notif', 'on');
        if (tog) tog.classList.add('on');
        startNotifScheduler();
        showToast('🔔 Notifications enabled!', 'success');
    }
}