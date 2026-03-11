// ── TOWN HUB — Město Ashenveil ─────────────────────────────────────────────
// Hlavní stránka hráče. Zobrazuje mapu města s budovami (aktivity) a NPC.
// Každá budova má živý status ze serveru (cooldown, progress, dostupnost).

// ── Hub Building SVG Art ────────────────────────────────────────────────────
const HUB_BUILDING_ART = {
  quests: `<svg viewBox="0 0 80 100" xmlns="http://www.w3.org/2000/svg" width="82" height="92" class="hub-b-svg">
    <defs>
      <radialGradient id="hb-q-bg" cx="50%" cy="50%" r="55%"><stop offset="0%" stop-color="#20b2aa" stop-opacity=".3"/><stop offset="100%" stop-color="#051510" stop-opacity="0"/></radialGradient>
      <linearGradient id="hb-q-scroll" x1="0%" y1="0%" x2="100%" y2="100%"><stop offset="0%" stop-color="#c8a060"/><stop offset="100%" stop-color="#8b6020"/></linearGradient>
      <filter id="hb-q-glow"><feGaussianBlur stdDeviation="2"/></filter>
    </defs>
    <ellipse cx="40" cy="50" rx="36" ry="45" fill="url(#hb-q-bg)"/>
    <rect x="18" y="28" width="44" height="52" rx="3" fill="url(#hb-q-scroll)" opacity=".9"/>
    <rect x="18" y="28" width="44" height="52" rx="3" fill="none" stroke="#d4a030" stroke-width=".8" opacity=".6"/>
    <rect x="14" y="24" width="52" height="8" rx="4" fill="#a07840"/>
    <rect x="14" y="72" width="52" height="8" rx="4" fill="#a07840"/>
    <line x1="24" y1="42" x2="56" y2="42" stroke="#3a2808" stroke-width="1.5" opacity=".7"/>
    <line x1="24" y1="49" x2="56" y2="49" stroke="#3a2808" stroke-width="1.5" opacity=".7"/>
    <line x1="24" y1="56" x2="50" y2="56" stroke="#3a2808" stroke-width="1.5" opacity=".7"/>
    <line x1="24" y1="63" x2="52" y2="63" stroke="#3a2808" stroke-width="1.5" opacity=".7"/>
    <circle cx="40" cy="54" r="9" fill="#8b1a1a" opacity=".8"/>
    <circle cx="40" cy="54" r="9" fill="none" stroke="#d4a030" stroke-width="1" opacity=".9"/>
    <text x="40" y="58" text-anchor="middle" font-size="9" fill="#f0c84a" font-family="serif">✦</text>
    <ellipse cx="40" cy="90" rx="20" ry="5" fill="#20b2aa" opacity=".12" filter="url(#hb-q-glow)"/>
  </svg>`,

  arena: `<svg viewBox="0 0 80 100" xmlns="http://www.w3.org/2000/svg" width="82" height="92" class="hub-b-svg">
    <defs>
      <radialGradient id="hb-a-bg" cx="50%" cy="60%" r="55%"><stop offset="0%" stop-color="#c0392b" stop-opacity=".35"/><stop offset="100%" stop-color="#0a0200" stop-opacity="0"/></radialGradient>
      <radialGradient id="hb-a-sand" cx="50%" cy="100%" r="60%"><stop offset="0%" stop-color="#8b4010" stop-opacity=".4"/><stop offset="100%" stop-color="#8b4010" stop-opacity="0"/></radialGradient>
      <filter id="hb-a-glow"><feGaussianBlur stdDeviation="2.5"/></filter>
    </defs>
    <ellipse cx="40" cy="52" rx="38" ry="48" fill="url(#hb-a-bg)"/>
    <ellipse cx="40" cy="92" rx="38" ry="15" fill="url(#hb-a-sand)"/>
    <ellipse cx="40" cy="75" rx="22" ry="7" fill="none" stroke="#8b1010" stroke-width="1.5" opacity=".7"/>
    <ellipse cx="40" cy="75" rx="16" ry="5" fill="#5a0808" opacity=".3"/>
    <g transform="rotate(-25, 40, 45)">
      <rect x="39" y="20" width="2.5" height="42" rx="1" fill="#c8c8d8"/>
      <rect x="39" y="20" width="2.5" height="42" rx="1" fill="none" stroke="#808090" stroke-width=".4"/>
      <rect x="39.8" y="24" width=".9" height="32" fill="#9898a8" opacity=".6"/>
      <rect x="33" y="52" width="16" height="3" rx="1.5" fill="#8b6820"/>
      <rect x="33" y="52" width="16" height="3" rx="1.5" fill="none" stroke="#d4a030" stroke-width=".5"/>
      <ellipse cx="40.25" cy="62" rx="3.5" ry="3" fill="#8b6820" stroke="#d4a030" stroke-width=".5"/>
    </g>
    <g transform="rotate(25, 40, 45)">
      <rect x="39" y="20" width="2.5" height="42" rx="1" fill="#c8c8d8"/>
      <rect x="39" y="20" width="2.5" height="42" rx="1" fill="none" stroke="#808090" stroke-width=".4"/>
      <rect x="39.8" y="24" width=".9" height="32" fill="#9898a8" opacity=".6"/>
      <rect x="33" y="52" width="16" height="3" rx="1.5" fill="#8b6820"/>
      <rect x="33" y="52" width="16" height="3" rx="1.5" fill="none" stroke="#d4a030" stroke-width=".5"/>
      <ellipse cx="40.25" cy="62" rx="3.5" ry="3" fill="#8b6820" stroke="#d4a030" stroke-width=".5"/>
    </g>
    <ellipse cx="40" cy="90" rx="25" ry="6" fill="#c0392b" opacity=".15" filter="url(#hb-a-glow)"/>
  </svg>`,

  boss: `<svg viewBox="0 0 80 100" xmlns="http://www.w3.org/2000/svg" width="82" height="92" class="hub-b-svg">
    <defs>
      <radialGradient id="hb-bo-bg" cx="50%" cy="50%" r="55%"><stop offset="0%" stop-color="#8b0000" stop-opacity=".4"/><stop offset="100%" stop-color="#050000" stop-opacity="0"/></radialGradient>
      <radialGradient id="hb-bo-fire" cx="50%" cy="100%" r="50%"><stop offset="0%" stop-color="#ff4400" stop-opacity=".5"/><stop offset="100%" stop-color="#ff4400" stop-opacity="0"/></radialGradient>
      <filter id="hb-bo-glow"><feGaussianBlur stdDeviation="3"/></filter>
      <filter id="hb-bo-glow2"><feGaussianBlur stdDeviation="1.5"/></filter>
    </defs>
    <ellipse cx="40" cy="50" rx="36" ry="46" fill="url(#hb-bo-bg)"/>
    <path d="M15,90 L15,48 Q15,18 40,18 Q65,18 65,48 L65,90" fill="none" stroke="#3d1a0a" stroke-width="4"/>
    <path d="M15,90 L15,48 Q15,18 40,18 Q65,18 65,48 L65,90" fill="none" stroke="#6b2d12" stroke-width="1.5"/>
    <ellipse cx="40" cy="50" rx="16" ry="18" fill="#d8c8b0" opacity=".85"/>
    <ellipse cx="40" cy="50" rx="16" ry="18" fill="none" stroke="#8b7050" stroke-width=".8"/>
    <ellipse cx="33" cy="47" rx="5" ry="6" fill="#0a0000"/>
    <ellipse cx="47" cy="47" rx="5" ry="6" fill="#0a0000"/>
    <ellipse cx="33" cy="47" rx="3" ry="3.5" fill="#ff2000" opacity=".7" filter="url(#hb-bo-glow2)"/>
    <ellipse cx="47" cy="47" rx="3" ry="3.5" fill="#ff2000" opacity=".7" filter="url(#hb-bo-glow2)"/>
    <path d="M37,56 L40,60 L43,56" fill="#8b7050" opacity=".5"/>
    <rect x="33" y="62" width="4" height="5" rx="1" fill="#c8b898"/>
    <rect x="38" y="62" width="4" height="5" rx="1" fill="#c8b898"/>
    <rect x="43" y="62" width="4" height="5" rx="1" fill="#c8b898"/>
    <path d="M24,62 Q40,72 56,62" fill="none" stroke="#8b7050" stroke-width="1.5"/>
    <ellipse cx="40" cy="92" rx="28" ry="8" fill="url(#hb-bo-fire)"/>
    <ellipse cx="40" cy="90" rx="20" ry="8" fill="#ff2200" opacity=".2" filter="url(#hb-bo-glow)"/>
  </svg>`,

  dungeons: `<svg viewBox="0 0 80 100" xmlns="http://www.w3.org/2000/svg" width="82" height="92" class="hub-b-svg">
    <defs>
      <radialGradient id="hb-d-bg" cx="50%" cy="50%" r="55%"><stop offset="0%" stop-color="#7b2fbf" stop-opacity=".3"/><stop offset="100%" stop-color="#050005" stop-opacity="0"/></radialGradient>
      <linearGradient id="hb-d-stone" x1="0%" y1="0%" x2="100%" y2="100%"><stop offset="0%" stop-color="#2a1a0a"/><stop offset="100%" stop-color="#1a0a04"/></linearGradient>
      <radialGradient id="hb-d-dark" cx="50%" cy="50%" r="45%"><stop offset="0%" stop-color="#0a0010" stop-opacity=".9"/><stop offset="100%" stop-color="#0a0010" stop-opacity="0"/></radialGradient>
      <filter id="hb-d-glow"><feGaussianBlur stdDeviation="2.5"/></filter>
    </defs>
    <ellipse cx="40" cy="50" rx="36" ry="46" fill="url(#hb-d-bg)"/>
    <path d="M12,88 L12,45 Q12,15 40,15 Q68,15 68,45 L68,88 Z" fill="url(#hb-d-stone)"/>
    <path d="M12,88 L12,45 Q12,15 40,15 Q68,15 68,45 L68,88 Z" fill="none" stroke="#4a2a10" stroke-width="2"/>
    <path d="M20,88 L20,47 Q20,23 40,23 Q60,23 60,47 L60,88 Z" fill="url(#hb-d-dark)"/>
    <line x1="12" y1="60" x2="20" y2="60" stroke="#3d1a0a" stroke-width="1" opacity=".6"/>
    <line x1="60" y1="60" x2="68" y2="60" stroke="#3d1a0a" stroke-width="1" opacity=".6"/>
    <line x1="12" y1="72" x2="20" y2="72" stroke="#3d1a0a" stroke-width="1" opacity=".6"/>
    <line x1="60" y1="72" x2="68" y2="72" stroke="#3d1a0a" stroke-width="1" opacity=".6"/>
    <path d="M34,15 L40,8 L46,15 Z" fill="#4a2a10" stroke="#6b2d12" stroke-width=".8"/>
    <line x1="30" y1="30" x2="30" y2="70" stroke="#5a3a1a" stroke-width="1.5" stroke-dasharray="4,3"/>
    <line x1="50" y1="30" x2="50" y2="70" stroke="#5a3a1a" stroke-width="1.5" stroke-dasharray="4,3"/>
    <ellipse cx="40" cy="60" rx="14" ry="18" fill="#4a00a0" opacity=".25" filter="url(#hb-d-glow)"/>
    <ellipse cx="25" cy="88" rx="2" ry="1" fill="#3a1a08" opacity=".6"/>
    <ellipse cx="55" cy="88" rx="2" ry="1" fill="#3a1a08" opacity=".6"/>
  </svg>`,

  shop: `<svg viewBox="0 0 80 100" xmlns="http://www.w3.org/2000/svg" width="82" height="92" class="hub-b-svg">
    <defs>
      <radialGradient id="hb-s-bg" cx="50%" cy="55%" r="55%"><stop offset="0%" stop-color="#c89010" stop-opacity=".3"/><stop offset="100%" stop-color="#050300" stop-opacity="0"/></radialGradient>
      <linearGradient id="hb-s-chest" x1="0%" y1="0%" x2="100%" y2="110%"><stop offset="0%" stop-color="#5a3a10"/><stop offset="100%" stop-color="#2a1a04"/></linearGradient>
      <radialGradient id="hb-s-gold" cx="50%" cy="30%" r="60%"><stop offset="0%" stop-color="#f0c840" stop-opacity=".8"/><stop offset="100%" stop-color="#c89010" stop-opacity="0"/></radialGradient>
      <filter id="hb-s-glow"><feGaussianBlur stdDeviation="2"/></filter>
    </defs>
    <ellipse cx="40" cy="52" rx="36" ry="45" fill="url(#hb-s-bg)"/>
    <rect x="14" y="56" width="52" height="32" rx="3" fill="url(#hb-s-chest)"/>
    <rect x="14" y="56" width="52" height="32" rx="3" fill="none" stroke="#8b6020" stroke-width="1.2"/>
    <rect x="14" y="68" width="52" height="4" fill="#4a3010" stroke="#8b6020" stroke-width=".5"/>
    <rect x="36" y="56" width="8" height="32" fill="#4a3010" stroke="#8b6020" stroke-width=".5"/>
    <rect x="36" y="69" width="8" height="7" rx="2" fill="#c8a020" stroke="#f0c840" stroke-width=".8"/>
    <path d="M14,56 L14,40 Q14,32 40,32 Q66,32 66,40 L66,56" fill="url(#hb-s-chest)"/>
    <path d="M14,56 L14,40 Q14,32 40,32 Q66,32 66,40 L66,56" fill="none" stroke="#8b6020" stroke-width="1.2"/>
    <ellipse cx="40" cy="50" rx="20" ry="8" fill="url(#hb-s-gold)"/>
    <circle cx="30" cy="52" r="4" fill="#d4a030" stroke="#f0c840" stroke-width=".8"/>
    <circle cx="40" cy="48" r="5" fill="#d4a030" stroke="#f0c840" stroke-width=".8"/>
    <circle cx="50" cy="52" r="4" fill="#d4a030" stroke="#f0c840" stroke-width=".8"/>
    <circle cx="35" cy="56" r="3.5" fill="#c89020" stroke="#f0c840" stroke-width=".6"/>
    <circle cx="46" cy="56" r="3" fill="#c89020" stroke="#f0c840" stroke-width=".6"/>
    <ellipse cx="40" cy="50" rx="22" ry="10" fill="#f0c840" opacity=".15" filter="url(#hb-s-glow)"/>
    <rect x="62" y="38" width="4" height="14" rx="1" fill="#e8d090"/>
    <ellipse cx="64" cy="36" rx="2" ry="3" fill="#ff8800" opacity=".8" filter="url(#hb-s-glow)"/>
  </svg>`,

  taverna: `<svg viewBox="0 0 80 100" xmlns="http://www.w3.org/2000/svg" width="82" height="92" class="hub-b-svg" style="opacity:.5">
    <defs>
      <radialGradient id="hb-t-bg" cx="50%" cy="50%" r="55%"><stop offset="0%" stop-color="#c8860f" stop-opacity=".2"/><stop offset="100%" stop-color="#050300" stop-opacity="0"/></radialGradient>
      <linearGradient id="hb-t-mug" x1="0%" y1="0%" x2="100%" y2="100%"><stop offset="0%" stop-color="#6b4010"/><stop offset="100%" stop-color="#3a2008"/></linearGradient>
      <filter id="hb-t-glow"><feGaussianBlur stdDeviation="2"/></filter>
    </defs>
    <ellipse cx="40" cy="50" rx="36" ry="46" fill="url(#hb-t-bg)"/>
    <path d="M22,35 L22,75 Q22,80 28,80 L52,80 Q58,80 58,75 L58,35 Z" fill="url(#hb-t-mug)"/>
    <path d="M22,35 L22,75 Q22,80 28,80 L52,80 Q58,80 58,75 L58,35 Z" fill="none" stroke="#8b5820" stroke-width="1.2"/>
    <path d="M58,42 Q72,42 72,57 Q72,70 58,70" fill="none" stroke="#8b5820" stroke-width="5" stroke-linecap="round"/>
    <path d="M20,35 Q30,26 40,30 Q50,26 60,35" fill="#e8e0d0" opacity=".7"/>
    <ellipse cx="32" cy="30" rx="6" ry="4" fill="#f0ece0" opacity=".6"/>
    <ellipse cx="48" cy="30" rx="5" ry="3.5" fill="#f0ece0" opacity=".6"/>
    <ellipse cx="40" cy="37" rx="17" ry="5" fill="#c8780a" opacity=".5"/>
    <path d="M32,22 Q30,16 33,12" fill="none" stroke="#a09080" stroke-width="1.2" opacity=".4" stroke-linecap="round"/>
    <path d="M40,18 Q38,12 41,8" fill="none" stroke="#a09080" stroke-width="1.2" opacity=".4" stroke-linecap="round"/>
    <path d="M48,20 Q50,14 47,10" fill="none" stroke="#a09080" stroke-width="1.2" opacity=".4" stroke-linecap="round"/>
    <rect x="32" y="52" width="16" height="13" rx="2" fill="#1c0e08" opacity=".7"/>
    <text x="40" y="62" text-anchor="middle" font-size="10" fill="#6b2d12">🔒</text>
  </svg>`,
};

