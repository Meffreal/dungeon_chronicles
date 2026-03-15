// ── NOTIFIKACE ────────────────────────────────────────────────────────────
let notifPollInterval = null;

async function loadNotifications() {
  try {
    const d = await api('GET', '/notifications/');
    renderNotifications(d.notifications);
    updateNotifBadge(d.unread);
  } catch(e) {}
}

function updateNotifBadge(count) {
  const badge = document.getElementById('notif-badge');
  const bell  = document.getElementById('notif-bell');
  if (!badge) return;
  if (count > 0) {
    badge.textContent = count > 9 ? '9+' : count;
    badge.style.display = 'flex';
    if (bell) bell.classList.add('has-notif');
  } else {
    badge.style.display = 'none';
    if (bell) bell.classList.remove('has-notif');
  }
}

function renderNotifications(notifs) {
  const el = document.getElementById('notif-list');
  if (!el) return;
  if (!notifs.length) {
    el.innerHTML = '<div class="notif-empty">Žádné notifikace 🎉<br><span style="font-size:.8rem;display:block;margin-top:6px">Jdi bojovat do arény nebo nakupovat na tržišti!</span></div>';
    return;
  }
  el.innerHTML = notifs.map(n => {
    const dt = new Date(n.created_at);
    const timeStr = `${dt.toLocaleDateString('cs')} ${String(dt.getHours()).padStart(2,'0')}:${String(dt.getMinutes()).padStart(2,'0')}`;
    return `<div class="notif-card ${n.is_read ? '' : 'unread'}" onclick="readNotif(${n.id}, this)">
      <div class="notif-icon">${n.icon}</div>
      <div class="notif-body">
        <div class="notif-title">${esc(n.title)}</div>
        ${n.body ? `<div class="notif-text">${esc(n.body)}</div>` : ''}
        <div class="notif-time">${timeStr}</div>
      </div>
    </div>`;
  }).join('');
}

async function readNotif(id, el) {
  el.classList.remove('unread');
  try {
    await api('POST', `/notifications/read/${id}`);
    const d = await api('GET', '/notifications/');
    updateNotifBadge(d.unread);
  } catch(e) {}
}

async function markAllRead() {
  try {
    await api('POST', '/notifications/read-all');
    await loadNotifications();
    toast('Vše označeno jako přečteno', 'i', 2000);
  } catch(e) { toast(e.message, 'e'); }
}

async function clearNotifs() {
  try {
    const d = await api('DELETE', '/notifications/clear');
    await loadNotifications();
    toast(`Smazáno ${d.deleted} notifikací`, 'i', 2000);
  } catch(e) { toast(e.message, 'e'); }
}

function startNotifPolling() {
  if (notifPollInterval) clearInterval(notifPollInterval);
  notifPollInterval = setInterval(async () => {
    try {
      const d = await api('GET', '/notifications/');
      updateNotifBadge(d.unread);
    } catch(e) {}
  }, 30000);
}
