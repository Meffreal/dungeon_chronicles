// ── TOWN HUB — Město Ashenveil ─────────────────────────────────────────────
// Hlavní stránka hráče. Zobrazuje mapu města s budovami (aktivity) a NPC.
// Každá budova má živý status ze serveru (cooldown, progress, dostupnost).

// ── Hub Building SVG Art — 2.5D Gothic Architecture ─────────────────────────
const HUB_BUILDING_ART = {

  dungeons: `<svg viewBox="0 0 100 180" xmlns="http://www.w3.org/2000/svg" width="100" height="180" class="hub-b-svg">
    <defs>
      <linearGradient id="hbd-stone" x1="0%" y1="0%" x2="100%" y2="100%"><stop offset="0%" stop-color="#2c1e10"/><stop offset="100%" stop-color="#1a1008"/></linearGradient>
      <linearGradient id="hbd-stone2" x1="0%" y1="0%" x2="100%" y2="100%"><stop offset="0%" stop-color="#251808"/><stop offset="100%" stop-color="#160e04"/></linearGradient>
      <radialGradient id="hbd-void" cx="50%" cy="60%" r="55%"><stop offset="0%" stop-color="#12003a" stop-opacity=".97"/><stop offset="80%" stop-color="#0a0020" stop-opacity=".85"/><stop offset="100%" stop-color="#060010" stop-opacity="0"/></radialGradient>
      <radialGradient id="hbd-glow" cx="50%" cy="50%" r="50%"><stop offset="0%" stop-color="#6428c0" stop-opacity=".7"/><stop offset="100%" stop-color="#3a0890" stop-opacity="0"/></radialGradient>
      <radialGradient id="hbd-shadow" cx="50%" cy="100%" r="50%"><stop offset="0%" stop-color="#3a1080" stop-opacity=".5"/><stop offset="100%" stop-color="#3a1080" stop-opacity="0"/></radialGradient>
      <filter id="hbd-blur"><feGaussianBlur stdDeviation="3"/></filter>
      <filter id="hbd-blur2"><feGaussianBlur stdDeviation="1.5"/></filter>
    </defs>
    <!-- Left stone wall -->
    <rect x="4" y="30" width="26" height="145" fill="url(#hbd-stone)"/>
    <rect x="4" y="30" width="26" height="145" fill="none" stroke="#4a2e14" stroke-width=".8"/>
    <!-- Right stone wall -->
    <rect x="70" y="30" width="26" height="145" fill="url(#hbd-stone)"/>
    <rect x="70" y="30" width="26" height="145" fill="none" stroke="#4a2e14" stroke-width=".8"/>
    <!-- Stone block texture left -->
    <line x1="4" y1="55" x2="30" y2="55" stroke="#1a0e06" stroke-width=".7" opacity=".6"/>
    <line x1="4" y1="75" x2="30" y2="75" stroke="#1a0e06" stroke-width=".7" opacity=".6"/>
    <line x1="4" y1="95" x2="30" y2="95" stroke="#1a0e06" stroke-width=".7" opacity=".6"/>
    <line x1="4" y1="115" x2="30" y2="115" stroke="#1a0e06" stroke-width=".7" opacity=".6"/>
    <line x1="4" y1="135" x2="30" y2="135" stroke="#1a0e06" stroke-width=".7" opacity=".6"/>
    <line x1="17" y1="30" x2="17" y2="175" stroke="#1a0e06" stroke-width=".5" opacity=".4"/>
    <!-- Stone block texture right -->
    <line x1="70" y1="55" x2="96" y2="55" stroke="#1a0e06" stroke-width=".7" opacity=".6"/>
    <line x1="70" y1="75" x2="96" y2="75" stroke="#1a0e06" stroke-width=".7" opacity=".6"/>
    <line x1="70" y1="95" x2="96" y2="95" stroke="#1a0e06" stroke-width=".7" opacity=".6"/>
    <line x1="70" y1="115" x2="96" y2="115" stroke="#1a0e06" stroke-width=".7" opacity=".6"/>
    <line x1="70" y1="135" x2="96" y2="135" stroke="#1a0e06" stroke-width=".7" opacity=".6"/>
    <line x1="83" y1="30" x2="83" y2="175" stroke="#1a0e06" stroke-width=".5" opacity=".4"/>
    <!-- Gothic arch keystone -->
    <path d="M30,30 Q50,2 70,30 Z" fill="url(#hbd-stone2)" stroke="#4a2e14" stroke-width="1.2"/>
    <!-- Arch void / darkness inside -->
    <path d="M30,30 Q50,4 70,30 L70,175 L30,175 Z" fill="url(#hbd-void)"/>
    <!-- Purple mist rising from base -->
    <ellipse cx="50" cy="165" rx="22" ry="14" fill="#6428c0" opacity=".18" filter="url(#hbd-blur)"/>
    <ellipse cx="50" cy="152" rx="14" ry="10" fill="#7030d0" opacity=".14" filter="url(#hbd-blur)"/>
    <ellipse cx="50" cy="138" rx="8" ry="8" fill="#8040e0" opacity=".12" filter="url(#hbd-blur)"/>
    <!-- Purple inner glow -->
    <ellipse cx="50" cy="110" rx="16" ry="25" fill="url(#hbd-glow)" filter="url(#hbd-blur)"/>
    <!-- Iron gate bars (vertical) -->
    <rect x="35" y="80" width="3" height="95" rx="1" fill="#2a1a0c" stroke="#3a2a14" stroke-width=".5"/>
    <rect x="43" y="80" width="3" height="95" rx="1" fill="#2a1a0c" stroke="#3a2a14" stroke-width=".5"/>
    <rect x="51" y="80" width="3" height="95" rx="1" fill="#2a1a0c" stroke="#3a2a14" stroke-width=".5"/>
    <rect x="59" y="80" width="3" height="95" rx="1" fill="#2a1a0c" stroke="#3a2a14" stroke-width=".5"/>
    <!-- Gate spikes top -->
    <polygon points="35,80 37,70 39,80" fill="#2a1a0c"/>
    <polygon points="43,80 45,70 47,80" fill="#2a1a0c"/>
    <polygon points="51,80 53,70 55,80" fill="#2a1a0c"/>
    <polygon points="59,80 61,70 63,80" fill="#2a1a0c"/>
    <!-- Gate horizontal bar -->
    <rect x="33" y="105" width="34" height="3" rx="1" fill="#2e200e" stroke="#3a2a14" stroke-width=".5"/>
    <!-- Chains from arch apex -->
    <line x1="44" y1="20" x2="38" y2="85" stroke="#3a2a10" stroke-width="1.2" stroke-dasharray="3,2" opacity=".7"/>
    <line x1="56" y1="20" x2="62" y2="85" stroke="#3a2a10" stroke-width="1.2" stroke-dasharray="3,2" opacity=".7"/>
    <!-- Rune carvings left wall -->
    <rect x="9" y="42" width="8" height="2" rx="1" fill="#5a3a18" opacity=".5"/>
    <rect x="11" y="38" width="4" height="8" rx="1" fill="#5a3a18" opacity=".4"/>
    <!-- Rune carvings right wall -->
    <rect x="79" y="42" width="8" height="2" rx="1" fill="#5a3a18" opacity=".5"/>
    <rect x="81" y="38" width="4" height="8" rx="1" fill="#5a3a18" opacity=".4"/>
    <!-- Ground shadow -->
    <ellipse cx="50" cy="174" rx="35" ry="7" fill="url(#hbd-shadow)" filter="url(#hbd-blur2)"/>
  </svg>`,

  quests: `<svg viewBox="0 0 100 160" xmlns="http://www.w3.org/2000/svg" width="100" height="160" class="hub-b-svg">
    <defs>
      <linearGradient id="hbq-wall" x1="0%" y1="0%" x2="100%" y2="100%"><stop offset="0%" stop-color="#c8b89a"/><stop offset="100%" stop-color="#a09070"/></linearGradient>
      <linearGradient id="hbq-beam" x1="0%" y1="0%" x2="100%" y2="100%"><stop offset="0%" stop-color="#3a2008"/><stop offset="100%" stop-color="#251206"/></linearGradient>
      <linearGradient id="hbq-roof" x1="0%" y1="0%" x2="100%" y2="100%"><stop offset="0%" stop-color="#4a3018"/><stop offset="100%" stop-color="#2a1808"/></linearGradient>
      <radialGradient id="hbq-wingl" cx="50%" cy="50%" r="50%"><stop offset="0%" stop-color="#20b2aa" stop-opacity=".5"/><stop offset="100%" stop-color="#0a4844" stop-opacity="0"/></radialGradient>
      <radialGradient id="hbq-shadow" cx="50%" cy="100%" r="50%"><stop offset="0%" stop-color="#20b2aa" stop-opacity=".35"/><stop offset="100%" stop-color="#20b2aa" stop-opacity="0"/></radialGradient>
      <filter id="hbq-blur"><feGaussianBlur stdDeviation="2.5"/></filter>
    </defs>
    <!-- Main 3-storey facade -->
    <rect x="8" y="50" width="84" height="107" fill="url(#hbq-wall)"/>
    <rect x="8" y="50" width="84" height="107" fill="none" stroke="#7a6040" stroke-width=".8"/>
    <!-- Timbered pattern: horizontal beams -->
    <rect x="8" y="72" width="84" height="4" fill="url(#hbq-beam)" opacity=".75"/>
    <rect x="8" y="100" width="84" height="4" fill="url(#hbq-beam)" opacity=".75"/>
    <rect x="8" y="128" width="84" height="4" fill="url(#hbq-beam)" opacity=".75"/>
    <!-- Timbered diagonal braces 1st floor -->
    <line x1="8" y1="104" x2="50" y2="128" stroke="#3a2008" stroke-width="2.5" opacity=".55"/>
    <line x1="92" y1="104" x2="50" y2="128" stroke="#3a2008" stroke-width="2.5" opacity=".55"/>
    <!-- Timbered diagonal braces 2nd floor -->
    <line x1="8" y1="76" x2="50" y2="100" stroke="#3a2008" stroke-width="2" opacity=".5"/>
    <line x1="92" y1="76" x2="50" y2="100" stroke="#3a2008" stroke-width="2" opacity=".5"/>
    <!-- Roof (gabled) -->
    <polygon points="4,52 50,18 96,52" fill="url(#hbq-roof)" stroke="#2a1808" stroke-width="1"/>
    <polygon points="4,52 50,18 96,52" fill="none" stroke="#6a4828" stroke-width=".6"/>
    <!-- Roof ridge horizontal beam -->
    <rect x="4" y="50" width="92" height="5" fill="url(#hbq-beam)" opacity=".8"/>
    <!-- Gothic windows 3rd floor with arch + teal glow -->
    <rect x="20" y="56" width="16" height="20" rx="0" fill="#0a2020"/>
    <path d="M20,66 Q28,54 36,66" fill="#0d2820" stroke="#4a6858" stroke-width=".7"/>
    <ellipse cx="28" cy="66" rx="5" ry="6" fill="#20b2aa" opacity=".18" filter="url(#hbq-blur)"/>
    <rect x="64" y="56" width="16" height="20" rx="0" fill="#0a2020"/>
    <path d="M64,66 Q72,54 80,66" fill="#0d2820" stroke="#4a6858" stroke-width=".7"/>
    <ellipse cx="72" cy="66" rx="5" ry="6" fill="#20b2aa" opacity=".18" filter="url(#hbq-blur)"/>
    <!-- Gothic windows 2nd floor -->
    <rect x="16" y="80" width="18" height="22" rx="0" fill="#0a1a18"/>
    <path d="M16,92 Q25,78 34,92" fill="#0d2020" stroke="#3a5848" stroke-width=".7"/>
    <rect x="66" y="80" width="18" height="22" rx="0" fill="#0a1a18"/>
    <path d="M66,92 Q75,78 84,92" fill="#0d2020" stroke="#3a5848" stroke-width=".7"/>
    <!-- Notice board with scrolls on 1st floor (left of door) -->
    <rect x="10" y="108" width="24" height="25" rx="1" fill="#5a3a14" stroke="#7a5020" stroke-width=".8"/>
    <rect x="12" y="110" width="9" height="12" rx="1" fill="#d4b87a" opacity=".85"/>
    <rect x="23" y="110" width="9" height="8" rx="1" fill="#c8a86a" opacity=".8"/>
    <rect x="12" y="124" width="20" height="7" rx="1" fill="#d4b87a" opacity=".75"/>
    <line x1="13" y1="112" x2="20" y2="112" stroke="#5a3808" stroke-width=".6" opacity=".7"/>
    <line x1="13" y1="115" x2="20" y2="115" stroke="#5a3808" stroke-width=".6" opacity=".7"/>
    <!-- Arched door center -->
    <rect x="40" y="118" width="20" height="39" rx="0" fill="#2a1808"/>
    <path d="M40,128 Q50,112 60,128" fill="#201008" stroke="#4a2e10" stroke-width=".8"/>
    <!-- Iron door hinges -->
    <rect x="41" y="128" width="4" height="2" rx=".5" fill="#3a2808"/>
    <rect x="55" y="128" width="4" height="2" rx=".5" fill="#3a2808"/>
    <rect x="41" y="145" width="4" height="2" rx=".5" fill="#3a2808"/>
    <rect x="55" y="145" width="4" height="2" rx=".5" fill="#3a2808"/>
    <!-- Lantern over door on iron bracket -->
    <line x1="50" y1="108" x2="50" y2="116" stroke="#3a2808" stroke-width="1.2"/>
    <rect x="46" y="100" width="8" height="10" rx="1" fill="#3a2808" stroke="#5a4020" stroke-width=".6"/>
    <rect x="47" y="101" width="6" height="8" rx="1" fill="#ff9900" opacity=".35"/>
    <ellipse cx="50" cy="116" rx="10" ry="5" fill="#ff8800" opacity=".12" filter="url(#hbq-blur)"/>
    <!-- Banner hanging from 3rd floor window -->
    <rect x="45" y="18" width="10" height="16" rx="1" fill="#0d4a44" stroke="#1a7060" stroke-width=".7"/>
    <line x1="50" y1="20" x2="50" y2="32" stroke="#20b2aa" stroke-width=".8" opacity=".5"/>
    <!-- Ground shadow -->
    <ellipse cx="50" cy="157" rx="38" ry="7" fill="url(#hbq-shadow)" filter="url(#hbq-blur)"/>
  </svg>`,

  boss: `<svg viewBox="0 0 120 210" xmlns="http://www.w3.org/2000/svg" width="120" height="210" class="hub-b-svg">
    <defs>
      <linearGradient id="hbb-stone" x1="0%" y1="0%" x2="100%" y2="100%"><stop offset="0%" stop-color="#2a1a10"/><stop offset="100%" stop-color="#180a06"/></linearGradient>
      <linearGradient id="hbb-stone2" x1="0%" y1="0%" x2="100%" y2="100%"><stop offset="0%" stop-color="#221208"/><stop offset="100%" stop-color="#140804"/></linearGradient>
      <radialGradient id="hbb-rose" cx="50%" cy="50%" r="50%"><stop offset="0%" stop-color="#cc0000" stop-opacity=".9"/><stop offset="60%" stop-color="#880000" stop-opacity=".5"/><stop offset="100%" stop-color="#440000" stop-opacity="0"/></radialGradient>
      <radialGradient id="hbb-glow" cx="50%" cy="100%" r="55%"><stop offset="0%" stop-color="#cc1010" stop-opacity=".55"/><stop offset="100%" stop-color="#880000" stop-opacity="0"/></radialGradient>
      <radialGradient id="hbb-shadow" cx="50%" cy="100%" r="50%"><stop offset="0%" stop-color="#8b0000" stop-opacity=".5"/><stop offset="100%" stop-color="#8b0000" stop-opacity="0"/></radialGradient>
      <filter id="hbb-blur"><feGaussianBlur stdDeviation="4"/></filter>
      <filter id="hbb-blur2"><feGaussianBlur stdDeviation="2"/></filter>
    </defs>
    <!-- Left tower -->
    <rect x="2" y="45" width="22" height="165" fill="url(#hbb-stone)"/>
    <rect x="2" y="45" width="22" height="165" fill="none" stroke="#3a2010" stroke-width=".8"/>
    <polygon points="2,45 13,22 24,45" fill="url(#hbb-stone2)" stroke="#3a2010" stroke-width=".8"/>
    <!-- Left tower battlements -->
    <rect x="2" y="37" width="5" height="9" fill="#1e1008"/><rect x="9" y="37" width="5" height="9" fill="#1e1008"/><rect x="17" y="37" width="5" height="9" fill="#1e1008"/>
    <!-- Left tower window -->
    <rect x="7" y="68" width="12" height="16" rx="0" fill="#0a0000"/>
    <path d="M7,76 Q13,64 19,76" fill="#0d0004" stroke="#3a1010" stroke-width=".6"/>
    <!-- Right tower -->
    <rect x="96" y="45" width="22" height="165" fill="url(#hbb-stone)"/>
    <rect x="96" y="45" width="22" height="165" fill="none" stroke="#3a2010" stroke-width=".8"/>
    <polygon points="96,45 107,22 118,45" fill="url(#hbb-stone2)" stroke="#3a2010" stroke-width=".8"/>
    <!-- Right tower battlements -->
    <rect x="96" y="37" width="5" height="9" fill="#1e1008"/><rect x="103" y="37" width="5" height="9" fill="#1e1008"/><rect x="111" y="37" width="5" height="9" fill="#1e1008"/>
    <!-- Right tower window -->
    <rect x="101" y="68" width="12" height="16" rx="0" fill="#0a0000"/>
    <path d="M101,76 Q107,64 113,76" fill="#0d0004" stroke="#3a1010" stroke-width=".6"/>
    <!-- Central main body -->
    <rect x="22" y="60" width="76" height="150" fill="url(#hbb-stone)"/>
    <rect x="22" y="60" width="76" height="150" fill="none" stroke="#3a2010" stroke-width=".8"/>
    <!-- Central battlements top -->
    <rect x="22" y="52" width="9" height="10" fill="#1e1008"/><rect x="34" y="52" width="9" height="10" fill="#1e1008"/><rect x="46" y="52" width="9" height="10" fill="#1e1008"/><rect x="58" y="52" width="9" height="10" fill="#1e1008"/><rect x="70" y="52" width="9" height="10" fill="#1e1008"/><rect x="82" y="52" width="9" height="10" fill="#1e1008"/>
    <!-- Nave roof line -->
    <rect x="22" y="58" width="76" height="5" fill="url(#hbb-stone2)"/>
    <!-- Flying buttresses left -->
    <path d="M22,120 Q10,130 6,155" fill="none" stroke="#2a1808" stroke-width="3" stroke-linecap="round"/>
    <path d="M22,120 Q10,130 6,155" fill="none" stroke="#3a2010" stroke-width="1"/>
    <!-- Flying buttresses right -->
    <path d="M98,120 Q110,130 114,155" fill="none" stroke="#2a1808" stroke-width="3" stroke-linecap="round"/>
    <path d="M98,120 Q110,130 114,155" fill="none" stroke="#3a2010" stroke-width="1"/>
    <!-- Stone block lines facade -->
    <line x1="22" y1="90" x2="98" y2="90" stroke="#160c04" stroke-width=".7" opacity=".6"/>
    <line x1="22" y1="120" x2="98" y2="120" stroke="#160c04" stroke-width=".7" opacity=".6"/>
    <line x1="22" y1="150" x2="98" y2="150" stroke="#160c04" stroke-width=".7" opacity=".6"/>
    <line x1="22" y1="180" x2="98" y2="180" stroke="#160c04" stroke-width=".7" opacity=".6"/>
    <!-- Rose window (center facade) -->
    <circle cx="60" cy="82" r="14" fill="none" stroke="#3a1008" stroke-width="2"/>
    <circle cx="60" cy="82" r="14" fill="#1a0008" opacity=".8"/>
    <circle cx="60" cy="82" r="11" fill="url(#hbb-rose)" filter="url(#hbb-blur2)"/>
    <circle cx="60" cy="82" r="5" fill="#cc0000" opacity=".55" filter="url(#hbb-blur2)"/>
    <!-- Rose window spokes -->
    <line x1="60" y1="68" x2="60" y2="96" stroke="#5a0808" stroke-width=".8" opacity=".7"/>
    <line x1="46" y1="82" x2="74" y2="82" stroke="#5a0808" stroke-width=".8" opacity=".7"/>
    <line x1="50" y1="72" x2="70" y2="92" stroke="#5a0808" stroke-width=".6" opacity=".5"/>
    <line x1="70" y1="72" x2="50" y2="92" stroke="#5a0808" stroke-width=".6" opacity=".5"/>
    <!-- Massive arched door with iron hinges -->
    <rect x="43" y="158" width="34" height="52" rx="0" fill="#100404"/>
    <path d="M43,175 Q60,148 77,175" fill="#0d0204" stroke="#3a1008" stroke-width="1.2"/>
    <!-- Door hinges kované -->
    <path d="M44,165 L52,162 L56,168" fill="none" stroke="#2a1008" stroke-width="1.5" stroke-linecap="round"/>
    <path d="M76,165 L68,162 L64,168" fill="none" stroke="#2a1008" stroke-width="1.5" stroke-linecap="round"/>
    <path d="M44,185 L52,183 L54,190" fill="none" stroke="#2a1008" stroke-width="1.5" stroke-linecap="round"/>
    <path d="M76,185 L68,183 L66,190" fill="none" stroke="#2a1008" stroke-width="1.5" stroke-linecap="round"/>
    <!-- Stone steps (3) -->
    <rect x="35" y="204" width="50" height="5" rx="0" fill="#2a1a0c" stroke="#3a2010" stroke-width=".6"/>
    <rect x="38" y="200" width="44" height="5" rx="0" fill="#281808" stroke="#3a2010" stroke-width=".6"/>
    <rect x="41" y="196" width="38" height="5" rx="0" fill="#261606" stroke="#3a2010" stroke-width=".6"/>
    <!-- Gargoyle hints top corners -->
    <path d="M22,62 Q16,58 12,62 Q14,68 22,66" fill="#1a0c04" opacity=".7"/>
    <path d="M98,62 Q104,58 108,62 Q106,68 98,66" fill="#1a0c04" opacity=".7"/>
    <!-- Ground blood glow pool -->
    <ellipse cx="60" cy="207" rx="44" ry="10" fill="url(#hbb-glow)" filter="url(#hbb-blur)"/>
    <ellipse cx="60" cy="206" rx="26" ry="7" fill="#cc1010" opacity=".22" filter="url(#hbb-blur2)"/>
    <!-- Ground shadow -->
    <ellipse cx="60" cy="208" rx="46" ry="8" fill="url(#hbb-shadow)" filter="url(#hbb-blur2)"/>
  </svg>`,

  shop: `<svg viewBox="0 0 100 150" xmlns="http://www.w3.org/2000/svg" width="100" height="150" class="hub-b-svg">
    <defs>
      <linearGradient id="hbs-wall" x1="0%" y1="0%" x2="100%" y2="100%"><stop offset="0%" stop-color="#c8a878"/><stop offset="100%" stop-color="#9a7848"/></linearGradient>
      <linearGradient id="hbs-wall2" x1="0%" y1="0%" x2="100%" y2="100%"><stop offset="0%" stop-color="#b89868"/><stop offset="100%" stop-color="#8a6838"/></linearGradient>
      <linearGradient id="hbs-beam" x1="0%" y1="0%" x2="100%" y2="100%"><stop offset="0%" stop-color="#3a2008"/><stop offset="100%" stop-color="#251206"/></linearGradient>
      <linearGradient id="hbs-roof" x1="0%" y1="0%" x2="100%" y2="100%"><stop offset="0%" stop-color="#5a3818"/><stop offset="100%" stop-color="#3a2010"/></linearGradient>
      <radialGradient id="hbs-wingl" cx="50%" cy="50%" r="50%"><stop offset="0%" stop-color="#ffb840" stop-opacity=".65"/><stop offset="100%" stop-color="#c87000" stop-opacity="0"/></radialGradient>
      <radialGradient id="hbs-shadow" cx="50%" cy="100%" r="50%"><stop offset="0%" stop-color="#c89010" stop-opacity=".4"/><stop offset="100%" stop-color="#c89010" stop-opacity="0"/></radialGradient>
      <filter id="hbs-blur"><feGaussianBlur stdDeviation="2.5"/></filter>
    </defs>
    <!-- Ground floor walls -->
    <rect x="8" y="72" width="84" height="72" fill="url(#hbs-wall)"/>
    <rect x="8" y="72" width="84" height="72" fill="none" stroke="#7a5828" stroke-width=".8"/>
    <!-- 2nd floor overhang (projects 6px left and right) -->
    <rect x="2" y="36" width="96" height="38" fill="url(#hbs-wall2)"/>
    <rect x="2" y="36" width="96" height="38" fill="none" stroke="#6a4818" stroke-width=".8"/>
    <!-- Overhang bottom shadow -->
    <rect x="2" y="72" width="96" height="4" fill="#2a1808" opacity=".4"/>
    <!-- Timber beams 2nd floor -->
    <line x1="2" y1="55" x2="98" y2="55" stroke="#3a2008" stroke-width="2" opacity=".6"/>
    <line x1="30" y1="36" x2="30" y2="74" stroke="#3a2008" stroke-width="1.5" opacity=".45"/>
    <line x1="70" y1="36" x2="70" y2="74" stroke="#3a2008" stroke-width="1.5" opacity=".45"/>
    <!-- Diagonal brace 2nd floor -->
    <line x1="2" y1="56" x2="30" y2="74" stroke="#3a2008" stroke-width="1.2" opacity=".4"/>
    <line x1="98" y1="56" x2="70" y2="74" stroke="#3a2008" stroke-width="1.2" opacity=".4"/>
    <!-- Roof (hipped) -->
    <polygon points="2,38 50,10 98,38" fill="url(#hbs-roof)" stroke="#2a1408" stroke-width=".8"/>
    <rect x="2" y="36" width="96" height="4" fill="#3a2010" opacity=".8"/>
    <!-- Amber windows 1st floor with warm glow -->
    <rect x="16" y="82" width="18" height="20" rx="0" fill="#1a0e04"/>
    <path d="M16,92 Q25,80 34,92" fill="#140a02" stroke="#5a3810" stroke-width=".6"/>
    <ellipse cx="25" cy="93" rx="6" ry="7" fill="url(#hbs-wingl)" filter="url(#hbs-blur)"/>
    <rect x="66" y="82" width="18" height="20" rx="0" fill="#1a0e04"/>
    <path d="M66,92 Q75,80 84,92" fill="#140a02" stroke="#5a3810" stroke-width=".6"/>
    <ellipse cx="75" cy="93" rx="6" ry="7" fill="url(#hbs-wingl)" filter="url(#hbs-blur)"/>
    <!-- 2nd floor windows with amber glow -->
    <rect x="14" y="44" width="16" height="18" rx="0" fill="#1a0e04"/>
    <path d="M14,52 Q22,42 30,52" fill="#140a02" stroke="#5a3810" stroke-width=".6"/>
    <ellipse cx="22" cy="53" rx="5" ry="5" fill="url(#hbs-wingl)" filter="url(#hbs-blur)"/>
    <rect x="70" y="44" width="16" height="18" rx="0" fill="#1a0e04"/>
    <path d="M70,52 Q78,42 86,52" fill="#140a02" stroke="#5a3810" stroke-width=".6"/>
    <ellipse cx="78" cy="53" rx="5" ry="5" fill="url(#hbs-wingl)" filter="url(#hbs-blur)"/>
    <!-- Decorative carved lintel over door -->
    <rect x="36" y="108" width="28" height="4" rx="1" fill="#5a3818" stroke="#8a5828" stroke-width=".5"/>
    <line x1="40" y1="109" x2="40" y2="111" stroke="#8a5828" stroke-width=".8" opacity=".5"/>
    <line x1="50" y1="109" x2="50" y2="111" stroke="#8a5828" stroke-width=".8" opacity=".5"/>
    <line x1="60" y1="109" x2="60" y2="111" stroke="#8a5828" stroke-width=".8" opacity=".5"/>
    <!-- Arched door -->
    <rect x="38" y="112" width="24" height="32" rx="0" fill="#1e1008"/>
    <path d="M38,122 Q50,106 62,122" fill="#180c04" stroke="#4a2e10" stroke-width=".8"/>
    <!-- Iron door hinges -->
    <rect x="39" y="123" width="5" height="2" rx=".5" fill="#2a1808"/>
    <rect x="56" y="123" width="5" height="2" rx=".5" fill="#2a1808"/>
    <!-- Swinging iron sign (bracket + board) -->
    <line x1="72" y1="76" x2="72" y2="86" stroke="#3a2808" stroke-width="1.5"/>
    <line x1="72" y1="76" x2="84" y2="76" stroke="#3a2808" stroke-width="1.5"/>
    <rect x="76" y="76" width="16" height="12" rx="1" fill="#4a3010" stroke="#7a5020" stroke-width=".7"/>
    <ellipse cx="84" cy="82" rx="4" ry="4" fill="#c89010" opacity=".6"/>
    <!-- Barrels and crates outside -->
    <rect x="10" y="126" width="10" height="12" rx="1" fill="#5a3810" stroke="#7a5020" stroke-width=".6"/>
    <line x1="10" y1="131" x2="20" y2="131" stroke="#7a5020" stroke-width=".8" opacity=".6"/>
    <ellipse cx="15" cy="138" rx="5" ry="3" fill="#4a2e0c" stroke="#6a4818" stroke-width=".5"/>
    <rect x="22" y="129" width="8" height="9" rx="1" fill="#4a2e0c" stroke="#6a3e14" stroke-width=".6"/>
    <!-- Ground shadow warm amber -->
    <ellipse cx="50" cy="146" rx="40" ry="7" fill="url(#hbs-shadow)" filter="url(#hbs-blur)"/>
  </svg>`,

  arena: `<svg viewBox="0 0 100 165" xmlns="http://www.w3.org/2000/svg" width="100" height="165" class="hub-b-svg">
    <defs>
      <linearGradient id="hba-stone" x1="0%" y1="0%" x2="100%" y2="100%"><stop offset="0%" stop-color="#2a1a10"/><stop offset="100%" stop-color="#180a06"/></linearGradient>
      <linearGradient id="hba-stone2" x1="0%" y1="0%" x2="100%" y2="100%"><stop offset="0%" stop-color="#221208"/><stop offset="100%" stop-color="#120804"/></linearGradient>
      <radialGradient id="hba-inner1" cx="50%" cy="50%" r="50%"><stop offset="0%" stop-color="#c03020" stop-opacity=".7"/><stop offset="100%" stop-color="#6a0808" stop-opacity="0"/></radialGradient>
      <radialGradient id="hba-inner2" cx="50%" cy="50%" r="50%"><stop offset="0%" stop-color="#e06030" stop-opacity=".5"/><stop offset="100%" stop-color="#8a2008" stop-opacity="0"/></radialGradient>
      <radialGradient id="hba-glow" cx="50%" cy="100%" r="55%"><stop offset="0%" stop-color="#c0392b" stop-opacity=".55"/><stop offset="100%" stop-color="#8b1a1a" stop-opacity="0"/></radialGradient>
      <radialGradient id="hba-shadow" cx="50%" cy="100%" r="50%"><stop offset="0%" stop-color="#8b1a1a" stop-opacity=".45"/><stop offset="100%" stop-color="#8b1a1a" stop-opacity="0"/></radialGradient>
      <filter id="hba-blur"><feGaussianBlur stdDeviation="3"/></filter>
      <filter id="hba-blur2"><feGaussianBlur stdDeviation="1.5"/></filter>
    </defs>
    <!-- Main colosseum wall -->
    <rect x="4" y="22" width="92" height="138" fill="url(#hba-stone)"/>
    <rect x="4" y="22" width="92" height="138" fill="none" stroke="#3a2010" stroke-width=".8"/>
    <!-- Battle damage cracks -->
    <path d="M15,50 Q18,62 14,75" fill="none" stroke="#120804" stroke-width="1" opacity=".5"/>
    <path d="M80,40 Q83,55 78,68" fill="none" stroke="#120804" stroke-width=".8" opacity=".4"/>
    <path d="M55,90 Q58,100 54,108" fill="none" stroke="#120804" stroke-width=".8" opacity=".35"/>
    <!-- Three gothic arches in row -->
    <!-- Arch 1 left -->
    <rect x="10" y="55" width="22" height="85" rx="0" fill="#0e0608"/>
    <path d="M10,78 Q21,50 32,78" fill="#0a0406" stroke="#2a1008" stroke-width="1"/>
    <ellipse cx="21" cy="95" rx="8" ry="20" fill="url(#hba-inner1)" filter="url(#hba-blur2)"/>
    <!-- Arch 2 center -->
    <rect x="39" y="55" width="22" height="85" rx="0" fill="#0e0608"/>
    <path d="M39,78 Q50,50 61,78" fill="#0a0406" stroke="#2a1008" stroke-width="1"/>
    <ellipse cx="50" cy="95" rx="8" ry="20" fill="url(#hba-inner2)" filter="url(#hba-blur2)"/>
    <!-- Arch 3 right -->
    <rect x="68" y="55" width="22" height="85" rx="0" fill="#0e0608"/>
    <path d="M68,78 Q79,50 90,78" fill="#0a0406" stroke="#2a1008" stroke-width="1"/>
    <ellipse cx="79" cy="95" rx="8" ry="20" fill="url(#hba-inner1)" filter="url(#hba-blur2)"/>
    <!-- Arch pillars between -->
    <rect x="32" y="55" width="7" height="110" fill="url(#hba-stone2)" stroke="#2a1008" stroke-width=".5"/>
    <rect x="61" y="55" width="7" height="110" fill="url(#hba-stone2)" stroke="#2a1008" stroke-width=".5"/>
    <!-- Torch brackets between arches -->
    <line x1="35" y1="48" x2="35" y2="58" stroke="#2a1808" stroke-width="1.5"/>
    <rect x="31" y="40" width="8" height="10" rx="1" fill="#2a1808" stroke="#3a2810" stroke-width=".5"/>
    <rect x="32" y="41" width="6" height="8" rx="1" fill="#ff5500" opacity=".3"/>
    <ellipse cx="35" cy="58" rx="9" ry="5" fill="#ff6600" opacity=".14" filter="url(#hba-blur2)"/>
    <line x1="65" y1="48" x2="65" y2="58" stroke="#2a1808" stroke-width="1.5"/>
    <rect x="61" y="40" width="8" height="10" rx="1" fill="#2a1808" stroke="#3a2810" stroke-width=".5"/>
    <rect x="62" y="41" width="6" height="8" rx="1" fill="#ff5500" opacity=".3"/>
    <ellipse cx="65" cy="58" rx="9" ry="5" fill="#ff6600" opacity=".14" filter="url(#hba-blur2)"/>
    <!-- Stone block rows facade -->
    <line x1="4" y1="45" x2="96" y2="45" stroke="#160c04" stroke-width=".7" opacity=".5"/>
    <line x1="4" y1="125" x2="96" y2="125" stroke="#160c04" stroke-width=".7" opacity=".5"/>
    <!-- Banners hanging from top -->
    <rect x="18" y="22" width="10" height="22" rx="1" fill="#6a0808" stroke="#8b1a1a" stroke-width=".6"/>
    <line x1="23" y1="24" x2="23" y2="42" stroke="#8b1a1a" stroke-width=".7" opacity=".5"/>
    <rect x="72" y="22" width="10" height="22" rx="1" fill="#6a0808" stroke="#8b1a1a" stroke-width=".6"/>
    <line x1="77" y1="24" x2="77" y2="42" stroke="#8b1a1a" stroke-width=".7" opacity=".5"/>
    <!-- Red ground glow pool -->
    <ellipse cx="50" cy="158" rx="42" ry="10" fill="url(#hba-glow)" filter="url(#hba-blur)"/>
    <ellipse cx="50" cy="156" rx="24" ry="7" fill="#c0392b" opacity=".18" filter="url(#hba-blur2)"/>
    <!-- Ground shadow -->
    <ellipse cx="50" cy="160" rx="44" ry="8" fill="url(#hba-shadow)" filter="url(#hba-blur2)"/>
  </svg>`,

};

