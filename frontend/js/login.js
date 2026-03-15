const API = window.location.origin;

// ── Loading screen ────────────────────────────────────────────
window.addEventListener('load', () => {
  const token = localStorage.getItem('dc_token');
  if (token) {
    fetch(`${API}/auth/me`, { headers: { Authorization: `Bearer ${token}` } })
      .then(r => r.ok ? r.json() : null)
      .then(data => {
        if (data) {
          const hasChar = localStorage.getItem('dc_has_character') === 'true';
          if (!hasChar) localStorage.setItem('dc_new_user', '1');
          window.location.href = '/game';
        } else {
          localStorage.clear();
          hideLoading();
        }
      })
      .catch(() => hideLoading());
  } else {
    setTimeout(hideLoading, 800);
  }
});

function hideLoading() {
  document.getElementById('loading').classList.add('hidden');
}

// ── Tab přepínání ────────────────────────────────────────────
function switchTab(tab) {
  document.querySelectorAll('.tab-btn').forEach((b, i) => {
    b.classList.toggle('active', (i === 0) === (tab === 'login'));
  });
  document.getElementById('tab-login').classList.toggle('active', tab === 'login');
  document.getElementById('tab-register').classList.toggle('active', tab === 'register');
}

// ── Helpers ──────────────────────────────────────────────────
function showMsg(id, text, type = 'error') {
  const el = document.getElementById(id);
  el.textContent = text;
  el.className = `message ${type}`;
}
function setLoading(btnId, loading) {
  const btn = document.getElementById(btnId);
  btn.disabled = loading;
  btn.textContent = loading ? 'Chvíli strpení...' : btn.dataset.orig || btn.textContent;
  if (!loading && !btn.dataset.orig) btn.dataset.orig = btn.textContent;
}

async function apiPost(url, body) {
  const res = await fetch(`${API}${url}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
  const data = await res.json();
  if (!res.ok) throw new Error(data.detail || 'Chyba serveru');
  return data;
}

async function apiPostForm(url, body) {
  const form = new URLSearchParams(body);
  const res = await fetch(`${API}${url}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    body: form,
  });
  const data = await res.json();
  if (!res.ok) throw new Error(data.detail || 'Chyba serveru');
  return data;
}

function saveAuth(data) {
  localStorage.setItem('dc_token', data.access_token);
  localStorage.setItem('dc_username', data.username);
  localStorage.setItem('dc_has_character', data.has_character);
}

// ── Login ────────────────────────────────────────────────────
async function doLogin() {
  const username = document.getElementById('login-username').value.trim();
  const password = document.getElementById('login-password').value;
  if (!username || !password) return showMsg('login-msg', 'Vyplň všechna pole.');

  setLoading('login-btn', true);
  try {
    const data = await apiPostForm('/auth/login', { username, password });
    saveAuth(data);
    showMsg('login-msg', 'Přihlášení úspěšné! Vstupuješ...', 'success');
    setTimeout(() => {
      if (!data.has_character) {
        localStorage.setItem('dc_new_user', '1');
      }
      window.location.href = '/game';
    }, 600);
  } catch (e) {
    showMsg('login-msg', e.message);
    setLoading('login-btn', false);
  }
}

// ── Register ─────────────────────────────────────────────────
async function doRegister() {
  const username = document.getElementById('reg-username').value.trim();
  const email    = document.getElementById('reg-email').value.trim();
  const password = document.getElementById('reg-password').value;
  if (!username || !email || !password) return showMsg('reg-msg', 'Vyplň všechna pole.');

  setLoading('reg-btn', true);
  try {
    const data = await apiPost('/auth/register', { username, email, password });
    saveAuth(data);
    localStorage.setItem('dc_new_user', '1');
    showMsg('reg-msg', 'Účet vytvořen! Vítej, hrdino!', 'success');
    setTimeout(() => { window.location.href = '/game'; }, 700);
  } catch (e) {
    showMsg('reg-msg', e.message);
    setLoading('reg-btn', false);
  }
}

// Enter klávesa
document.addEventListener('keydown', e => {
  if (e.key !== 'Enter') return;
  const activeTab = document.querySelector('.tab-content.active').id;
  if (activeTab === 'tab-login') doLogin();
  else doRegister();
});
