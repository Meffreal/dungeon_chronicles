// ── GLOBÁLNÍ STAV ─────────────────────────────────────────────────────────
let char = null, questTimer = null, selCls = null, clsData = {};
let _prevGold = null, _prevXp = null, _prevLevel = null;


let invData = [], invFilter = 'all', invSort = 'rarity', sellInvId = null;
let mktCurrentPage = 1, mktTotalPages = 1;
let searchTimeout = null;

const CLS_N = { warrior:'Válečník', mage:'Mág', ranger:'Lovec' };
const CLS_E = { warrior:'⚔️', mage:'🔮', ranger:'🏹' };
const CLS_D = { warrior:'Silný bojovník. Vysoký HP a obrana.', mage:'Mistr magie. Devastující kouzla.', ranger:'Rychlý lovec. Kritické zásahy.' };
const RARITY_COL = { common:'#9d9d9d', uncommon:'#1eff00', rare:'#0070dd', epic:'#a335ee', legendary:'#ff8000', set:'#00d4ff' };
const RARITY_CZ  = { common:'Běžný', uncommon:'Neobvyklý', rare:'Vzácný', epic:'Epický', legendary:'Legendární', set:'Setový' };
const SLOT_ICONS = {
  helmet: `<svg class="slot-svg-icon" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 48 48" fill="none"><path d="M18 10 L20 5 L22 9 L24 3 L26 9 L28 5 L30 10" stroke="#b89a6a" stroke-width="1.2" fill="none" stroke-linejoin="round" stroke-linecap="round"/><path d="M13 26 L9 24 L9 30 L13 32" fill="#1a1412" stroke="#7a6a5a" stroke-width="1.3"/><path d="M35 26 L39 24 L39 30 L35 32" fill="#1a1412" stroke="#7a6a5a" stroke-width="1.3"/><path d="M13 28 C13 15 18 10 24 10 C30 10 35 15 35 28 L35 38 L13 38 Z" fill="#1a1412" stroke="#7a6a5a" stroke-width="1.5"/><line x1="24" y1="10" x2="24" y2="28" stroke="#5a4a3a" stroke-width="0.8" opacity="0.7"/><path d="M13 28 L35 28 L35 38 L13 38 Z" fill="#110e0d" stroke="#7a6a5a" stroke-width="1"/><line x1="16" y1="32" x2="22" y2="32" stroke="#b89a6a" stroke-width="1.8" stroke-linecap="round"/><line x1="26" y1="32" x2="32" y2="32" stroke="#b89a6a" stroke-width="1.8" stroke-linecap="round"/><line x1="24" y1="28" x2="24" y2="38" stroke="#b89a6a" stroke-width="1" stroke-linecap="round"/><path d="M18 16 Q20 13 24 12 Q28 13 30 16" stroke="#5a4a38" stroke-width="0.8" stroke-linecap="round" opacity="0.9"/><path d="M13 38 Q24 43 35 38" stroke="#7a6a5a" stroke-width="1.3" stroke-linecap="round"/><circle cx="14" cy="20" r="1" fill="#b89a6a" opacity="0.7"/><circle cx="34" cy="20" r="1" fill="#b89a6a" opacity="0.7"/></svg>`,
  armor:  `<svg class="slot-svg-icon" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 48 48" fill="none"><path d="M8 15 Q9 10 16 12 L18 22 L8 20 Z" fill="#1a1412" stroke="#7a6a5a" stroke-width="1.3"/><line x1="9" y1="14" x2="17" y2="16" stroke="#5a4a38" stroke-width="0.7" opacity="0.7"/><path d="M40 15 Q39 10 32 12 L30 22 L40 20 Z" fill="#1a1412" stroke="#7a6a5a" stroke-width="1.3"/><line x1="39" y1="14" x2="31" y2="16" stroke="#5a4a38" stroke-width="0.7" opacity="0.7"/><path d="M16 12 Q24 8 32 12 L34 34 Q30 42 24 44 Q18 42 14 34 Z" fill="#1a1412" stroke="#7a6a5a" stroke-width="1.5"/><line x1="24" y1="12" x2="24" y2="40" stroke="#5a4a3a" stroke-width="1" opacity="0.6"/><path d="M18 17 Q24 14 30 17" stroke="#b89a6a" stroke-width="0.8" stroke-linecap="round" opacity="0.7"/><path d="M17 23 Q24 20 31 23" stroke="#b89a6a" stroke-width="0.8" stroke-linecap="round" opacity="0.7"/><path d="M24 20 L24 36 M20 27 L28 27" stroke="#7a2020" stroke-width="1.2" stroke-linecap="round" opacity="0.7"/><path d="M15 34 L13 40 L18 43 L24 44 L30 43 L35 40 L33 34 Z" fill="#150f0e" stroke="#7a6a5a" stroke-width="1.2"/><line x1="19" y1="36" x2="18" y2="43" stroke="#5a4a38" stroke-width="0.8" opacity="0.6"/><line x1="24" y1="36" x2="24" y2="44" stroke="#5a4a38" stroke-width="0.8" opacity="0.6"/><line x1="29" y1="36" x2="30" y2="43" stroke="#5a4a38" stroke-width="0.8" opacity="0.6"/><path d="M17 12 Q24 9 31 12 L30 15 Q24 12 18 15 Z" fill="#221814" stroke="#b89a6a" stroke-width="0.8"/></svg>`,
  gloves: `<svg class="slot-svg-icon" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 48 48" fill="none"><path d="M13 22 L13 13 Q14 10 16 13 L16 22" fill="#1a1412" stroke="#7a6a5a" stroke-width="1.2"/><path d="M17 21 L17 11 Q18 8 20 11 L20 21" fill="#1a1412" stroke="#7a6a5a" stroke-width="1.2"/><path d="M21 21 L21 11 Q22 8 24 11 L24 21" fill="#1a1412" stroke="#7a6a5a" stroke-width="1.2"/><path d="M25 22 L25 13 Q26 10 28 13 L28 22" fill="#1a1412" stroke="#7a6a5a" stroke-width="1.2"/><path d="M29 24 L34 19 Q37 17 37 20 L33 26" fill="#1a1412" stroke="#7a6a5a" stroke-width="1.2"/><path d="M11 22 L11 36 Q11 40 15 42 L31 42 Q35 40 35 36 L35 22 Z" fill="#1a1412" stroke="#7a6a5a" stroke-width="1.5"/><line x1="23" y1="22" x2="23" y2="40" stroke="#5a4a3a" stroke-width="0.7" opacity="0.5"/><path d="M13 22 L28 22" stroke="#7a6a5a" stroke-width="0.8" opacity="0.6"/><ellipse cx="14.5" cy="22" rx="1.8" ry="1.4" fill="#221a14" stroke="#b89a6a" stroke-width="0.9"/><ellipse cx="18.5" cy="22" rx="1.8" ry="1.4" fill="#221a14" stroke="#b89a6a" stroke-width="0.9"/><ellipse cx="22.5" cy="22" rx="1.8" ry="1.4" fill="#221a14" stroke="#b89a6a" stroke-width="0.9"/><ellipse cx="26.5" cy="22" rx="1.8" ry="1.4" fill="#221a14" stroke="#b89a6a" stroke-width="0.9"/><path d="M11 36 L35 36 L35 42 Q23 46 11 42 Z" fill="#150f0e" stroke="#7a6a5a" stroke-width="1.3"/><path d="M15 38 Q23 36 31 38" stroke="#b89a6a" stroke-width="0.8" stroke-linecap="round" opacity="0.6"/><circle cx="23" cy="40" r="1.2" fill="#b89a6a" opacity="0.7"/></svg>`,
  amulet: `<svg class="slot-svg-icon" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 48 48" fill="none"><path d="M24 5 Q14 7 12 14" stroke="#7a6a5a" stroke-width="1.3" stroke-linecap="round" stroke-dasharray="2.5 2"/><path d="M24 5 Q34 7 36 14" stroke="#7a6a5a" stroke-width="1.3" stroke-linecap="round" stroke-dasharray="2.5 2"/><circle cx="24" cy="5" r="2" fill="#221a14" stroke="#b89a6a" stroke-width="1"/><path d="M24 14 L30 20 L34 26 L30 30 L24 46 L18 30 L14 26 L18 20 Z" fill="#1a1412" stroke="#7a6a5a" stroke-width="1.5"/><path d="M24 14 L21 18 L24 16 L27 18 L24 14" fill="#b89a6a" stroke="#b89a6a" stroke-width="0.5"/><path d="M24 19 L28 24 L24 29 L20 24 Z" fill="#0f0a0a" stroke="#b89a6a" stroke-width="1.2"/><path d="M24 19 L27 23 L24 27 L21 23 Z" fill="#7a2020" stroke="#9a3030" stroke-width="0.5" opacity="0.9"/><line x1="24" y1="19" x2="24" y2="27" stroke="#2a0808" stroke-width="0.6" opacity="0.7"/><line x1="20" y1="24" x2="28" y2="24" stroke="#2a0808" stroke-width="0.6" opacity="0.7"/><path d="M22.5 20.5 L23.5 21.5" stroke="#ff9a7a" stroke-width="0.8" stroke-linecap="round" opacity="0.8"/><path d="M20 30 Q18 36 24 46 Q30 36 28 30" fill="#150f0e" stroke="#7a6a5a" stroke-width="1"/><path d="M14 26 Q11 22 14 20" stroke="#b89a6a" stroke-width="1" stroke-linecap="round" opacity="0.6"/><path d="M34 26 Q37 22 34 20" stroke="#b89a6a" stroke-width="1" stroke-linecap="round" opacity="0.6"/><circle cx="13" cy="26" r="1" fill="#b89a6a" opacity="0.5"/><circle cx="35" cy="26" r="1" fill="#b89a6a" opacity="0.5"/></svg>`,
  ring:   `<svg class="slot-svg-icon" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 48 48" fill="none"><ellipse cx="24" cy="32" rx="15" ry="9" fill="none" stroke="#7a6a5a" stroke-width="2"/><ellipse cx="24" cy="32" rx="9" ry="5.5" fill="#0a0808" stroke="#5a4a3a" stroke-width="1"/><path d="M10 30 Q14 28 18 30" stroke="#b89a6a" stroke-width="0.9" stroke-linecap="round" opacity="0.6"/><path d="M30 30 Q34 28 38 30" stroke="#b89a6a" stroke-width="0.9" stroke-linecap="round" opacity="0.6"/><path d="M19 24 L17 18" stroke="#b89a6a" stroke-width="1.5" stroke-linecap="round"/><path d="M29 24 L31 18" stroke="#b89a6a" stroke-width="1.5" stroke-linecap="round"/><path d="M22 22 L21 16" stroke="#b89a6a" stroke-width="1.5" stroke-linecap="round"/><path d="M26 22 L27 16" stroke="#b89a6a" stroke-width="1.5" stroke-linecap="round"/><path d="M18 18 Q24 14 30 18 L30 26 Q24 30 18 26 Z" fill="#1a1412" stroke="#b89a6a" stroke-width="1.2"/><path d="M24 15 L27.5 17 L28 21 L24 24 L20 21 L20.5 17 Z" fill="#0f0808" stroke="#8a3a2a" stroke-width="0.9"/><path d="M24 15 L27 17.5 L26 21.5 L24 23 L22 21.5 L21 17.5 Z" fill="#7a2020" opacity="0.8"/><line x1="24" y1="15" x2="24" y2="23" stroke="#2a0808" stroke-width="0.5" opacity="0.6"/><line x1="20.5" y1="17" x2="27.5" y2="17" stroke="#2a0808" stroke-width="0.5" opacity="0.6"/><line x1="20" y1="21" x2="28" y2="21" stroke="#2a0808" stroke-width="0.5" opacity="0.6"/><path d="M22.5 16 L23.5 17" stroke="#ffaa88" stroke-width="0.8" stroke-linecap="round" opacity="0.9"/></svg>`,
  boots:  `<svg class="slot-svg-icon" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 48 48" fill="none"><path d="M16 3 L16 28 Q16 32 18 34 L30 34 Q32 32 32 28 L32 3 Z" fill="#1a1412" stroke="#7a6a5a" stroke-width="1.5"/><line x1="24" y1="3" x2="24" y2="28" stroke="#5a4a3a" stroke-width="0.9" opacity="0.6"/><line x1="16" y1="11" x2="32" y2="11" stroke="#5a4a3a" stroke-width="0.8" opacity="0.5"/><line x1="16" y1="19" x2="32" y2="19" stroke="#5a4a3a" stroke-width="0.8" opacity="0.5"/><line x1="16" y1="27" x2="32" y2="27" stroke="#5a4a3a" stroke-width="0.8" opacity="0.5"/><path d="M21 5 L24 9 L27 5" stroke="#b89a6a" stroke-width="0.9" fill="none" stroke-linecap="round" stroke-linejoin="round"/><path d="M15 22 Q11 22 11 28 Q11 32 15 32 L16 32 L16 22 Z" fill="#1a1412" stroke="#7a6a5a" stroke-width="1.2"/><path d="M32 22 Q36 22 36 28 Q36 32 32 32 L31 32 L31 22 Z" fill="#1a1412" stroke="#7a6a5a" stroke-width="1.2"/><path d="M14 34 Q12 36 13 41 Q16 45 26 45 Q36 43 38 39 Q38 35 34 34 L18 34 Z" fill="#1a1412" stroke="#7a6a5a" stroke-width="1.5"/><path d="M26 45 Q36 43 38 39 Q40 36 37 36 Q33 40 28 43 Z" fill="#150f0e" stroke="#7a6a5a" stroke-width="1"/><line x1="15" y1="37" x2="32" y2="37" stroke="#5a4a3a" stroke-width="0.8" opacity="0.5"/><line x1="16" y1="41" x2="30" y2="41" stroke="#5a4a3a" stroke-width="0.8" opacity="0.5"/><rect x="20" y="31" width="8" height="4" rx="1" fill="#221a14" stroke="#b89a6a" stroke-width="0.9"/><circle cx="24" cy="33" r="0.8" fill="#b89a6a" opacity="0.8"/></svg>`,
  weapon: `<svg class="slot-svg-icon" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 48 48" fill="none"><defs><linearGradient id="si_wblade" x1="20" y1="3" x2="28" y2="3" gradientUnits="userSpaceOnUse"><stop stop-color="#5a4a38"/><stop offset="0.45" stop-color="#c4a882"/><stop offset="1" stop-color="#3a2a20"/></linearGradient></defs><path d="M22 3 L24 1 L26 3" fill="#c4a882" stroke="#c4a882" stroke-width="0.6"/><path d="M21 3 L23 3 L24.5 33 L24 36 L23.5 33 L25 3 L27 3 Z" fill="url(#si_wblade)" stroke="#8a7060" stroke-width="0.7"/><line x1="24" y1="4" x2="24" y2="30" stroke="#1a1010" stroke-width="0.7" opacity="0.8"/><path d="M22 5 L22 28" stroke="#7a6a5a" stroke-width="0.4" opacity="0.5"/><path d="M9 33 Q11 31 24 33 Q37 31 39 33 L38 37 Q25 35 24 35 Q23 35 10 37 Z" fill="#221814" stroke="#7a6a5a" stroke-width="1.3"/><path d="M9 33 Q6 34 7 37 Q9 38 10 37" fill="#221814" stroke="#b89a6a" stroke-width="0.9"/><path d="M39 33 Q42 34 41 37 Q39 38 38 37" fill="#221814" stroke="#b89a6a" stroke-width="0.9"/><path d="M24 32 L26.5 35 L24 38 L21.5 35 Z" fill="#0f0808" stroke="#b89a6a" stroke-width="1"/><path d="M24 32 L26 35 L24 37 L22 35 Z" fill="#7a2020" opacity="0.9"/><rect x="22.5" y="38" width="3" height="7" rx="0.8" fill="#2a1808" stroke="#6a3a18" stroke-width="0.9"/><line x1="22.5" y1="40" x2="25.5" y2="40" stroke="#8a5a28" stroke-width="0.7" opacity="0.8"/><line x1="22.5" y1="42" x2="25.5" y2="42" stroke="#8a5a28" stroke-width="0.7" opacity="0.8"/><line x1="22.5" y1="44" x2="25.5" y2="44" stroke="#8a5a28" stroke-width="0.7" opacity="0.8"/><path d="M20 45 Q24 48 28 45 L27 45 Q24 47.5 21 45 Z" fill="#221814" stroke="#7a6a5a" stroke-width="1.2"/><circle cx="24" cy="45" r="1.5" fill="#7a2020" stroke="#b89a6a" stroke-width="0.6"/></svg>`,
};
const SLOT_CZ    = { weapon:'Zbraň', helmet:'Přilba', armor:'Brnění', gloves:'Rukavice', boots:'Boty', ring:'Prsten', amulet:'Amulet' };

