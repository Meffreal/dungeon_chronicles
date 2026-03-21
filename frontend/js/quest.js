// ── QUESTY ────────────────────────────────────────────────────────────────
let _dailyResetTimer = null;
let _availableQuestsCache = [];

// ── NPC Quest Givers ──
const NPC_GIVERS = [
  {
    id: 'mage',
    name: 'Aldric Moudrý',
    title: 'Mystický Mág',
    avatar: `<svg viewBox="0 0 80 100" xmlns="http://www.w3.org/2000/svg" width="82" height="92" class="npc-portrait-svg">
      <defs>
        <radialGradient id="ald-bg" cx="50%" cy="40%" r="55%"><stop offset="0%" stop-color="#5030c0" stop-opacity=".4"/><stop offset="100%" stop-color="#1a0850" stop-opacity="0"/></radialGradient>
        <radialGradient id="ald-skin" cx="45%" cy="30%" r="60%"><stop offset="0%" stop-color="#c4a070"/><stop offset="100%" stop-color="#8a5c30"/></radialGradient>
        <radialGradient id="ald-orb" cx="35%" cy="30%" r="60%"><stop offset="0%" stop-color="#e0d0ff"/><stop offset="100%" stop-color="#6030c0"/></radialGradient>
        <filter id="ald-gf"><feGaussianBlur stdDeviation="2.5"/></filter>
      </defs>
      <ellipse cx="40" cy="44" rx="36" ry="46" fill="url(#ald-bg)"/>
      <line x1="67" y1="100" x2="71" y2="10" stroke="#4a3014" stroke-width="3.5"/>
      <circle cx="72" cy="12" r="9" fill="#7030c0" opacity=".45" filter="url(#ald-gf)"/>
      <circle cx="72" cy="12" r="6" fill="url(#ald-orb)"/>
      <circle cx="69" cy="9" r="2.2" fill="#fff" opacity=".85"/>
      <path d="M8,100 Q14,58 40,50 Q66,58 72,100Z" fill="#0e0330"/>
      <path d="M14,100 Q20,62 40,54 Q60,62 66,100Z" fill="#1c0650"/>
      <path d="M18,40 Q20,10 40,7 Q60,10 62,40 Q58,55 40,58 Q22,55 18,40Z" fill="#0e0330"/>
      <path d="M22,40 Q24,16 40,13 Q56,16 58,40 Q54,53 40,56 Q26,53 22,40Z" fill="#1a0548"/>
      <ellipse cx="40" cy="39" rx="13" ry="17" fill="url(#ald-skin)"/>
      <ellipse cx="34" cy="37" rx="5.5" ry="4" fill="#7030c0" opacity=".45" filter="url(#ald-gf)"/>
      <ellipse cx="46" cy="37" rx="5.5" ry="4" fill="#7030c0" opacity=".45" filter="url(#ald-gf)"/>
      <ellipse cx="34" cy="37" rx="4" ry="3" fill="#8845d5"/>
      <ellipse cx="46" cy="37" rx="4" ry="3" fill="#8845d5"/>
      <circle cx="32.5" cy="35.5" r="1.6" fill="#d0b0ff"/>
      <circle cx="44.5" cy="35.5" r="1.6" fill="#d0b0ff"/>
      <path d="M29,31 Q34,28 38,30" stroke="#6a4820" stroke-width="1.8" fill="none" stroke-linecap="round"/>
      <path d="M42,30 Q46,28 51,31" stroke="#6a4820" stroke-width="1.8" fill="none" stroke-linecap="round"/>
      <path d="M37,42 Q40,47 43,42" stroke="#a07040" stroke-width=".9" fill="none"/>
      <path d="M34,50 Q40,54 46,50" stroke="#7a5030" stroke-width="1.2" fill="none" stroke-linecap="round"/>
      <path d="M29,48 Q40,68 51,48 Q46,65 40,72 Q34,65 29,48Z" fill="#706050"/>
      <path d="M33,48 Q40,62 47,48 Q44,58 40,64 Q36,58 33,48Z" fill="#908070"/>
      <text x="6" y="26" font-size="11" fill="#8050e0" opacity=".5" font-family="serif">✦</text>
      <text x="62" y="72" font-size="9" fill="#6040c0" opacity=".4" font-family="serif">✧</text>
      <circle cx="11" cy="42" r="1.5" fill="#a080f0" opacity=".65"/>
      <circle cx="70" cy="44" r="1.2" fill="#c0a0ff" opacity=".5"/>
      <circle cx="7" cy="70" r="1" fill="#8060d0" opacity=".4"/>
    </svg>`,
    artClass: 'npc-art--mage',
    color: '#9868f0',
    rgb: '152,104,240',
    difficulty: 'easy',
    slotHint: 0,
    speechActive: 'Potřebuji někoho odhodlaného. Snad jsi to ty, hrdino...',
    speechIdle: 'Zatím nemám nic vhodného. Vrať se zanedlouho.',
    particleColor: 'rgba(180,140,255,',
  },
  {
    id: 'merc',
    name: 'Brutus Železný',
    title: 'Žoldnéř v Taverně',
    avatar: `<svg viewBox="0 0 80 100" xmlns="http://www.w3.org/2000/svg" width="82" height="92" class="npc-portrait-svg">
      <defs>
        <radialGradient id="bru-bg" cx="50%" cy="45%" r="55%"><stop offset="0%" stop-color="#c06018" stop-opacity=".32"/><stop offset="100%" stop-color="#500808" stop-opacity="0"/></radialGradient>
        <radialGradient id="bru-skin" cx="42%" cy="28%" r="65%"><stop offset="0%" stop-color="#c87850"/><stop offset="100%" stop-color="#8a4028"/></radialGradient>
        <linearGradient id="bru-metal" x1="0%" y1="0%" x2="100%" y2="100%"><stop offset="0%" stop-color="#686050"/><stop offset="100%" stop-color="#2a1c10"/></linearGradient>
      </defs>
      <ellipse cx="40" cy="52" rx="36" ry="46" fill="url(#bru-bg)"/>
      <path d="M4,100 Q8,60 40,52 Q72,60 76,100Z" fill="#1c1208"/>
      <path d="M8,100 Q12,64 40,56 Q68,64 72,100Z" fill="#281a10"/>
      <ellipse cx="16" cy="62" rx="14" ry="9" fill="url(#bru-metal)" transform="rotate(-12,16,62)"/>
      <ellipse cx="64" cy="62" rx="14" ry="9" fill="url(#bru-metal)" transform="rotate(12,64,62)"/>
      <ellipse cx="16" cy="60" rx="12" ry="7" fill="#585040" transform="rotate(-12,16,60)"/>
      <ellipse cx="64" cy="60" rx="12" ry="7" fill="#585040" transform="rotate(12,64,60)"/>
      <circle cx="11" cy="57" r="1.6" fill="#c0a060"/><circle cx="19" cy="54" r="1.6" fill="#c0a060"/>
      <circle cx="61" cy="54" r="1.6" fill="#c0a060"/><circle cx="69" cy="57" r="1.6" fill="#c0a060"/>
      <path d="M20,68 Q40,62 60,68 L64,100 L16,100Z" fill="#342018"/>
      <path d="M26,68 L26,100 M40,62 L40,100 M54,68 L54,100" stroke="#48301a" stroke-width=".8" opacity=".45"/>
      <ellipse cx="40" cy="54" rx="12" ry="7" fill="#484040"/>
      <ellipse cx="40" cy="36" rx="19" ry="22" fill="#c07850"/>
      <ellipse cx="40" cy="34" rx="17" ry="20" fill="url(#bru-skin)"/>
      <path d="M23,26 Q27,12 40,10 Q53,12 57,26 Q49,16 40,14 Q31,16 23,26Z" fill="#281808"/>
      <path d="M23,24 Q27,14 40,12 Q53,14 57,24" fill="#1e1006"/>
      <line x1="27" y1="33" x2="31" y2="43" stroke="#a04828" stroke-width="2" stroke-linecap="round"/>
      <path d="M26,27 Q32,23 37,26" stroke="#28140a" stroke-width="2.8" fill="none" stroke-linecap="round"/>
      <path d="M43,26 Q48,23 54,27" stroke="#28140a" stroke-width="2.8" fill="none" stroke-linecap="round"/>
      <ellipse cx="33" cy="31" rx="4.5" ry="3" fill="#ecdcbc"/>
      <ellipse cx="47" cy="31" rx="4.5" ry="3" fill="#ecdcbc"/>
      <ellipse cx="33" cy="31" rx="2.8" ry="2" fill="#701808"/>
      <ellipse cx="47" cy="31" rx="2.8" ry="2" fill="#701808"/>
      <circle cx="31.5" cy="30" r="1" fill="#fff" opacity=".8"/>
      <circle cx="45.5" cy="30" r="1" fill="#fff" opacity=".8"/>
      <path d="M37,37 Q40,42 43,37" stroke="#904030" stroke-width="1" fill="none"/>
      <path d="M33,47 Q40,51 47,47" stroke="#6a2818" stroke-width="1.5" fill="none" stroke-linecap="round"/>
      <ellipse cx="40" cy="49" rx="10" ry="7" fill="#3a2010" opacity=".4"/>
      <rect x="69" y="50" width="4" height="50" rx="2" fill="#3a2010"/>
      <path d="M67,50 Q73,43 79,50 L77,63 Q73,58 69,63Z" fill="#706040"/>
      <path d="M67.5,51 Q73,45 78.5,51" fill="none" stroke="#c0a060" stroke-width=".9"/>
      <circle cx="8" cy="42" r="1.5" fill="#ff8030" opacity=".55"/>
      <circle cx="6" cy="72" r="1" fill="#ff6020" opacity=".4"/>
      <circle cx="74" cy="68" r="1" fill="#ffa040" opacity=".4"/>
    </svg>`,
    artClass: 'npc-art--merc',
    color: '#e08830',
    rgb: '224,136,48',
    difficulty: 'normal',
    slotHint: 1,
    speechActive: 'Dobré zlato za dobrou práci. Žádné výmluvy.',
    speechIdle: 'Dneska nic kloudného nemám. Zkus to zítra.',
    particleColor: 'rgba(255,148,60,',
  },
  {
    id: 'guard',
    name: 'Kapitán Vayne',
    title: 'Královský Kapitán',
    avatar: `<svg viewBox="0 0 80 100" xmlns="http://www.w3.org/2000/svg" width="82" height="92" class="npc-portrait-svg">
      <defs>
        <radialGradient id="vay-bg" cx="50%" cy="38%" r="55%"><stop offset="0%" stop-color="#c09010" stop-opacity=".3"/><stop offset="100%" stop-color="#402800" stop-opacity="0"/></radialGradient>
        <radialGradient id="vay-skin" cx="45%" cy="30%" r="60%"><stop offset="0%" stop-color="#c29870"/><stop offset="100%" stop-color="#8a6040"/></radialGradient>
        <linearGradient id="vay-gold" x1="0%" y1="0%" x2="100%" y2="100%"><stop offset="0%" stop-color="#f0d050"/><stop offset="100%" stop-color="#907010"/></linearGradient>
        <linearGradient id="vay-armor" x1="0%" y1="0%" x2="100%" y2="100%"><stop offset="0%" stop-color="#505060"/><stop offset="100%" stop-color="#18181e"/></linearGradient>
      </defs>
      <ellipse cx="40" cy="46" rx="36" ry="46" fill="url(#vay-bg)"/>
      <path d="M14,56 Q10,80 16,100 L36,100 L36,60Z" fill="#8a0012" opacity=".92"/>
      <path d="M66,56 Q70,80 64,100 L44,100 L44,60Z" fill="#8a0012" opacity=".92"/>
      <path d="M15,62 Q12,84 18,100" stroke="#cc0020" stroke-width="1.2" fill="none" opacity=".45"/>
      <path d="M65,62 Q68,84 62,100" stroke="#cc0020" stroke-width="1.2" fill="none" opacity=".45"/>
      <path d="M10,100 Q14,62 40,54 Q66,62 70,100Z" fill="url(#vay-armor)"/>
      <path d="M14,100 Q18,66 40,58 Q62,66 66,100Z" fill="#2e2e3e"/>
      <path d="M16,75 Q40,69 64,75" stroke="#b08012" stroke-width="1.5" fill="none"/>
      <path d="M18,87 Q40,81 62,87" stroke="#b08012" stroke-width="1" fill="none" opacity=".6"/>
      <polygon points="40,62 43.5,71 53,71 45.5,76.5 48,85 40,80 32,85 34.5,76.5 27,71 36.5,71" fill="#c09010"/>
      <polygon points="40,64 43,71 51,71 44.5,76 47,84 40,79 33,84 35.5,76 29,71 37,71" fill="#f0d050"/>
      <path d="M7,58 Q10,46 22,48 Q28,50 26,64 Q18,68 8,62Z" fill="#28283a"/>
      <path d="M7,56 Q10,44 22,46 Q28,48 26,62 Q18,66 8,60Z" fill="url(#vay-gold)"/>
      <path d="M73,58 Q70,46 58,48 Q52,50 54,64 Q62,68 72,62Z" fill="#28283a"/>
      <path d="M73,56 Q70,44 58,46 Q52,48 54,62 Q62,66 72,60Z" fill="url(#vay-gold)"/>
      <path d="M9,55 Q17,50 24,54" stroke="#8a6010" stroke-width=".9" fill="none"/>
      <path d="M71,55 Q63,50 56,54" stroke="#8a6010" stroke-width=".9" fill="none"/>
      <path d="M20,30 Q22,8 40,5 Q58,8 60,30 Q58,40 40,42 Q22,40 20,30Z" fill="#28283c"/>
      <path d="M23,30 Q25,12 40,9 Q55,12 57,30 Q55,39 40,41 Q25,39 23,30Z" fill="#38384e"/>
      <rect x="38" y="22" width="4" height="20" rx="2" fill="#24243a"/>
      <path d="M20,32 Q40,37 60,32" stroke="#c09010" stroke-width="1.3" fill="none"/>
      <path d="M22,20 Q40,17 58,20" stroke="#c09010" stroke-width=".9" fill="none" opacity=".7"/>
      <path d="M24,26 Q29,23 36,25" stroke="#14141e" stroke-width="1.8" fill="none"/>
      <path d="M44,25 Q51,23 56,26" stroke="#14141e" stroke-width="1.8" fill="none"/>
      <path d="M36,5 Q40,1 44,5" stroke="#c09010" stroke-width="2.2" fill="none" stroke-linecap="round"/>
      <path d="M28,6 Q24,2 18,4 Q14,0 10,2 Q14,6 20,7 Q24,8 28,7Z" fill="#b01a1a"/>
      <path d="M52,6 Q56,2 62,4 Q66,0 70,2 Q66,6 60,7 Q56,8 52,7Z" fill="#b01a1a"/>
      <path d="M30,5 Q26,1 22,3" stroke="#dd2222" stroke-width=".8" fill="none" opacity=".6"/>
      <path d="M50,5 Q54,1 58,3" stroke="#dd2222" stroke-width=".8" fill="none" opacity=".6"/>
      <ellipse cx="40" cy="30" rx="12" ry="15" fill="url(#vay-skin)"/>
      <path d="M29,23 Q35,20 39,22" stroke="#3a2010" stroke-width="2.4" fill="none" stroke-linecap="round"/>
      <path d="M41,22 Q45,20 51,23" stroke="#3a2010" stroke-width="2.4" fill="none" stroke-linecap="round"/>
      <ellipse cx="35" cy="27" rx="4" ry="2.8" fill="#e8e2d0"/>
      <ellipse cx="45" cy="27" rx="4" ry="2.8" fill="#e8e2d0"/>
      <ellipse cx="35" cy="27" rx="2.4" ry="1.8" fill="#3a5898"/>
      <ellipse cx="45" cy="27" rx="2.4" ry="1.8" fill="#3a5898"/>
      <circle cx="33.8" cy="26.2" r="1" fill="#fff" opacity=".8"/>
      <circle cx="43.8" cy="26.2" r="1" fill="#fff" opacity=".8"/>
      <path d="M38,32 Q40,37 42,32" stroke="#906040" stroke-width=".9" fill="none"/>
      <path d="M33,40 Q40,44 47,40" stroke="#906040" stroke-width=".9" fill="none" opacity=".5"/>
      <circle cx="7" cy="32" r="1.5" fill="#f0d050" opacity=".55"/>
      <circle cx="73" cy="26" r="1.2" fill="#e0c030" opacity=".45"/>
      <circle cx="66" cy="72" r="1" fill="#c0a020" opacity=".4"/>
    </svg>`,
    artClass: 'npc-art--guard',
    color: '#f0d050',
    rgb: '240,208,80',
    difficulty: 'hard',
    slotHint: 2,
    speechActive: 'Toto je královský rozkaz. Selhat není možnost.',
    speechIdle: 'Pro tebe momentálně nemám úkol hodný Krále.',
    particleColor: 'rgba(255,220,80,',
  },
];

