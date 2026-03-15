// ── GUILD ─────────────────────────────────────────────────────────────────
const GUILD_EMBLEMS = ['🛡️','⚔️','🏰','🐉','🦅','🔮','⚡','🌙','🔥','💀','🐺','🍀'];
let guildTab = 'members';
let guildCreateOpen = false;
let selEmblem = '🛡️';
let chatPollInterval = null;

// ── WebSocket pro guild chat ───────────────────────────────────────────────
let _guildWs = null;
let _guildWsId = null;      // guild_id pro aktuální WS spojení
let _guildWsFailed = false; // true pokud WS selhal → fallback polling

function connectGuildWs(guildId) {
  if (_guildWs && _guildWsId === guildId && _guildWs.readyState <= WebSocket.OPEN) return;
  disconnectGuildWs();
  _guildWsFailed = false;
  _guildWsId = guildId;

  const proto = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
  const wsUrl = `${proto}//${window.location.host}/guild/ws/${guildId}?token=${encodeURIComponent(token || '')}`;

  try {
    _guildWs = new WebSocket(wsUrl);
  } catch(e) {
    _guildWsFailed = true;
    startChatPoll();
    return;
  }

  _guildWs.onopen = () => {
    console.log('[Guild WS] Připojeno');
    stopChatPoll();
  };

  _guildWs.onmessage = (event) => {
    try {
      const data = JSON.parse(event.data);
      if (data.type === 'history') {
        renderChat(data.messages);
      } else if (data.type === 'message') {
        _appendChatMsg(data.message);
      }
    } catch(e) {}
  };

  _guildWs.onerror = () => {
    console.warn('[Guild WS] Chyba — fallback na polling');
    _guildWsFailed = true;
  };

  _guildWs.onclose = () => {
    console.log('[Guild WS] Odpojeno');
    if (_guildWsFailed && guildTab === 'chat') startChatPoll();
  };
}

function disconnectGuildWs() {
  if (_guildWs) {
    _guildWs.onclose = null; // nezapínat fallback při manuálním zavření
    _guildWs.close();
    _guildWs = null;
    _guildWsId = null;
  }
}

function _appendChatMsg(m) {
  const el = document.getElementById('gchat-log');
  if (!el) return;
  // Odstraní "prázdný" placeholder
  const placeholder = el.querySelector('[data-empty]');
  if (placeholder) placeholder.remove();

  const CLS_E_MAP = {warrior:'⚔️',mage:'🔮',ranger:'🏹'};
  const t = new Date(m.created_at);
  const timeStr = `${String(t.getHours()).padStart(2,'0')}:${String(t.getMinutes()).padStart(2,'0')}`;
  const div = document.createElement('div');
  div.className = 'gchat-msg';
  div.innerHTML = `<span class="gchat-author">${CLS_E_MAP[m.author_cls]||'⚔'} ${esc(m.author)}</span>
    <span style="color:var(--text3);font-size:.65rem;margin:0 4px">›</span>
    <span class="gchat-text">${esc(m.text)}</span>
    <span class="gchat-time">${timeStr}</span>`;
  el.appendChild(div);
  el.scrollTop = el.scrollHeight;
}

async function loadGuild() {
  try {
    const d = await api('GET', '/guild/my');
    if (d.guild) {
      renderMyGuild(d);
    } else {
      await loadGuildList();
    }
  } catch(e) { toast(e.message, 'e'); }
}

async function loadGuildList() {
  try {
    const d = await api('GET', '/guild/list');
    renderGuildList(d.guilds);
  } catch(e) { toast(e.message, 'e'); }
}

