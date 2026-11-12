import { BUTTON, BUTTON_PRIMARY } from "./styles"
import type { T } from "./texts.de"
import type { SyncStatus } from "./types"

interface Props {
  status: SyncStatus
  busy: boolean
  t: T
  onRetry: () => void
  onKeepMine: () => void
  onTakeTheirs: () => void
}

/** Meldung über der Zeichenfläche, wenn Laden oder Speichern nicht geklappt hat oder ein Konflikt besteht. */
export function SyncNotice({ status, busy, t, onRetry, onKeepMine, onTakeTheirs }: Props) {
  if (status === "loading" || status === "saved" || status === "saving") return null
  const conflict = status === "conflict"
  const tone = conflict
    ? "border-amber-400/30 bg-amber-400/10 text-amber-100"
    : "border-rose-400/30 bg-rose-400/10 text-rose-100"
  return (
    <div role="alert" className={`flex flex-wrap items-center gap-x-3 gap-y-2 border-b px-4 py-2 text-xs ${tone}`}>
      <div className="min-w-0 flex-1">
        <p className="font-semibold">{t(`notice_${status}`)}</p>
        {conflict && <p className="mt-0.5 opacity-80">{t("conflict_keep_hint")} {t("conflict_load_hint")}</p>}
      </div>
      {conflict && (
        <>
          <button type="button" onClick={onKeepMine} disabled={busy} className={BUTTON_PRIMARY}>{t("conflict_keep")}</button>
          <button type="button" onClick={onTakeTheirs} disabled={busy} className={BUTTON}>{t("conflict_load")}</button>
        </>
      )}
      {(status === "load_error" || status === "save_error") && (
        <button type="button" onClick={onRetry} disabled={busy} className={BUTTON}>{t("retry")}</button>
      )}
    </div>
  )
}
