"""Erzeugt die Konfiguration für Icecast und Liquidsoap aus den Sender-Einstellungen (PLAN-E2.md).

Reine Textbausteine ohne Seiteneffekte – geschrieben werden sie von control.write_config(). Icecast lauscht nur auf
127.0.0.1; Passwörter kommen aus secrets.env und stehen nie in Logs. Liquidsoap 2.2 (Ubuntu 24.04) und 2.4 (26.04)
unterscheiden sich bei protocol.add, null und on_metadata – das Skript wählt per %ifversion beim Laden.
"""
from __future__ import annotations

from xml.sax.saxutils import escape

ICECAST_PORT = 8810
MOUNT = "/radio.mp3"


def _liq(s: str) -> str:
    """Zeichenkette für Liquidsoap: nur " und \\ maskieren, keine Zeilenumbrüche."""
    return '"' + str(s).replace("\\", "\\\\").replace('"', '\\"').replace("\n", " ") + '"'


def _fallback(path: str) -> str:
    """Pausenzeichen in Schleife; fehlt die Datei, Stille (sonst startet Liquidsoap gar nicht)."""
    if not path:
        return 'blank(id="notschleife")'
    return f'amplify(0.3, single(id="notschleife", {_liq(path)}))'


def icecast_xml(*, source_password: str, admin_password: str, max_listeners: int, name: str, log_dir: str) -> str:
    e = escape
    return f"""<icecast>
  <location>{e(name)}</location>
  <admin>radiostream@localhost</admin>
  <limits>
    <clients>{max_listeners + 5}</clients>
    <sources>2</sources>
    <queue-size>524288</queue-size>
    <client-timeout>30</client-timeout>
    <header-timeout>15</header-timeout>
    <source-timeout>10</source-timeout>
    <burst-size>65535</burst-size>
  </limits>
  <authentication>
    <source-password>{e(source_password)}</source-password>
    <admin-user>admin</admin-user>
    <admin-password>{e(admin_password)}</admin-password>
  </authentication>
  <hostname>localhost</hostname>
  <listen-socket>
    <port>{ICECAST_PORT}</port>
    <bind-address>127.0.0.1</bind-address>
  </listen-socket>
  <mount type="normal">
    <mount-name>{MOUNT}</mount-name>
    <max-listeners>{max_listeners}</max-listeners>
    <public>0</public>
    <stream-name>{e(name)}</stream-name>
  </mount>
  <fileserve>1</fileserve>
  <paths>
    <basedir>/usr/share/icecast2</basedir>
    <logdir>{e(log_dir)}</logdir>
    <webroot>/usr/share/icecast2/web</webroot>
    <adminroot>/usr/share/icecast2/admin</adminroot>
  </paths>
  <logging>
    <accesslog>-</accesslog>
    <errorlog>-</errorlog>
    <loglevel>2</loglevel>
  </logging>
  <security>
    <chroot>0</chroot>
  </security>
</icecast>
"""


