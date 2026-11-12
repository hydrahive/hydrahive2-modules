import { Wrench } from "lucide-react"
import { BUTTON } from "./styles"
import type { T } from "./texts.de"
import type { ChatInfo } from "./types"

interface Props {
  info: ChatInfo | null
  /** Einstiegstext der Sitzung, oder null, solange es keine gibt. */
  intro: string | null
  showIntro: boolean
  isAdmin: boolean
  busy: boolean
  failed: boolean
  /** Warum sich die fehlenden Werkzeuge nicht ergänzen ließen (z. B. ein vom Modul verwalteter Agent). */
  toolsError?: string | null
  copied: "" | "ok" | "fail"
  t: T
  onAddTools: () => void
  onCopy: () => void
  onToggleIntro: () => void
}

const WARN = "rounded border border-amber-400/30 bg-amber-400/5 px-2 py-1.5 text-amber-200"

/** Hinweise über dem Chat: warum es keinen gibt, fehlende Werkzeuge, Einstiegstext für die erste Nachricht. */
export function ChatNotice(p: Props) {
  const { info, intro, t } = p
  const missing = info?.agent ? info.tools_missing : []
  if (!p.failed && !info?.reason && missing.length === 0 && intro === null) return null
  return (
    <div className="shrink-0 space-y-2 p-3 text-xs text-[#c8d2df]">
      {p.failed && <p role="alert" className="text-rose-200">{t("chat_failed")}</p>}
      {info?.reason && <p className={WARN}>{t(`chat_reason_${info.reason}`)}</p>}
      {missing.length > 0 && (
        <div className={`${WARN} space-y-1.5`}>
          <p>{t("chat_tools_missing", { tools: missing.join(", ") })}</p>
          {p.toolsError && <p role="alert" className="text-rose-200">{p.toolsError}</p>}
          {p.isAdmin ? (
            <button type="button" onClick={p.onAddTools} disabled={p.busy} className={BUTTON}>
              <Wrench size={12} aria-hidden />{t("chat_tools_add")}
            </button>
          ) : (
            <p>{t("chat_tools_ask_admin")}</p>
          )}
        </div>
      )}
      {intro !== null && !p.showIntro && (
        <button type="button" onClick={p.onToggleIntro} className={BUTTON}>{t("chat_intro_show")}</button>
      )}
      {intro !== null && p.showIntro && (
        <div className="space-y-1.5">
          <p>{t("chat_intro_hint")}</p>
          <pre className={"max-h-40 overflow-y-auto whitespace-pre-wrap rounded px-2 py-1.5 text-[11px] text-[#e8eef8] " +
            "bg-[rgb(var(--hh-s-tief,13_20_32))]"}>{intro}</pre>
          <div className="flex flex-wrap gap-2">
            <button type="button" onClick={p.onCopy} className={BUTTON}>
              {p.copied === "ok" ? t("copied") : p.copied === "fail" ? t("copy_failed") : t("chat_intro_copy")}
            </button>
            <button type="button" onClick={p.onToggleIntro} className={BUTTON}>{t("chat_intro_hide")}</button>
          </div>
        </div>
      )}
    </div>
  )
}