// ── Inject building art into DOM ────────────────────────────────────────────
function _injectBuildingArt() {
  Object.entries(HUB_BUILDING_ART).forEach(([key, svg]) => {
    const el = document.querySelector(`#hub-b-${key} .hub-b-art`);
    if (el) el.innerHTML = svg;
  });
}


let _hubCdIntervals = [];

// ── Time-of-day ambient atmosphere ──────────────────────────────────────────

function applyTimeOfDay() {
  const h = new Date().getHours();
  const tod = h >= 5 && h < 10 ? 'dawn' : h >= 10 && h < 17 ? 'day' : h >= 17 && h < 21 ? 'dusk' : 'night';
  const el = document.querySelector('.hub-panorama');
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

  // A.9 — district cards + ambient particles
  renderDistrictCards();
  initHubParticles(15);
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

// ── A.9 District Cards ───────────────────────────────────────────────────────

const DISTRICTS = [
  { id: 'quests',  icon: '📜', name: 'Tabule Úkolů',   desc: 'Přijmi výzvu, vydělej zlato.',       badge: null,      cls: '' },
  { id: 'dungeon', icon: '⚔️', name: 'Gauntlet',        desc: 'Vstup do dungeonu. Nebo nevcházej.', badge: 'HC ONLY', cls: 'hub-district-card--gauntlet' },
  { id: 'arena',   icon: '🏟', name: 'Aréna',           desc: 'Boj bez sázky o život.',             badge: null,      cls: '' },
  { id: 'market',  icon: '⚖️', name: 'Tržiště',         desc: 'Nakup. Prodej. Přežij.',             badge: null,      cls: '' },
  { id: 'guild',   icon: '⚜️', name: 'Cech',            desc: 'Síla ve společenství.',              badge: null,      cls: '' },
  { id: 'profile', icon: '📖', name: 'Kodex',           desc: 'Tvůj příběh. Tvůj build.',           badge: null,      cls: '' },
];

function renderDistrictCards() {
  const container = document.getElementById('hub-districts');
  if (!container) return;

  container.innerHTML = '';
  const grid = document.createElement('div');
  grid.className = 'hub-district-grid';

  DISTRICTS.forEach(d => {
    const card = document.createElement('div');
    card.className = 'hub-district-card' + (d.cls ? ' ' + d.cls : '');
    card.setAttribute('role', 'button');
    card.setAttribute('tabindex', '0');

    const icon = document.createElement('span');
    icon.className = 'hub-district-icon';
    icon.textContent = d.icon;

    const name = document.createElement('div');
    name.className = 'hub-district-name';
    name.textContent = d.name;

    const desc = document.createElement('div');
    desc.className = 'hub-district-desc';
    desc.textContent = d.desc;

    card.appendChild(icon);
    card.appendChild(name);
    card.appendChild(desc);

    if (d.badge) {
      const badge = document.createElement('div');
      badge.className = 'hub-district-badge';
      badge.textContent = d.badge;
      card.appendChild(badge);
    }

    const pageId = d.id === 'dungeon' ? 'dungeons' : d.id;
    card.addEventListener('click', () => {
      if (pageId === 'dungeons') {
        showDungeonPage();
      } else {
        showPage(pageId);
      }
    });
    card.addEventListener('keydown', e => {
      if (e.key === 'Enter' || e.key === ' ') card.click();
    });

    grid.appendChild(card);
  });

  container.appendChild(grid);
}

// ── A.9 Ambient Particles ────────────────────────────────────────────────────

function initHubParticles(count) {
  const n = count || 15;
  const container = document.querySelector('.hub-particles');
  if (!container) return;

  // Clear any previous particles to avoid duplication on re-init
  container.innerHTML = '';

  for (let i = 0; i < n; i++) {
    const p = document.createElement('div');
    const isEmber = Math.random() > .45;
    p.className = 'hub-particle hub-particle--' + (isEmber ? 'ember' : 'ash');

    const size    = 2 + Math.random() * 3;                   // 2-5px
    const dur     = 8 + Math.random() * 12;                  // 8-20s
    const delay   = -(Math.random() * 10);                   // 0-10s (negative = already running)
    const left    = Math.random() * 100;                     // 0-100%
    const opacity = .2 + Math.random() * .4;                 // 0.2-0.6
    const drift   = (Math.random() - .5) * 80;               // -40 to +40px

    p.style.cssText = [
      `width:${size}px`,
      `height:${size}px`,
      `left:${left}%`,
      `animation-duration:${dur}s`,
      `animation-delay:${delay}s`,
      `--p-opacity:${opacity.toFixed(2)}`,
      `--p-drift:${drift.toFixed(0)}px`,
    ].join(';');

    container.appendChild(p);
  }
}

