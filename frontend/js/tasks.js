// ============================================================
// tasks.js — Task CRUD, rendering, filtering, sorting, search
// ============================================================


// ── Load tasks from server and render ────────────────────
async function loadTasks() {
    let url = '/tasks?';
    if (curFilter && curFilter !== 'all') url += `status=${curFilter}&`;
    if (curCat)    url += `category=${curCat}&`;
    if (curSort)   url += `sort=${curSort}&`;
    if (searchQ)   url += `search=${encodeURIComponent(searchQ)}&`;
    try {
        const res = await api(url);
        tasks = await res.json();
        if (_notifEnabled) checkTaskNotifications();
        renderTasks();
    } catch(e) {
        document.getElementById('task-list').innerHTML =
            `<div style="text-align:center;padding:60px;color:var(--red)">⚠️ Cannot reach server. Is Flask running on port 5000?</div>`;
    }
}

// ── Render the task list HTML ─────────────────────────────
function renderTasks() {
    const el = document.getElementById('task-list');
    if (!tasks.length) {
        el.innerHTML = `<div class="task-empty"><div class="ei">📭</div><h3>No tasks here</h3><p>Add a task using the button above.</p></div>`;
        return;
    }
    el.innerHTML = tasks.map(t => {
        const done = t.is_done === 1;
        const dCls = dueCls(t.due_date, done);
        const dLbl = fmtDue(t.due_date);
        const cCls = (t.category || 'personal').toLowerCase();
        const pCls = (t.priority  || 'medium').toLowerCase();
        return `<div class="task-card ${done ? 'done-card' : ''}">
            <div class="t-check ${done ? 'checked' : ''}" onclick="toggleDone(${t.id})">${done ? '✓' : ''}</div>
            <div class="t-pri ${pCls}"></div>
            <div class="t-body">
                <div class="t-title">${esc(t.title)}</div>
                ${t.description ? `<div class="t-desc">${esc(t.description)}</div>` : ''}
                <div class="t-meta">
                    <span class="t-tag ${cCls}">${cap(t.category)}</span>
                    ${dLbl ? `<span class="t-due ${dCls}">📅 ${dLbl}</span>` : ''}
                </div>
            </div>
            <div class="t-actions">
                <button class="t-btn" onclick="openModal(${t.id})">✏️</button>
                <button class="t-btn del" onclick="askDelTask(${t.id})">🗑️</button>
            </div>
        </div>`;
    }).join('');
}


// ── Filter chips ──────────────────────────────────────────
function setFilter(f) {
    curFilter = f; curCat = '';
    document.querySelectorAll('.f-chip').forEach(c =>
        c.className = 'f-chip' + (c.dataset.f === f ? ' on ' + f : '')
    );
    document.querySelectorAll('.cat-tab').forEach(c =>
        c.classList.toggle('on', c.dataset.c === '')
    );
    const titles = { all:'All Tasks', today:'Due Today', pending:'Pending', done:'Completed', overdue:'Overdue' };
    document.getElementById('tasks-title').textContent = titles[f] || 'All Tasks';
    loadTasks();
}

// ── Category tabs ─────────────────────────────────────────
function setCat(cat) {
    curCat = cat; curFilter = 'all';
    document.querySelectorAll('.f-chip').forEach(c =>
        c.classList.toggle('on', c.dataset.f === 'all')
    );
    document.querySelectorAll('.cat-tab').forEach(c =>
        c.classList.toggle('on', c.dataset.c === cat)
    );
    document.getElementById('tasks-title').textContent = cat ? cap(cat) + ' Tasks' : 'All Tasks';
    loadTasks();
}

// ── Sort dropdown ─────────────────────────────────────────
function onSort(v) { curSort = v; loadTasks(); }

// ── Search (debounced 300ms) ──────────────────────────────
let sTimer;
function onSearch(v) { searchQ = v; clearTimeout(sTimer); sTimer = setTimeout(loadTasks, 300); }


