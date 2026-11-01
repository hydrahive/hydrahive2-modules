import { useTranslation } from "react-i18next"
import type { Meta } from "./admin"
import { BTN } from "./ui"
import { when } from "./when"

/** Kopfzeile der Verwaltungs-Reiter: Hinweis bei altem Stand, Fehler, Neu laden. */
export function Stale({ meta, err, busy, onReload }: { meta: Meta | null; err: string | null; busy: boolean; onReload: () => void }) {
  const { t, i18n } = useTranslation("network")
  return (
    <div className="flex flex-wrap items-center gap-3">
      <button type="button" className={BTN} disabled={busy} onClick={onReload}>{t("refresh")}</button>
      {meta?.stale && <span role="status" className="text-sm text-amber-300">{t("stale", { when: when(meta.fetched_at, i18n.language) })}</span>}
      {err && <span role="status" className="text-sm text-rose-300">{t(err)}</span>}
    </div>
  )
}
