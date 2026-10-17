import { ArrowRight, Construction } from "lucide-react"
import { useTranslation } from "react-i18next"

/** Ton, Untertitel, Ausgabe: ehrlicher Hinweis, was dort kommt – statt Beispieldaten. */
export function ComingSoon({ workspace, onCut }: { workspace: "audio" | "subtitles" | "deliver"; onCut: () => void }) {
  const { t } = useTranslation("studio")
  return (
    <section className="flex h-full min-h-0 flex-col items-center justify-center gap-3 p-4 text-center" data-studio-panel="timeline" data-studio-soon={workspace}>
      <Construction size={22} className="text-[#ffb86b]" />
      <p className="max-w-xl text-xs leading-relaxed text-[#8d9ab0]">{t(`soon.${workspace}`)}</p>
      <button type="button" onClick={onCut} data-soon-to-cut
        className="flex items-center gap-1.5 rounded-[4px] border border-[#46617f] px-2.5 py-1 text-xs font-bold text-[#69d7ff] hover:bg-[#1c2940]">
        {t("soon_to_cut")} <ArrowRight size={12} />
      </button>
    </section>
  )
}
