import { useState } from "react"
import { Film, Link2 } from "lucide-react"
import { useTranslation } from "react-i18next"
import { fileUrl } from "@/shared/files"
import type { LibraryItem } from "./api"
import { fieldCls } from "./formParts"
import { freeImages, shotChoices } from "./freeLogic"
import type { Plan } from "./planApi"

interface Props {
  items: LibraryItem[]
  plan: Plan | null
  busy: boolean
  onAssign: (sceneId: string, shotId: string, rel: string) => void
  onTimeline: (rel: string) => void
}

/** Mitte bei „Freies Bild“: alle freien Bilder, neueste zuerst – einem Shot zuweisen oder auf die Zeitleiste legen. */
export function FreeGallery({ items, plan, busy, onAssign, onTimeline }: Props) {
  const { t } = useTranslation("studio")
  const list = freeImages(items)
  const choices = shotChoices(plan)
  if (!list.length) return <p className="max-w-sm text-center text-xs leading-relaxed text-[#8d9ab0]" data-free-none>{t("free_none")}</p>
  return (
    <div className="grid w-full grid-cols-[repeat(auto-fill,minmax(220px,1fr))] content-start gap-3 self-start" data-free-gallery>
      {list.map((i) => <Card key={i.id} item={i} choices={choices} busy={busy} onAssign={onAssign} onTimeline={onTimeline} />)}
      {!choices.length && <p className="col-span-full text-[11px] text-[#68758a]">{t("free_no_shots")}</p>}
    </div>
  )
}

function Card({ item, choices, busy, onAssign, onTimeline }: { item: LibraryItem; choices: ReturnType<typeof shotChoices> } & Omit<Props, "items" | "plan">) {
  const { t } = useTranslation("studio")
  const [target, setTarget] = useState("")
  const btn = "flex flex-1 items-center justify-center gap-1 rounded-[4px] border border-[#2a364b] px-2 py-1 text-[11px] font-bold text-[#69d7ff] hover:border-[#69d7ff] hover:bg-[#1c2940] disabled:opacity-40"
  return (
    <figure className="space-y-1.5 rounded-[6px] border border-[#2a364b] bg-[#0d1420] p-2" data-free-image={item.rel}>
      <img src={fileUrl(item.abs)} alt={item.prompt || item.name} loading="lazy" className="aspect-video w-full rounded-[3px] bg-black object-contain" />
      {item.prompt && <figcaption className="line-clamp-2 text-[10px] text-[#8d9ab0]" title={item.prompt}>{item.prompt}</figcaption>}
      {choices.length > 0 && (
        <div className="flex gap-1">
          <select value={target} onChange={(e) => setTarget(e.target.value)} aria-label={t("free_assign_to")} className={`${fieldCls} mt-0 min-w-0 flex-1 py-0.5 text-[11px]`}>
            <option value="">{t("free_assign_to")}</option>
            {choices.map((c) => <option key={c.value} value={c.value}>{c.scene || t("untitled")} · {t("shot", { n: c.n })}</option>)}
          </select>
          <button type="button" disabled={busy || !target} className={btn}
            onClick={() => { const [s, sh] = target.split(":"); onAssign(s, sh, item.rel) }}>
            <Link2 size={11} /> {t("free_assign")}
          </button>
        </div>
      )}
      <button type="button" onClick={() => onTimeline(item.rel)} disabled={busy} className={`${btn} w-full`}>
        <Film size={11} /> {t("free_timeline")}
      </button>
    </figure>
  )
}