// ── ATTRIBUTE SVG ICONS — globální, používají currentColor ──────────────
const ATTR_SVG = {
  strength:     `<svg class="sp-attr-svg" viewBox="0 0 16 16" fill="none"><path d="M12 2.5L3.5 11" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"/><path d="M10.5 2H12.5V4" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/><path d="M3.5 11L2 14.5L5.5 13Z" fill="currentColor" opacity=".5"/><path d="M7.2 7L5.8 8.5" stroke="currentColor" stroke-width="1.2" stroke-linecap="round" opacity=".35"/></svg>`,
  dexterity:    `<svg class="sp-attr-svg" viewBox="0 0 16 16" fill="none"><path d="M2 14L13 3" stroke="currentColor" stroke-width="1.3" stroke-linecap="round" opacity=".3"/><path d="M13 3L10 3L13 6" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/><path d="M2 14L8.5 7.5" stroke="currentColor" stroke-width="1.9" stroke-linecap="round"/><path d="M2 14L3.5 11.5" stroke="currentColor" stroke-width="1.3" stroke-linecap="round" opacity=".45"/></svg>`,
  intelligence: `<svg class="sp-attr-svg" viewBox="0 0 16 16" fill="none"><polygon points="8,1.5 11,6.5 8,14 5,6.5" stroke="currentColor" stroke-width="1.2" fill="currentColor" fill-opacity=".13"/><line x1="5" y1="6.5" x2="11" y2="6.5" stroke="currentColor" stroke-width="1" stroke-linecap="round" opacity=".4"/><circle cx="8" cy="3.8" r="1.3" fill="currentColor" opacity=".5"/></svg>`,
  endurance:    `<svg class="sp-attr-svg" viewBox="0 0 16 16" fill="none"><path d="M8 2L13 4.5V9C13 12 10.5 13.8 8 14.5C5.5 13.8 3 12 3 9V4.5L8 2Z" stroke="currentColor" stroke-width="1.3" fill="currentColor" fill-opacity=".1"/><path d="M5.5 8.2L7 9.7L10.5 6.5" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/></svg>`,
  luck:         `<svg class="sp-attr-svg" viewBox="0 0 16 16" fill="none"><circle cx="5.5" cy="5.5" r="2.3" stroke="currentColor" stroke-width="1.1" fill="currentColor" fill-opacity=".12"/><circle cx="10.5" cy="5.5" r="2.3" stroke="currentColor" stroke-width="1.1" fill="currentColor" fill-opacity=".12"/><circle cx="5.5" cy="10.5" r="2.3" stroke="currentColor" stroke-width="1.1" fill="currentColor" fill-opacity=".12"/><circle cx="10.5" cy="10.5" r="2.3" stroke="currentColor" stroke-width="1.1" fill="currentColor" fill-opacity=".12"/><path d="M8 8V15" stroke="currentColor" stroke-width="1.3" stroke-linecap="round"/></svg>`,
  crit:         `<svg class="sp-attr-svg" viewBox="0 0 16 16" fill="none"><path d="M8 1L9.5 6H14.5L10.5 9L12 14L8 11L4 14L5.5 9L1.5 6H6.5Z" stroke="currentColor" stroke-width="1.3" stroke-linejoin="round" fill="currentColor" fill-opacity=".15"/><path d="M8 4L9 7H12L9.5 8.5L10.5 11.5L8 9.8L5.5 11.5L6.5 8.5L4 7H7Z" fill="currentColor" opacity=".3"/></svg>`,
};

