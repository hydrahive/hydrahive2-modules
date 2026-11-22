import { useEffect, useState } from "react"
import { useTranslation } from "react-i18next"
import { tasksApi } from "../api"
import { detailState, formatStamp } from "../foreign"
import type { ForeignTask, ForeignTaskFull } from "../types"

interface Props {
  task: ForeignTask
  /** Nur für Tests: Volltext direkt vorgeben statt laden. */
  initial?: ForeignTaskFull | null
}

// Detailansicht eines fremden Tasks: lädt den Volltext live (Spec §Oberfläche, AK G14).
// Ursprung offline → Snapshot mit „Stand vom …“ oder nur Metadaten mit „<instanz> zuletzt gesehen am …“;
// Hub offline → Metadaten aus der Kopie mit „Hub nicht erreichbar“. Nur lesen (Bearbeiten kommt mit G4).
export function ForeignDetail({ task, initial }: Props) {
  const { t, i18n } = useTranslation("tasks")
  const [full, setFull] = useState<ForeignTaskFull | null>(initial ?? null)
  const [error, setError] = useState(false)
  const name = task.origin_name || task.origin_fp.slice(0, 12)

  useEffect(() => {
    if (initial !== undefined) return
    let cancelled = false
    tasksApi.foreign(task.origin_fp, task.item_id)
      .then((r) => { if (!cancelled) setFull(r) })
      .catch(() => { if (!cancelled) setError(true) })
    return () => { cancelled = true }
  }, [task.origin_fp, task.item_id, initial])

  if (error) return <p className="text-[10px] text-rose-400 ml-5 mt-1">{t("foreign_detail_error")}</p>
  if (!full) return <p className="text-[10px] text-[#9aa7bc] ml-5 mt-1">{t("foreign_detail_loading")}</p>

  const state = detailState(full)
  const description = full.content?.description ?? ""
  const hint =
    state === "hub_unreachable" ? t("foreign_hub_unreachable")
    : state === "snapshot" ? t("foreign_snapshot", { stand: formatStamp(full.snapshot_at, i18n.language) })
    : state === "origin_offline" ? t("foreign_last_seen", { name, seen: formatStamp(full.last_seen, i18n.language) })
    : null

  return (
    <div className="ml-5 mt-1 space-y-1" data-testid="foreign-detail" data-state={state}>
      {hint && <p className="text-[10px] text-amber-300/90">{hint}</p>}
      {description
        ? <p className="text-[10px] text-[#c8d2df] whitespace-pre-wrap">{description}</p>
        : state === "live" || state === "snapshot"
          ? <p className="text-[10px] text-[#9aa7bc]">{t("foreign_no_description")}</p>
          : null}
    </div>
  )
}