function renderGuildList(guilds) {
  stopChatPoll();
  const el = document.getElementById('guild-content');
  el.innerHTML = `
    <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:14px">
      <div style="font-family:'Cinzel',serif;font-size:0.62rem;letter-spacing:2px;text-transform:uppercase;color:var(--text2)">${guilds.length} cechů existuje</div>
      <button class="btn btn-gold btn-sm" onclick="toggleCreateForm()">⚜ Vytvořit cech</button>
    </div>
    <div id="guild-create-wrap" style="display:none">
      <div class="guild-create-form">
        <div style="font-family:'Cinzel',serif;font-size:0.85rem;color:var(--gold2);margin-bottom:12px">⚜ Nový cech <span style="font-size:0.65rem;color:var(--text2);font-family:inherit">(stojí 500 G)</span></div>
        <div class="fld"><label>Jméno cechu</label><input type="text" id="gc-name" placeholder="Legendární jméno cechu..." maxlength="48"></div>
        <div class="fld"><label>Popis</label><input type="text" id="gc-desc" placeholder="Krátký popis cechu..." maxlength="256"></div>
        <div class="fld">
          <label>Emblem cechu</label>
          <div class="guild-emblem-picker" id="gc-emblem-picker">
            ${GUILD_EMBLEMS.map(e => `<div class="guild-emblem-opt${e === selEmblem ? ' sel' : ''}" onclick="pickEmblem('${e}')" data-emblem="${e}">${e}</div>`).join('')}
          </div>
        </div>
        <div class="fmsg" id="gc-msg" style="margin-bottom:8px"></div>
        <button class="btn btn-gold btn-full" onclick="createGuild()">⚜ Vytvořit cech</button>
      </div>
    </div>
    <div id="guild-list-wrap">
      ${!guilds.length
        ? '<div style="color:var(--text2);font-style:italic;text-align:center;padding:30px">Zatím žádné cechy. Buď první!</div>'
        : guilds.map(g => `
          <div class="guild-list-card" onclick="joinGuild(${g.id},'${esc(g.name)}')">
            <div class="guild-list-emblem">${g.emblem}</div>
            <div>
              <div class="guild-list-name">${esc(g.name)}</div>
              ${g.description ? `<div class="guild-list-desc">${esc(g.description)}</div>` : ''}
              <div class="guild-list-meta">Lv.${g.level} · ${g.member_count} členů · ${g.gold.toLocaleString('cs')} G v bance</div>
            </div>
            <button class="join-btn" onclick="event.stopPropagation();joinGuild(${g.id},'${esc(g.name)}')">Vstoupit</button>
          </div>`).join('')
      }
    </div>`;
}

function toggleCreateForm() {
  guildCreateOpen = !guildCreateOpen;
  document.getElementById('guild-create-wrap').style.display = guildCreateOpen ? 'block' : 'none';
}

function pickEmblem(e) {
  selEmblem = e;
  document.querySelectorAll('.guild-emblem-opt').forEach(el => {
    el.classList.toggle('sel', el.dataset.emblem === e);
  });
}

async function createGuild() {
  const name = document.getElementById('gc-name')?.value?.trim();
  const desc = document.getElementById('gc-desc')?.value?.trim() || '';
  const msgEl = document.getElementById('gc-msg');

  if (!name || name.length < 3) {
    if (msgEl) { msgEl.className = 'fmsg err'; msgEl.textContent = 'Jméno musí mít alespoň 3 znaky.'; }
    return;
  }
  try {
    const d = await api('POST', '/guild/create', { name, description: desc, emblem: selEmblem });
    toast(d.message, 's', 4000);
    addAct(`⚜ Cech "${name}" byl vytvořen`);
    await refreshChar();
    await loadGuild();
    await loadGuildTopList();
  } catch(e) {
    if (msgEl) { msgEl.className = 'fmsg err'; msgEl.textContent = e.message; }
  }
}

async function joinGuild(id, name) {
  if (!confirm(`Vstoupit do cechu "${name}"?`)) return;
  try {
    const d = await api('POST', `/guild/join/${id}`);
    toast(d.message, 's', 4000);
    addAct(`⚜ Vstoupil jsi do cechu ${name}`);
    await refreshChar();
    await loadGuild();
    await loadGuildTopList();
  } catch(e) { toast(e.message, 'e'); }
}

