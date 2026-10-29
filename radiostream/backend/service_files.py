"""Erzeugt die Konfiguration für Icecast und Liquidsoap aus den Sender-Einstellungen (PLAN-E2.md).

Reine Textbausteine ohne Seiteneffekte – geschrieben werden sie von control.write_config(). Icecast lauscht nur auf
127.0.0.1; Passwörter kommen aus secrets.env und stehen nie in Logs. Liquidsoap nutzt nur Funktionen, die es in 2.2
(Ubuntu 24.04) und 2.4 (26.04) gibt.
"""
from __future__ import annotations

from xml.sax.saxutils import escape

ICECAST_PORT = 8810
MOUNT = "/radio.mp3"


def _liq(s: str) -> str:
    """Zeichenkette für Liquidsoap: nur " und \\ maskieren, keine Zeilenumbrüche."""
    return '"' + str(s).replace("\\", "\\\\").replace('"', '\\"').replace("\n", " ") + '"'


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
    """Programm: Modul fragt den Titel (request.dynamic), gleiche Lautheit, weiche Überblendung, MP3 192k an Icecast.

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
def fetch_track(~rlog, ~maxtime, arg) =
  ignore(maxtime)
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
  if ok() then [tmp] else
    file.remove(tmp)
    []
  end
end
protocol.add("radiostream", fetch_track, temporary=true, doc="Radiostream-Titel", syntax="radiostream:<id>.<ext>")

def next_track() =
  r = http.get(headers=[("X-Radiostream-Feed", feed_key)], timeout=10.0, "#{{feed_base}}/feed/next")
  if r.status_code == 200 then
    uri = string.trim(r)
    if uri == "" then null() else request.create(uri) end
  else
    log.important("Radiostream: kein nächster Titel (HTTP #{{r.status_code}})")
    null()
  end
end

auto = request.dynamic(id="autodj", retry_delay=3.0, prefetch=3, next_track)
auto = normalize(auto)
auto = crossfade(duration=3.0, fade_out=3.0, fade_in=1.0, auto)
notschleife = amplify(0.3, single(id="notschleife", {_liq(fallback_file)}))
radio = fallback(id="programm", track_sensitive=false, [auto, notschleife])
radio = mksafe(radio)

# „Jetzt läuft“ für die Hörer-Seite: nur Künstler und Titel. An den Metadaten, nicht am Titelwechsel – nach der
# Überblendung kommt der neue Titel nur als Metadaten an (Probe hydratest 29.10.). Leere Meldungen überschreiben nichts.
def write_now(m) =
  if m["title"] != "" or m["artist"] != "" then
    file.write(data=json.stringify({{artist=m["artist"], title=m["title"]}}), {_liq(now_file)})
  end
end
radio = source.on_metadata(radio, write_now)

output.icecast(%mp3(bitrate=192), id="sender",
  host="127.0.0.1", port={ICECAST_PORT}, password={_liq(source_password)}, mount={_liq(MOUNT)},
  name={_liq(name)}, description={_liq(subtitle)}, public=false, radio)
"""