// ── Inject building art into DOM ────────────────────────────────────────────
function _injectBuildingArt() {
  Object.entries(HUB_BUILDING_ART).forEach(([key, svg]) => {
    const el = document.querySelector(`#hub-b-${key} .hub-b-art`);
    if (el) el.innerHTML = svg;
  });
}

// ── Hub NPC SVG Portraits ───────────────────────────────────────────────────
const HUB_NPC_STYLES = {
  aldric: {
    color: '#9060d0', rgb: '144,96,208',
    avatar: `<svg viewBox="0 0 80 100" xmlns="http://www.w3.org/2000/svg" width="56" height="64" class="npc-portrait-svg">
    <defs>
      <radialGradient id="hn-al-bg" cx="50%" cy="40%" r="55%"><stop offset="0%" stop-color="#6030a0" stop-opacity=".4"/><stop offset="100%" stop-color="#0a0510" stop-opacity="0"/></radialGradient>
      <radialGradient id="hn-al-skin" cx="45%" cy="30%" r="60%"><stop offset="0%" stop-color="#c8a878"/><stop offset="100%" stop-color="#806040"/></radialGradient>
      <radialGradient id="hn-al-aura" cx="50%" cy="50%" r="50%"><stop offset="0%" stop-color="#a060f0" stop-opacity=".3"/><stop offset="100%" stop-color="#a060f0" stop-opacity="0"/></radialGradient>
      <filter id="hn-al-gf"><feGaussianBlur stdDeviation="2"/></filter>
    </defs>
    <ellipse cx="40" cy="50" rx="36" ry="46" fill="url(#hn-al-bg)"/>
    <path d="M10,100 L15,55 Q20,45 40,45 Q60,45 65,55 L70,100 Z" fill="#1a0a30"/>
    <path d="M10,100 L15,55 Q20,45 40,45 Q60,45 65,55 L70,100 Z" fill="none" stroke="#4a1a70" stroke-width=".8"/>
    <text x="40" y="80" text-anchor="middle" font-size="12" fill="#6030a0" opacity=".5">✦</text>
    <path d="M26,45 Q24,65 28,85 Q35,92 40,90 Q45,92 52,85 Q56,65 54,45" fill="#d0c8c0" opacity=".85"/>
    <path d="M28,50 Q27,68 31,82" fill="none" stroke="#a09888" stroke-width=".8" opacity=".5"/>
    <path d="M52,50 Q53,68 49,82" fill="none" stroke="#a09888" stroke-width=".8" opacity=".5"/>
    <ellipse cx="40" cy="32" rx="16" ry="18" fill="url(#hn-al-skin)"/>
    <path d="M24,30 Q26,12 40,8 Q54,12 56,30 Q50,26 40,26 Q30,26 24,30 Z" fill="#1a0a30"/>
    <path d="M40,8 L38,0 L40,4 L42,0 Z" fill="#4a1a70"/>
    <ellipse cx="34" cy="30" rx="3.5" ry="3" fill="#fff8f0" opacity=".9"/>
    <ellipse cx="46" cy="30" rx="3.5" ry="3" fill="#fff8f0" opacity=".9"/>
    <circle cx="34" cy="31" r="2" fill="#3a2060"/>
    <circle cx="46" cy="31" r="2" fill="#3a2060"/>
    <path d="M30,26 Q34,23 38,25" fill="none" stroke="#d0c8c0" stroke-width="1.8" stroke-linecap="round"/>
    <path d="M42,25 Q46,23 50,26" fill="none" stroke="#d0c8c0" stroke-width="1.8" stroke-linecap="round"/>
    <path d="M34,38 Q40,41 46,38" fill="#c0b8b0" opacity=".8"/>
    <line x1="62" y1="10" x2="70" y2="90" stroke="#5020a0" stroke-width="2" opacity=".4"/>
    <ellipse cx="63" cy="14" rx="5" ry="5" fill="#a060f0" opacity=".5" filter="url(#hn-al-gf)"/>
    <ellipse cx="40" cy="92" rx="28" ry="6" fill="url(#hn-al-aura)" filter="url(#hn-al-gf)"/>
  </svg>`,
  },

  brutus: {
    color: '#c0392b', rgb: '192,57,43',
    avatar: `<svg viewBox="0 0 80 100" xmlns="http://www.w3.org/2000/svg" width="56" height="64" class="npc-portrait-svg">
    <defs>
      <radialGradient id="hn-br-bg" cx="50%" cy="55%" r="55%"><stop offset="0%" stop-color="#c0392b" stop-opacity=".35"/><stop offset="100%" stop-color="#0a0200" stop-opacity="0"/></radialGradient>
      <radialGradient id="hn-br-skin" cx="42%" cy="30%" r="60%"><stop offset="0%" stop-color="#a07050"/><stop offset="100%" stop-color="#603020"/></radialGradient>
      <linearGradient id="hn-br-armor" x1="0%" y1="0%" x2="100%" y2="100%"><stop offset="0%" stop-color="#4a4a5a"/><stop offset="100%" stop-color="#202028"/></linearGradient>
      <filter id="hn-br-gf"><feGaussianBlur stdDeviation="2.5"/></filter>
    </defs>
    <ellipse cx="40" cy="52" rx="38" ry="48" fill="url(#hn-br-bg)"/>
    <path d="M5,100 L8,55 Q10,42 40,42 Q70,42 72,55 L75,100 Z" fill="url(#hn-br-armor)"/>
    <ellipse cx="14" cy="55" rx="12" ry="8" fill="#383848" stroke="#505060" stroke-width=".8"/>
    <ellipse cx="66" cy="55" rx="12" ry="8" fill="#383848" stroke="#505060" stroke-width=".8"/>
    <line x1="30" y1="55" x2="50" y2="55" stroke="#505060" stroke-width=".8" opacity=".6"/>
    <line x1="28" y1="65" x2="52" y2="65" stroke="#505060" stroke-width=".8" opacity=".6"/>
    <ellipse cx="40" cy="32" rx="17" ry="19" fill="url(#hn-br-skin)"/>
    <path d="M23,26 Q24,10 40,8 Q56,10 57,26" fill="#383848" stroke="#505060" stroke-width=".8"/>
    <path d="M23,26 L21,30" stroke="#505060" stroke-width="1.5" stroke-linecap="round"/>
    <path d="M57,26 L59,30" stroke="#505060" stroke-width="1.5" stroke-linecap="round"/>
    <ellipse cx="33" cy="30" rx="3.8" ry="3.2" fill="#e8d8c0" opacity=".9"/>
    <ellipse cx="47" cy="30" rx="3.8" ry="3.2" fill="#e8d8c0" opacity=".9"/>
    <circle cx="33" cy="31" r="2.2" fill="#5a1800"/>
    <circle cx="47" cy="31" r="2.2" fill="#5a1800"/>
    <path d="M29,25 Q33,22 37,24" fill="none" stroke="#3a1a08" stroke-width="2" stroke-linecap="round"/>
    <path d="M43,24 Q47,22 51,25" fill="none" stroke="#3a1a08" stroke-width="2" stroke-linecap="round"/>
    <path d="M26,34 Q32,38 36,36" fill="none" stroke="#8b1a1a" stroke-width="1.5" stroke-linecap="round" opacity=".8"/>
    <path d="M26,42 Q40,50 54,42" fill="#4a2a10" opacity=".3"/>
    <path d="M37,35 Q40,40 43,35" fill="none" stroke="#7a4020" stroke-width="1" opacity=".5"/>
    <ellipse cx="40" cy="92" rx="30" ry="7" fill="#c0392b" opacity=".18" filter="url(#hn-br-gf)"/>
  </svg>`,
  },
};

