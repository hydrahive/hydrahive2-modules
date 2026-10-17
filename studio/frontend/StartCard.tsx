import { Download, Loader2, PenLine } from "lucide-react"
import { useTranslation } from "react-i18next"

interface Props {
  atelier: boolean
  busy: boolean
  onStart: () => void
  onImport: () => void
}

/** Planen ohne Szenen: „So fängst du an“ – was ein Film hier ist und der erste Schritt als Knopf. */
export function StartCard({ atelier, busy, onStart, onImport }: Props) {
  const { t } = useTranslation("studio")
  const way = "flex flex-col items-start gap-1 rounded-[6px] border p-3 text-left"
  return (
    <div className="mx-auto w-full max-w-xl space-y-3 rounded-[6px] border border-[#46617f] bg-[#0e1420] p-4" data-studio-start>
      <h2 className="text-base font-black text-[#e8eef8]">{t("start_title")}</h2>
      <p className="text-xs leading-relaxed text-[#c3ccdd]">{t("start_text")}</p>
      <div className="grid gap-2 sm:grid-cols-2">
        <div className={`${way} border-[#69d7ff]/50 bg-[#69d7ff]/5`}>
          <button type="button" onClick={onStart} disabled={busy}
            className="flex items-center gap-1.5 rounded-[4px] bg-[#69d7ff] px-3 py-1.5 text-xs font-black text-[#08111c] disabled:opacity-50">
            {busy ? <Loader2 size={13} className="animate-spin" /> : <PenLine size={13} />} {t("start_self")}
          </button>
          <span className="text-[11px] leading-relaxed text-[#8d9ab0]">{t("start_self_hint")}</span>
        </div>
        {atelier && (
          <div className={`${way} border-[#2a364b]`}>
            <button type="button" onClick={onImport}
              className="flex items-center gap-1.5 rounded-[4px] border border-[#69d7ff] px-3 py-1.5 text-xs font-bold text-[#69d7ff] hover:bg-[#1c2940]">
              <Download size={13} /> {t("start_atelier")}
            </button>
            <span className="text-[11px] leading-relaxed text-[#8d9ab0]">{t("start_atelier_hint")}</span>
          </div>
        )}
      </div>
    </div>
  )
}
