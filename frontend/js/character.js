// ── TVORBA POSTAVY ────────────────────────────────────────────────────────
const CLS_MECHANIC = {
  warrior: {
    badge: 'rage-badge',
    label: 'Rage',
    flavor: 'Tvoje zuřivost roste s každou ránou. Přežij dost dlouho a staneš se neovladatelný.',
    detail: 'Buduj rage každým zásahem. Při 100: Berserker Burst!',
  },
  mage: {
    badge: 'chain-badge',
    label: 'Chain',
    flavor: 'Magie reaguje na sebe. Každé kouzlo nastaví to příští. Poznej pořadí.',
    detail: 'Střídej typy kouzel pro +20% damage combo.',
  },
  ranger: {
    badge: 'first-strike-badge',
    label: 'First Strike',
    flavor: 'První šíp zasáhne vždy. Druhý trochu míň. Třetí... doufej, že ho nepotřebuješ.',
    detail: '+40% damage kolo 1. Výhoda klesá každé kolo.',
  },
};

function loadCls() {
  clsData = {
    warrior: { description:'Silný bojovník v přední linii. Vysoký HP a obrana.', hp_base:120, atk_base:18, spd_base:8 },
    mage:    { description:'Mistr arkánné magie. Devastující kouzla, křehké tělo.', hp_base:70,  atk_base:10, spd_base:10 },
    ranger:  { description:'Rychlý a přesný lovec. Mistr kritických zásahů.', hp_base:90,  atk_base:14, spd_base:18 },
  };
  renderClsGrid();
}

function renderClsGrid() {
  const grid = document.getElementById('cls-grid');
  if (!grid) return;
  grid.innerHTML = Object.entries(clsData).map(([k,c])=>{
    const m = CLS_MECHANIC[k];
    const badge = m ? `<span class="cls-mechanic-badge ${m.badge}">${m.label}</span>` : '';
    const flavor = m?.flavor ? `<div class="cls-flavor">${m.flavor}</div>` : '';
    const detail = m?.detail ? `<div class="cls-mechanic-detail ${m.badge}">${m.detail}</div>` : '';
    return `
    <div class="cls-card" id="cc-${k}" onclick="pickCls('${k}')">
      <div class="cls-emoji">${CLS_E[k]}</div>
      <div class="cls-name">${CLS_N[k]}</div>
      ${badge}
      <div class="cls-desc">${c.description}</div>
      ${flavor}
      ${detail}
      <div class="cls-nums">❤ ${c.hp_base} · ⚔ ${c.atk_base} · ⚡ ${c.spd_base}</div>
    </div>`;
  }).join('');
  // Vždy taky překresli faction grid (faction.js je načten před character.js)
  _renderFactionModalGrid();
}

function _renderFactionModalGrid() {
  const wrap = document.getElementById('faction-grid-modal');
  if (!wrap) return;
  // Použij FACTION_META ze faction.js (nebo fallback)
  const meta = typeof FACTION_META !== 'undefined' ? FACTION_META : {
    rad_popele:         { emblem:'🔥', color:'#c0392b', dim:'rgba(192,57,43,0.15)',  name:'Řád Popele' },
    pakt_stinu:         { emblem:'🌑', color:'#6c3483', dim:'rgba(108,52,131,0.15)', name:'Pakt Stínu' },
    kongregace_prazdna: { emblem:'🌀', color:'#1a6b8a', dim:'rgba(26,107,138,0.15)',name:'Kongregace Prázdna' },
  };
  const af = typeof allFactions !== 'undefined' ? allFactions : null;
  wrap.innerHTML = Object.entries(meta).map(([id, m]) => {
    const f = af?.find(x => x.id === id) || {};
    return `
      <div class="faction-card" id="fm-${id}"
           onclick="_pickFactionModal('${id}','${m.color}','${m.dim}')"
           style="border-color:var(--border)">
        <div class="faction-emblem">${m.emblem}</div>
        <div class="faction-card-name" style="color:${m.color}">${m.name}</div>
        <div class="faction-card-tagline" style="font-size:0.62rem;color:var(--text3);font-style:italic;line-height:1.3">${esc(f.tagline || '')}</div>
      </div>`;
  }).join('');
  // Obnov případný výběr
  const sf = typeof selFaction !== 'undefined' ? selFaction : null;
  if (sf && meta[sf]) _pickFactionModal(sf, meta[sf].color, meta[sf].dim);
}