// ── Inject NPC portraits ────────────────────────────────────────────────────
function _injectHubNPCPortraits() {
  Object.entries(HUB_NPC_STYLES).forEach(([key, style]) => {
    const el = document.querySelector(`.hub-npc[data-npc="${key}"] .hub-npc-portrait`);
    if (el) el.innerHTML = style.avatar;
  });

  // Orin — reuse z shop.js
  const orinEl = document.querySelector('.hub-npc[data-npc="orin"] .hub-npc-portrait');
  if (orinEl && typeof SHOP_NPC_STYLES !== 'undefined' && SHOP_NPC_STYLES.merchant) {
    orinEl.innerHTML = SHOP_NPC_STYLES.merchant.avatar;
  }
}

const HUB_NPCS = [
  {
    id:       'aldric',
    name:     'Aldric Starý',
    role:     'Správce questů',
    emoji:    '🧙',
    link:     'quests',
    btnLabel: '📜 Questy',
    dialogue: {
      idle:       'Mám pro tebe důležitý úkol, hrdino...',
      active:     'Vrať se, až quest splníš. Čas jsou peníze!',
      collecting: 'Výborně! Pojď si pro zaslouženou odměnu.',
    },
  },
  {
    id:       'brutus',
    name:     'Kapitán Brutus',
    role:     'Velitel arény',
    emoji:    '⚔️',
    link:     'arena',
    btnLabel: '🏟 Aréna',
    dialogue: {
      idle:     'Výzva tě čeká na pískovišti krve, bojovníku!',
      cooldown: 'Regeneruj síly. Aréna nikam neodejde.',
    },
  },
  {
    id:       'orin',
    name:     'Orin Obchodník',
    role:     'Potulný kupec',
    emoji:    '🏪',
    link:     'shop',
    btnLabel: '🛒 Obchod',
    dialogue: {
      idle: 'Čerstvé zboží právě přišlo, příteli! Podívej se.',
    },
  },
];