async function loadQuests() {
  try {
    const [data, status, daily] = await Promise.all([
      api('GET', '/quest/list'),
      api('GET', '/quest/status'),
      api('GET', '/quest/daily').catch(() => null),
    ]);
    const quests      = data.quests ?? data;
    const recommended = data.recommended || [];
    const chainQuests = data.chain_quests || [];
    renderAQ(status);
    renderRecommended(recommended, status);
    renderDailyQuests(daily, status.status);
    renderQList(quests, status.status, chainQuests, status);
  } catch(e) { toast(e.message,'e'); }
}

// ── Difficulty metadata ──
const DIFF_META = {
  easy:   { c:'#30a848', rgb:'48,168,72',  label:'Easy',   badge:'de' },
  normal: { c:'#3070c8', rgb:'48,112,200', label:'Normal', badge:'dn' },
  hard:   { c:'#b82030', rgb:'184,32,48',  label:'Hard',   badge:'dh' },
  boss:   { c:'#9030d0', rgb:'144,48,208', label:'Boss',   badge:'db' },
};

// ── Win chance ring color ──
function _wc(wp) {
  return wp >= 70 ? '#30a848' : wp >= 40 ? '#c89010' : '#b82030';
}

// ── Build quest card (horizontal landscape) ──
function buildQuestCard(q, active, isRecommended = false, isDaily = false, skipable = false) {
  const dm  = DIFF_META[q.difficulty] || DIFF_META.normal;
  const wp  = Math.round(q.win_chance * 100);
  const wc  = _wc(wp);
  const ci  = q.chain_info;

  const chainBadge = ci
    ? `<div class="qv2-chain-badge" style="--att-color:${ci.color}">${ci.badge} <span>${ci.step}/${ci.total}</span></div>`
    : '';

  const chainBottom = ci
    ? `<span class="qv2-chain-lbl">${esc(ci.chain_name)} · krok ${ci.step} z ${ci.total}</span>
       <div class="qv2-chain-strip"><div class="qv2-chain-fill" style="width:${Math.round(ci.completed/ci.total*100)}%;background:${ci.color}"></div></div>`
    : '';

  const dailyBadge = isDaily
    ? `<span class="daily-bonus-badge">📅 +25% XP/Gold</span>`
    : '';

  const extraClass = [
    isRecommended ? 'qv2--recommended' : '',
    isDaily       ? 'qv2--daily'       : '',
    ci            ? 'qv2--chain'       : '',
    active        ? 'qv2--locked'      : '',
    active        ? 'qv2--active'      : '',
  ].filter(Boolean).join(' ');

  const clickFn = active ? '' : `startQuest(${q.id},'${esc(q.name)}',${isDaily})`;

  return `<div class="qv2 ${extraClass}"
      style="--qc:${dm.c};--qrgb:${dm.rgb};--wc:${wc};--wp:${wp}${ci?`;--att-color:${ci.color}`:''}"
      ${active ? '' : `onclick="${clickFn}"`}>
    ${chainBadge}
    <div class="qv2-stripe"></div>
    ${active ? `<div class="qv2-active-badge">&#9654; Probíhá</div>` : ''}
    <div class="qv2-ico"><span>${q.icon}</span></div>
    <div class="qv2-body">
      <div class="qv2-head">
        <span class="qv2-title">${esc(q.name)}</span>
        <span class="dbadge ${dm.badge}">${dm.label}</span>
      </div>
      <div class="qv2-desc">${esc(q.desc)}</div>
      <div class="qv2-loot">
        <span class="qloot qloot-time">⏱ ${q.duration}m</span>
        <span class="qloot qloot-xp">✨ ${q.reward_xp} XP</span>
        <span class="qloot qloot-gold">💰 ${q.reward_gold_min}–${q.reward_gold_max} G</span>
        ${dailyBadge}
      </div>
      ${chainBottom}
    </div>
    <div class="qv2-right">
      <div class="qv2-ring">
        <span class="qv2-ring-val">${wp}%</span>
      </div>
      <span class="qv2-ring-lbl">šance</span>
      ${(skipable && q.slot_index != null)
        ? `<button class="qv2-skip ${q.free_skip ? 'qv2-skip--free' : 'qv2-skip--paid'}"
             onclick="event.stopPropagation();skipQuestSlot(${q.slot_index})"
             title="${q.free_skip ? 'Přeskočit (zdarma)' : 'Přeskočit (10 G)'}">${q.free_skip ? '🔄' : '💰'}</button>`
        : ''}
    </div>
  </div>`;
}

// ── Recommended section — cleared; quests are surfaced via NPC board ──
function renderRecommended(recommended, status) {
  const wrap = document.getElementById('recommended-quests-wrap');
  if (wrap) wrap.innerHTML = '';
}

// ── Daily countdown format ──
function _fmtDailyReset(seconds) {
  const h = Math.floor(seconds / 3600);
  const m = Math.floor((seconds % 3600) / 60);
  const s = seconds % 60;
  return `${String(h).padStart(2,'0')}:${String(m).padStart(2,'0')}:${String(s).padStart(2,'0')}`;
}

// ── Daily quests section — cleared; daily bonus applied by backend automatically ──
function renderDailyQuests(daily, questStatus) {
  clearInterval(_dailyResetTimer);
  const el = document.getElementById('daily-quests-wrap');
  if (el) el.innerHTML = '';
}

// ── Active quest banner ──
function renderAQ(s) {
  clearInterval(questTimer);
  const wrap    = document.getElementById('aq-wrap');
  const chip    = document.getElementById('tb-quest-chip');
  const chipLbl = document.getElementById('tb-quest-label');

  if (chip) {
    const isActive = s.status === 'active' || s.status === 'collecting';
    chip.style.display = isActive ? '' : 'none';
    chip.classList.toggle('collecting', s.status === 'collecting');
    if (chipLbl) chipLbl.textContent = s.status === 'collecting' ? '✅ Quest hotov!' : `⚔ ${s.quest?.name || 'Quest'}`;
  }

  if (s.status === 'idle') { wrap.innerHTML = ''; return; }

  const q           = s.quest || {};
  const isCollecting = s.status === 'collecting';
  const isActive    = s.status === 'active';
  const diffBadge   = {boss:'db', hard:'dh', normal:'dn', easy:'de'}[q.difficulty] || 'dn';
  const statusLabel = isCollecting ? '✅ Dokončeno!' : 'Probíhá...';
  const timerVal    = isCollecting ? '00:00' : '--:--';
  const initPct     = isCollecting ? 100 : 0;

  wrap.innerHTML = `
    <div class="aq-banner">
      <div class="aq-main">
        <div class="aq-icon-zone">
          <div class="aq-icon">${q.icon||'⚔️'}</div>
        </div>
        <div class="aq-center">
          <div class="aq-status-row">
            <span class="dbadge ${diffBadge}">${q.difficulty||''}</span>
            <span class="aq-lbl" id="aq-lbl">${statusLabel}</span>
          </div>
          <div class="aq-name">${esc(q.name||'—')}</div>
        </div>
        <div class="aq-timer-zone">
          <div class="aq-timer" id="aq-timer">${timerVal}</div>
          <div class="aq-timer-sub">zbývá</div>
        </div>
      </div>
      <div class="aq-footer">
        <div class="aq-prog-wrap">
          <div class="aq-prog-hdr"><span>Postup</span><span id="aq-pct">${initPct}%</span></div>
          <div class="aq-prog-track"><div class="aq-prog-fill" id="aq-fill" style="width:${initPct}%"></div></div>
        </div>
        <div class="aq-chips">
          <div class="aq-chip">✨ <span class="aq-chip-val">${s.reward_xp}</span> XP</div>
          <div class="aq-chip">💰 <span class="aq-chip-val">${s.reward_gold}</span> G</div>
          ${s.reward_item ? `<div class="aq-chip">🎁 <span class="aq-chip-val">${esc(s.reward_item.name)}</span></div>` : ''}
        </div>
      </div>
      <div class="aq-actions">
        <button class="btn-collect" id="aq-btn" ${isCollecting?'':'disabled'} onclick="collectQuest()">
          ${isCollecting ? '🎁 Sebrat odměnu!' : '⏳ Quest probíhá...'}
        </button>
        ${isActive ? `<button class="quest-abandon-btn" onclick="abandonQuest()">🚫 Přerušit</button>` : ''}
      </div>
    </div>`;

  if (isActive) runTimer(s);
  if (isCollecting) { pct('aq-fill',100); set('aq-pct','100%'); }
}

// ── Timer tick ──
function runTimer(s) {
  const total = (s.quest?.duration||1)*60, start = Date.now(), initRem = s.seconds_remaining;
  function tick() {
    const rem  = Math.max(0, initRem - Math.floor((Date.now()-start)/1000));
    const prog = Math.min(100, ((total-rem)/total)*100);
    const te=document.getElementById('aq-timer'), fe=document.getElementById('aq-fill'), pe=document.getElementById('aq-pct');
    if(te) { te.textContent = `${String(Math.floor(rem/60)).padStart(2,'0')}:${String(rem%60).padStart(2,'0')}`; te.classList.toggle('urgent', rem > 0 && rem <= 60); }
    if(fe) fe.style.width = `${prog}%`;
    if(pe) pe.textContent = `${Math.round(prog)}%`;
    if(rem<=0){
      clearInterval(questTimer);
      if(te) te.textContent='00:00';
      const lbl=document.getElementById('aq-lbl'), btn=document.getElementById('aq-btn');
      if(lbl) lbl.textContent='✅ Dokončeno — seber odměnu!';
      if(btn){btn.disabled=false;btn.textContent='🎁 Sebrat odměnu!';}
    }
  }
  tick(); questTimer = setInterval(tick, 1000);
}

// ── Available quests list — renders NPC encounter board ──
function renderQList(quests, status, chainQuests = [], fullStatus = null) {
  const el = document.getElementById('qlist-wrap');
  if (status !== 'idle') {
    let html = '';
    if (fullStatus?.quest && (status === 'active' || status === 'collecting')) {
      html += buildQuestCard(fullStatus.quest, true, false, false, false);
    }
    html += `<div class="empty-state-card">
  <div class="empty-state-icon">📜</div>
  <div class="empty-state-title">Žádné dostupné questy</div>
  <div class="empty-state-sub">Dokonči aktuální quest a potom si vyber nový.</div>
</div>`;
    el.innerHTML = html;
    return;
  }

  const DIFF_ORDER = {easy:0, normal:1, hard:2};
  const available  = [...quests].sort((a, b) => (DIFF_ORDER[a.difficulty]??9) - (DIFF_ORDER[b.difficulty]??9));
  _availableQuestsCache = available;

  let html = '';

  // Chain quests section (preserved)
  if (chainQuests?.length) {
    html += `<div class="qsection-sep">🗝 Série questů</div><div class="qboard">`;
    chainQuests.forEach(q => { html += buildQuestCard(q, false, false, false, false); });
    html += '</div>';
  }

  // NPC encounter board
  html += `<div class="qsection-sep">⚔ Vyber zadavatele</div>`;
  html += renderNPCBoard(available, false);

  el.innerHTML = html;

  // Spawn particles after DOM is ready
  requestAnimationFrame(() => {
    el.querySelectorAll('.npc-particles').forEach(c => spawnNPCParticles(c));
  });
}

// ── Build 3-card NPC board ──
function renderNPCBoard(available, locked) {
  let html = '<div class="npc-board">';
  NPC_GIVERS.forEach(npc => {
    // Match by slot_index first, then difficulty
    let q = available.find(q => q.slot_index === npc.slotHint);
    if (!q) q = available.find(q => q.difficulty === npc.difficulty) || null;
    html += buildNPCCard(npc, q, locked);
  });
  html += '</div>';
  return html;
}

// ── Build a single NPC portrait card ──
function buildNPCCard(npc, quest, locked) {
  const hasQuest = !!quest;
  const dm  = hasQuest ? (DIFF_META[quest.difficulty] || DIFF_META.normal) : null;
  const wp  = hasQuest ? Math.round(quest.win_chance * 100) : 0;
  const wc  = hasQuest ? _wc(wp) : '#555';
  const isSkipable = hasQuest && quest.slot_index != null && !locked;

  const cardClasses = [
    'npc-card',
    locked    ? 'npc-card--locked' : '',
    !hasQuest ? 'npc-card--empty'  : '',
  ].filter(Boolean).join(' ');

  const clickAttr = (!locked && hasQuest)
    ? `onclick="openQuestPreview(${quest.id},'${npc.id}')"`
    : '';

  const skipBtn = isSkipable
    ? `<button class="npc-skip-btn" onclick="event.stopPropagation();skipQuestSlot(${quest.slot_index})"
         title="${quest.free_skip ? 'Přeskočit (zdarma)' : 'Přeskočit (10 G)'}">
         ${quest.free_skip ? '🔄' : '💰'}
       </button>`
    : '';

  const diffBadge = dm
    ? `<span class="dbadge ${dm.badge} npc-diff-badge" style="position:absolute;top:10px;left:10px;z-index:5">${dm.label}</span>`
    : '';

  const questOverlay = hasQuest ? `
    <div class="npc-quest-overlay">
      <div class="npc-quest-title">${esc(quest.name)}</div>
      <div class="npc-quest-rewards">
        <span class="npc-reward-chip nrc--xp">✨ ${quest.reward_xp} XP</span>
        <span class="npc-reward-chip nrc--gold">💰 ${quest.reward_gold_min}–${quest.reward_gold_max} G</span>
        <span class="npc-reward-chip nrc--time">⏱ ${quest.duration}m</span>
      </div>
      <button class="npc-start-btn" style="--nc-color:${npc.color};--nc-rgb:${npc.rgb}"
        onclick="event.stopPropagation();${!locked && hasQuest ? `openQuestPreview(${quest.id},'${npc.id}')` : ''}">
        ${locked ? '⏳ Quest probíhá...' : '📜 Zobrazit quest'}
      </button>
    </div>` : `
    <div class="npc-quest-overlay">
      <div class="npc-quest-title" style="color:var(--text3);font-style:italic;font-size:.82rem">Žádný dostupný úkol</div>
      <button class="npc-start-btn" style="--nc-color:${npc.color};--nc-rgb:${npc.rgb}" disabled>
        🔒 Zvyš svůj level
      </button>
    </div>`;

  return `
    <div class="${cardClasses}" style="--nc-color:${npc.color};--nc-rgb:${npc.rgb}" ${clickAttr}>
      ${diffBadge}
      ${skipBtn}
      <div class="npc-art ${npc.artClass}"></div>
      <div class="npc-particles" data-color="${npc.particleColor}"></div>
      <div class="npc-portrait-zone">
        <div class="npc-avatar-wrap">
          <div class="npc-avatar-ring"></div>
          <div class="npc-avatar">${npc.avatar}</div>
        </div>
        <div class="npc-name">${npc.name}</div>
        <div class="npc-title">${npc.title}</div>
        <div class="npc-speech-bubble">${hasQuest ? npc.speechActive : npc.speechIdle}</div>
      </div>
      ${questOverlay}
    </div>`;
}

// ── Spawn floating particle dots inside NPC card ──
function spawnNPCParticles(container) {
  const color = container.dataset.color || 'rgba(180,140,255,';
  for (let i = 0; i < 9; i++) {
    const p = document.createElement('div');
    p.className = 'npc-particle';
    const size  = 1.5 + Math.random() * 3;
    const x     = 5 + Math.random() * 90;
    const y     = 15 + Math.random() * 65;
    const dur   = 3 + Math.random() * 4;
    const delay = Math.random() * 5;
    const tx    = (Math.random() - .5) * 28;
    const ty    = -(18 + Math.random() * 38);
    const opa   = .25 + Math.random() * .5;
    p.style.cssText = `
      width:${size}px;height:${size}px;left:${x}%;top:${y}%;
      background:${color}${opa});
      box-shadow:0 0 ${size * 2.5}px ${color}${opa * .7});
      --dur:${dur}s;--delay:${delay}s;--tx:${tx}px;--ty:${ty}px;--opa:${opa};
      animation-delay:${delay}s;
    `;
    container.appendChild(p);
  }
}

// ── Open quest preview modal ──
function openQuestPreview(questId, npcId) {
  const npc   = NPC_GIVERS.find(n => n.id === npcId);
  const quest = _availableQuestsCache.find(q => q.id === questId);
  if (!npc || !quest) return;

  const dm  = DIFF_META[quest.difficulty] || DIFF_META.normal;
  const wp  = Math.round(quest.win_chance * 100);
  const wcColor = wp >= 70 ? '#30a848' : wp >= 40 ? '#c89010' : '#b82030';

  const modal = document.getElementById('modal-quest-preview');
  modal.innerHTML = `
    <div class="qpreview-panel" style="--nc-color:${npc.color};--nc-rgb:${npc.rgb}">
      <button class="qpreview-close-btn" onclick="closeModal('modal-quest-preview')">✕</button>
      <div class="qpreview-header">
        <div class="npc-art ${npc.artClass}"></div>
        <div class="npc-particles" data-color="${npc.particleColor}"></div>
        <div class="qpreview-npc-avatar">${npc.avatar}</div>
        <div class="qpreview-npc-name">${npc.name}</div>
      </div>
      <div class="qpreview-body">
        <div class="qpreview-quest-name">
          <span class="dbadge ${dm.badge}" style="position:static;display:inline-flex;margin-right:8px;vertical-align:middle">${dm.label}</span>${esc(quest.name)}
        </div>
        <div class="qpreview-desc">${esc(quest.desc)}</div>
        <div class="qpreview-rewards">
          <div class="qpreview-reward-block">
            <span class="qpreview-reward-icon">✨</span>
            <span class="qpreview-reward-val">${quest.reward_xp}</span>
            <span class="qpreview-reward-label">Zkušenosti</span>
          </div>
          <div class="qpreview-reward-block">
            <span class="qpreview-reward-icon">💰</span>
            <span class="qpreview-reward-val">${quest.reward_gold_min}–${quest.reward_gold_max}</span>
            <span class="qpreview-reward-label">Zlaté</span>
          </div>
          <div class="qpreview-reward-block">
            <span class="qpreview-reward-icon">⏱</span>
            <span class="qpreview-reward-val">${quest.duration}m</span>
            <span class="qpreview-reward-label">Trvání</span>
          </div>
        </div>
        <div class="qpreview-win-row">
          <span class="qpreview-win-label">Šance na výhru</span>
          <div class="qpreview-win-bar-wrap">
            <div class="qpreview-win-bar-fill" id="qpreview-winbar" style="width:0%;background:${wcColor}"></div>
          </div>
          <span class="qpreview-win-pct" style="color:${wcColor}">${wp}%</span>
        </div>
        <button class="qpreview-start-btn"
          onclick="startQuestFromPreview(${quest.id},'${esc(quest.name)}',false,'${npc.rgb}')">
          ⚔ Zahájit výpravu
        </button>
      </div>
    </div>`;

  openModal('modal-quest-preview');

  // Animate win bar + spawn particles after open
  setTimeout(() => {
    const bar = document.getElementById('qpreview-winbar');
    if (bar) bar.style.width = `${wp}%`;
    modal.querySelectorAll('.npc-particles').forEach(c => spawnNPCParticles(c));
  }, 80);
}

// ── Start quest from preview panel ──
async function startQuestFromPreview(id, name, isDaily, npcRgb) {
  closeModal('modal-quest-preview');
  triggerQuestStartCinematic(npcRgb);
  await startQuest(id, name, isDaily);
}

// ── Quest start cinematic flash ──
function triggerQuestStartCinematic(rgb) {
  const el = document.getElementById('qstart-flash');
  if (!el) return;
  el.style.setProperty('--flash-rgb', rgb);
  el.innerHTML = '<div class="qstart-flash-ring"></div>';
  el.classList.add('qstart-flash--active');
  setTimeout(() => { el.classList.remove('qstart-flash--active'); el.innerHTML = ''; }, 1300);
}

// ── Reward burst on quest collect ──
function triggerRewardBurst(xp, gold) {
  const el = document.getElementById('reward-burst');
  if (!el) return;
  el.innerHTML = '';
  el.classList.add('reward-burst--active');

  // Scatter coins
  const coinCount = Math.min(10, Math.floor(gold / 15) + 4);
  for (let i = 0; i < coinCount; i++) {
    const coin  = document.createElement('div');
    coin.className = 'reward-coin';
    const angle = (i / coinCount) * Math.PI * 2;
    const dist  = 55 + Math.random() * 90;
    coin.style.cssText = `
      --tx:${Math.cos(angle) * dist}px;
      --ty:${Math.sin(angle) * dist - 85}px;
      --rot:${Math.random() * 360}deg;
      --dur:${.75 + Math.random() * .5}s;
      left:${44 + Math.random() * 12}%;
      top:${44 + Math.random() * 12}%;
      animation-delay:${i * 0.045}s;
    `;
    coin.textContent = '🪙';
    el.appendChild(coin);
  }

  // XP counter
  const xpEl = document.createElement('div');
  xpEl.className = 'reward-xp-pop';
  xpEl.textContent = `+${xp} XP`;
  el.appendChild(xpEl);

  // Gold counter
  const goldEl = document.createElement('div');
  goldEl.className = 'reward-gold-pop';
  goldEl.textContent = `+${gold} G`;
  el.appendChild(goldEl);

  setTimeout(() => { el.classList.remove('reward-burst--active'); el.innerHTML = ''; }, 2200);
}

function _questFlash() {
  const el = document.createElement('div');
  el.className = 'quest-flash';
  document.body.appendChild(el);
  setTimeout(() => el.remove(), 600);
}

// ── Start quest ──
async function startQuest(id, name, isDaily = false) {
  try {
    const d = await api('POST', '/quest/start', { quest_id: id, is_daily: isDaily });
    _questFlash();
    toast(`Quest "${name}" zahájen! ${d.success?'✅ Výhra předpovězena':'⚠ Bude to těžké'}`, 's', 3500);
    addAct(`⚔ Zahájen: ${name}`);
    await loadQuests();
  } catch(e) { toast(e.message,'e'); }
}

// ── Abandon quest ──
async function abandonQuest() {
  clearInterval(questTimer);
  try {
    await api('POST', '/quest/abandon');
    toast('Quest přerušen.', 'i', 2500);
    addAct('🚫 Quest přerušen');
    await loadQuests();
  } catch(e) { toast(e.message, 'e'); }
}

// ── Collect quest rewards ──
async function collectQuest() {
  clearInterval(questTimer);
  try {
    const d = await api('POST','/quest/collect');
    const success = d.success !== false;
    if (success) _questFlash();
    let msg = `+${d.rewards.xp} XP`;
    if (d.rewards.gold > 0) msg += `, +${d.rewards.gold} G`;
    if (d.rewards.item) {
      if (d.rewards.item.rarity === 'set') {
        msg += `, ✦ ${d.rewards.item.name}`;
      } else {
        msg += `, 🎁 ${d.rewards.item.name}`;
      }
    }
    if (success) {
      toast(`✅ Quest splněn! ${msg}`, 's', 5000);
      addAct(`✅ Quest splněn: ${msg}`);
      triggerRewardBurst(d.rewards.xp, d.rewards.gold);
    } else {
      toast(`⚠ Quest se nezdařil — ${msg}`, 'i', 5000);
      addAct(`⚠ Quest se nezdařil: ${msg}`);
    }
    if(d.leveled_up?.length) {
      const lv = d.leveled_up.at(-1);
      const sp = d.character?.stat_points || 0;
      const spHint = sp > 0 ? ` · <span style="color:var(--green2);cursor:pointer" onclick="showPage('equipment')">Přiděl ${sp} bod${sp===1?'':'y'}!</span>` : '';
      toast(`⚡ Level Up! → Level ${lv}${spHint}`, 's', 7000);
      addAct(`⚡ Level Up → Level ${lv}${sp>0?' ('+sp+' bodů k přidělení)':''}`);
    }
    if(d.newly_unlocked_talents?.length) {
      d.newly_unlocked_talents.forEach(t => {
        toast(`🌟 Talent odemčen: ${t.emoji} <strong>${t.name}</strong> — ${t.desc}`, 's', 6000);
        addAct(`🌟 Nový talent: ${t.emoji} ${t.name}`);
      });
    }
    if (d.daily_bonus_applied) {
      toast('📅 Denní bonus +25% aplikován!', 'i', 3000);
    }
    if(d.rewards.item?.rarity === 'set') {
      toast(`✦ SETOVÝ ITEM: <strong style="color:#00d4ff">${d.rewards.item.name}</strong> — část sady <em>${d.rewards.item.set_name}</em>!`, 's', 7000);
    }
    if(d.faction_rep_gained > 0) {
      const fMeta = typeof FACTION_META !== 'undefined' && d.character?.faction ? FACTION_META[d.character.faction] : null;
      const fName = fMeta?.name || 'Frakce';
      toast(`⚜ +${d.faction_rep_gained} reputace (${fName})`, 'i', 3000);
      if(factionData?.reputation !== undefined) factionData.reputation += d.faction_rep_gained;
    }
    if (d.chain_step_done && d.chain_info) {
      const ci = d.chain_info;
      if (d.chain_completed) {
        toast(`${ci.badge} Série dokončena! Attunement "${ci.chain_name}" odemčen! Vstup do ${ci.dungeon_icon} ${ci.dungeon_name} je otevřen!`, 's', 7000);
        addAct(`${ci.badge} Attunement odemčen: ${ci.chain_name}`);
      } else {
        toast(`${ci.badge} Krok ${ci.step}/${ci.total} série "${ci.chain_name}" dokončen!`, 'i', 4000);
      }
    }
    showAchievementToasts(d.new_achievements);
    if (typeof notifyWeeklyCompleted === 'function') notifyWeeklyCompleted(d.weekly_completed);
    if(d.battle_log?.length){
      const logEl=document.getElementById('ov-log');
      logEl.innerHTML=d.battle_log.map(line=>{
        const cls=line.includes('zvítězil')?'bwin':line.includes('poražen')?'blose':line.includes('KRITICKÝ')?'bcrit':line.startsWith('─')||line.startsWith('[Kolo')?'bsep':'';
        return `<div class="${cls}">${esc(line)}</div>`;
      }).join('');
      document.getElementById('ov-log-wrap').style.display='block';
      const _replayData = d.battle_events?.length ? d.battle_events : d.battle_log;
      const _questWon   = success;
      const _enemyHpStr = d.battle_log?.[1]?.match(/HP:\s*(\d+)/)?.[1];
      const _enemyHpMax = _enemyHpStr ? parseInt(_enemyHpStr) : (char?.combat?.hp_max || 100);
      if (typeof showCombatReplay === 'function') {
        const replayBtn = document.createElement('button');
        replayBtn.className = 'btn btn-sm';
        replayBtn.style.cssText = 'margin-top:8px;background:rgba(30,127,184,.15);border-color:var(--accent)';
        replayBtn.textContent = '⚔ Přehrát boj';
        replayBtn.onclick = () => {
          try {
            showCombatReplay(_replayData, char?.name||'Hráč', 'Nepřítel', _questWon,
              char?.combat?.hp_max||100, _enemyHpMax, { playerAppearance: char?.appearance });
          } catch(e) { console.error('Quest replay error:', e); }
        };
        document.getElementById('ov-log-wrap').appendChild(replayBtn);
        try {
          showCombatReplay(_replayData, char?.name||'Hráč', 'Nepřítel', _questWon,
            char?.combat?.hp_max||100, _enemyHpMax, { playerAppearance: char?.appearance });
        } catch(e) { console.error('Quest auto-replay error:', e); }
      }
      if (typeof showCombatInsights === 'function' && d.battle_events?.length) {
        let insightsEl = document.getElementById('quest-insights');
        if (!insightsEl) {
          insightsEl = document.createElement('div');
          insightsEl.id = 'quest-insights';
          document.getElementById('ov-log-wrap').after(insightsEl);
        }
        showCombatInsights('quest-insights', d.battle_events, success,
          char?.name || 'Hráč', char?.cls, null);
      }
    }
    updateUI(d.character);
    if (document.getElementById('page-equipment')?.classList.contains('active')) renderEquip();
    await loadQuests();
  } catch(e) { toast(e.message,'e'); }
}

// ── Skip quest slot ──
async function skipQuestSlot(slotIndex) {
  try {
    const d = await api('POST', `/quest/slot/skip/${slotIndex}`);
    if (d.paid) toast(`🔄 Quest přeskočen za ${d.cost} G`, 'i', 2500);
    else toast('🔄 Quest přeskočen (gratis)', 'i', 2000);
    await loadQuests();
  } catch(e) { toast(e.message, 'e'); }
}
