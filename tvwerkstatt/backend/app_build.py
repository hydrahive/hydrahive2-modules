"""G2: HydraHive-App im Container bauen (PLAN-APP.md). Muster: Bau des Startbildschirms (build.py, build_jobs.py).

Der Quelltext liegt im Modul (android/hydra-app) und geht als tar über stdin in den Container. Gebaut wird mit dem
geprüften Gradle-Wrapper aus cleanyourtv (Prüfsummen wie beim Startbildschirm), die JUnit-Tests laufen vorher. Danach
wird die App gelesen (Paket, Signatur, Rechte genau INTERNET, Größe, Testergebnis), geholt und mit der Prüfsumme aus dem
Container verglichen. Erst dann ersetzt sie die vorige App unter data_dir/tvwerkstatt/app/.
"""
from __future__ import annotations

import hashlib
import io
import logging
import tarfile
from pathlib import Path

from hydrahive.containers.incus_client import IncusError
from hydrahive.settings import settings

from . import build, build_jobs, container, incus, jobs, network, source, state

logger = logging.getLogger(__name__)
SRC_DIR = Path(__file__).resolve().parents[1] / "android" / "hydra-app"
PACKAGE = "io.hydrahive.app"
PERMISSIONS = "INTERNET"
MAX_SIZE = 5 * 1024 * 1024
PART = "hydra-app"
DIR = f"{source.HOME}/src/hydra-app"
APK = f"{DIR}/app/build/outputs/apk/release/app-release.apk"
LOG = f"{source.HOME}/build-logs/hydra-app.log"
_SKIP = ("build", ".gradle", ".idea")
_MARK = "__TVW__"

UNPACK_SCRIPT = f"set -eu; rm -rf {DIR}; mkdir -p {DIR}; tar -x -C {DIR} --no-same-owner -f -"
BUILD_SCRIPT = (
    f"set -u; cd {DIR}; mkdir -p {source.HOME}/build-logs; "
    f"export ANDROID_HOME={build.SDK} ANDROID_SDK_ROOT={build.SDK} GRADLE_USER_HOME={source.HOME}/.gradle; "
    f"sh {source.SRC}/launcher/gradlew -p {DIR} --no-daemon --console=plain testReleaseUnitTest assembleRelease "
    f"> {LOG} 2>&1; rc=$?; tail -n {build.LOG_LINES} {LOG}; exit $rc"
)
_TESTS = f"{DIR}/app/build/test-results/testReleaseUnitTest"
COLLECT_SCRIPT = (
    build.COLLECT_SCRIPT.replace(build.APK, APK)
    + f'; echo "{_MARK} perms=$({build.BT}/aapt2 dump permissions "$A" '
    f'| sed -n "s/^uses-permission: name=.\\([A-Za-z0-9_.]*\\).*/\\1/p" | tr \'\\n\' \',\')"; '
    f"t=0; f=0; e=0; for x in {_TESTS}/*.xml; do [ -f \"$x\" ] || continue; "
    "h=$(grep -m1 -o '<testsuite [^>]*' \"$x\"); "
    "t=$((t + $(echo \"$h\" | sed -n 's/.* tests=\"\\([0-9]*\\)\".*/\\1/p'))); "
    "f=$((f + $(echo \"$h\" | sed -n 's/.* failures=\"\\([0-9]*\\)\".*/\\1/p'))); "
    "e=$((e + $(echo \"$h\" | sed -n 's/.* errors=\"\\([0-9]*\\)\".*/\\1/p'))); done; "
    f'echo "{_MARK} tests=$t $f $e"'
)


def source_files() -> list[str]:
    """Dateien des Quelltexts (ohne Bauergebnisse, ohne Symlinks), sortiert."""
    out = []
    for p in sorted(SRC_DIR.rglob("*")):
        rel = p.relative_to(SRC_DIR)
        if any(part in _SKIP for part in rel.parts) or p.is_symlink() or not p.is_file() or p.suffix == ".apk":
            continue
        out.append(rel.as_posix())
    return out


def source_tar() -> tuple[bytes, str]:
    """tar des Quelltexts, immer gleich (Reihenfolge, Besitzer, Zeit), und Prüfsumme über Namen + Inhalt."""
    buf, h = io.BytesIO(), hashlib.sha256()
    with tarfile.open(fileobj=buf, mode="w", format=tarfile.PAX_FORMAT) as t:
        for name in source_files():
            data = (SRC_DIR / name).read_bytes()
            ti = tarfile.TarInfo(name)
            ti.size, ti.mode, ti.mtime = len(data), 0o644, 0
            t.addfile(ti, io.BytesIO(data))
            h.update(name.encode() + b"\0" + hashlib.sha256(data).digest())
    return buf.getvalue(), h.hexdigest()


