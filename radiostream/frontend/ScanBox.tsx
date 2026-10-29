import { useCallback, useEffect, useState } from "react"
import { useTranslation } from "react-i18next"
import { cancelScan, getScan, getSource, startScan, type Scan } from "./api"
import { errorKey, scanLabel } from "./logic"

/** Stand des Einlesens mit Fortschritt; Admins können starten/abbrechen. Fragt während des Laufs alle 3 s nach. */
export function ScanBox({ isAdmin, configured, onFinished }: { isAdmin: boolean; configured: boolean; onFinished: () => void }) {
  const { t } = useTranslation("radiostream")
  const [scan, setScan] = useState<Scan | null>(null)
  const [msg, setMsg] = useState("")
  const [lastError, setLastError] = useState<string | null>(null)

  const load = useCallback(() => {
    getScan().then(setScan).catch(() => {})
    if (isAdmin) getSource().then((s) => setLastError(s.last_scan_error)).catch(() => {})
  }, [isAdmin])
  useEffect(() => { load() }, [load])
  useEffect(() => {
    if (!scan?.running) return
    const h = setTimeout(() => getScan().then((s) => { setScan(s); if (!s.running) { setLastError(null); onFinished() } }).catch(() => {}), 3000)
    return () => clearTimeout(h)
  }, [scan, onFinished])

  const lbl = scan ? scanLabel(scan, lastError) : { key: "scan.idle", pct: null, eta_min: null }
  const start = () => startScan().then(() => { setMsg(t("scan.started")); load() }).catch((e) => setMsg(t(errorKey(e))))
  const stop = () => cancelScan().then(setScan).catch((e) => setMsg(t(errorKey(e))))

  return (
    <div className="flex flex-wrap items-center gap-3 rounded border border-white/10 bg-white/[3%] px-3 py-2 text-sm" data-radiostream-scan>
      <span className="text-zinc-300">{t(lbl.key, { pct: lbl.pct, files: (scan?.files_seen ?? 0).toLocaleString("de-DE") })}</span>
      {lbl.pct !== null && (
        <div className="h-1.5 w-40 overflow-hidden rounded bg-white/10" role="progressbar" aria-valuenow={lbl.pct} aria-valuemin={0} aria-valuemax={100}>
          <div className="h-full bg-emerald-400" style={{ width: `${lbl.pct}%` }} />
        </div>
      )}
      {lbl.eta_min !== null && <span className="text-zinc-400">{t("scan.eta", { min: lbl.eta_min })}</span>}
      {isAdmin && configured && !scan?.running && (
        <button type="button" onClick={start} className="rounded bg-emerald-600 px-3 py-1 text-white hover:bg-emerald-500">{t("scan.start")}</button>
      )}
      {isAdmin && scan?.running && (
        <button type="button" onClick={stop} className="rounded border border-white/15 px-3 py-1 text-zinc-200 hover:bg-white/10">{t("scan.cancel")}</button>
      )}
      {msg && <span className="text-zinc-400">{msg}</span>}
    </div>
  )
}