let _hubCdIntervals = [];

// ── Time-of-day ambient atmosphere ──────────────────────────────────────────

function applyTimeOfDay() {
  const h = new Date().getHours();
  const tod = h >= 5 && h < 10 ? 'dawn' : h >= 10 && h < 17 ? 'day' : h >= 17 && h < 21 ? 'dusk' : 'night';
  const el = document.querySelector('.hub-header');
  if (!el) return;
  el.classList.remove('tod-dawn','tod-day','tod-dusk','tod-night');
  el.classList.add('tod-' + tod);
}

// ── Hlavní load funkce ──────────────────────────────────────────────────────

async function loadHub() {
  _hubCdIntervals.forEach(clearInterval);
  _hubCdIntervals = [];
  applyTimeOfDay();

  // Načti news feed (nezávislé, non-blocking)
  if (typeof loadNewsFeed === 'function') loadNewsFeed();

  // Parallel: hub-summary (aggregated) + boss + arena (pro budovy)
  const [summaryRes, bossRes, arenaRes] = await Promise.allSettled([
    api('GET', '/character/hub-summary'),
    api('GET', '/boss/current'),
    api('GET', '/arena/opponents'),
  ]);

  const summary = summaryRes.status === 'fulfilled' ? summaryRes.value : null;
  const boss    = bossRes.status    === 'fulfilled' ? bossRes.value    : null;
  const arena   = arenaRes.status   === 'fulfilled' ? arenaRes.value   : null;

  // Budovy
  if (summary) {
    _updateQuestBuilding(summary.quest ? { status: summary.quest.status, quest: { name: summary.quest.quest_name }, seconds_remaining: summary.quest.seconds_remaining } : null);
    _updateDungeonBuilding(summary.dungeon ? { run: summary.dungeon.status !== 'idle' ? summary.dungeon : null } : null);
  }
  _updateArenaBuilding(arena); // arena data jsou z /arena/opponents, nezávislé na summary
  _updateBossBuilding(boss);
  _updateHubNPCDialogue({ quest: summary?.quest, arena });

  // Nový dashboard strip
  if (summary) {
    _renderHubSummaryStrip(summary);
    _renderNextAction(summary.next_action);
  }

  // Character tagline
  if (typeof char !== 'undefined' && char) {
    const el = document.getElementById('hub-char-tagline');
    if (el) el.textContent = `${char.name} · Lv.${char.level} ${CLS_N?.[char.cls] || char.cls}`;
  }

  _injectBuildingArt();
  _injectHubNPCPortraits();
}