function renderMyGuild(data) {
  const g = data.guild;
  const members = data.members;
  const isLeader = data.is_leader;

  set('portrait-guild-name', `${g.emblem} ${g.name}`);

  const el = document.getElementById('guild-content');
  el.innerHTML = `
    <div class="guild-header">
      <div class="guild-emblem">${g.emblem}</div>
      <div style="flex:1">
        <div class="guild-title">${esc(g.name)}</div>
        ${g.description ? `<div class="guild-desc">${esc(g.description)}</div>` : ''}
        <div class="guild-meta-chips">
          <span class="guild-chip">${g.rank_emoji || '⚡'} Lv.${g.level} ${esc(g.rank_name || '')}</span>
          <span class="guild-chip">👥 ${g.member_count}/${g.member_cap || 20} členů</span>
          <span class="guild-chip">💰 ${g.gold.toLocaleString('cs')} G</span>
        </div>
        ${g.level < 10 ? `
        <div class="guild-xp-bar-wrap">
          <div class="guild-xp-fill" style="width:${Math.min(100, Math.round((g.xp / Math.max(1, g.xp_to_next)) * 100))}%"></div>
          <div class="guild-xp-label">${g.xp.toLocaleString('cs')} / ${(g.xp_to_next||0).toLocaleString('cs')} XP</div>
        </div>` : '<div class="guild-xp-maxlevel">✨ MAX LEVEL — Nesmrtelní</div>'}
      </div>
      <div style="display:flex;flex-direction:column;gap:6px;align-items:flex-end">
        ${isLeader
          ? `<button class="btn btn-sm" style="background:rgba(180,30,30,.2);border-color:var(--accent);color:var(--accent2);font-size:.62rem" onclick="disbandGuild()">💀 Rozpustit</button>`
          : `<button class="btn btn-sm" style="font-size:.62rem" onclick="leaveGuild()">🚪 Opustit</button>`
        }
      </div>
    </div>

    <div class="guild-tabs">
      <button class="guild-tab active" id="gtab-members" onclick="switchGuildTab('members')">👥 Členové (${members.length})</button>
      <button class="guild-tab" id="gtab-dungeon" onclick="switchGuildTab('dungeon')">⚔ Dungeon</button>
      <button class="guild-tab" id="gtab-weekly" onclick="switchGuildTab('weekly')">📋 Weekly</button>
      <button class="guild-tab" id="gtab-war" onclick="switchGuildTab('war')">⚔️ Válka</button>
      <button class="guild-tab" id="gtab-chat" onclick="switchGuildTab('chat')">💬 Chat</button>
    </div>

    <div id="guild-tab-dungeon" style="display:none">
      <div id="dungeon-content">
        <div style="color:var(--text2);font-style:italic;text-align:center;padding:30px">Načítám dungeon...</div>
      </div>
    </div>

    <div id="guild-tab-weekly" style="display:none">
      <div id="weekly-content">
        <div style="color:var(--text2);font-style:italic;text-align:center;padding:30px">Načítám weekly quest...</div>
      </div>
    </div>

    <div id="guild-tab-war" style="display:none">
      <div id="war-content">
        <div style="color:var(--text2);font-style:italic;text-align:center;padding:30px">Načítám válku...</div>
      </div>
    </div>

    <div id="guild-tab-members">
      ${members.map(m => `
        <div class="member-row">
          <div class="member-avatar">${m.cls_emoji}</div>
          <div style="flex:1">
            <div class="member-name"><span class="player-name-link" onclick="showPlayerProfile('${m.name}')">${esc(m.name)}</span> ${m.is_leader ? '<span class="member-leader-badge">LEADER</span>' : ''}</div>
            <div class="member-lvl">Lv.${m.level} ${m.cls_name}</div>
          </div>
          ${isLeader && !m.is_leader
            ? `<button class="member-kick-btn" onclick="kickMember(${m.id},'${esc(m.name)}')">Vyhodit</button>`
            : ''
          }
        </div>`).join('')
      }
    </div>

    <div id="guild-tab-chat" style="display:none">
      <div class="gchat-wrap">
        <div class="gchat-log" id="gchat-log">
          <div style="color:var(--text3);font-size:.75rem;font-style:italic;text-align:center">Načítám chat...</div>
        </div>
        <div class="gchat-input-row">
          <input class="gchat-input" id="gchat-input" placeholder="Napiš zprávu..." maxlength="300"
            onkeydown="if(event.key==='Enter')sendChatMsg()">
          <button class="gchat-send" onclick="sendChatMsg()">Odeslat</button>
        </div>
      </div>
    </div>`;

  guildTab = 'members';
}