// ── TOAST ─────────────────────────────────────────────────────────────────
function toast(msg, type='i', dur=3500) {
  const ic = {s:'✅',e:'❌',i:'ℹ️'};
  const el = document.createElement('div');
  el.className = `toast t${type}`;
  el.innerHTML = `<span>${ic[type]}</span><span>${msg}</span>`;
  document.getElementById('toasts').append(el);
  const removeEl = () => {
    el.classList.add('removing');
    el.addEventListener('animationend', () => el.remove(), { once: true });
    setTimeout(() => el.remove(), 300); // fallback
  };
  setTimeout(removeEl, dur);
}

// ── MODAL ─────────────────────────────────────────────────────────────────
const openModal = (id) => {
  document.getElementById(id).classList.add('open');
  if (id === 'modal-create') {
    renderClsGrid();
    if (typeof renderFactionGrid === 'function') renderFactionGrid();
  }
};
const closeModal = id => document.getElementById(id).classList.remove('open');
document.addEventListener('DOMContentLoaded', () => {
  document.querySelectorAll('.overlay').forEach(m => m.addEventListener('click', e => {
    if (e.target === m && m.id !== 'modal-create') closeModal(m.id);
  }));
  initNavGroups();
  _initMobileUI();
  _initStatPanelTabs();
});