// ── Dashboard summary strip ─────────────────────────────────────────────────

function _renderHubSummaryStrip(s) {
  const el = document.getElementById('hub-summary-strip');
  if (!el) return;

  const chips = [];

  // Quest chip
  const qs = s.quest?.status;
  if (qs === 'collecting') {
    chips.push(_chip('🎁', 'Quest dokončen!', 'hub-chip-ready', 'quests'));
  } else if (qs === 'active') {
    const rem = s.quest.seconds_remaining || 0;
    const m = Math.floor(rem / 60), sec = rem % 60;
    chips.push(_chip('⚔', `Quest · ⏱ ${m}:${String(sec).padStart(2,'0')}`, 'hub-chip-active', 'quests', true, s.quest.seconds_remaining, 'quest'));
  } else {
    chips.push(_chip('⚔', 'Questy dostupné', 'hub-chip-idle', 'quests'));
  }

  // Arena chip
  const a = s.arena;
  if (a) {
    if (a.on_cooldown) {
      chips.push(_chip('🏟', `Aréna · ELO ${a.rank}`, 'hub-chip-cooldown', 'arena'));
    } else {
      chips.push(_chip('🏟', `Aréna · #${a.rank} · Připravena`, 'hub-chip-ready', 'arena'));
    }
  }

  // Dungeon chip
  const d = s.dungeon;
  if (d && d.status === 'active') {
    chips.push(_chip('🏰', `Dungeon · Stage ${d.current_stage}/${d.total_stages}`, 'hub-chip-active', 'dungeons'));
  } else if (d && d.status === 'completed' && !d.reward_claimed) {
    chips.push(_chip('🏆', 'Dungeon dokončen!', 'hub-chip-ready', 'dungeons'));
  } else if (d && d.on_cooldown) {
    chips.push(_chip('🏰', 'Dungeon · Cooldown', 'hub-chip-cooldown', 'dungeons'));
  } else {
    chips.push(_chip('🏰', 'Dungeon · Dostupný', 'hub-chip-idle', 'dungeons'));
  }

  // Season pass chip
  if (s.season_pass) {
    const sp = s.season_pass;
    const pct = sp.next_tier_xp ? Math.round((sp.season_xp / sp.next_tier_xp) * 100) : 100;
    chips.push(_chip('🏅', `Sezóna · Tier ${sp.current_tier}/${sp.max_tier} · ${pct}%`, 'hub-chip-season', 'season'));
  }

  // Guild weekly chip
  if (s.guild_weekly) {
    const gw = s.guild_weekly;
    const pct = Math.round((gw.progress / gw.goal_target) * 100);
    const label = gw.is_completed ? 'Cech · ✓ Splněno!' : `Cech · ${pct}% týdenního cíle`;
    chips.push(_chip('⚜', label, gw.is_completed ? 'hub-chip-ready' : 'hub-chip-guild', 'guild'));
  }

  // World event chip
  if (s.world_event && !s.world_event.is_completed) {
    const we = s.world_event;
    const pct = Math.round((we.current_progress / we.goal) * 100);
    chips.push(_chip('🌍', `${we.name} · ${pct}%`, 'hub-chip-event', 'world-events'));
  }

  // Daily quests chip
  if (s.daily_quests?.available > 0) {
    chips.push(_chip('📋', `${s.daily_quests.available} denní questy`, 'hub-chip-daily', 'quests'));
  }

  el.innerHTML = chips.join('');
}

