"""Editorial-Magazin-CSS für den Report — Design 1:1 nach odysseus' visual_report
(eigene Re-Implementierung der Tokens/Layout/Typo; AGPL → nachgebaut, nicht kopiert)."""
from __future__ import annotations

# Filmkorn: SVG feTurbulence (mit feColorMatrix getönt) als data-URI.
_GRAIN = (
    "url(\"data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' "
    "viewBox='0 0 200 200'><filter id='n'><feTurbulence type='fractalNoise' "
    "baseFrequency='0.9' numOctaves='2' stitchTiles='stitch'/><feColorMatrix "
    "values='0 0 0 0 0  0 0 0 0 0  0 0 0 0 0  0 0 0 0.32 0'/></filter><rect "
    "width='100%25' height='100%25' filter='url(%23n)'/></svg>\")"
)

CSS = """
*,*::before,*::after{box-sizing:border-box;margin:0;padding:0}
:root{
  --font-display:'Charter','Iowan Old Style',Georgia,serif;
  --font-body:system-ui,-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;
  --font-mono:ui-monospace,SFMono-Regular,Menlo,Monaco,Consolas,monospace;
  --bg:#fbf9f4; --bg-surface:#fff; --bg-surface-alt:#f1ede4;
  --border:rgba(0,0,0,.08); --border-strong:rgba(0,0,0,.16);
  --text:#1a1817; --text-dim:#5a5651; --text-muted:#8a8580;
  --accent:#b8543a; --accent-light:#d97a5e; --accent-bg:rgba(184,84,58,.06);
  --gold:#c9952e; --gold-bg:rgba(201,149,46,.09);
  --aurora-a:rgba(184,84,58,.10); --aurora-b:rgba(201,149,46,.08); --aurora-c:rgba(64,98,128,.07);
  --radius:12px; --shadow-sm:0 1px 3px rgba(0,0,0,.05); --shadow-md:0 4px 24px rgba(0,0,0,.07); --max-w:760px;
}
@media (prefers-color-scheme:dark){:root{
  --bg:#131214; --bg-surface:#1c1a1e; --bg-surface-alt:#25232a;
  --border:rgba(255,255,255,.07); --border-strong:rgba(255,255,255,.16);
  --text:#ece8e2; --text-dim:#a8a39c; --text-muted:#6f6b66;
  --accent:#e88f73; --accent-light:#f4ad95; --accent-bg:rgba(232,143,115,.09);
  --gold:#e8c05a; --gold-bg:rgba(232,192,90,.09);
  --aurora-a:rgba(232,143,115,.13); --aurora-b:rgba(232,192,90,.09); --aurora-c:rgba(125,180,224,.10);
  --shadow-sm:0 1px 3px rgba(0,0,0,.4); --shadow-md:0 4px 28px rgba(0,0,0,.55);
}}
html{scroll-behavior:smooth;scroll-padding-top:4rem}
body{font-family:var(--font-body);background:var(--bg);color:var(--text);line-height:1.75;
  font-size:17px;font-feature-settings:'ss01','cv11';-webkit-font-smoothing:antialiased;
  text-rendering:optimizeLegibility;position:relative;min-height:100vh}
body::before{content:'';position:fixed;inset:-20vh -20vw;z-index:-2;filter:blur(20px);pointer-events:none;
  background:
    radial-gradient(40vw 50vh at 18% 22%,var(--aurora-a) 0%,transparent 60%),
    radial-gradient(45vw 55vh at 82% 12%,var(--aurora-b) 0%,transparent 65%),
    radial-gradient(55vw 60vh at 50% 88%,var(--aurora-c) 0%,transparent 70%);
  animation:aurora-drift 28s ease-in-out infinite alternate}
body::after{content:'';position:fixed;inset:0;z-index:-1;pointer-events:none;
  background-image:__GRAIN__;opacity:.045;mix-blend-mode:overlay}
@keyframes aurora-drift{0%{transform:translate3d(0,0,0) scale(1)}50%{transform:translate3d(2vw,-1vh,0) scale(1.04)}100%{transform:translate3d(-1vw,1.5vh,0) scale(1.02)}}
@media (prefers-reduced-motion:reduce){body::before{animation:none}}

.toolbar{position:fixed;top:1rem;right:1rem;z-index:100;display:flex;gap:.4rem;opacity:.7;transition:opacity .2s}
.toolbar:hover{opacity:1}
.toolbar button{display:inline-flex;align-items:center;gap:5px;padding:6px 14px;border:1px solid var(--border-strong);
  border-radius:8px;background:var(--bg-surface);color:var(--text);font-family:inherit;font-size:.78rem;font-weight:500;
  cursor:pointer;box-shadow:var(--shadow-sm)}
.toolbar button:hover{background:var(--bg-surface-alt)}
.dropdown{position:relative}
.menu{display:none;position:absolute;top:calc(100% + 4px);right:0;background:var(--bg-surface);
  border:1px solid var(--border-strong);border-radius:8px;box-shadow:var(--shadow-md);overflow:hidden;min-width:150px}
.menu.open{display:block}
.menu button{display:block;width:100%;padding:8px 14px;border:none;background:none;color:var(--text);
  font-family:inherit;font-size:.8rem;text-align:left;cursor:pointer}
.menu button:hover{background:var(--bg-surface-alt)}

.hero{position:relative;padding:5.5rem 2rem 2.5rem;text-align:center;overflow:hidden}
.hero::before{content:'';position:absolute;inset:0;pointer-events:none;
  background:radial-gradient(ellipse 70% 60% at 50% 40%,color-mix(in srgb,var(--accent) 10%,transparent) 0%,transparent 70%)}
.hero::after{content:'';position:absolute;left:50%;bottom:0;width:min(60%,320px);height:1px;transform:translateX(-50%);
  background:linear-gradient(90deg,transparent,var(--border-strong),transparent)}
.hero-label{position:relative;text-transform:uppercase;letter-spacing:.28em;font-size:.68rem;font-weight:600;
  color:var(--accent);opacity:.85;margin-bottom:1.4rem}
.hero h1{position:relative;font-family:var(--font-display);font-size:clamp(2rem,4.5vw,3rem);font-weight:600;
  font-variation-settings:'opsz' 120,'SOFT' 50;line-height:1.15;max-width:720px;margin:0 auto;letter-spacing:-.02em}
.hero-image{max-width:var(--max-w);margin:-2rem auto 0;position:relative;z-index:1;padding:0 2rem}
.hero-image img{width:100%;max-height:360px;object-fit:cover;border-radius:var(--radius);box-shadow:var(--shadow-md);display:block}
.section-image{margin:1.5rem 0}
.section-image img{width:100%;max-height:300px;object-fit:cover;border-radius:var(--radius);box-shadow:var(--shadow-sm);display:block}

.stats-bar{display:flex;justify-content:center;gap:1.5rem;flex-wrap:wrap;padding:.9rem 2rem;background:var(--bg-surface);
  border-bottom:1px solid var(--border);font-size:.82rem;color:var(--text-dim)}
.stat{display:flex;align-items:center;gap:.35rem}
.stat-value{font-weight:600;color:var(--text)}

.layout{display:grid;grid-template-columns:200px 1fr;max-width:calc(var(--max-w) + 260px);margin:0 auto}
@media (max-width:900px){.layout{grid-template-columns:1fr}.toc-sidebar{display:none}}
.toc-sidebar{position:sticky;top:0;height:100vh;overflow-y:auto;padding:3.2rem .8rem 2rem 1.4rem;
  border-right:1px solid var(--border);font-size:.78rem}
.toc-sidebar a{position:relative;display:block;color:var(--text-dim);text-decoration:none;
  padding:.42rem .7rem .42rem .85rem;margin:1px 0;border-radius:6px;line-height:1.4;
  transition:color .18s,background .18s,padding-left .18s}
.toc-sidebar a::before{content:'';position:absolute;left:0;top:50%;width:2px;height:0;background:var(--accent);
  transform:translateY(-50%);border-radius:1px;transition:height .18s,opacity .18s;opacity:0}
.toc-sidebar a:hover{color:var(--text);background:var(--accent-bg);padding-left:1rem}
.toc-sidebar a:hover::before{height:60%;opacity:1}
.toc-sidebar a.active{color:var(--accent);font-weight:600;background:var(--accent-bg)}
.toc-sidebar a.active::before{height:80%;opacity:1}
.toc-sidebar a.depth-3{padding-left:1.3rem;font-size:.72rem;color:var(--text-muted)}

.content{max-width:var(--max-w);padding:3rem 2.5rem 4rem}
.content h2{font-family:var(--font-display);font-size:clamp(1.55rem,2.4vw,1.85rem);font-weight:600;
  font-variation-settings:'opsz' 96,'SOFT' 50;margin:3rem 0 1rem;padding-bottom:.55rem;border-bottom:1px solid transparent;
  border-image:linear-gradient(90deg,var(--accent) 0%,transparent 65%) 1;letter-spacing:-.022em;line-height:1.2}
.content h2:first-child{margin-top:0}
.content h3{font-family:var(--font-display);font-size:1.22rem;font-weight:600;margin:2.2rem 0 .6rem;letter-spacing:-.015em}
.content p{margin-bottom:1.1rem}
.content>p:first-of-type::first-letter,.content>h2:first-child + p::first-letter{
  font-family:var(--font-display);font-weight:700;font-variation-settings:'opsz' 144;font-size:3.6em;
  line-height:.85;float:left;margin:.15em .12em 0 -.04em;color:var(--accent)}
.content a{color:var(--accent);text-decoration:underline;text-decoration-color:color-mix(in srgb,var(--accent) 35%,transparent);
  text-decoration-thickness:1.5px;text-underline-offset:3px;transition:text-decoration-color .15s,color .15s}
.content a:hover{text-decoration-color:var(--accent);color:var(--accent-light)}
.content ul,.content ol{margin:0 0 1.1rem 1.6rem}
.content li{margin-bottom:.4rem}
.content li::marker{color:var(--accent)}
.content blockquote{position:relative;border-left:3px solid var(--gold);background:var(--gold-bg);
  padding:1.1rem 1.4rem 1.1rem 2.6rem;margin:1.5rem 0;border-radius:0 var(--radius) var(--radius) 0;
  font-family:var(--font-display);font-style:italic;font-size:1.05rem;line-height:1.55}
.content blockquote::before{content:'\\201C';position:absolute;left:.5rem;top:.3rem;font-family:var(--font-display);
  font-size:3rem;font-style:normal;color:var(--gold);opacity:.5;line-height:1}
.content code{font-family:var(--font-mono);font-size:.86em;background:var(--bg-surface-alt);padding:.15em .4em;border-radius:4px}

.sources-panel{margin-top:3rem;border-top:2px solid var(--border);padding-top:1.5rem}
.sources-panel summary{display:flex;align-items:center;gap:.5rem;cursor:pointer;font-size:1rem;font-weight:600;
  color:var(--text);padding:.5rem 0;list-style:none;user-select:none}
.sources-panel summary::-webkit-details-marker{display:none}
.sources-panel summary::before{content:'\\25B6';font-size:.65em;color:var(--text-muted);transition:transform .2s}
.sources-panel details[open] summary::before{transform:rotate(90deg)}
.sources-list a{display:flex;align-items:baseline;gap:.5rem;padding:.35rem 0;font-size:.85rem;color:var(--text);
  text-decoration:none;transition:color .15s}
.sources-list a:hover{color:var(--accent)}
.snum{color:var(--text-muted);font-size:.75rem;min-width:1.5rem;text-align:right;flex-shrink:0}
.sdomain{color:var(--text-muted);font-size:.75rem;margin-left:auto;flex-shrink:0}
.report-footer{text-align:center;padding:2rem;font-size:.75rem;color:var(--text-muted);border-top:1px solid var(--border);margin-top:2rem}

@media (prefers-reduced-motion:no-preference){
  .content h2,.content h3,.content p,.content ul,.content ol,.content blockquote,.section-image{animation:fadeUp .4s ease both}
  @keyframes fadeUp{from{opacity:0;transform:translateY(8px)}to{opacity:1;transform:translateY(0)}}
}
@media print{.toc-sidebar,.toolbar{display:none!important}.layout{grid-template-columns:1fr}
  .hero{-webkit-print-color-adjust:exact;print-color-adjust:exact}body::before,body::after{display:none}}
""".replace("__GRAIN__", _GRAIN)
