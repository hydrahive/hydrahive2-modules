"""Statische Hörer-Seite: HTML, CSS, JS (ohne Fremd-Dateien, ohne Inline-Skript; CSP default-src 'self').

{{NAME}} und {{SUBTITLE}} setzt listener_site.page_files() HTML-maskiert ein. Das Skript schreibt Titel nur über
textContent, nie als HTML.
"""
from __future__ import annotations

HTML = """<!doctype html>
<html lang="de">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="referrer" content="no-referrer">
<title>{{NAME}}</title>
<link rel="stylesheet" href="radio.css">
<script src="radio.js" defer></script>
</head>
<body>
<main>
  <header>
    <div class="logo" aria-hidden="true">&#x1F4FB;</div>
    <h1>{{NAME}}</h1>
    <p class="sub">{{SUBTITLE}}</p>
  </header>
  <section class="player">
    <button id="play" type="button" aria-label="Abspielen">&#x25B6;</button>
    <label class="vol">Lautstärke <input id="vol" type="range" min="0" max="1" step="0.05" value="0.8"></label>
    <audio id="audio" preload="none" src="stream.mp3"></audio>
  </section>
  <section class="now" aria-live="polite">
    <h2>Jetzt läuft</h2>
    <p id="now-title">–</p>
    <p id="now-artist"></p>
    <p id="state" class="state"></p>
  </section>
  <section class="recent">
    <h2>Zuletzt gespielt</h2>
    <ol id="recent"></ol>
  </section>
  <footer><a href="stream.m3u">In VLC oder iTunes öffnen</a></footer>
</main>
</body>
</html>
"""

CSS = """:root{color-scheme:dark;--bg:#0f1115;--fg:#e8e8ea;--muted:#9aa0aa;--acc:#f5b301}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--fg);font:16px/1.5 system-ui,sans-serif}
main{max-width:34rem;margin:0 auto;padding:2rem 1.25rem}header{text-align:center}
.logo{font-size:3rem}h1{margin:.25rem 0;font-size:1.8rem}.sub{margin:0;color:var(--muted)}
.player{display:flex;align-items:center;gap:1rem;justify-content:center;margin:2rem 0}
#play{width:4.5rem;height:4.5rem;border-radius:50%;border:0;background:var(--acc);color:#111;font-size:1.8rem;cursor:pointer}
#play.on{background:var(--fg)}.vol{display:flex;flex-direction:column;font-size:.8rem;color:var(--muted)}
.now{text-align:center}.now h2,.recent h2{font-size:.8rem;text-transform:uppercase;letter-spacing:.1em;color:var(--muted)}
#now-title{font-size:1.3rem;font-weight:600;margin:.25rem 0}#now-artist{margin:0;color:var(--muted)}
.state{font-size:.85rem;color:var(--acc);min-height:1.2em}.recent ol{padding-left:1.25rem;color:var(--muted)}
footer{margin-top:2rem;text-align:center}a{color:var(--acc)}
"""

JS = """'use strict';
(function () {
  var audio = document.getElementById('audio');
  var play = document.getElementById('play');
  var vol = document.getElementById('vol');
  var state = document.getElementById('state');
  function setText(id, t) { document.getElementById(id).textContent = t || ''; }
  play.addEventListener('click', function () {
    if (audio.paused) {
      audio.src = 'stream.mp3?' + Date.now();
      audio.play().catch(function () { state.textContent = 'Wiedergabe nicht möglich.'; });
    } else {
      audio.pause();
      audio.removeAttribute('src');
      audio.load();
    }
  });
  audio.addEventListener('playing', function () { play.classList.add('on'); play.textContent = '\\u275A\\u275A';
    play.setAttribute('aria-label', 'Anhalten'); state.textContent = ''; });
  audio.addEventListener('pause', function () { play.classList.remove('on'); play.textContent = '\\u25B6';
    play.setAttribute('aria-label', 'Abspielen'); });
  audio.addEventListener('waiting', function () { state.textContent = 'Lädt …'; });
  audio.addEventListener('error', function () { if (audio.getAttribute('src')) state.textContent = 'Sender gerade nicht erreichbar.'; });
  audio.volume = Number(vol.value);
  vol.addEventListener('input', function () { audio.volume = Number(vol.value); });
  function load() {
    fetch('jetzt', { cache: 'no-store' }).then(function (r) { return r.ok ? r.json() : null; }).then(function (d) {
      if (!d || typeof d !== 'object') return;
      setText('now-title', typeof d.title === 'string' && d.title ? d.title : '–');
      setText('now-artist', typeof d.artist === 'string' ? d.artist : '');
      var list = document.getElementById('recent');
      while (list.firstChild) list.removeChild(list.firstChild);
      (Array.isArray(d.recent) ? d.recent : []).slice(0, 10).forEach(function (t) {
        if (!t || typeof t !== 'object') return;
        var li = document.createElement('li');
        li.textContent = [t.artist, t.title].filter(function (x) { return typeof x === 'string' && x; }).join(' – ');
        list.appendChild(li);
      });
    }).catch(function () {});
  }
  load();
  setInterval(load, 15000);
})();
"""