function _initStatPanelTabs() {
  document.querySelectorAll('.sp-tab').forEach(btn => {
    btn.addEventListener('click', () => {
      const target = btn.dataset.spTab;
      document.querySelectorAll('.sp-tab').forEach(t => t.classList.remove('sp-tab--active'));
      document.querySelectorAll('.sp-tab-panel').forEach(p => p.classList.remove('sp-tab-panel--active'));
      btn.classList.add('sp-tab--active');
      document.querySelector(`.sp-tab-panel[data-sp-panel="${target}"]`).classList.add('sp-tab-panel--active');
    });
  });
}

// ── MOBILNÍ UI ────────────────────────────────────────────────────────────
const _MOB_GROUP_META = {
  combat:      { icon: '⚔️', label: 'Boj' },
  progression: { icon: '🎯', label: 'Postava' },
  social:      { icon: '👥', label: 'Sociální' },
  seasonal:    { icon: '🌟', label: 'Sezónní' },
  cosmetics:   { icon: '🎨', label: 'Kosmetika' },
};

function _isMobile() { return window.innerWidth <= 768; }

function _initMobileUI() {
  if (document.getElementById('mob-tabbar')) return;

  // ── Bottom tab bar ────────────────────────────────────────────────────
  const tabbar = document.createElement('div');
  tabbar.className = 'mob-tabbar';
  tabbar.id = 'mob-tabbar';
  tabbar.innerHTML = Object.entries(_MOB_GROUP_META).map(([id, m]) =>
    `<button class="mob-tab" id="mob-tab-${id}" onclick="openMobileDrawer('${id}')">
       <span class="mob-tab-icon">${m.icon}</span>
       <span class="mob-tab-label">${m.label}</span>
     </button>`
  ).join('');

  // ── Backdrop ──────────────────────────────────────────────────────────
  const backdrop = document.createElement('div');
  backdrop.className = 'mob-backdrop';
  backdrop.id = 'mob-backdrop';
  backdrop.onclick = closeMobileDrawer;

  // ── Nav drawer ────────────────────────────────────────────────────────
  const drawer = document.createElement('div');
  drawer.className = 'mob-drawer';
  drawer.id = 'mob-drawer';
  drawer.innerHTML = `
    <div class="mob-drawer-header">
      <span class="mob-drawer-title" id="mob-drawer-title"></span>
      <button class="mob-drawer-close" onclick="closeMobileDrawer()">✕</button>
    </div>
    <div class="mob-drawer-nav" id="mob-drawer-nav"></div>`;

  document.body.append(backdrop, drawer, tabbar);
}

function openMobileDrawer(groupId) {
  if (!_isMobile()) return;
  const meta = _MOB_GROUP_META[groupId];
  if (!meta) return;

  const drawer   = document.getElementById('mob-drawer');
  const backdrop = document.getElementById('mob-backdrop');
  const titleEl  = document.getElementById('mob-drawer-title');
  const navEl    = document.getElementById('mob-drawer-nav');
  if (!drawer) return;

  // Naplníme drawer nav položkami skupiny
  titleEl.textContent = `${meta.icon} ${meta.label}`;
  navEl.innerHTML = '';
  const src = document.getElementById(`ngbody-${groupId}`);
  if (src) {
    src.querySelectorAll('.nav-btn').forEach(btn => {
      const clone = btn.cloneNode(true);
      const orig = clone.getAttribute('onclick') || '';
      if (orig) clone.setAttribute('onclick', orig + '; closeMobileDrawer()');
      navEl.appendChild(clone);
    });
  }

  // Zvýrazníme aktivní tab
  document.querySelectorAll('.mob-tab').forEach(t => t.classList.remove('active'));
  document.getElementById(`mob-tab-${groupId}`)?.classList.add('active');

  drawer.classList.add('open');
  backdrop.classList.add('open');
}

function closeMobileDrawer() {
  document.getElementById('mob-drawer')?.classList.remove('open');
  document.getElementById('mob-backdrop')?.classList.remove('open');
  document.querySelectorAll('.mob-tab').forEach(t => t.classList.remove('active'));
}

// ── GROUPED NAVIGATION ────────────────────────────────────────────────────
const _NAV_GROUP_PAGES = {
  quests:'combat', arena:'combat', boss:'combat', dungeons:'combat', build:'combat',
  equipment:'progression', inventory:'progression', subclass:'progression',
  prestige:'progression', professions:'progression', attunement:'progression',
  guild:'social', faction:'social', market:'social', shop:'social',
  weekly:'seasonal', season:'seasonal', 'world-events':'seasonal', achievements:'seasonal',
  crystals:'cosmetics',
};
const _NAV_GROUPS = ['combat','progression','social','seasonal','cosmetics'];

function _getNavGroupState() {
  try { return JSON.parse(localStorage.getItem('dc_nav_groups') || '{}'); }
  catch { return {}; }
}
function _saveNavGroupState(state) {
  localStorage.setItem('dc_nav_groups', JSON.stringify(state));
}

function toggleNavGroup(id) {
  const body   = document.getElementById(`ngbody-${id}`);
  const header = document.getElementById(`ngh-${id}`);
  if (!body || !header) return;
  const isOpen = body.classList.contains('open');
  body.classList.toggle('open', !isOpen);
  header.classList.toggle('open', !isOpen);
  const state = _getNavGroupState();
  state[id] = !isOpen;
  _saveNavGroupState(state);
}

function initNavGroups() {
  const state = _getNavGroupState();
  _NAV_GROUPS.forEach(id => {
    const isOpen = id in state ? state[id] : (id === 'combat');
    const body   = document.getElementById(`ngbody-${id}`);
    const header = document.getElementById(`ngh-${id}`);
    if (body)   body.classList.toggle('open', isOpen);
    if (header) header.classList.toggle('open', isOpen);
  });
}

function _expandGroupForPage(name) {
  const groupId = _NAV_GROUP_PAGES[name];
  if (!groupId) return;
  const body   = document.getElementById(`ngbody-${groupId}`);
  const header = document.getElementById(`ngh-${groupId}`);
  if (body && !body.classList.contains('open')) {
    body.classList.add('open');
    header?.classList.add('open');
    const state = _getNavGroupState();
    state[groupId] = true;
    _saveNavGroupState(state);
  }
}

