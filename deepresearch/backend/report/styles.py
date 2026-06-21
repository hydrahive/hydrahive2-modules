"""Editorial-Magazin-CSS für den Report (an odysseus' visual_report angelehnt)."""
from __future__ import annotations

# Filmkorn: inline SVG feTurbulence als data-URI (das, was es nicht flach wirken lässt).
_GRAIN = (
    "url(\"data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='140' "
    "height='140'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' "
    "baseFrequency='0.82' numOctaves='2' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect "
    "width='100%25' height='100%25' filter='url(%23n)'/%3E%3C/svg%3E\")"
)

CSS = """
:root {
  --font-display: 'Charter','Iowan Old Style','Palatino Linotype',Georgia,serif;
  --font-body: system-ui,-apple-system,'Segoe UI',Roboto,sans-serif;
  --font-mono: ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;
  --bg:#fbf9f4; --surface:#ffffff; --surface-alt:#f1ede4;
  --text:#1a1817; --text-dim:#5a5651; --text-muted:#8a8580; --line:#e4ddd0;
  --accent:#b8543a; --accent-light:#d97a5e; --gold:#c9952e;
  --aurora-a:rgba(184,84,58,.12); --aurora-b:rgba(201,149,46,.10); --aurora-c:rgba(64,98,128,.08);
  --radius:14px; --shadow:0 6px 30px rgba(40,30,20,.09); --max-w:760px;
}
@media (prefers-color-scheme:dark){:root{
  --bg:#131214; --surface:#1c1a1e; --surface-alt:#26232a;
  --text:#ece8e2; --text-dim:#b3ada6; --text-muted:#7c766f; --line:#2e2b31;
  --accent:#e88f73; --accent-light:#f0a98f; --gold:#e8c05a;
  --aurora-a:rgba(232,143,115,.10); --aurora-b:rgba(232,192,90,.08); --aurora-c:rgba(120,150,190,.08);
  --shadow:0 6px 34px rgba(0,0,0,.5);
}}
*{box-sizing:border-box}
html{scroll-behavior:smooth}
body{
  margin:0; background:var(--bg); color:var(--text);
  font-family:var(--font-body); font-size:17px; line-height:1.75;
  font-feature-settings:'ss01','cv11'; -webkit-font-smoothing:antialiased;
}
body::before{
  content:''; position:fixed; inset:-20%; z-index:-2; filter:blur(22px);
  background:
    radial-gradient(40% 40% at 18% 22%, var(--aurora-a), transparent 70%),
    radial-gradient(38% 38% at 82% 30%, var(--aurora-b), transparent 70%),
    radial-gradient(45% 45% at 50% 88%, var(--aurora-c), transparent 70%);
  animation:aurora 28s ease-in-out infinite alternate;
}
body::after{
  content:''; position:fixed; inset:0; z-index:-1; pointer-events:none;
  background-image:__GRAIN__; background-size:140px 140px;
  opacity:.05; mix-blend-mode:overlay;
}
@keyframes aurora{from{transform:translate3d(-2%,-1%,0) scale(1)}to{transform:translate3d(3%,2%,0) scale(1.08)}}
@media (prefers-reduced-motion:reduce){body::before{animation:none}}

.wrap{max-width:1100px; margin:0 auto; padding:4rem 1.5rem 6rem}
.hero{margin-bottom:2.5rem}
.eyebrow{font-family:var(--font-mono); text-transform:uppercase; letter-spacing:.28em;
  font-size:.7rem; color:var(--accent); margin:0 0 1rem}
.hero h1{font-family:var(--font-display); font-weight:600; letter-spacing:-.02em;
  font-size:clamp(2rem,4.6vw,3.1rem); line-height:1.1; margin:0 0 1.2rem;
  font-variation-settings:'opsz' 120,'SOFT' 50}
.hero-img{width:100%; max-height:380px; object-fit:cover; border-radius:var(--radius);
  box-shadow:var(--shadow); margin:.5rem 0 1.5rem}
.stats{display:flex; flex-wrap:wrap; gap:1.4rem; padding:1rem 1.2rem; margin-bottom:.5rem;
  background:var(--surface); border:1px solid var(--line); border-radius:var(--radius)}
.stat b{display:block; font-family:var(--font-display); font-size:1.25rem; color:var(--accent)}
.stat span{font-family:var(--font-mono); font-size:.66rem; text-transform:uppercase;
  letter-spacing:.12em; color:var(--text-muted)}

.layout{display:grid; grid-template-columns:200px minmax(0,1fr); gap:2.5rem; margin-top:2.5rem}
@media (max-width:900px){.layout{grid-template-columns:1fr} .toc{display:none}}
.toc{position:sticky; top:2rem; align-self:start; font-size:.85rem}
.toc-title{font-family:var(--font-mono); text-transform:uppercase; letter-spacing:.14em;
  font-size:.62rem; color:var(--text-muted); margin-bottom:.7rem}
.toc a{display:block; padding:.25rem 0 .25rem .7rem; color:var(--text-dim);
  border-left:2px solid var(--line); text-decoration:none; transition:.15s}
.toc a.lvl3{padding-left:1.4rem; font-size:.8rem}
.toc a:hover{color:var(--text)}
.toc a.active{color:var(--accent); border-left-color:var(--accent)}

.content{max-width:var(--max-w)}
.content h2{font-family:var(--font-display); font-weight:600; font-size:1.7rem;
  letter-spacing:-.015em; margin:2.6rem 0 1rem; padding-top:.3rem}
.content h3{font-family:var(--font-display); font-weight:600; font-size:1.28rem; margin:1.8rem 0 .7rem}
.content p{margin:0 0 1.15rem}
.content a{color:var(--accent); text-decoration:none; border-bottom:1px solid color-mix(in srgb,var(--accent) 35%,transparent)}
.content a:hover{border-bottom-color:var(--accent)}
.content ul,.content ol{margin:0 0 1.2rem; padding-left:1.3rem}
.content li{margin:.35rem 0}
.content ul li::marker{color:var(--accent)}
.content blockquote{margin:1.4rem 0; padding:.4rem 0 .4rem 1.3rem;
  border-left:3px solid var(--accent); color:var(--text-dim); font-style:italic}
.content code{font-family:var(--font-mono); font-size:.86em; background:var(--surface-alt);
  padding:.1em .4em; border-radius:5px}
figure.shot{margin:2rem 0}
figure.shot img{width:100%; max-height:420px; object-fit:cover; border-radius:var(--radius); box-shadow:var(--shadow)}

.sources{margin-top:3rem; border-top:1px solid var(--line); padding-top:1.5rem}
.sources summary{cursor:pointer; font-family:var(--font-mono); text-transform:uppercase;
  letter-spacing:.12em; font-size:.72rem; color:var(--text-muted)}
.sources ol{margin:1rem 0 0; padding-left:1.4rem}
.sources li{margin:.4rem 0; font-size:.92rem}
.sources a{color:var(--accent); text-decoration:none}
.sources .dom{color:var(--text-muted); font-family:var(--font-mono); font-size:.8rem}
.foot{margin-top:3rem; padding-top:1.4rem; border-top:1px solid var(--line);
  font-family:var(--font-mono); font-size:.72rem; color:var(--text-muted)}

.toolbar{position:fixed; top:1rem; right:1rem; z-index:50; opacity:.65; transition:.2s}
.toolbar:hover{opacity:1}
.toolbar button{font-family:var(--font-mono); font-size:.78rem; cursor:pointer;
  background:var(--surface); color:var(--text); border:1px solid var(--line);
  border-radius:9px; padding:.45rem .8rem; box-shadow:var(--shadow)}
.toolbar button:hover{border-color:var(--accent); color:var(--accent)}
.menu{position:absolute; right:0; margin-top:.3rem; display:none; flex-direction:column;
  background:var(--surface); border:1px solid var(--line); border-radius:9px; overflow:hidden; box-shadow:var(--shadow)}
.menu.open{display:flex}
.menu button{border:0; border-radius:0; box-shadow:none; text-align:left; white-space:nowrap}
@media print{.toolbar,.toc{display:none!important} body::before,body::after{display:none}
  .layout{grid-template-columns:1fr} .wrap{padding:1rem}}
""".replace("__GRAIN__", _GRAIN)
