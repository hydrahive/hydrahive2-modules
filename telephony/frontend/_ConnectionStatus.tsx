import { CheckCircle2, CircleDashed, Loader2, TriangleAlert, XCircle } from "lucide-react"
import { useTranslation } from "react-i18next"
import { toneOf, type Tone } from "./connectionLogic"
import type { ConnectionStatus } from "./types"

const STYLE: Record<Tone, string> = {
  ok: "border-emerald-500/30 bg-emerald-500/5 text-emerald-200",
  busy: "border-[#69d7ff]/30 bg-[#69d7ff]/5 text-[#69d7ff]",
  warn: "border-amber-500/30 bg-amber-500/5 text-amber-100",
  error: "border-red-500/30 bg-red-500/5 text-red-200",
  idle: "border-[rgb(var(--hh-s-rand,42_54_75))] bg-[rgb(var(--hh-s-box,21_28_43)/0.6)] text-[#c8d2df]",
}

function Icon({ tone }: { tone: Tone }) {
  if (tone === "ok") return <CheckCircle2 size={18} className="text-emerald-400" />
  if (tone === "busy") return <Loader2 size={18} className="animate-spin text-[#69d7ff]" />
  if (tone === "warn") return <TriangleAlert size={18} className="text-amber-400" />
  if (tone === "error") return <XCircle size={18} className="text-red-400" />
  return <CircleDashed size={18} className="text-[#9aa7bc]" />
}

/** Stand der Verbindung in einem Satz plus was zu tun ist. */
export function ConnectionStatusBox({ status }: { status: ConnectionStatus }) {
  const { t } = useTranslation("voip")
  const tone = toneOf(status)
  return (
    <div className={`flex items-start gap-3 rounded-xl border px-4 py-3 ${STYLE[tone]}`} role="status"
      data-voip-status={status}>
      <Icon tone={tone} />
      <div>
        <p className="text-sm font-semibold">{t(`conn.status.${status}.title`)}</p>
        <p className="mt-0.5 text-sm leading-6 opacity-80">{t(`conn.status.${status}.hint`)}</p>
      </div>
    </div>
  )
}