// ── FEATURE DISCOVERY TOOLTIPS ────────────────────────────────────────────
// Jednorázové informační tipy při prvním otevření každé stránky.
// Uloženo v localStorage jako dc_seen_tips = { "arena": true, ... }

const PAGE_TIPS = {
  quests:          'Questy jsou hlavní zdroj XP, zlata a vybavení. Vyber quest, počkej na dokončení, pak seber odměnu.',
  equipment:       'Přiděluj stat body tlačítky +. Nasazené předměty v slotů zvyšují bojové statistiky.',
  inventory:       'Inventář obsahuje všechny tvé předměty. Klikni na předmět pro equipnutí, prodej nebo použití.',
  market:          'Tržiště je hráčská burza. Prodávej přebytečné předměty a nakupuj od ostatních hráčů.',
  shop:            'Obchod nabízí items od NPC. Každý NPC má jiný sortiment — podívej se na všechny záložky.',
  arena:           'Aréna je asynchronní PvP. Útočíš na vybraného soupeře — jejich postava se brání automaticky dle statistik.',
  guild:           'Cech je sociální hub: guild chat, sdílené cíle (weekly quests) a bonusy pro všechny členy.',
  dungeons:        'Dungeony jsou 5-stagová dobrodružství s přenosem HP. Přežij všechny stagy bez obnovy životů.',
  boss:            'World Boss je kooperativní výzva — přispívej k oslabení bosse spolu s ostatními hráči pro velké odměny.',
  achievements:    'Achievementy sledují tvé pokroky a odemykají tituly, bonusy a crystaly. Zkontroluj skryté úkoly.',
  faction:         'Frakce ovlivňuje tvůj herní styl a odemyká exkluzivní questy. Reputace roste splněním frakčních questů.',
  attunement:      'Attunement chains jsou série questů, které odemknou přístup do uzamčených dungeonů.',
  professions:     'Profese jsou pasivní specializace s unikátními schopnostmi — každý quest nebo arena boj může spustit efekt.',
  weekly:          'Týdenní questy se resetují každý týden a nabízejí výrazně lepší odměny než denní questy.',
  season:          'Sezónní pass sleduje tvou aktivitu a odměňuje tě kosmetickými předměty za každý level aktivity.',
  'world-events':  'World Events jsou komunitní výzvy — splňuj cíle spolu se všemi hráči pro sdílené odměny a body příspěvku.',
  crystals:        'Crystaly jsou prémiová měna NEZÍSKANÁ koupí — vyděláváš je achievementy, sezónou a eventy. Bez P2W!',
  prestige:        'Prestiž je dostupná po dosažení max levelu. Reset postavy za trvalé bonusy a exkluzivní tituly.',
  subclass:        'Subclass je trvalá specializace třídy dostupná od levelu 10. Volba je nevratná — vyber pečlivě!',
  build:           'Combat Build zobrazuje kompletní bojový profil — strategii, talenty, effective stats a dungeon modifikátor.',
  support:         'Tato stránka transparentně ukazuje jak funguje monetizace, drop rates a herní mechaniky. Žádné skryté algoritmy.',
};

/**
 * Zobrazí jednorázový informační tip při prvním otevření stránky.
 * Vloží se na začátek stránky a zmizí po 7s nebo po kliknutí ✕.
 *
 * @param {string} pageId — ID stránky (bez předpony "page-")
 * @param {string} text   — text tipu (max 2 věty)
 */
function showFeatureTip(pageId, text) {
  if (!text) return;

  // Přečti/aktualizuj localStorage
  let seen = {};
  try { seen = JSON.parse(localStorage.getItem('dc_seen_tips') || '{}'); } catch {}
  if (seen[pageId]) return;
  seen[pageId] = true;
  try { localStorage.setItem('dc_seen_tips', JSON.stringify(seen)); } catch {}

  // Odstraň předchozí tip pokud existuje
  document.getElementById('feature-tip')?.remove();

  const el = document.createElement('div');
  el.id        = 'feature-tip';
  el.className = 'feature-tip';
  el.innerHTML = `
    <span class="ft-icon">💡</span>
    <span class="ft-text">${esc(text)}</span>
    <button class="ft-close" onclick="document.getElementById('feature-tip')?.remove()" title="Zavřít">✕</button>`;

  // Vlož na začátek aktivní stránky
  const page = document.getElementById(`page-${pageId}`);
  if (page) page.insertAdjacentElement('afterbegin', el);

  // Auto-zmizí po 7s
  setTimeout(() => el?.remove(), 7000);
}

// ── NAVIGACE ──────────────────────────────────────────────────────────────
function showPage(name) {
  console.log('[UI] showPage() called with:', name);
  closeMobileDrawer();
  document.querySelectorAll('.page').forEach(p => p.classList.remove('active', 'page-entering'));
  document.querySelectorAll('.nav-btn[id]').forEach(b => b.classList.remove('active'));
  const target = document.getElementById(`page-${name}`);
  if (target) {
    target.classList.add('active', 'page-entering');
    setTimeout(() => target.classList.remove('page-entering'), 250);
  }
  document.getElementById(`nav-${name}`)?.classList.add('active');
  _expandGroupForPage(name);
  if (name === 'quests')        loadQuests();
  if (name === 'equipment')     { renderEquip(); loadInventory(); }  // renderEquip je async, fire-and-forget OK
  if (name === 'inventory')     loadInventory();
  if (name === 'market')        { loadMarket(); loadMyListings(); }
  if (name === 'shop')          loadShop();
  if (name === 'arena')         loadArena();
  if (name === 'guild')         loadGuild();
  if (name === 'achievements')  loadAchievements();
  if (name === 'notifications') loadNotifications();
  if (name === 'faction')       loadFaction();
  if (name === 'dungeons') {
    console.log('[UI] Calling loadDungeons() for dungeons page');
    loadDungeons();
  }
  if (name === 'attunement')    loadAttunement();
  if (name === 'professions')   loadProfessions();
  if (name === 'build')         loadBuild();
  if (name === 'overview')      loadHub();
  if (name === 'legacy-item') {
    document.getElementById('page-death')?.classList.remove('active');
    loadLegacyItems();
  }

  // Zobraz jednorázový discovery tip při prvním otevření stránky
  if (name !== 'overview') showFeatureTip(name, PAGE_TIPS[name]);
}