def evaluate(vals: dict[str, str]) -> dict:
    """Wie build.evaluate, dazu: erwartetes Paket, Rechte genau INTERNET, Größe, Tests liefen und sind grün."""
    sha, signer, key = vals.get("sha256", ""), vals.get("signer", "").lower(), vals.get("keystore", "").lower()
    m = build._BADGING.search(vals.get("badging", ""))
    if not build._HEX64.match(sha) or not m or not vals.get("size", "").isdigit():
        raise build.TvwBuildError("tvw_build_unreadable")
    if m["pkg"] != PACKAGE:
        raise build.TvwBuildError("tvw_build_unexpected", m["pkg"])
    if not build._HEX64.match(signer) or signer != key:
        raise build.TvwBuildError("tvw_signer_mismatch")
    perms = sorted({p.removeprefix("android.permission.") for p in vals.get("perms", "").split(",") if p})
    if ",".join(perms) != PERMISSIONS:
        raise build.TvwBuildError("tvw_app_build_perms", ",".join(perms)[:200])
    if int(vals["size"]) > MAX_SIZE:
        raise build.TvwBuildError("tvw_app_build_too_large")
    t = vals.get("tests", "").split()
    if len(t) != 3 or not all(x.isdigit() for x in t) or int(t[0]) == 0 or int(t[1]) + int(t[2]) > 0:
        raise build.TvwBuildError("tvw_app_build_tests", " ".join(t))
    return {"sha256": sha, "size": int(vals["size"]), "package": m["pkg"], "version": f"{m['name']} ({m['code']})",
            "signer": signer, "permissions": PERMISSIONS}


def apk_dir() -> Path:
    return settings.data_dir / "tvwerkstatt" / "app"


def apk_path() -> Path | None:
    p = apk_dir() / "hydrahive.apk"
    return p if p.is_file() else None


def last_good() -> dict | None:
    return next((b for b in state.builds(100) if b["part"] == PART and b["state"] == "done"), None)


async def _fetch(expected_sha: str) -> None:
    """App aus dem Container holen; nur mit passender Prüfsumme ersetzt sie die vorige."""
    d = apk_dir()
    d.mkdir(parents=True, exist_ok=True)
    tmp = d / "hydrahive.apk.tmp"
    tmp.unlink(missing_ok=True)
    try:
        rc, _, err = await incus.run("file", "pull", f"{container.NAME}{APK}", str(tmp), timeout=120)
    except IncusError as exc:
        rc, err = 1, str(exc)
    if rc != 0 or not tmp.is_file() or tmp.stat().st_size > MAX_SIZE \
            or hashlib.sha256(tmp.read_bytes()).hexdigest() != expected_sha:
        tmp.unlink(missing_ok=True)
        raise build.TvwBuildError("tvw_build_unreadable", str(err)[-200:])
    tmp.replace(d / "hydrahive.apk")


async def _step(job_id: str, step: str, script: str, code: str, stdin: bytes | None = None) -> str:
    jobs.update(job_id, step=step)
    try:
        rc, out, err = await incus.run("exec", container.NAME, "--cwd", source.HOME, "--user", build_jobs.UID,
                                       "--group", build_jobs.UID, "--env", f"HOME={source.HOME}", "--",
                                       "bash", "-c", script, timeout=build_jobs._TIMEOUTS.get(step, 120.0),
                                       input_bytes=stdin)
    except IncusError as exc:
        rc, out, err = 1, "", str(exc)
    if rc != 0:
        raise build.TvwBuildError("tvw_source_mismatch" if rc == source.RC_MISMATCH else code,
                                  build.clean_log(f"{out}\n{err}"))
    return out


async def run(job_id: str) -> None:
    """Auftrag „App bauen“. Container danach immer aus; Fehler enden im Auftrag und im Bau-Eintrag."""
    step, build_id = "container", ""
    try:
        if await container.status() == "missing":
            raise build.TvwBuildError("tvw_not_set_up")
        await network.sync_rules(state.device_targets())
        await container.ensure_running()
        await container.wait_for_address()
        blob, digest = source_tar()
        build_id = build_jobs._new_build(source.source_id())
        build_jobs._set_build(build_id, part=PART, commit_id=digest)
        step = "fetch"
        await _step(job_id, step, source.FETCH_SCRIPT, "tvw_source_failed")
        step = "verify"
        await _step(job_id, step, source.VERIFY_SCRIPT, "tvw_source_mismatch")
        step = "unpack"
        await _step(job_id, step, UNPACK_SCRIPT, "tvw_build_failed", stdin=blob)
        step = "build"
        try:
            log = build.clean_log(await _step(job_id, step, BUILD_SCRIPT, "tvw_build_failed"))
        except build.TvwBuildError as exc:
            build_jobs._set_build(build_id, log_tail=exc.detail)
            raise
        build_jobs._set_build(build_id, log_tail=log)
        step = "collect"
        info = evaluate(build.parse(await _step(job_id, step, COLLECT_SCRIPT, "tvw_build_unreadable")))
        await _fetch(info["sha256"])
        build_jobs._set_build(build_id, state="done", **info)
        jobs.finish(job_id)
    except (build.TvwBuildError, network.TvwNetworkError, container.TvwContainerError) as exc:
        if build_id:
            build_jobs._set_build(build_id, state="failed")
        jobs.finish(job_id, error=exc.code, step=step, detail=getattr(exc, "detail", ""))
    except Exception:
        logger.exception("TV-Werkstatt: Bau der App gescheitert")
        if build_id:
            build_jobs._set_build(build_id, state="failed")
        jobs.finish(job_id, error="tvw_build_failed", step=step)
    finally:
        try:
            await container.stop()
        except container.TvwContainerError:
            logger.warning("TV-Werkstatt: Container nach dem Bau der App nicht angehalten")