function _pickFactionModal(id, color, dim) {
  if (typeof selFaction !== 'undefined') selFaction = id;
  document.querySelectorAll('#faction-grid-modal .faction-card').forEach(c => {
    c.style.borderColor = 'var(--border)';
    c.style.background  = 'var(--panel)';
  });
  const card = document.getElementById(`fm-${id}`);
  if (card) { card.style.borderColor = color; card.style.background = dim; }
}

function pickCls(k){selCls=k;document.querySelectorAll('.cls-card').forEach(c=>c.classList.remove('sel'));document.getElementById(`cc-${k}`)?.classList.add('sel');}

async function createChar(){
  const name=document.getElementById('c-name').value.trim();
  if(!name) return showFMsg('Zadej jméno.','err');
  if(!selCls) return showFMsg('Vyber povolání.','err');
  if(!selFaction) {
    showFMsg('Vyber frakci (Řád Popele, Pakt Stínu nebo Kongregace Prázdna).','err');
    document.getElementById('faction-grid-modal')?.scrollIntoView({behavior:'smooth',block:'center'});
    // Pokud grid je prázdný, překresli
    if(!document.getElementById('faction-grid-modal')?.children.length) _renderFactionModalGrid();
    return;
  }
  document.getElementById('c-btn').disabled=true;
  try{
    const d=await api('POST','/character/create',{name,cls:selCls,faction:selFaction});
    localStorage.setItem('dc_has_character','true');
    closeModal('modal-create');
    updateUI(d.character);
    addAct(`🎉 Hrdina ${d.character.name} vstoupil!`);
    const fName = FACTION_META[selFaction]?.name || selFaction;
    toast(`Vítej, hrdino! Frakce: ${fName}`, 's', 5000);
    // Spustit onboarding průvodce pro nové hráče
    setTimeout(() => {
      if (typeof startOnboarding === 'function') startOnboarding();
    }, 800);
  }catch(e){showFMsg(e.message,'err');document.getElementById('c-btn').disabled=false;}
}

function showFMsg(msg,type){const el=document.getElementById('c-msg');el.className=`fmsg ${type}`;el.textContent=msg;}

// ── ŽEBŘÍČEK — nyní pouze pro interní použití; rpanel odstraněn ───────────
async function loadLB(){}

// ── AKTIVITA (in-memory, syncs to Hub dashboard) ──────────────────────────
window._actLog = window._actLog || [];
function addAct(text) {
  const now = new Date();
  const t = `${String(now.getHours()).padStart(2,'0')}:${String(now.getMinutes()).padStart(2,'0')}`;
  window._actLog.unshift({ t, text });
  if (window._actLog.length > 15) window._actLog.pop();
  if (typeof _syncDashActivity === 'function') _syncDashActivity();
}

async function refreshChar(){
  try{
    updateUI(await api('GET','/character/me'));
    if (document.getElementById('page-equipment')?.classList.contains('active')) renderEquip();
    toast('Obnoveno','i',1200);
  }
  catch(e){if(e.message.includes('404'))openModal('modal-create');else toast(e.message,'e');}
}

// ── STAT ALOKACE ──────────────────────────────────────────────────────────
const STAT_CZ = {strength:'Síla',dexterity:'Obratnost',intelligence:'Inteligence',endurance:'Výdrž',luck:'Štěstí'};

async function allocStat(stat, ev) {
  // ── Floating "+1" animace ze středu tlačítka ──
  const btn = ev?.target?.closest('button');
  if (btn) {
    const rect = btn.getBoundingClientRect();
    const floater = document.createElement('div');
    floater.className = 'stat-alloc-float';
    floater.textContent = '+1';
    floater.style.left = (rect.left + rect.width / 2 - 12) + 'px';
    floater.style.top  = (rect.top - 2) + 'px';
    document.body.appendChild(floater);
    floater.addEventListener('animationend', () => floater.remove());
  }

  try {
    const d = await api('POST', '/character/allocate-stat', { stat });
    updateUI(d.character);
    if (document.getElementById('page-equipment')?.classList.contains('active')) {
      renderEquip();
      // Flash highlight na alokovanou stat kartu
      setTimeout(() => {
        const card = document.getElementById(`sp-attr-${stat}`);
        if (card) {
          card.classList.remove('stat-flash');
          void card.offsetWidth; // force reflow
          card.classList.add('stat-flash');
        }
      }, 0);
    }
    toast(`+1 ${STAT_CZ[stat] || stat}! Zbývá ${d.stat_points_remaining} bodů.`, 's', 3000);
    addAct(`⬆ Alokováno: +1 ${STAT_CZ[stat] || stat}`);
  } catch(e) { toast(e.message, 'e'); }
}