function switchGuildTab(tab) {
  guildTab = tab;
  document.getElementById('guild-tab-members').style.display = tab === 'members' ? 'block' : 'none';
  document.getElementById('guild-tab-dungeon').style.display = tab === 'dungeon' ? 'block' : 'none';
  document.getElementById('guild-tab-weekly').style.display  = tab === 'weekly'  ? 'block' : 'none';
  document.getElementById('guild-tab-war').style.display     = tab === 'war'     ? 'block' : 'none';
  document.getElementById('guild-tab-chat').style.display    = tab === 'chat'    ? 'block' : 'none';
  document.querySelectorAll('.guild-tab').forEach(b => b.classList.remove('active'));
  document.getElementById(`gtab-${tab}`)?.classList.add('active');

  if (tab === 'chat') {
    const guildId = char?.guild_id;
    if (guildId) {
      connectGuildWs(guildId);
    } else {
      loadGuildChat();
      startChatPoll();
    }
  } else {
    stopChatPoll();
    disconnectGuildWs();
  }
  if (tab === 'dungeon') loadGuildDungeon();
  if (tab === 'weekly')  loadGuildWeekly();
  if (tab === 'war')     loadGuildWar();
}

async function loadGuildDungeon() {
  const wrap = document.getElementById('dungeon-content');
  if (!wrap) return;
  try {
    const d = await api('GET', '/guild/dungeon');
    renderGuildDungeon(d);
  } catch(e) {
    wrap.innerHTML = `<div style="color:var(--accent);text-align:center;padding:20px">${esc(e.message)}</div>`;
  }
}

function renderGuildDungeon(d) {
  const wrap = document.getElementById('dungeon-content');
  if (!wrap) return;
  const b = d.dungeon;
  const CLS_E_MAP = { warrior:'⚔️', mage:'🔮', ranger:'🏹' };
  const maxDmg = d.contributions.length ? d.contributions[0].damage_dealt : 1;

  const bossCard = b.is_defeated
    ? `<div class="dungeon-defeated">✅ Boss poražen! Nový boss se brzy objeví.</div>`
    : `
      <div class="dungeon-boss-card">
        <span class="dungeon-boss-emoji">${b.boss_emoji}</span>
        <div class="dungeon-boss-name">${esc(b.boss_name.replace(b.boss_emoji,'').trim())}</div>
        <div class="dungeon-hp-bar">
          <div class="dungeon-hp-fill" style="width:${b.hp_percent}%"></div>
        </div>
        <div class="dungeon-hp-text">${b.boss_hp_current.toLocaleString()} / ${b.boss_hp_max.toLocaleString()} HP</div>
        ${d.can_attack
          ? `<button class="btn btn-red dungeon-attack-btn" onclick="dungeonAttack()">⚔ Zaútočit!</button>`
          : b.is_defeated
            ? ''
            : `<button class="btn dungeon-attack-btn" disabled style="opacity:.5">⚔ Zaútočit</button>
               <div class="dungeon-cooldown">Cooldown: ${d.cooldown_minutes} min</div>`
        }
      </div>`;

  const contribRows = d.contributions.length === 0
    ? `<div style="color:var(--text3);font-style:italic;font-size:.78rem;padding:10px 0">Zatím nikdo nezaútočil.</div>`
    : d.contributions.map((c, i) => `
      <div class="dungeon-contrib-row">
        <div class="dungeon-contrib-rank">#${i+1}</div>
        <div>${CLS_E_MAP[c.cls]||'⚔'} ${esc(c.name)}</div>
        <div class="dungeon-contrib-dmg">${c.damage_dealt.toLocaleString()} dmg</div>
      </div>
      <div class="dungeon-contrib-bar">
        <div class="dungeon-contrib-fill" style="width:${Math.round(c.damage_dealt/maxDmg*100)}%"></div>
      </div>`).join('');

  wrap.innerHTML = `
    ${bossCard}
    <div style="font-family:'Cinzel',serif;font-size:0.72rem;color:var(--text2);letter-spacing:1px;margin-bottom:8px;text-transform:uppercase">
      Přispěvatelé
    </div>
    ${contribRows}`;
}

async function dungeonAttack() {
  try {
    const d = await api('POST', '/guild/dungeon/attack');
    toast(`⚔ Zasáhl jsi za ${d.damage.toLocaleString()} dmg!`, 's');
    if (d.boss_defeated) {
      toast(`🏆 Boss poražen! +${d.reward_gold} G, +${d.reward_xp} XP`, 's', 5000);
      addAct(`⚔ Boss cechu poražen! +${d.reward_gold} G`);
      await refreshChar();
    }
    await loadGuildDungeon();
  } catch(e) {
    toast(e.message, 'e');
  }
}