// ── Add/Edit task modal ───────────────────────────────────
function openModal(id = null) {
    editingId = id;
    document.getElementById('t-title-err').textContent = '';
    document.getElementById('t-date-err').textContent  = '';
    const now = new Date();
    now.setMinutes(now.getMinutes() - now.getTimezoneOffset()); // local timezone fix
    if (id) {
        const t = tasks.find(x => x.id === id); if (!t) return;
        document.getElementById('modal-ttl').textContent = 'Edit Task';
        document.getElementById('t-title').value = t.title || '';
        document.getElementById('t-desc').value  = t.description || '';
        document.getElementById('t-cat').value   = (t.category || 'personal').toLowerCase();
        document.getElementById('t-date').value  = t.due_date || '';
        document.getElementById('t-date').min    = now.toISOString().slice(0,16);
        setPri((t.priority || 'medium').toLowerCase());
    } else {
        document.getElementById('modal-ttl').textContent = 'Add New Task';
        document.getElementById('t-title').value = '';
        document.getElementById('t-desc').value  = '';
        document.getElementById('t-cat').value   = 'work';
        document.getElementById('t-date').value  = '';
        document.getElementById('t-date').min    = now.toISOString().slice(0,16);
        setPri('high');
    }
    document.getElementById('task-overlay').classList.add('open');
    setTimeout(() => document.getElementById('t-title').focus(), 80);
}

function closeModal() {
    document.getElementById('task-overlay').classList.remove('open');
}

// ── Priority selector ─────────────────────────────────────
function setPri(p) {
    selPri = p;
    document.querySelectorAll('.pri-btn').forEach(b =>
        b.classList.toggle('sel', b.dataset.p === p)
    );
}


// ── Save (create or update) ───────────────────────────────
async function saveTask() {
    const title   = document.getElementById('t-title').value.trim();
    const dateVal = document.getElementById('t-date').value;
    document.getElementById('t-title-err').textContent = '';
    document.getElementById('t-date-err').textContent  = '';
    if (!title) {
        document.getElementById('t-title-err').textContent = 'Title is required.';
        document.getElementById('t-title').focus(); return;
    }
    if (!dateVal) {
        document.getElementById('t-date-err').textContent = 'Due date & time is required.';
        document.getElementById('t-date').focus(); return;
    }
    if (new Date(dateVal) < new Date()) {
        document.getElementById('t-date-err').textContent = 'Due date & time cannot be in the past.';
        document.getElementById('t-date').focus(); return;
    }
    const payload = {
        title,
        description: document.getElementById('t-desc').value.trim(),
        category:    document.getElementById('t-cat').value,
        due_date:    dateVal,
        priority:    selPri
    };
    try {
        const res = editingId
            ? await api(`/tasks/${editingId}`, { method: 'PUT',  body: JSON.stringify(payload) })
            : await api('/tasks',              { method: 'POST', body: JSON.stringify(payload) });
        if (!res.ok) { const d = await res.json(); throw new Error(d.error || 'Failed'); }
        closeModal();
        showToast(editingId ? '✅ Task updated!' : '✅ Task added!', 'success');
        await loadTasks(); await loadStats(); refreshViews();
    } catch(e) { showToast(e.message, 'error'); }
}


// ── Toggle done/undone ────────────────────────────────────
async function toggleDone(id) {
    try {
        await api(`/tasks/${id}/done`, { method: 'PATCH' });
        await loadTasks(); await loadStats(); refreshViews();
    } catch(e) { showToast('Update failed', 'error'); }
}


// ── Delete task (with confirm dialog) ─────────────────────
function askDelTask(id) {
    deleteTaskId = id;
    document.getElementById('del-task-overlay').classList.add('open');
}
function closeDelTask() {
    deleteTaskId = null;
    document.getElementById('del-task-overlay').classList.remove('open');
}
async function doDeleteTask() {
    if (!deleteTaskId) return;
    try {
        const res = await api(`/tasks/${deleteTaskId}`, { method: 'DELETE' });
        if (!res.ok) throw new Error('Delete failed');
        closeDelTask();
        showToast('🗑️ Task deleted.', 'success');
        await loadTasks(); await loadStats(); refreshViews();
    } catch(e) { showToast(e.message, 'error'); }
}