function _chip(icon, text, cls, page, hasCd = false, cdSec = 0, cdKey = '') {
  return `<div class="hub-chip ${cls}" onclick="showPage('${page}')">
    <span class="hub-chip-icon">${icon}</span>
    <span class="hub-chip-text" ${hasCd ? `id="hub-cd-${cdKey}"` : ''}>${text}</span>
  </div>`;
}

// ── Next action widget ──────────────────────────────────────────────────────

function _renderNextAction(action) {
  const el = document.getElementById('hub-next-action');
  if (!el) return;
  if (!action) { el.innerHTML = ''; return; }
  el.innerHTML = `
    <div class="hub-next-action" onclick="showPage('${action.page}')">
      <span class="hub-na-icon">${action.icon}</span>
      <div class="hub-na-body">
        <div class="hub-na-label">Doporučená akce</div>
        <div class="hub-na-text">${action.text}</div>
      </div>
      <span class="hub-na-arrow">→</span>
    </div>`;
}

// ── Building status updaters ────────────────────────────────────────────────

function _setBuildingStatus(id, badgeClass, badgeText, subText, btnText, btnDisabled) {
  const card = document.getElementById('hub-b-' + id);
  if (!card) return;
  const badge = card.querySelector('.hub-b-badge');
  const sub   = card.querySelector('.hub-b-sub');
  const btn   = card.querySelector('.hub-b-btn');
  if (badge) { badge.className = 'hub-b-badge ' + badgeClass; badge.textContent = badgeText; }
  if (sub   && subText  !== null) sub.textContent  = subText;
  if (btn   && btnText  !== null) btn.textContent   = btnText;
  if (btn   && btnDisabled !== null) btn.disabled   = btnDisabled;
}

