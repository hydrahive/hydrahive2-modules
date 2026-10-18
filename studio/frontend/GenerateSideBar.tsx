import { ImagePlus, Plus } from "lucide-react"
import { useTranslation } from "react-i18next"
import type { Plan } from "./planApi"

interface Props {
  plan: Plan | null
  free: boolean
  busy: boolean
  /** Liste der Szenen für „+ Shot“ ist offen */
  pickScene?: boolean
  onFree: () => void
  onAddShot: (sceneId?: string) => void
}

/** Reiter „Erzeugen“, links über der Shot-Liste: „+ Shot“ (Szene wählen) und „Freies Bild“ (B3). */
export function GenerateSideBar({ plan, free, busy, pickScene = false, onFree, onAddShot }: Props) {
  const { t } = useTranslation("studio")
  const scenes = plan?.scenes ?? []
  const btn = "flex flex-1 items-center justify-center gap-1 rounded-[4px] border px-2 py-1 text-[11px] font-bold disabled:opacity-40"
  return (
    <div className="space-y-1.5 border-b border-[#2a364b] p-2" data-gen-sidebar>
      <div className="flex gap-1.5">
        <button type="button" onClick={() => onAddShot()} disabled={busy || !scenes.length} aria-expanded={pickScene} data-gen-add-shot
          className={`${btn} border-[#2a364b] text-[#69d7ff] hover:border-[#69d7ff] hover:bg-[#1c2940]`}>
          <Plus size={12} /> {t("gen_add_shot")}
        </button>
        <button type="button" onClick={onFree} aria-pressed={free} data-gen-free
          className={`${btn} ${free ? "border-[#69d7ff] bg-[#1c2940] text-[#69d7ff]" : "border-[#2a364b] text-[#69d7ff] hover:border-[#69d7ff] hover:bg-[#1c2940]"}`}>
          <ImagePlus size={12} /> {t("gen_free")}
        </button>
      </div>
      {pickScene && (
        <div className="space-y-0.5 rounded-[4px] border border-[#2a364b] bg-[#0d1420] p-1" role="group" aria-label={t("gen_pick_scene")}>
          <p className="px-1 text-[10px] text-[#68758a]">{t("gen_pick_scene")}</p>
          {scenes.map((s) => (
            <button key={s.id} type="button" onClick={() => onAddShot(s.id)} disabled={busy} data-gen-add-to={s.id}
              className="block w-full truncate rounded-[3px] px-1.5 py-1 text-left text-[11px] text-[#e8eef8] hover:bg-[#1c2940]">
              {s.title || t("untitled")}
            </button>
          ))}
        </div>
      )}
    </div>
  )
}
