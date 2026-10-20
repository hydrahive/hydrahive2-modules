import { useEffect, useState } from "react"
import { useTranslation } from "react-i18next"
import { Network } from "lucide-react"
import { previewUrl, type Item } from "./api"
import { kindLabelKey, shortDate } from "./logic"

/** Kachel einer Sammlung: Vorschaubild (oder Platzhalter), Titel, Art in Worten, Projekt, Datum, Fassungen. */
export function Tile({ item, onOpen }: { item: Item; onOpen: (item: Item) => void }) {
  const { t } = useTranslation("diagramme")
  const [img, setImg] = useState<string | null>(null)

  useEffect(() => {
    let url: string | null = null
    let alive = true
    previewUrl(item.id).then((u) => { url = u; if (alive) setImg(u) }).catch(() => {})
    return () => { alive = false; if (url) URL.revokeObjectURL(url) }
  }, [item.id])

  return (
    <button type="button" onClick={() => onOpen(item)} data-diagram-tile={item.id}
      className="group flex flex-col overflow-hidden rounded-lg border border-white/10 bg-white/[3%] text-left hover:border-white/25">
      <div className="flex aspect-[16/10] items-center justify-center bg-zinc-900/60">
        {img ? <img src={img} alt="" className="h-full w-full object-cover object-top" />
          : <span className="flex flex-col items-center gap-1 text-xs text-zinc-500"><Network size={22} />{t("no_preview")}</span>}
      </div>
      <div className="space-y-0.5 p-3">
        <div className="truncate text-sm font-medium text-zinc-100">{item.title}</div>
        <div className="truncate text-xs text-zinc-400">
          {t(kindLabelKey(item.kind))}{item.project_name ? ` · ${item.project_name}` : ""}
        </div>
        <div className="flex justify-between text-[11px] text-zinc-500">
          <span>{shortDate(item.created_at)}</span>
          {item.versions > 1 && <span>{t("versions_count", { count: item.versions })}</span>}
        </div>
      </div>
    </button>
  )
}
