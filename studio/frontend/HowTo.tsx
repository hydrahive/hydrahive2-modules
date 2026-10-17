import { ArrowRight } from "lucide-react"
import { useTranslation } from "react-i18next"
import type { Workspace } from "./workspaces"

const STEPS: { n: 1 | 2 | 3 | 4 | 5; ws: Workspace }[] = [
  { n: 1, ws: "plan" }, { n: 2, ws: "plan" }, { n: 3, ws: "generate" }, { n: 4, ws: "generate" }, { n: 5, ws: "edit" },
]

/** „So geht’s“: der Ablauf in fünf Schritten, jeder mit einem Sprung in den passenden Reiter. */
export function HowTo({ onGo }: { onGo: (w: Workspace) => void }) {
  const { t } = useTranslation("studio")
  return (
    <div className="max-h-[60vh] space-y-3 overflow-y-auto px-4 py-3 text-xs" data-studio-howto>
      <ol className="space-y-3">
        {STEPS.map(({ n, ws }) => (
          <li key={n} className="flex gap-3" data-howto-step={n}>
            <span className="grid h-6 w-6 shrink-0 place-items-center rounded-full bg-[#1c2940] text-[11px] font-black text-[#69d7ff]">{n}</span>
            <div className="min-w-0 flex-1 space-y-1">
              <p className="font-bold text-[#e8eef8]">{t(`howto.s${n}.title`)}</p>
              <p className="leading-relaxed text-[#c3ccdd]">{t(`howto.s${n}.text`)}</p>
              <button type="button" onClick={() => onGo(ws)} className="flex items-center gap-1 text-[11px] font-bold text-[#69d7ff] hover:underline">
                {t(`howto_go.${ws}`)} <ArrowRight size={11} />
              </button>
            </div>
          </li>
        ))}
      </ol>
      <p className="rounded-[4px] border border-[#46617f] bg-[#111827] px-2.5 py-2 leading-relaxed text-[#8d9ab0]">{t("howto_costs")}</p>
    </div>
  )
}