async function loadGuildChat() {
  try {
    const d = await api('GET', '/guild/chat');
    renderChat(d.messages);
  } catch(e) {}
}

function renderChat(messages) {
  const el = document.getElementById('gchat-log');
  if (!el) return;
  if (!messages.length) {
    el.innerHTML = '<div data-empty style="color:var(--text3);font-size:.75rem;font-style:italic;text-align:center">Zatím žádné zprávy. Buď první!</div>';
    return;
  }
  const CLS_E_MAP = {warrior:'⚔️',mage:'🔮',ranger:'🏹'};
  el.innerHTML = messages.map(m => {
    const t = new Date(m.created_at);
    const timeStr = `${String(t.getHours()).padStart(2,'0')}:${String(t.getMinutes()).padStart(2,'0')}`;
    return `<div class="gchat-msg">
      <span class="gchat-author">${CLS_E_MAP[m.author_cls]||'⚔'} ${esc(m.author)}</span>
      <span style="color:var(--text3);font-size:.65rem;margin:0 4px">›</span>
      <span class="gchat-text">${esc(m.text)}</span>
      <span class="gchat-time">${timeStr}</span>
    </div>`;
  }).join('');
  el.scrollTop = el.scrollHeight;
}

async function sendChatMsg() {
  const input = document.getElementById('gchat-input');
  if (!input) return;
  const text = input.value.trim();
  if (!text) return;

  // WebSocket cesta — pokud je připojeno a funkční
  if (_guildWs && _guildWs.readyState === WebSocket.OPEN) {
    _guildWs.send(JSON.stringify({ type: 'message', text }));
    input.value = '';
    return;
  }

  // Fallback: REST API
  try {
    await api('POST', '/guild/chat', { text });
    input.value = '';
    await loadGuildChat();
  } catch(e) { toast(e.message, 'e'); }
}

function startChatPoll() {
  stopChatPoll();
  chatPollInterval = setInterval(() => {
    if (guildTab === 'chat') loadGuildChat();
  }, 8000);
}

function stopChatPoll() {
  if (chatPollInterval) { clearInterval(chatPollInterval); chatPollInterval = null; }
}

async function leaveGuild() {
  if (!confirm('Opravdu chceš opustit cech?')) return;
  try {
    disconnectGuildWs();
    const d = await api('POST', '/guild/leave');
    toast(d.message, 'i', 3000);
    addAct('🚪 Opustil jsi cech');
    set('portrait-guild-name', '[bez cechu]');
    await refreshChar();
    await loadGuild();
    await loadGuildTopList();
  } catch(e) { toast(e.message, 'e'); }
}

async function disbandGuild() {
  if (!confirm('Opravdu chceš ROZPUSTIT cech? Tato akce je nevratná!')) return;
  try {
    const d = await api('DELETE', '/guild/disband');
    toast(d.message, 'i', 3000);
    addAct('💀 Cech byl rozpuštěn');
    set('portrait-guild-name', '[bez cechu]');
    await refreshChar();
    await loadGuild();
    await loadGuildTopList();
  } catch(e) { toast(e.message, 'e'); }
}

async function kickMember(charId, name) {
  if (!confirm(`Vyhodit ${name} z cechu?`)) return;
  try {
    const d = await api('DELETE', `/guild/kick/${charId}`);
    toast(d.message, 'i', 3000);
    addAct(`⚔ Vyhozen: ${name}`);
    await loadGuild();
  } catch(e) { toast(e.message, 'e'); }
}

// ── Guild Weekly Quest ─────────────────────────────────────────────────────────

async function loadGuildWeekly() {
  const wrap = document.getElementById('weekly-content');
  if (!wrap) return;
  try {
    const d = await api('GET', '/guild/weekly');
    renderGuildWeekly(d);
  } catch(e) {
    wrap.innerHTML = `<div style="color:var(--accent);text-align:center;padding:20px">${esc(e.message)}</div>`;
  }
}

