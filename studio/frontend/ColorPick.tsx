import { Plus, X } from "lucide-react"
import { useTranslation } from "react-i18next"
import { colorAdd, colorRemove, colorSet, longHex, MAX_COLORS } from "./colorLogic"
import { Label } from "./formParts"

/** Farben (C4): je Farbe ein Farbfeld (Klick öffnet den Farbwähler) mit ×, dazu „+ Farbe“. Statt „#1a2b3c“ eintippen. */
export function ColorPick({ label, colors, onChange }: { label: string; colors: string[]; onChange: (c: string[]) => void }) {
  const { t } = useTranslation("studio")
  return (
    <div data-color-pick>
      <Label>{label}</Label>
      <div className="mt-1 flex flex-wrap items-center gap-1.5">
        {colors.map((c, i) => (
          <span key={i} className="relative">
            <input type="color" value={longHex(c)} onChange={(e) => onChange(colorSet(colors, i, e.target.value))} aria-label={t("color_pick", { n: i + 1 })}
              title={longHex(c)} className="h-7 w-9 cursor-pointer rounded-[4px] border border-[#2a364b] bg-transparent p-0.5" />
            <button type="button" onClick={() => onChange(colorRemove(colors, i))} data-color-remove aria-label={t("color_remove")} title={t("color_remove")}
              className="absolute -right-1.5 -top-1.5 rounded-full bg-[#0e1420] p-0.5 text-[#8d9ab0] hover:text-[#ff6b8a]"><X size={9} /></button>
          </span>
        ))}
        {colors.length < MAX_COLORS && (
          <button type="button" onClick={() => onChange(colorAdd(colors))} data-color-add
            className="flex items-center gap-1 rounded-[4px] border border-dashed border-[#46617f] px-2 py-1 text-[11px] font-bold text-[#69d7ff] hover:bg-[#1c2940]">
            <Plus size={11} /> {t("color_add")}
          </button>
        )}
      </div>
      {!colors.length && <p className="mt-1 text-[10px] text-[#68758a]">{t("color_none")}</p>}
    </div>
  )
}
