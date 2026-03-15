// ── IN-GAME NEWS FEED ────────────────────────────────────────────────────────
// Zobrazí bannery na Hub stránce. Každá zpráva je dismissable (localStorage).

const _NEWS_DISMISSED_KEY = 'dc_dismissed_news';

const _NEWS_TYPE_CONF = {
  info:        { icon: '📢', label: 'Novinka',    cls: 'news-info' },
  event:       { icon: '🌟', label: 'Událost',    cls: 'news-event' },
  maintenance: { icon: '🔧', label: 'Údržba',     cls: 'news-maint' },
  balance:     { icon: '⚖',  label: 'Balance',    cls: 'news-balance' },
  hotfix:      { icon: '🐛', label: 'Oprava',     cls: 'news-hotfix' },
};

function _getDismissed() {
  try { return JSON.parse(localStorage.getItem(_NEWS_DISMISSED_KEY) || '[]'); }
  catch { return []; }
}

function _setDismissed(ids) {
  localStorage.setItem(_NEWS_DISMISSED_KEY, JSON.stringify(ids));
}

function dismissNews(id) {
  const ids = _getDismissed();
  if (!ids.includes(id)) ids.push(id);
  _setDismissed(ids);
  const el = document.getElementById('news-item-' + id);
  if (el) el.remove();
  // Skryj kontejner pokud je prázdný
  const feed = document.getElementById('hub-news-feed');
  if (feed && !feed.querySelector('.news-banner')) feed.style.display = 'none';
}

async function loadNewsFeed() {
  const feed = document.getElementById('hub-news-feed');
  if (!feed) return;

  let items;
  try { items = await api('GET', '/news/current'); }
  catch { feed.style.display = 'none'; return; }

  if (!items || items.length === 0) { feed.style.display = 'none'; return; }

  const dismissed = _getDismissed();
  const visible = items.filter(n => !dismissed.includes(n.id));

  if (visible.length === 0) { feed.style.display = 'none'; return; }

  feed.style.display = '';
  feed.innerHTML = visible.map(n => {
    const conf = _NEWS_TYPE_CONF[n.news_type] || _NEWS_TYPE_CONF.info;
    const dt = n.published_at
      ? new Date(n.published_at).toLocaleDateString('cs-CZ', { day: 'numeric', month: 'short' })
      : '';
    return `
      <div class="news-banner ${conf.cls}" id="news-item-${n.id}">
        <div class="news-banner-left">
          <span class="news-icon">${conf.icon}</span>
          <span class="news-type-label">${conf.label}</span>
        </div>
        <div class="news-banner-body">
          <div class="news-title">${_escHtml(n.title)}</div>
          <div class="news-body">${_escHtml(n.body)}</div>
        </div>
        <div class="news-banner-right">
          <span class="news-date">${dt}</span>
          <button class="news-dismiss" onclick="dismissNews(${n.id})" title="Zavřít">✕</button>
        </div>
      </div>`;
  }).join('');
}

function _escHtml(str) {
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}