function _updateQuestBuilding(q) {
  if (!q) return;
  if (q.status === 'collecting') {
    _setBuildingStatus('quests', 'hub-badge-ready', '✓ Hotovo!',
      'Quest dokončen — seber odměnu!', '🎁 Sebrat odměnu', false);
  } else if (q.status === 'active') {
    const questName = q.quest?.name || 'Quest';
    const initRem   = q.seconds_remaining || 0;
    const startTs   = Date.now();
    _setBuildingStatus('quests', 'hub-badge-active', '▶ Probíhá',
      questName, '⚔ Questy', false);
    const sub = document.querySelector('#hub-b-quests .hub-b-sub');
    const tick = () => {
      const rem = Math.max(0, initRem - Math.floor((Date.now() - startTs) / 1000));
      const m = Math.floor(rem / 60), s = rem % 60;
      if (sub) sub.textContent = `${questName} · ⏱ ${m}:${String(s).padStart(2,'0')}`;
      if (rem <= 0) {
        clearInterval(iv);
        _setBuildingStatus('quests', 'hub-badge-ready', '✓ Hotovo!',
          'Quest dokončen — seber odměnu!', '🎁 Sebrat odměnu', false);
      }
    };
    const iv = setInterval(tick, 1000);
    _hubCdIntervals.push(iv);
    tick();
  } else {
    _setBuildingStatus('quests', 'hub-badge-available', 'Dostupné',
      'Questy čekají na přijetí', '⚔ Vybrat quest', false);
  }
}

