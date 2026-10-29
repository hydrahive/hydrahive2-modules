"""Sony-BRAVIA-Client (JSON-RPC unter http://<adresse>/sony/<dienst>, SPEC.md „Befund“).

Alle Netz-Aufrufe laufen durch _post() – in Tests ersetzt. Der Schlüssel geht nur in die Kopfzeile X-Auth-PSK und
taucht in keiner Fehlermeldung auf. Schaltende Funktionen lesen danach nach und geben den echten Zustand zurück.
"""
from __future__ import annotations

import asyncio
import time

import httpx

from . import matching, settings_store
from .client_errors import TVError
from .volume import MAX_STEP as _MAX_STEP
from .volume import target as _target_volume

__all__ = ["TVError"]

_TIMEOUT = 6.0
_CACHE_SECONDS = 60.0
_SWITCH_WAIT = 1.5          # Sekunden bis zum Nachlesen; aus einer App heraus braucht der TV einen Moment
_cache: dict[str, tuple[float, list]] = {}


def clear_cache() -> None:
    _cache.clear()


async def _sleep(seconds: float) -> None:          # in Tests ersetzt
    await asyncio.sleep(seconds)


async def _post(ip: str, service: str, method: str, params: list, version: str, psk: str) -> tuple[int, dict]:
    headers = {"Content-Type": "application/json"}
    if psk:
        headers["X-Auth-PSK"] = psk
    body = {"method": method, "id": 1, "params": params, "version": version}
    async with httpx.AsyncClient(timeout=_TIMEOUT, follow_redirects=False) as http:
        r = await http.post(f"http://{ip}/sony/{service}", json=body, headers=headers)
    try:
        return r.status_code, r.json()
    except ValueError:
        return r.status_code, {"error": [r.status_code, "keine JSON-Antwort"]}


async def _call(service: str, method: str, params: dict | None = None, version: str = "1.0") -> list:
    conn = settings_store.connection()
    if conn is None:
        raise TVError("tv_not_configured", "Der Fernseher ist noch nicht eingerichtet.")
    ip, psk = conn
    try:
        status, data = await _post(ip, service, method, [params] if params is not None else [], version, psk)
    except (httpx.HTTPError, OSError, TimeoutError) as exc:
        raise TVError("tv_unreachable", f"Fernseher nicht erreichbar ({type(exc).__name__}).") from exc
    err = data.get("error") if isinstance(data, dict) else None
    if status == 404 or (err and err[0] == 404):
        raise TVError("tv_needs_restart", "Die Steuerung des Fernsehers antwortet nicht – bitte den Fernseher "
                                          "einmal ganz neu starten (Netzstecker).")
    if err and err[0] in (401, 403):
        raise TVError("tv_auth_failed", "Der Fernseher lehnt den Schlüssel ab.")
    if err and err[0] == 40005:                       # „Display Is Turned off“ (gemessen im Standby)
        raise TVError("tv_is_off", "Der Fernseher ist aus.")
    if err:
        raise TVError("tv_upstream_error", f"Fernseher meldet Fehler {err[0]} bei {method}.")
    if status >= 400:
        raise TVError("tv_upstream_error", f"Fernseher antwortet mit HTTP {status}.")
    return data.get("result") or []


async def _model() -> str:
    try:
        res = await _call("system", "getInterfaceInformation")
        return res[0].get("modelName", "") if res else ""
    except TVError:
        return ""


async def _power() -> str:
    res = await _call("system", "getPowerStatus")
    return "on" if res and res[0].get("status") == "active" else "standby"


async def _playing() -> tuple[dict | None, str]:
    try:
        res = await _call("avContent", "getPlayingContentInfo")
    except TVError as exc:
        if exc.code == "tv_upstream_error":          # Standby oder App läuft: kein Sender
            return None, ""
        raise
    if not res:
        return None, ""
    r = res[0]
    num = int(r["dispNum"]) if str(r.get("dispNum", "")).isdigit() else None
    return {"number": num, "name": r.get("title", "")}, r.get("programTitle", "")


async def _volume() -> tuple[int, bool]:
    res = await _call("audio", "getVolumeInformation")
    rows = res[0] if res else []
    spk = next((v for v in rows if v.get("target") == "speaker"), rows[0] if rows else {})
    return int(spk.get("volume", 0)), bool(spk.get("mute", False))


