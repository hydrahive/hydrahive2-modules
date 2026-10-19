import { ArrowRight } from "lucide-react"
import { useTranslation } from "react-i18next"
import { HOWTO } from "./guideLogic"
import type { Workspace } from "./workspaces"

const MORE = ["delete", "files", "costs"] as const


/** „So geht’s“: alle Schritte in der Reihenfolge der Arbeit, dazu Löschen, Dateien, Kosten. */
export function HowTo({ onGo }: { onGo: (w: Workspace) => void }) {
  const { t } = useTranslation("studio")
  return (
    <div className="max-h-[64vh] space-y-3 overflow-y-auto px-4 py-3 text-xs" data-studio-howto>
      <ol className="space-y-3">
        {HOWTO.map(({ key, ws }, i) => (
          <li key={key} className="flex gap-3" data-howto-step={key}>
            <span className="grid h-6 w-6 shrink-0 place-items-center rounded-full bg-[#1c2940] text-[11px] font-black text-[#69d7ff]">{i + 1}</span>
            <div className="min-w-0 flex-1 space-y-1">
              <p className="font-bold text-[#e8eef8]">{t(`howto.${key}.title`)}</p>
              <p className="leading-relaxed text-[#c3ccdd]">{t(`howto.${key}.text`)}</p>
              <button type="button" onClick={() => onGo(ws)} data-howto-go={ws} className="flex items-center gap-1 text-[11px] font-bold text-[#69d7ff] hover:underline">
                {t(`howto_go.${ws}`)} <ArrowRight size={11} />
              </button>
            </div>
          </li>
        ))}
      </ol>
      <div className="space-y-2 border-t border-[#2a364b] pt-3">
        {MORE.map((k) => (
          <div key={k} className="rounded-[4px] border border-[#46617f] bg-[#111827] px-2.5 py-2" data-howto-more={k}>
            <p className="font-bold text-[#e8eef8]">{t(`howto_more.${k}.title`)}</p>
            <p className="mt-0.5 leading-relaxed text-[#8d9ab0]">{t(`howto_more.${k}.text`)}</p>
          </div>
        ))}
      </div>
    </div>
  )
}