def liquidsoap_script(*, feed_base: str, feed_key: str, source_password: str, name: str, subtitle: str,
                      fallback_file: str, control_socket: str, now_file: str) -> str:
    """Programm: Modul fragt den Titel (request.dynamic), fester Lautheitswert je Titel, weiche Überblendung, MP3 192k an Icecast.

    Fehlt der nächste Titel (NAS weg, Modul neu gestartet), läuft eine leise Notschleife statt Stille."""
    return f"""# Erzeugt von HydraHive Radiostream – nicht von Hand ändern.
settings.log.stdout.set(true)
settings.log.file.set(false)
settings.log.level.set(3)
settings.server.socket.set(true)
settings.server.socket.path.set({_liq(control_socket)})
settings.server.socket.permissions.set(384)

feed_key = {_liq(feed_key)}
feed_base = {_liq(feed_base)}

# radiostream:<track_id>.<mp3|flac> → Datei mit Feed-Schlüssel in eine Temp-Datei laden (wird danach gelöscht).
def fetch_file(rlog, arg) =
  parts = string.split(separator="[.]", arg)
  ext = list.nth(default="mp3", parts, 1)
  tmp = file.temp("radiostream", ".#{{ext}}")
  ok = ref(true)
  writer = file.write.stream(tmp)
  try
    http.get.stream(headers=[("X-Radiostream-Feed", feed_key)], timeout=60.0,
      "#{{feed_base}}/feed/file/#{{list.hd(default='', parts)}}", on_body_data=writer)
  catch err do
    rlog("Radiostream: Titel nicht ladbar: #{{err.kind}}")
    ok := false
  end
  if not ok() then file.remove(tmp) end
  (ok(), tmp)
end
# 2.3+ erwartet string? (null = kein Titel), 2.2 eine Liste.
%ifversion >= 2.3.0
def fetch_track(~rlog, ~maxtime, arg) =
  ignore(maxtime)
  let (ok, tmp) = fetch_file(rlog, arg)
  if ok then tmp else null end
end
%else
def fetch_track(~rlog, ~maxtime, arg) =
  ignore(maxtime)
  let (ok, tmp) = fetch_file(rlog, arg)
  if ok then [tmp] else [] end
end
%endif
protocol.add("radiostream", fetch_track, temporary=true, doc="Radiostream-Titel", syntax="radiostream:<id>.<ext>")

%ifversion >= 2.3.0
def no_request() = null end
%else
def no_request() = null() end
%endif

def next_track() =
  r = http.get(headers=[("X-Radiostream-Feed", feed_key)], timeout=10.0, "#{{feed_base}}/feed/next")
  if r.status_code == 200 then
    uri = string.trim(r)
    if uri == "" then no_request() else request.create(uri) end
  else
    log.important("Radiostream: kein nächster Titel (HTTP #{{r.status_code}})")
    no_request()
  end
end

auto = request.dynamic(id="autodj", retry_delay=3.0, prefetch=1, next_track)
# Programm geändert („Als Nächstes“, andere Playlist): vorgeladenen Titel verwerfen und seine Spiel-Kennung (rs_play)
# nennen – das Modul nimmt ihn zurück (preload.py). Danach fragt Liquidsoap sofort neu. Geht auf 2.2 und 2.4.
def flush(_) =
  q = auto.queue()
  auto.set_queue([])
  def play_id(r) =
    m = request.metadata(r)
    m["rs_play"]
  end
  string.concat(separator=",", list.map(play_id, q))
end
server.register(namespace="autodj", description="Vorgeladenen Titel verwerfen", "flush", flush)
# Lautheit je Titel als fester Wert (liq_amplify aus /feed/next, loudness.py) – keine laufende Nachregelung, die am
# Titelende das Ausklingen hochzieht. Titel ohne Wert laufen unverändert.
auto = amplify(1.0, override="liq_amplify", auto)
auto = crossfade(duration=3.0, fade_out=3.0, fade_in=1.0, auto)
notschleife = {_fallback(fallback_file)}
radio = fallback(id="programm", track_sensitive=false, [auto, notschleife])
radio = mksafe(radio)

# „Jetzt läuft“ für die Hörer-Seite: nur Künstler und Titel, dazu die letzten 10. An den Metadaten, nicht am
# Titelwechsel – nach der Überblendung kommt der neue Titel nur als Metadaten an (Probe hydratest 29.10.).
# Leere Meldungen (Notschleife) überschreiben nichts. Die Datei ist für nginx lesbar (0644).
zuletzt = ref([])
def write_now(m) =
  if m["title"] != "" or m["artist"] != "" then
    jetzt = {{artist=m["artist"], title=m["title"]}}
    file.write(perms=420, data=json.stringify({{artist=jetzt.artist, title=jetzt.title, recent=zuletzt()}}),
      {_liq(now_file)})
    zuletzt := list.prefix(10, list.add(jetzt, zuletzt()))
  end
end
%ifversion >= 2.3.0
radio.on_metadata(synchronous=false, write_now)
%else
radio = source.on_metadata(radio, write_now)
%endif

output.icecast(%mp3(bitrate=192), id="sender",
  host="127.0.0.1", port={ICECAST_PORT}, password={_liq(source_password)}, mount={_liq(MOUNT)},
  name={_liq(name)}, description={_liq(subtitle)}, public=false, radio)
"""