async def status() -> dict:
    """Im Standby fragt der TV Ton und Sender nicht ab (40005) – dann bleiben sie leer, das ist kein Fehler."""
    power = await _power()
    if power != "on":
        return {"power": power, "channel": None, "program": "", "volume": None, "muted": None,
                "model": await _model()}
    channel, program = await _playing()
    volume, muted = await _volume()
    return {"power": power, "channel": channel, "program": program, "volume": volume, "muted": muted,
            "model": await _model()}


async def _require_on() -> None:
    if await _power() != "on":
        raise TVError("tv_is_off", "Der Fernseher ist aus. Erst einschalten.")


async def test() -> dict:
    return {"ok": True, "model": await _model(), "power": await _power()}


async def channels() -> list[dict]:
    hit = _cache.get("channels")
    if hit and time.monotonic() - hit[0] < _CACHE_SECONDS:
        return hit[1]
    out: list[dict] = []
    start = 0
    while True:
        res = await _call("avContent", "getContentList", {"source": "tv:dvbt", "stIdx": start, "cnt": 50}, "1.2")
        page = res[0] if res else []
        for c in page:
            num = c.get("dispNum", "")
            out.append({"number": int(num) if str(num).isdigit() else 0, "name": c.get("title", ""),
                        "uri": c.get("uri", "")})
        if len(page) < 50 or start > 2000:
            break
        start += 50
    _cache["channels"] = (time.monotonic(), out)
    return out


async def find_channel(query: str) -> dict:
    return matching.pick_channel(await channels(), query)


async def set_channel(query: str) -> dict:
    """Umschalten und nachlesen. Gemessen am KD-60XF8305 (29.10.): Ist eine App vorne, holt der erste Befehl nur in
    den Fernsehmodus, erst der zweite wechselt den Sender. Deshalb: nachlesen, höchstens einmal wiederholen, und
    wenn der Sender danach nicht stimmt, ehrlich tv_switch_failed melden statt Erfolg vorzutäuschen."""
    ch = await find_channel(query)
    await _require_on()
    for attempt in range(2):
        await _call("avContent", "setPlayContent", {"uri": ch["uri"]})
        await _sleep(_SWITCH_WAIT)
        now = await status()
        if now["channel"] and now["channel"]["name"] == ch["name"]:
            return now
    raise TVError("tv_switch_failed", f"Der Fernseher hat nicht auf „{ch['name']}“ umgeschaltet.")


async def set_volume(value: str) -> dict:
    """Schutz (SPEC): nie über der Grenze aus den Einstellungen, und höchstens _MAX_STEP auf einmal – in beide
    Richtungen gemessen am angefragten Schritt, damit „-50“ nicht zufällig durchrutscht, wenn der TV leise ist."""
    await _require_on()
    current, _ = await _volume()
    target = _target_volume(value, current)
    v = value.strip()
    step = int(v[1:]) if v[:1] in "+-" else abs(target - current)
    limit = settings_store.volume_limit()
    if target > limit or step > _MAX_STEP:
        raise TVError("tv_volume_limit", f"Höchstens Lautstärke {limit} und höchstens {_MAX_STEP} Schritte auf einmal.")
    await _call("audio", "setAudioVolume", {"target": "speaker", "volume": str(target)})
    return await status()


async def set_mute(on: bool) -> dict:
    await _require_on()
    await _call("audio", "setAudioMute", {"status": bool(on)})
    return await status()


async def set_power(on: bool) -> dict:
    await _call("system", "setPowerStatus", {"status": bool(on)})
    return await status()


async def _app_list() -> list[dict]:
    hit = _cache.get("apps")
    if hit and time.monotonic() - hit[0] < _CACHE_SECONDS:
        return hit[1]
    res = await _call("appControl", "getApplicationList")
    out = sorted(({"name": a.get("title", ""), "uri": a.get("uri", "")} for a in (res[0] if res else [])),
                 key=lambda a: a["name"].lower())
    _cache["apps"] = (time.monotonic(), out)
    return out


async def apps() -> list[dict]:
    return [{"name": a["name"]} for a in await _app_list()]


async def start_app(name: str) -> dict:
    app = matching.pick_app(await _app_list(), name)
    await _call("appControl", "setActiveApp", {"uri": app["uri"]})
    return {"started": app["name"]}
