"""Sony-BRAVIA-Client (JSON-RPC unter http://<adresse>/sony/<dienst>, SPEC.md „Befund“).

Alle Netz-Aufrufe laufen durch _post() – in Tests ersetzt. Der Schlüssel geht nur in die Kopfzeile X-Auth-PSK und
taucht in keiner Fehlermeldung auf. Schaltende Funktionen lesen danach nach und geben den echten Zustand zurück.
"""
from __future__ import annotations

import time

import httpx

from . import matching, settings_store
from .client_errors import TVError

__all__ = ["TVError"]

_TIMEOUT = 6.0
_CACHE_SECONDS = 60.0
_MAX_STEP = 20
_cache: dict[str, tuple[float, list]] = {}


def clear_cache() -> None:
    _cache.clear()


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
    power = await _power()
    channel, program = (await _playing()) if power == "on" else (None, "")
    volume, muted = await _volume()
    return {"power": power, "channel": channel, "program": program, "volume": volume, "muted": muted,
            "model": await _model()}


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
    ch = await find_channel(query)
    await _call("avContent", "setPlayContent", {"uri": ch["uri"]})
    return await status()


def _target_volume(value: str, current: int) -> int:
    """Zielwert aus „20“, „+3“ oder „-5“. Unter 0 wird 0, über 100 wird 100."""
    v = (value or "").strip()
    sign = v[:1] if v[:1] in "+-" else ""
    digits = v[1:] if sign else v
    if not digits.isdigit():
        raise TVError("tv_volume_invalid", "Lautstärke als Zahl 0–100 oder +n/-n angeben.")
    n = int(digits)
    if sign == "+":
        return min(100, current + n)
    if sign == "-":
        return max(0, current - n)
    return min(100, n)


async def set_volume(value: str) -> dict:
    """Schutz (SPEC): nie über der Grenze aus den Einstellungen, und höchstens _MAX_STEP auf einmal – in beide
    Richtungen gemessen am angefragten Schritt, damit „-50“ nicht zufällig durchrutscht, wenn der TV leise ist."""
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