function renderGuildWeekly(d) {
  const wrap = document.getElementById('weekly-content');
  if (!wrap) return;
  const wq = d.weekly;
  const CLS_E_MAP = { warrior:'⚔️', mage:'🔮', ranger:'🏹' };

  // Progress bar color
  const pct = wq.progress_pct;
  const barColor = wq.is_completed ? 'var(--green)' : pct >= 75 ? 'var(--gold2)' : 'var(--blue)';

  const contribRows = d.contributions.length === 0
    ? `<div style="color:var(--text3);font-size:.78rem;font-style:italic;padding:8px 0">Nikdo zatím nepřispěl.</div>`
    : d.contributions.map((c, i) => `
        <div class="dungeon-contrib-row">
          <div class="dungeon-contrib-rank">#${i+1}</div>
          <div>${CLS_E_MAP[c.cls]||'⚔'} ${esc(c.name)}</div>
          <div class="dungeon-contrib-dmg">${c.contribution.toLocaleString('cs')}</div>
        </div>`).join('');

  const weekEnd = new Date(wq.week_start);
  weekEnd.setDate(weekEnd.getDate() + 7);
  const weekEndStr = weekEnd.toLocaleDateString('cs', { day:'numeric', month:'short' });

  wrap.innerHTML = `
    <div class="weekly-quest-card ${wq.is_completed ? 'weekly-completed' : ''}">
      <div class="weekly-quest-header">
        <div class="weekly-quest-emoji">${wq.emoji}</div>
        <div style="flex:1">
          <div class="weekly-quest-title">${esc(wq.label)}</div>
          <div class="weekly-quest-desc">${esc(wq.desc)}</div>
          <div class="weekly-quest-expires">Resetuje se: ${weekEndStr}</div>
        </div>
        ${wq.is_completed ? '<div class="weekly-completed-badge">✅ SPLNĚNO</div>' : ''}
      </div>

      <div class="weekly-progress-wrap">
        <div class="weekly-progress-bar">
          <div class="weekly-progress-fill" style="width:${pct}%;background:${barColor}"></div>
        </div>
        <div class="weekly-progress-text">
          ${wq.progress.toLocaleString('cs')} / ${wq.goal_target.toLocaleString('cs')}
          <span style="color:var(--text3);margin-left:6px">(${pct}%)</span>
        </div>
      </div>

      <div class="weekly-reward">
        🏆 Odměna pro aktivní členy: <strong style="color:var(--gold2)">${wq.reward_gold.toLocaleString('cs')} G</strong>
        ${wq.is_completed && d.my_contribution > 0 ? '<span style="color:var(--green);margin-left:8px">— Obdrženo ✓</span>' : ''}
      </div>
    </div>

    <div style="font-family:'Cinzel',serif;font-size:0.72rem;color:var(--text2);letter-spacing:1px;margin:14px 0 8px;text-transform:uppercase">
      Přispěvatelé
    </div>
    ${contribRows}
    ${d.my_contribution > 0 ? `<div style="color:var(--text3);font-size:.72rem;margin-top:8px">Tvůj příspěvek: <strong style="color:var(--text)">${d.my_contribution.toLocaleString('cs')}</strong></div>` : ''}`;
}

async function loadGuildTopList() {
  try {
    const d = await api('GET', '/guild/list');
    const el = document.getElementById('rp-guild-list');
    if (!el) return;
    if (!d.guilds.length) {
      el.innerHTML = '<div style="color:var(--text3);font-size:.75rem">Zatím žádné cechy.</div>';
      return;
    }
    el.innerHTML = d.guilds.slice(0, 5).map((g, i) => `
      <div style="display:flex;align-items:center;gap:6px;padding:5px 0;border-bottom:1px solid rgba(255,255,255,.04);font-size:.78rem">
        <div style="color:var(--text3);width:14px;text-align:right;font-family:'Cinzel',serif;font-size:.66rem">${i+1}</div>
        <div style="font-size:.9rem">${g.emblem}</div>
        <div style="flex:1;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">${esc(g.name)}</div>
        <div style="font-size:.68rem;color:var(--text2)">Lv.${g.level}</div>
        <div style="font-size:.68rem;color:var(--text3)">${g.member_count}👥</div>
      </div>`).join('');
  } catch(e) {}
}

// ── GUILD WAR ──────────────────────────────────────────────────────────────────

let _warOpponents = null;
let _warData      = null;

async function loadGuildWar() {
    const wrap = document.getElementById('war-content');
    if (!wrap) return;
    try {
        const d = await api('GET', '/guild/war/current');
        _warData = d;
        renderGuildWar(d, wrap);
    } catch(e) {
        wrap.innerHTML = `<div style="color:var(--accent);text-align:center;padding:20px">${esc(e.message)}</div>`;
    }
}

