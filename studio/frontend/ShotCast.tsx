import { Image as ImageIcon } from "lucide-react"
import { useTranslation } from "react-i18next"
import { castNames } from "./elementPhotoLogic"
import type { PlanElement, Shot } from "./planApi"

/** Im Shot (C2): wer mit ins Bild kommt – genannt im Text oder angehakt; mit Hinweis, ob ein Vorlage-Foto mitgeht. */
export function ShotCast({ shot, elements }: { shot: Shot; elements: PlanElement[] }) {
  const { t } = useTranslation("studio")
  const list = castNames(shot.cast, elements)
  return (
    <div className="space-y-1 rounded-[4px] bg-[#0d1420] px-2 py-1.5" data-shot-cast-box>
      <p className="text-[10px] font-bold uppercase tracking-wide text-[#68758a]">{t("shot_cast_title")}</p>
      {list.length ? (
        <div className="flex flex-wrap gap-1">
          {list.map((c) => (
            <span key={c.id} data-shot-cast={c.id} className="flex items-center gap-1 rounded-full bg-[#1c2940] px-2 py-0.5 text-[11px] text-[#e8eef8]">{c.name}
              {c.photo && <span className="flex items-center gap-0.5 text-[10px] text-[#7ee2a8]"><ImageIcon size={10} /> {t("shot_cast_photo")}</span>}
            </span>
          ))}
        </div>
      ) : <p className="text-[11px] text-[#8d9ab0]">{t("shot_cast_none")}</p>}
      <p className="text-[10px] leading-relaxed text-[#68758a]">{t("shot_cast_hint")}</p>
    </div>
  )
}
