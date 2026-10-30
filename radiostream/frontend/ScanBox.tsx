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
    <div className="flex flex-wrap items-center gap-3 rounded border border-[rgb(var(--hh-s-rand,42_54_75))] bg-[rgb(var(--hh-s-innen,17_24_39))] px-3 py-2 text-sm" data-radiostream-scan>
      <span className="text-[#c8d2df]">{t(lbl.key, { pct: lbl.pct, files: (scan?.files_seen ?? 0).toLocaleString("de-DE") })}</span>
      {lbl.pct !== null && (
        <div className="h-1.5 w-40 overflow-hidden rounded bg-[rgb(var(--hh-s-hebung,27_37_54))]" role="progressbar" aria-valuenow={lbl.pct} aria-valuemin={0} aria-valuemax={100}>
          <div className="h-full bg-emerald-400" style={{ width: `${lbl.pct}%` }} />
        </div>
      )}
      {lbl.eta_min !== null && <span className="text-[#c8d2df]">{t("scan.eta", { min: lbl.eta_min })}</span>}
      {isAdmin && configured && !scan?.running && (
        <button type="button" onClick={start} className="rounded bg-emerald-600 px-3 py-1 text-white hover:bg-emerald-500">{t("scan.start")}</button>
      )}
      {isAdmin && scan?.running && (
        <button type="button" onClick={stop} className="rounded border border-[rgb(var(--hh-s-rand,42_54_75))] px-3 py-1 text-[#e8eef8] hover:bg-[rgb(var(--hh-s-hebung,27_37_54))]">{t("scan.cancel")}</button>
      )}
      {msg && <span className="text-[#c8d2df]">{msg}</span>}
    </div>
  )
}
