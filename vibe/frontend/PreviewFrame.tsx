import { useCallback, useEffect, useRef, useState } from "react"
import { Loader2, RefreshCw } from "lucide-react"
import { useTranslation } from "react-i18next"
import * as api from "./api"
import { BTN } from "./ui"

const KNOWN = ["vibe_container_down", "vibe_not_ready", "vibe_project_not_found", "vibe_preview_unavailable", "vibe_preview_bad_host",
  "vibe_incus_failed", "vibe_network_missing"] as const

/** Vorschau der gebauten Seite im eigenen, abgeschotteten Fenster (eigener Ursprung, `sandbox` ohne `allow-same-origin`).
 *  `reloadKey` zählt hoch, wenn der Agent einen Zug beendet hat: dann lädt die Vorschau neu. */
export function PreviewFrame({ projectId, reloadKey }: { projectId: string; reloadKey: string }) {
  const { t } = useTranslation("vibe")
  const [url, setUrl] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [nonce, setNonce] = useState(0)
  const first = useRef(true)

  const start = useCallback(() => {
    setUrl(null); setError(null)
    api.openPreview(projectId).then((r) => setUrl(r.url)).catch((e) => setError(api.errorKey(e, KNOWN)))
  }, [projectId])
  // Neuladen mit FRISCHEM Ticket: das erste ist nach dem Einlösen verbraucht (gilt einmal, 60 s). Die alte Ansicht
  // bleibt stehen, bis die neue Adresse da ist – kein Aufblitzen.
  const reload = useCallback(() => {
    api.openPreview(projectId).then((r) => { setUrl(r.url); setNonce((n) => n + 1) }).catch((e) => setError(api.errorKey(e, KNOWN)))
  }, [projectId])
  useEffect(() => { start() }, [start])
  useEffect(() => {
    if (!reloadKey) return
    if (first.current) { first.current = false; return }      // die erste Meldung ist nur der Stand beim Öffnen
    reload()
  }, [reloadKey, reload])

  return (
    <div className="flex min-h-[320px] flex-1 flex-col gap-2">
      <div className="flex items-center gap-2">
        <h2 className="flex-1 text-sm text-[#e8eef8]">{t("preview_title")}</h2>
        <button type="button" className={BTN} title={t("preview_reload")} aria-label={t("preview_reload")} onClick={() => url ? reload() : start()}>
          <RefreshCw size={14} aria-hidden="true" /></button>
      </div>
      {error && <p className="text-sm text-rose-300" role="alert">{t(error)} <button type="button" className="underline" onClick={start}>{t("retry")}</button></p>}
      {!url && !error && <div className="flex flex-1 items-center justify-center text-sm text-[#9aa7bc]"><Loader2 size={14} className="mr-2 animate-spin" />{t("preview_loading")}</div>}
      {url && (
        <iframe key={nonce} title={t("preview_title")} src={url} sandbox="allow-scripts allow-forms allow-popups allow-same-origin"
          className="min-h-[320px] w-full flex-1 rounded border border-[rgb(var(--hh-s-rand,42_54_75))] bg-white" />
      )}
    </div>
  )
}