function _warTimeLeft(endsAt) {
    const diff = new Date(endsAt + 'Z') - Date.now();
    if (diff <= 0) return 'Skončila';
    const h = Math.floor(diff / 3600000);
    const m = Math.floor((diff % 3600000) / 60000);
    return `${h}h ${m}m`;
}

function renderGuildWar(d, wrap) {
    if (!d || !d.war) {
        // Žádná aktivní válka — ukáž formulář pro vyhlášení + historii
        const isLeader = char && char.guild_id; // omezíme tlačítko v renderMyGuild přes isLeader
        wrap.innerHTML = `
            <div class="war-idle">
                <div class="war-idle-icon">🕊️</div>
                <h3>Žádná aktivní válka</h3>
                <p>Leader cechu může vyhlásit válku jinému cechu.</p>
                <div class="war-declare-form" id="war-declare-form">
                    <input class="war-input" id="war-target-id" type="number" placeholder="ID cílového cechu" min="1">
                    <button class="btn war-declare-btn" onclick="declareWar()">⚔️ Vyhlásit válku</button>
                </div>
            </div>
            <div id="war-history-section"></div>`;
        loadWarHistory();
        return;
    }

    const w = d.war;
    const myId = d.my_guild_id;
    const isAttacker = w.attacker_guild_id === myId;
    const myGuild  = isAttacker ? d.attacker_guild : d.defender_guild;
    const foeGuild = isAttacker ? d.defender_guild : d.attacker_guild;
    const myPts  = isAttacker ? w.attacker_points : w.defender_points;
    const foePts = isAttacker ? w.defender_points : w.attacker_points;
    const isActive = w.status === 'active';
    const timeLeft = isActive ? _warTimeLeft(w.ends_at) : 'Skončila';

    const recentHtml = (d.recent_attacks || []).map(a => `
        <div class="war-log-row ${a.attacker_won ? 'war-log-win' : 'war-log-loss'}">
            <span class="war-log-icon">${a.attacker_won ? '✅' : '❌'}</span>
            <span>${esc(a.attacker)} → ${esc(a.defender)}</span>
            <span class="war-log-pts">+${a.points} bodů</span>
        </div>`).join('') || '<div style="color:var(--text3);font-size:.78rem">Zatím žádné útoky.</div>';

    wrap.innerHTML = `
        <div class="war-scoreboard">
            <div class="war-team ${isAttacker ? 'war-team-my' : ''}">
                <div class="war-team-emblem">${myGuild?.emblem || '🛡️'}</div>
                <div class="war-team-name">${esc(myGuild?.name || '?')}</div>
                <div class="war-team-pts">${myPts}</div>
                <div class="war-team-label">bodů</div>
            </div>
            <div class="war-vs">
                <div class="war-vs-text">VS</div>
                <div class="war-timer ${isActive ? '' : 'war-timer-done'}">${timeLeft}</div>
                <div class="war-atks-left">Tvoje útoky: <strong>${d.attacks_remaining}</strong> / 3</div>
            </div>
            <div class="war-team ${!isAttacker ? 'war-team-my' : ''}">
                <div class="war-team-emblem">${foeGuild?.emblem || '🛡️'}</div>
                <div class="war-team-name">${esc(foeGuild?.name || '?')}</div>
                <div class="war-team-pts">${foePts}</div>
                <div class="war-team-label">bodů</div>
            </div>
        </div>

        ${isActive && d.attacks_remaining > 0 ? `
        <button class="btn war-attack-btn" onclick="loadWarOpponents()">⚔️ Zaútočit na soupeře</button>` : ''}
        ${isActive && d.attacks_remaining === 0 ? `
        <div class="war-no-atks">Vyčerpal jsi všechny útoky pro tuto válku.</div>` : ''}
        ${!isActive ? `<div class="war-ended">Válka skončila. Výsledek viz níže.</div>` : ''}

        <div class="war-log-section">
            <div class="war-log-title">Posledních 10 útoků</div>
            ${recentHtml}
        </div>

        <div id="war-opponents-section"></div>`;
}