function _updateArenaBuilding(a) {
  if (!a) return;
  const elo    = a.my_rank  || 1000;
  const wins   = a.my_wins  || 0;
  const losses = a.my_losses || 0;

  // cooldown_seconds je server-side výpočet (bez timezone problémů), cooldown_until jako záložní
  const cdSec = a.cooldown_seconds || 0;
  const cdEndMs = cdSec > 0
    ? Date.now() + cdSec * 1000
    : (a.cooldown_until ? new Date(a.cooldown_until).getTime() : 0);
  const rem = Math.max(0, (cdEndMs - Date.now()) / 1000);

  if (rem > 0) {
    _setBuildingStatus('arena', 'hub-badge-cooldown', '⏳ Cooldown', null, null, null);
    const sub = document.querySelector('#hub-b-arena .hub-b-sub');
    const tick = () => {
      const r = Math.max(0, (cdEndMs - Date.now()) / 1000);
      const m = Math.floor(r / 60), s = Math.floor(r % 60);
      if (sub) sub.textContent = `ELO ${elo} · ${wins}W/${losses}L · ⏳ ${m}:${String(s).padStart(2,'0')}`;
      if (r <= 0) {
        clearInterval(iv);
        _setBuildingStatus('arena', 'hub-badge-available', 'Připravena',
          `ELO ${elo} · ${wins}W/${losses}L`, null, null);
      }
    };
    const iv = setInterval(tick, 1000);
    _hubCdIntervals.push(iv);
    tick();
    return;
  }
  _setBuildingStatus('arena', 'hub-badge-available', 'Připravena',
    `ELO ${elo} · ${wins}W/${losses}L`, null, null);
}

function _updateDungeonBuilding(d) {
  if (!d) return;
  const run = d.run;
  if (run?.status === 'active') {
    _setBuildingStatus('dungeons', 'hub-badge-active', '▶ Probíhá',
      `${run.dungeon_name} — Stage ${run.current_stage}/${run.total_stages}`,
      '▶ Pokračovat', false);
  } else if (run?.status === 'completed') {
    _setBuildingStatus('dungeons', 'hub-badge-ready', '✓ Odměna!',
      `${run.dungeon_name} dokončen!`, '🏆 Sebrat', false);
  } else {
    _setBuildingStatus('dungeons', 'hub-badge-available', 'Dostupné',
      '3 dungeony k prozkoumání', '🗝 Vstoupit', false);
  }
}

function _updateBossBuilding(b) {
  if (!b?.boss) {
    _setBuildingStatus('boss', 'hub-badge-locked', 'Neaktivní',
      'Žádný aktivní boss', '— Zavřeno —', true);
    return;
  }
  const boss = b.boss;
  if (!boss.is_alive) {
    _setBuildingStatus('boss', 'hub-badge-locked', 'Poražen',
      `${boss.name} byl poražen`, '— Poražen —', true);
    return;
  }
  const hpPct = boss.hp_pct?.toFixed(0) ?? '?';
  _setBuildingStatus('boss', 'hub-badge-boss', '⚠ Živý!',
    `${boss.name} — ${hpPct}% HP`, '⚔ Zaútočit', false);
}

function _updateHubNPCDialogue(data) {
  const q = data.quest;
  const a = data.arena;

  const dialogues = {
    aldric: q?.status === 'collecting' ? HUB_NPCS[0].dialogue.collecting :
            q?.status === 'active'     ? HUB_NPCS[0].dialogue.active     :
                                         HUB_NPCS[0].dialogue.idle,
    brutus: (a?.cooldown_until && new Date(a.cooldown_until) > new Date())
            ? HUB_NPCS[1].dialogue.cooldown
            : HUB_NPCS[1].dialogue.idle,
    orin:   HUB_NPCS[2].dialogue.idle,
  };

  HUB_NPCS.forEach(npc => {
    const el = document.getElementById('hub-npc-speech-' + npc.id);
    if (el && dialogues[npc.id]) el.textContent = dialogues[npc.id];
  });
}
