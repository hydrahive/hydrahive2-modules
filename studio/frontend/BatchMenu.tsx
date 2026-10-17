import { useState } from "react"
import { ChevronDown, Layers } from "lucide-react"
import { useTranslation } from "react-i18next"
import { BATCH_KINDS, type BatchKind } from "./planApi"

/** Storyboard-Leiste: „Für alle …“ – startet einen Sammelauftrag (vorher Rückfrage im Dialog). */
export function BatchMenu({ running, onPick }: { running: boolean; onPick: (k: BatchKind) => void }) {
  const { t } = useTranslation("studio")
  const [open, setOpen] = useState(false)
  return (
    <div className="relative shrink-0">
      <button type="button" onClick={() => setOpen((o) => !o)} disabled={running} data-batch-open aria-expanded={open}
        className="flex items-center gap-1 rounded-[4px] border border-[#2a364b] px-2 py-0.5 font-bold text-[#c3ccdd] hover:bg-[#1c2940] disabled:opacity-50">
        <Layers size={12} /> {t("batch_menu")} <ChevronDown size={11} />
      </button>
      <ul className={`absolute right-0 top-full z-20 mt-1 w-60 overflow-hidden rounded-[4px] border border-[#46617f] bg-[#0e1420] shadow-xl ${open ? "" : "hidden"}`} role="menu">
        {BATCH_KINDS.map((k) => (
          <li key={k}>
            <button type="button" role="menuitem" data-batch-pick={k} onClick={() => { setOpen(false); onPick(k) }}
              className="block w-full px-3 py-1.5 text-left text-[11px] text-[#c3ccdd] hover:bg-[#1c2940] hover:text-[#e8eef8]">
              {t(`batch_title.${k}`)}
            </button>
          </li>
        ))}
      </ul>
    </div>
  )
}