// ── USE ITEM (lektvary / svitky) ──────────────────────────────────────────
async function useItem(invItemId, itemName) {
  await _doUseItem(invItemId, itemName, null);
}

async function _doUseItem(invItemId, itemName, replaceBuff) {
  try {
    const body = replaceBuff !== null ? { replace_buff: replaceBuff } : {};
    const d = await api('POST', `/inventory/use/${invItemId}`, Object.keys(body).length ? body : undefined);
    closeModal('modal-item');
    closeModal('modal-buff-replace');
    updateUI(d.character);
    if (document.getElementById('page-equipment')?.classList.contains('active')) renderEquip();

    const changes = Object.entries(d.stat_changes || {})
      .map(([k,v]) => `+${v} ${STAT_CZ[k]||k}`).join(', ');
    const dayStr = d.buff_duration_days ? ` (${d.buff_duration_days}d)` : '';
    const xpStr  = d.xp_gained ? ` +${d.xp_gained} XP` : '';
    toast(`🧪 '${itemName}' použit!${changes ? ' ' + changes + dayStr : ''}${xpStr}`, 's', 4000);
    addAct(`🧪 Použit: ${itemName}${changes ? ' ('+changes+dayStr+')' : ''}${xpStr}`);
    if (d.leveled_up?.length) {
      const lv = d.leveled_up.at(-1);
      const sp = d.character?.stat_points || 0;
      const spHint = sp > 0 ? ` · <span style="color:var(--green2);cursor:pointer" onclick="showPage('equipment')">Přiděl ${sp} bod${sp===1?'':'y'}!</span>` : '';
      toast(`⚡ Level up! Nyní level ${lv}${spHint}`, 's', 7000);
    }
    await loadInventory();
  } catch(e) {
    if (e.status === 409 && e.detail?.code === 'MAX_BUFFS') {
      _showBuffReplaceModal(e.detail.buffs, invItemId, itemName);
    } else {
      toast(e.message, 'e');
    }
  }
}

function _showBuffReplaceModal(buffs, invItemId, itemName) {
  const STAT_N = {bonus_str:'Síla',bonus_dex:'Obratnost',bonus_int:'Inteligence',bonus_end:'Výdrž',bonus_luck:'Štěstí'};
  const cards = buffs.map(b => {
    const stats = ['bonus_str','bonus_dex','bonus_int','bonus_end','bonus_luck']
      .filter(k => b[k]).map(k => `+${b[k]} ${STAT_N[k]}`).join(' · ');
    const exp = new Date(b.expires_at + 'Z').toLocaleDateString('cs');
    const safeN = b.name.replace(/\\/g,'\\\\').replace(/'/g,"\\'");
    const safeItem = itemName.replace(/\\/g,'\\\\').replace(/'/g,"\\'");
    return `
      <div class="buff-replace-card" onclick="_confirmBuffReplace('${safeN}',${invItemId},'${safeItem}')">
        <div class="buff-replace-name">${esc(b.name)}</div>
        ${stats ? `<div class="buff-replace-stats">${stats}</div>` : ''}
        <div class="buff-replace-expires">Vyprší: ${exp}</div>
      </div>`;
  }).join('');

  document.getElementById('modal-buff-replace-body').innerHTML = `
    <div class="modal-title" style="margin-bottom:14px">🧪 Nahradit elixír</div>
    <div class="buff-replace-hint">
      Máš <strong>3 aktivní elixíry</strong>. Vyber který chceš
      <span style="color:var(--accent2)">smazat</span>, aby se uvolnilo místo pro
      <span style="color:var(--gold2)">${esc(itemName)}</span>:
    </div>
    <div class="buff-replace-list">${cards}</div>
    <button class="btn" onclick="closeModal('modal-buff-replace')"
      style="margin-top:12px;width:100%;opacity:.7">Zrušit</button>`;

  closeModal('modal-item');
  openModal('modal-buff-replace');
}

async function _confirmBuffReplace(buffName, invItemId, itemName) {
  await _doUseItem(invItemId, itemName, buffName);
}