// ── UTILITY ───────────────────────────────────────────────────────────────
function set(id, v) { const e = document.getElementById(id); if(e) e.textContent = v; }
function setHTML(id, html) { const e = document.getElementById(id); if(e) e.innerHTML = html; }
function pct(id, p) { const e = document.getElementById(id); if(e) e.style.width = `${Math.max(0,Math.min(100,p))}%`; }
function esc(s) { return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;'); }

// ── LOADING STATES ────────────────────────────────────────────────────────
function showLoading(containerId, text = 'Načítám...') {
  const el = document.getElementById(containerId);
  if (el) el.innerHTML = `<div class="loading-state"><span class="loading-spinner"></span><span>${text}</span></div>`;
}
function hideLoading(containerId) {
  // Render funkce přepisuje innerHTML — voláme pro sémantiku nebo při chybě.
  const el = document.getElementById(containerId);
  if (el && el.querySelector('.loading-spinner')) el.innerHTML = '';
}

// ── SKELETON LOADING ──────────────────────────────────────────────────────
// Generuje placeholder skeleton HTML před načtením dat
function skelLines(count = 3) {
  return Array.from({length: count}, (_, i) =>
    `<div class="skel skel-line" style="width:${55 + Math.sin(i*1.7)*30}%"></div>`
  ).join('');
}
function skelQuestCards(count = 3) {
  return Array.from({length: count}, () =>
    `<div class="skel skel-quest-card"></div>`
  ).join('');
}
function skelItemGrid(count = 8) {
  return `<div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(80px,1fr));gap:8px">`
    + Array.from({length: count}, () => `<div class="skel skel-item-card" style="height:80px"></div>`).join('')
    + `</div>`;
}
function showSkeleton(containerId, type = 'lines', count = 3) {
  const el = document.getElementById(containerId);
  if (!el) return;
  const map = { lines: skelLines(count), quests: skelQuestCards(count), items: skelItemGrid(count) };
  el.innerHTML = map[type] || skelLines(count);
}

// ── PLAYER SEARCH AUTOCOMPLETE ────────────────────────────────────────────
// Generuje HTML pro políčko s autocomplete hledáním hráče.
// Skrytý input se stejným `id` uchovává vybrané char ID (číselná hodnota).
// Čtení: parseInt(document.getElementById(id).value)
function playerSearchHtml(id, placeholder = 'Jméno hráče...') {
  return `
    <div class="ps-wrap">
      <input type="text" class="pr-input ps-input" id="ps-text-${id}"
        placeholder="${placeholder}" autocomplete="off"
        oninput="psInput('${id}', this.value)"
        onblur="setTimeout(psClear, 150, '${id}')">
      <div class="ps-dropdown" id="ps-drop-${id}" style="display:none"></div>
      <input type="hidden" id="${id}">
    </div>`;
}

let _psTimer = null;

function psInput(id, q) {
  clearTimeout(_psTimer);
  document.getElementById(id).value = '';  // zrušit výběr při editaci
  if (q.length < 2) { psClear(id); return; }
  _psTimer = setTimeout(() => psSearch(id, q), 280);
}

async function psSearch(id, q) {
  try {
    const results = await api('GET', `/character/search?q=${encodeURIComponent(q)}`);
    const drop = document.getElementById(`ps-drop-${id}`);
    if (!drop) return;
    if (!results.length) {
      drop.innerHTML = '<div class="ps-no-result">Nic nenalezeno</div>';
      drop.style.display = 'block';
      return;
    }
    drop.innerHTML = results.map(c => `
      <div class="ps-item" onmousedown="psSelect('${id}', ${c.id}, ${JSON.stringify(c.name).replace(/"/g, '&quot;')})">
        <span class="ps-cls">${c.cls_emoji}</span>
        <span class="ps-name">${esc(c.name)}</span>
        <span class="ps-level">Lv.${c.level}</span>
      </div>`).join('');
    drop.style.display = 'block';
  } catch(e) { psClear(id); }
}

function psSelect(id, charId, name) {
  document.getElementById(`ps-text-${id}`).value = name;
  document.getElementById(id).value = charId;
  psClear(id);
}

function psClear(id) {
  const drop = document.getElementById(`ps-drop-${id}`);
  if (drop) drop.style.display = 'none';
}

// ── REWARD ANIMATIONS ─────────────────────────────────────────────────────
function _tweenGold(el, from, to) {
  if (!el) return;
  const dur  = 400;
  const t0   = performance.now();
  const diff = to - from;
  // Flash animace dle směru změny
  const flashClass = diff > 0 ? 'num-flash-up' : 'num-flash-down';
  el.classList.remove('num-flash-up', 'num-flash-down');
  void el.offsetWidth;
  el.classList.add(flashClass);
  el.addEventListener('animationend', () => el.classList.remove(flashClass), { once: true });
  function step(now) {
    const t    = Math.min(1, (now - t0) / dur);
    const ease = 1 - (1 - t) * (1 - t) * (1 - t); // easeOutCubic
    el.textContent = Math.round(from + diff * ease).toLocaleString('cs');
    if (t < 1) requestAnimationFrame(step);
  }
  requestAnimationFrame(step);
}

function _spawnRewardLabel(amount, type) {
  const anchorId = type === 'gold' ? 'tb-gold' : 'xp-strip';
  const anchor   = document.getElementById(anchorId);
  if (!anchor) return;
  const rect = anchor.getBoundingClientRect();
  const el   = document.createElement('div');
  el.className   = `reward-float-label reward-float-${type}`;
  el.textContent = type === 'gold'
    ? `+${amount.toLocaleString('cs')} G`
    : `+${amount.toLocaleString('cs')} XP`;
  el.style.left = `${rect.left + rect.width / 2}px`;
  el.style.top  = `${rect.top - 4}px`;
  document.body.appendChild(el);
  setTimeout(() => el.remove(), 1100);
}

// Offsesy pro 5 částic (gold = ventilátor dolů, xp = ventilátor nahoru/do stran)
const _PARTICLE_OFFSETS = {
  gold: [[-32, 28], [-14, 42], [0, 46], [14, 42], [32, 28]],
  xp:   [[-36, -8], [-18, -26], [0, -32], [18, -26], [36, -8]],
};

function _spawnRewardParticles(type) {
  const anchorId = type === 'gold' ? 'tb-gold' : 'xp-strip';
  const anchor   = document.getElementById(anchorId);
  if (!anchor) return;
  const rect    = anchor.getBoundingClientRect();
  const cx      = rect.left + rect.width / 2;
  const cy      = rect.top  + rect.height / 2;
  const symbols = type === 'gold' ? ['🪙', '💰', '✨'] : ['⭐', '✨', '💫'];
  const offsets = _PARTICLE_OFFSETS[type];
  offsets.forEach(([dx, dy], i) => {
    const p = document.createElement('span');
    p.className = 'reward-particle';
    p.textContent = symbols[i % symbols.length];
    p.style.setProperty('--dx', `${dx + (Math.random() * 8 - 4)}px`);
    p.style.setProperty('--dy', `${dy}px`);
    p.style.left           = `${cx}px`;
    p.style.top            = `${cy}px`;
    p.style.animationDelay = `${i * 55}ms`;
    document.body.appendChild(p);
    setTimeout(() => p.remove(), 950 + i * 55);
  });
}

function _playLevelUpAnim(newLevel) {
  const flash = document.createElement('div');
  flash.className = 'level-up-flash';
  document.body.appendChild(flash);
  setTimeout(() => flash.remove(), 900);
  const runes = document.createElement('div');
  runes.className = 'level-up-runes';
  runes.textContent = '✦ ᚱ ✦';
  document.body.appendChild(runes);
  setTimeout(() => runes.remove(), 960);
  document.querySelectorAll('.portrait-outer, .equip-portrait-outer').forEach(el => {
    el.classList.remove('portrait-level-glow');
    void el.offsetWidth; // restart animation
    el.classList.add('portrait-level-glow');
    setTimeout(() => el.classList.remove('portrait-level-glow'), 2000);
  });
  setTimeout(() => toast(`⬆️ Level Up! Dosáhl jsi levelu ${newLevel}!`, 's', 4000), 300);
}

// ── UPDATE UI ─────────────────────────────────────────────────────────────
function updateUI(c) {
  console.log('[UI] updateUI() called with char:', c.id, c.name);
  char = c;
  // Detekuj změny pro reward animace
  const _ag = _prevGold, _ax = _prevXp, _al = _prevLevel;
  _prevGold = c.gold; _prevXp = c.xp; _prevLevel = c.level;
  const goldGained = (_ag !== null && c.gold  > _ag) ? c.gold - _ag : 0;
  const xpGained   = (_ax !== null && c.xp   > _ax && c.level === _al) ? c.xp - _ax : 0;
  const leveledUp  = (_al !== null && c.level > _al);
  const cl = c.cls;
  document.getElementById('tb-char').style.display = 'flex';
  const titleHtml = c.current_title ? `<span class="char-title">[${esc(c.current_title)}]</span> ` : '';
  const nameColor  = c.crystal_name_color || null;
  const nameHtml   = nameColor
    ? `<span style="color:${nameColor}">${esc(c.name)}</span>`
    : esc(c.name);
  set('tb-avatar', CLS_E[cl]);
  const avatarEl = document.getElementById('tb-avatar');
  if (avatarEl) {
    avatarEl.dataset.cls = cl;
    const activeFrameTb = c.season_portrait_frame || c.prestige_portrait_frame || c.crystal_portrait_frame || null;
    if (activeFrameTb) avatarEl.dataset.frame = activeFrameTb;
    else delete avatarEl.dataset.frame;
  }
  setHTML('tb-name', titleHtml + nameHtml);
  set('tb-lvl', `Lv.${c.level}`); set('tb-cls', CLS_N[cl]);
  if (goldGained > 0) {
    _tweenGold(document.getElementById('tb-gold'), _ag, c.gold);
    _spawnRewardLabel(goldGained, 'gold');
    _spawnRewardParticles('gold');
  } else {
    set('tb-gold', c.gold.toLocaleString('cs'));
  }
  if (c.crystals != null) {
    const crystalsEl = document.getElementById('tb-crystals');
    if (crystalsEl) crystalsEl.style.display = '';
    set('tb-crystals-val', c.crystals.toLocaleString('cs'));
  }

  // Use DiceBear avatar if appearance is available
  const avatarImg = document.getElementById('p-avatar-img');
  const avatarEmoji = document.getElementById('p-emoji');
  
  // Portrait frame — pořadí priority: season > prestige > crystal
  const ALL_FRAME_KEYS = [
    'bronze','silver','gold','arcane','ruby','legendary',
    'season-champion','season-challenger','season-veteran',
    'prestige-1','prestige-2','prestige-3','prestige-4','prestige-5',
    'prestige-6','prestige-7','prestige-8','prestige-9','prestige-10',
  ];
  const activeFrame = c.season_portrait_frame || c.prestige_portrait_frame || c.crystal_portrait_frame || null;
  document.querySelectorAll('.portrait-outer, .equip-portrait-outer').forEach(el => {
    ALL_FRAME_KEYS.forEach(k => el.classList.remove('pf-' + k));
    if (activeFrame) el.classList.add('pf-' + activeFrame);
  });

  if (avatarImg && c.appearance) {
    console.log('[UI] c.appearance:', c.appearance);
    console.log('[UI] c.appearance keys:', Object.keys(c.appearance));
    const url = getAvatarUrl(c.appearance, c.id);
    console.log('[UI] getAvatarUrl returned:', url);
    console.log('[UI] Setting avatar URL on #p-avatar-img');
    avatarImg.src = url;
    avatarImg.style.display = 'block';
    
    // Setup error handling
    avatarImg.onerror = function() {
      console.error('[UI] Avatar failed to load from:', this.src);
      this.style.display = 'none';
      if (avatarEmoji) avatarEmoji.style.display = 'block';
    };
    
    avatarImg.onload = function() {
      console.log('[UI] Avatar loaded successfully from:', this.src);
      if (avatarEmoji) avatarEmoji.style.display = 'none';
    };
  } else if (avatarEmoji) {
    console.log('[UI] Appearance not available or no avatar img, showing emoji fallback');
    // Fallback to emoji
    const avatarEmojiText = (typeof getAppearanceAvatar === 'function' && c.appearance)
      ? getAppearanceAvatar(c.appearance)
      : CLS_E[cl];
    if (avatarImg) avatarImg.style.display = 'none';
    avatarEmoji.style.display = 'block';
    set('p-emoji', avatarEmojiText);
  }
  
  setHTML('p-name', titleHtml + nameHtml);
  set('p-level', `Level ${c.level}`);
  // XP strip
  const xpPct = c.xp_to_next > 0 ? Math.min(100, (c.xp / c.xp_to_next) * 100) : 0;
  const stripFill = document.getElementById('xp-strip-fill');
  const stripLbl = document.getElementById('xp-strip-lbl');
  if (stripFill) stripFill.style.width = xpPct.toFixed(1) + '%';
  if (stripLbl) stripLbl.textContent = `Lv.${c.level} · ${c.xp} / ${c.xp_to_next} XP (${Math.floor(xpPct)}%)`;
  const strip = document.getElementById('xp-strip');
  if (strip) strip.title = `Lv.${c.level} · ${c.xp} / ${c.xp_to_next} XP`;

  set('ov-level', c.level);
  set('ov-xp', `${c.xp} / ${c.xp_to_next} XP`);
  set('ov-gold', c.gold.toLocaleString('cs') + ' G');
  set('ov-arena', `#${c.arena.rank}`); set('ov-wl', `${c.arena.wins}W / ${c.arena.losses}L`);
  set('ov-cls', `${CLS_E[cl]} ${CLS_N[cl]}`); set('ov-desc', CLS_D[cl]);
  set('ov-name', c.name);
  // Dashboard avatar (emoji fallback)
  const dashAvatar = document.getElementById('dash-avatar');
  if (dashAvatar) dashAvatar.textContent = CLS_E[cl] || '⚔';
  // Dashboard XP bar
  const xpFill = document.getElementById('dash-xp-fill');
  if (xpFill) xpFill.style.width = `${Math.max(2, Math.min(100, (c.xp / c.xp_to_next) * 100))}%`;
  // Pending actions
  _updateDashPending(c);

  // Frakce v přehledu
  const ovFaction = document.getElementById('ov-faction');
  if (ovFaction) {
    const fRep = factionData?.reputation ?? 0;
    ovFaction.innerHTML = typeof getFactionChipHtml === 'function'
      ? getFactionChipHtml(c.faction, fRep)
      : (c.faction || 'Bez frakce');
  }

  // Vzhled v přehledu
  if (c.appearance && document.getElementById('ov-appearance')) {
    const appearanceDisplay = _getAppearanceDisplayText(c.appearance);
    set('ov-appearance', appearanceDisplay);
  }

  renderActiveBuffs(c.active_buffs || []);

  // Stat points nav badge + propagace do group headeru
  const spBadge = document.getElementById('sp-nav-badge');
  const hasPoints = (c.stat_points || 0) > 0;
  if (spBadge) spBadge.classList.toggle('visible', hasPoints);
  const gBadge = document.getElementById('ngn-progression');
  if (gBadge) {
    gBadge.style.display = hasPoints ? 'flex' : 'none';
    gBadge.textContent = hasPoints ? c.stat_points : '';
  }

  // Arena rank chip — show when rank is notable (top 100 = rank ≤ 100 usually)
  const rankChip = document.getElementById('tb-rank-chip');
  const rankVal  = document.getElementById('tb-rank-val');
  if (rankChip && rankVal) {
    rankVal.textContent = `#${c.arena?.rank ?? '—'}`;
    rankChip.style.display = 'flex';
  }

  // Pokud je Vybavení otevřené, překresli ho (obsahuje atributy a stat body)
  if (document.getElementById('page-equipment')?.classList.contains('active')) {
    if (typeof renderEquip === 'function') renderEquip();
  }

  // XP a Level Up animace — na konci aby neblokoval hlavní render
  if (xpGained > 0) {
    _spawnRewardLabel(xpGained, 'xp');
    _spawnRewardParticles('xp');
  }
  if (leveledUp) {
    _playLevelUpAnim(c.level);
  }
}

// ── DASHBOARD PENDING ACTIONS ──────────────────────────────────────────────
function _updateDashPending(c) {
  const el = document.getElementById('dash-pending-actions');
  if (!el) return;
  const actions = [];

  if ((c.stat_points || 0) > 0) {
    actions.push({
      ico: '⬆', urgent: true,
      txt: `<strong>${c.stat_points} ${c.stat_points === 1 ? 'bod' : 'body'} k přidělení</strong> — zvyš si statistiky`,
      page: 'equipment',
    });
  }

  if (!c.equipment?.weapon && !c.equipment?.armor) {
    actions.push({ ico: '🛡', urgent: false, txt: 'Navštiv <strong>Obchod</strong> nebo <strong>Tržiště</strong> pro vybavení', page: 'shop' });
  }

  if ((c.arena?.cooldown_until) === null) {
    actions.push({ ico: '🏟', urgent: false, txt: 'Jsi připraven do <strong>Arény</strong> — máš dostupné souboje', page: 'arena' });
  }

  if (actions.length === 0) {
    el.innerHTML = '<div class="dash-pending-empty">✓ Vše v pořádku — žádné čekající akce</div>';
    return;
  }

  el.innerHTML = actions.map(a => `
    <div class="dash-pending-item ${a.urgent ? 'urgent' : ''}" onclick="showPage('${a.page}')">
      <span class="dash-pending-ico">${a.ico}</span>
      <span class="dash-pending-txt">${a.txt}</span>
      <span style="color:var(--text3);font-size:.7rem">→</span>
    </div>
  `).join('');
}

// ── SYNC ACTIVITY LOG TO DASHBOARD ────────────────────────────────────────
function _syncDashActivity() {
  const dst = document.getElementById('dash-recent-activity');
  if (!dst || !window._actLog?.length) return;
  dst.innerHTML = window._actLog.slice(0, 6).map(e =>
    `<div class="dash-activity-row">
      <span class="dash-activity-time">${e.t}</span>
      <span class="dash-activity-txt">${esc(e.text)}</span>
    </div>`
  ).join('');
}

function _getAppearanceDisplayText(appearance) {
  if (!appearance) return 'Standardní vzhled';
  
  // Pokud máme načtené možnosti, použij je
  if (window.appearanceOptions) {
    const opts = window.appearanceOptions;
    const parts = [];
    
    if (appearance.hair_style !== undefined && opts.hair_styles[appearance.hair_style]) {
      parts.push(`<strong>Vlasy:</strong> ${opts.hair_styles[appearance.hair_style].name}`);
    }
    if (appearance.skin_tone !== undefined && opts.skin_tones[appearance.skin_tone]) {
      parts.push(`<strong>Pokožka:</strong> ${opts.skin_tones[appearance.skin_tone].name}`);
    }
    if (appearance.eye_color !== undefined && opts.eye_colors[appearance.eye_color]) {
      parts.push(`<strong>Oči:</strong> ${opts.eye_colors[appearance.eye_color].name}`);
    }
    
    return parts.length ? parts.join(' · ') : 'Přizpůsobený vzhled';
  }
  
  // Fallback: struktura bez překladu
  return 'Vlastní vzhled';
}

// ── AKTIVNÍ BUFFY ─────────────────────────────────────────────────────────
function renderActiveBuffs(buffs) {
  const chip  = document.getElementById('tb-buff-chip');
  const count = document.getElementById('tb-buff-count');
  const drop  = document.getElementById('tb-buff-dropdown');
  if (!chip) return;
  if (!buffs || buffs.length === 0) { chip.style.display = 'none'; return; }

  const STAT_N = {bonus_str:'Síla',bonus_dex:'Obratnost',bonus_int:'Inteligence',bonus_end:'Výdrž',bonus_luck:'Štěstí'};
  chip.style.display = 'flex';
  count.textContent  = buffs.length;

  drop.innerHTML = buffs.map(b => {
    const exp  = new Date((b.expires_at.includes('T') && !b.expires_at.endsWith('Z')) ? b.expires_at + 'Z' : b.expires_at);
    const diff = exp - new Date();
    const days = Math.floor(diff / 86400000);
    const hrs  = Math.floor((diff % 86400000) / 3600000);
    const mins = Math.floor((diff % 3600000)  / 60000);
    const timeStr = diff <= 0 ? 'Expirováno'
                  : days > 0  ? `${days}d ${hrs}h`
                  : hrs  > 0  ? `${hrs}h ${mins}m`
                  : `${mins}m`;
    const bons = Object.entries(STAT_N)
      .filter(([k]) => b[k] > 0)
      .map(([k,n]) => `+${b[k]} ${n}`).join(' · ');
    return `<div class="tb-buff-entry">
      <span class="tb-buff-entry-name">⚗️ ${esc(b.name)}</span>
      <span class="tb-buff-entry-bonuses">${bons || '—'}</span>
      <span class="tb-buff-entry-timer${diff <= 0 ? ' expired' : ''}">⏰ ${timeStr}</span>
    </div>`;
  }).join('');
}

function toggleBuffDropdown(e) {
  e.stopPropagation();
  const drop = document.getElementById('tb-buff-dropdown');
  if (!drop) return;
  drop.classList.toggle('open');
}

// Zavři dropdown při kliknutí mimo
document.addEventListener('click', () => {
  const drop = document.getElementById('tb-buff-dropdown');
  if (drop) drop.classList.remove('open');
});
