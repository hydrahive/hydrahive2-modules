import { useTranslation } from "react-i18next"
import { ExternalLink, Loader2 } from "lucide-react"
import { safeLink, type FlowStart, type FlowState } from "./msFlow"

const BTN = "rounded-[4px] border border-[#69d7ff]/50 bg-[#69d7ff]/15 px-3 py-1.5 text-sm font-semibold text-[#69d7ff] disabled:opacity-40"

interface Props {
  state: FlowState
  flow: FlowStart | null
  errKey: string | null
  detail: string
  onStart: () => void
}

/** Anzeige der Microsoft-Anmeldung: Knopf → Code + Link → Wartet … → fertig / abgelaufen / abgelehnt / Fehler. */
export function MsSignInView({ state, flow, errKey, detail, onStart }: Props) {
  const { t } = useTranslation("mailbox")
  if (state === "idle" || state === "starting") {
    return (
      <button type="button" onClick={onStart} disabled={state === "starting"} data-mbx-ms-start="1" className={BTN}>
        {state === "starting" ? t("ms.starting") : t("ms.signIn")}</button>
    )
  }
  if (state === "waiting" && flow) {
    const link = safeLink(flow.verification_uri)
    return (
      <div className="space-y-2 rounded-[4px] border border-[rgb(var(--hh-s-rand,42_54_75))] bg-[rgb(var(--hh-s-tief,13_19_31))] p-3 text-xs text-[#c8d2df]" data-mbx-ms-wait="1">
        <p>{t("ms.step1")}</p>
        <a href={link} target="_blank" rel="noopener noreferrer" className="inline-flex items-center gap-1 text-[#69d7ff] hover:underline">
          {link.replace(/^https:\/\//, "")}<ExternalLink size={12} /></a>
        <p>{t("ms.step2")}</p>
        <p className="select-all font-mono text-2xl tracking-widest text-[#e8eef8]" data-mbx-ms-code="1">{flow.user_code}</p>
        <p className="inline-flex items-center gap-1 text-[#9aa7bc]"><Loader2 size={12} className="animate-spin" />{t("ms.waiting")}</p>
      </div>
    )
  }
  if (state === "done") return <p className="text-xs text-emerald-300" data-mbx-ms-done="1">{t("ms.done")}</p>
  const key = state === "expired" ? "ms.expired" : state === "denied" ? "ms.denied" : errKey ?? "ms.err.generic"
  return (
    <div className="space-y-2 text-xs" data-mbx-ms-fail={state}>
      <p className="text-rose-300">{t(key)}</p>
      {detail && <p className="break-words text-[#9aa7bc]">{detail}</p>}
      {key !== "ms.err.notConfigured" && <button type="button" onClick={onStart} className={BTN}>{t("ms.retry")}</button>}
    </div>
  )
}