// ── Stats (sidebar badges + overview numbers) ─────────────
async function loadStats() {
    try {
        const res = await api('/stats');
        const d   = await res.json();
        document.getElementById('b-all').textContent   = d.total;
        document.getElementById('b-today').textContent = d.today;
        document.getElementById('b-pend').textContent  = d.pending;
        document.getElementById('b-done').textContent  = d.completed;
        document.getElementById('f-pend').textContent  = d.pending;
        document.getElementById('f-done').textContent  = d.completed;
        document.getElementById('f-over').textContent  = d.overdue;
        document.getElementById('sc-total').textContent = d.total;
        document.getElementById('sc-today').textContent = d.today;
        document.getElementById('sc-comp').textContent  = d.completed;
        document.getElementById('sc-over').textContent  = d.overdue;
        document.getElementById('rl-comp').textContent  = d.completed;
        document.getElementById('rl-pend').textContent  = d.pending;
        document.getElementById('rl-over').textContent  = d.overdue;
        const pct  = d.progress || 0;
        const circ = 2 * Math.PI * 58;
        document.getElementById('ring-arc').setAttribute('stroke-dashoffset', circ - (pct/100)*circ);
        document.getElementById('ring-pct-txt').textContent = Math.round(pct) + '%';
    } catch(e) {}
}



// ── Overview: today's tasks list ─────────────────────────
async function loadTodayTasks() {
    try {
        const res  = await api('/tasks?status=today');
        const data = await res.json();
        const el   = document.getElementById('ov-today-list');
        if (!data.length) {
            el.innerHTML = `<div style="text-align:center;padding:24px;color:var(--ink3);font-size:13px">🎉 No tasks due today!</div>`;
            return;
        }
        el.innerHTML = data.map(t => {
            const done = t.is_done === 1;
            return `<div class="mini-t">
                <div class="t-check ${done ? 'checked' : ''}" style="width:16px;height:16px;font-size:9px" onclick="toggleDone(${t.id})">${done ? '✓' : ''}</div>
                <span class="mini-t-name ${done ? 'done' : ''}">${esc(t.title)}</span>
                <span class="mini-t-st ${done ? 'done' : 'tod'}">${done ? 'Done' : 'Today'}</span>
            </div>`;
        }).join('');
    } catch(e) {}
}


// ── Categories view ───────────────────────────────────────
async function loadCategories() {
    try {
        const [w, p, s] = await Promise.all([
            api('/tasks?category=work').then(r => r.json()),
            api('/tasks?category=personal').then(r => r.json()),
            api('/tasks?category=study').then(r => r.json()),
        ]);
        const cats = [
            { name: 'Work',     icon: '💼', color: 'var(--brand)',  tasks: w },
            { name: 'Personal', icon: '🏠', color: 'var(--purple)', tasks: p },
            { name: 'Study',    icon: '📚', color: 'var(--green)',  tasks: s },
        ];
        document.getElementById('cat-list').innerHTML = cats.map(cat => {
            const tot = cat.tasks.length;
            const don = cat.tasks.filter(t => t.is_done === 1).length;
            const pct = tot ? Math.round(don / tot * 100) : 0;
            const k   = cat.name.toLowerCase();
            return `<div class="cat-card-wrap" id="cc-${k}">
                <div class="cat-card-head" onclick="toggleCatCard('${k}')">
                    <span class="cat-ci">${cat.icon}</span>
                    <div class="cat-cd">
                        <div class="cat-cd-name">${cat.name}</div>
                        <div class="cat-cd-sub">${tot} tasks · ${don} completed</div>
                    </div>
                    <div class="cat-right">
                        <div class="cat-bar-track"><div class="cat-bar-fill" style="width:${pct}%;background:${cat.color}"></div></div>
                        <span class="cat-pct">${pct}%</span>
                        <span class="cat-chev">›</span>
                    </div>
                </div>
                <div class="cat-body">
                    ${tot ? cat.tasks.map(t =>
                        `<div class="cat-t-item">
                            <div class="cat-mini-cb ${t.is_done ? 'ck' : ''}" onclick="toggleDone(${t.id}).then(()=>loadCategories())">${t.is_done ? '✓' : ''}</div>
                            <span class="cat-t-name ${t.is_done ? 'done' : ''}">${esc(t.title)}</span>
                            ${isOver(t.due_date, t.is_done) ? '<span class="ov-badge">Overdue</span>' : ''}
                        </div>`
                    ).join('') : '<div style="padding:12px 0;font-size:13px;color:var(--ink3)">No tasks in this category.</div>'}
                </div>
            </div>`;
        }).join('');
    } catch(e) {}
}

function toggleCatCard(k) {
    document.getElementById('cc-' + k).classList.toggle('open');
}