async function loadWarOpponents() {
    const wrap = document.getElementById('war-opponents-section');
    if (!wrap) return;
    wrap.innerHTML = '<div style="color:var(--text2);font-size:.8rem;padding:10px">Načítám soupeře...</div>';
    try {
        const d = await api('GET', '/guild/war/opponents');
        _warOpponents = d;
        renderWarOpponents(d, wrap);
    } catch(e) {
        wrap.innerHTML = `<div style="color:var(--accent);font-size:.8rem;padding:10px">${esc(e.message)}</div>`;
    }
}

function renderWarOpponents(d, wrap) {
    if (!d.opponents || !d.opponents.length) {
        wrap.innerHTML = '<div style="color:var(--text3);font-size:.8rem;padding:10px">Žádní soupeři v nepřátelském cechu.</div>';
        return;
    }
    const cards = d.opponents.map(o => `
        <div class="war-opp-card">
            <span class="war-opp-cls">${o.cls_emoji}</span>
            <div style="flex:1">
                <div class="war-opp-name player-name-link" onclick="showPlayerProfile('${o.name}')">${esc(o.name)}</div>
                <div class="war-opp-stats">Lv.${o.level} · HP ${o.hp_max} · ATK ${o.atk}</div>
            </div>
            <button class="btn war-opp-btn" onclick="warAttack(${o.id}, '${esc(o.name)}')">Útok</button>
        </div>`).join('');
    wrap.innerHTML = `<div class="war-opp-list"><div class="war-opp-title">Členové soupeřícího cechu</div>${cards}</div>`;
}

async function warAttack(defenderId, defenderName) {
    if (!confirm(`Zaútočit na ${defenderName}?`)) return;
    try {
        const strategy = localStorage.getItem('combatStrategy') || 'balanced';
        const d = await api('POST', '/guild/war/attack', { defender_id: defenderId, strategy });
        const outcome = d.won ? '✅ Výhra' : '❌ Prohra';
        toast(`${outcome} vs ${defenderName} — získáno ${d.points_earned} bodů!`, d.won ? 's' : 'i', 4000);
        await loadGuildWar();
    } catch(e) {
        toast(e.message || 'Chyba útoku.', 'e');
    }
}

async function declareWar() {
    const input = document.getElementById('war-target-id');
    const targetId = parseInt(input?.value || '0');
    if (!targetId || targetId < 1) {
        toast('Zadej platné ID cechu.', 'e');
        return;
    }
    if (!confirm(`Vyhlásit válku cechu ID ${targetId}? Válka trvá 24 hodin.`)) return;
    try {
        const d = await api('POST', '/guild/war/declare', { target_guild_id: targetId });
        toast(d.message || 'Válka vyhlášena!', 's', 4000);
        await loadGuildWar();
    } catch(e) {
        toast(e.message || 'Chyba při vyhlášení války.', 'e');
    }
}

async function loadWarHistory() {
    const section = document.getElementById('war-history-section');
    if (!section) return;
    try {
        const d = await api('GET', '/guild/war/history');
        if (!d.wars || !d.wars.length) return;
        const rows = d.wars.map(w => {
            const ico = w.my_result === 'win' ? '🏆' : w.my_result === 'draw' ? '🤝' : '💀';
            const label = w.my_result === 'win' ? 'Výhra' : w.my_result === 'draw' ? 'Remíza' : 'Prohra';
            const foe = w.attacker_guild_id === (char?.guild_id) ? w.defender_name : w.attacker_name;
            const myPts = w.attacker_guild_id === (char?.guild_id) ? w.attacker_points : w.defender_points;
            const foePts = w.attacker_guild_id === (char?.guild_id) ? w.defender_points : w.attacker_points;
            const date = new Date(w.ends_at + 'Z').toLocaleDateString('cs-CZ');
            return `<div class="war-hist-row">
                <span class="war-hist-ico">${ico}</span>
                <div class="war-hist-info">
                    <div class="war-hist-foe">vs ${esc(foe)}</div>
                    <div class="war-hist-pts">${myPts} : ${foePts}</div>
                </div>
                <div class="war-hist-meta">
                    <span class="war-hist-result ${w.my_result}">${label}</span>
                    <span class="war-hist-date">${date}</span>
                </div>
            </div>`;
        }).join('');
        section.innerHTML = `<div class="war-history"><div class="war-history-title">Historie válek</div>${rows}</div>`;
    } catch(e) {}
}
