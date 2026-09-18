import { useEffect, useRef, useState } from "react"
import { useTranslation } from "react-i18next"
import { Markdown } from "@/features/chat/Markdown"
import { HelpButton } from "@/i18n/HelpButton"
import { CockpitShell } from "@/features/cockpit/CockpitShell"
import { CockpitTopbar } from "@/features/cockpit/CockpitTopbar"
import { scratchpadApi } from "./api"

export function ScratchpadPage() {
  const { t } = useTranslation("scratchpad")
  const [userText, setUserText] = useState("")
  const [agentText, setAgentText] = useState("")
  const [loading, setLoading] = useState(true)
  const [saved, setSaved] = useState(true)
  const saveTimer = useRef<ReturnType<typeof setTimeout> | null>(null)

  useEffect(() => {
    scratchpadApi.get()
      .then((d) => { setUserText(d.user_content); setAgentText(d.agent_content) })
      .catch(() => {})
      .finally(() => setLoading(false))
  }, [])

  const onChange = (v: string) => {
    setUserText(v)
    setSaved(false)
    if (saveTimer.current) clearTimeout(saveTimer.current)
    saveTimer.current = setTimeout(() => {
      scratchpadApi.saveUser(v).then(() => setSaved(true)).catch(() => {})
    }, 800)
  }

  const clearAgent = () => {
    if (!confirm(t("clear_confirm"))) return
    scratchpadApi.clearAgent().then(() => setAgentText("")).catch(() => {})
  }

  return (
    <CockpitShell
      title={t("title")}
      className="flex h-full min-h-0 flex-col overflow-hidden bg-[#080b11]"
      hideHeader
    >
      <CockpitTopbar active="/scratchpad" context={t("title")} />
      <main className="min-h-0 flex-1 overflow-y-auto p-4 md:p-6">
        <div className="mx-auto max-w-6xl space-y-6">
          {loading ? (
            <div className="h-48 animate-pulse rounded-[4px] border border-[#2a364b] bg-[#151c2b]" />
          ) : (
            <>
              <header className="flex flex-wrap items-center gap-3">
                <div>
                  <p className="font-mono text-[10px] uppercase tracking-[0.16em] text-[#69d7ff]">Workspace</p>
                  <h1 className="mt-1 text-xl font-black tracking-tight text-[#e8eef8]">{t("title")}</h1>
                </div>
                <HelpButton topic="scratchpad" />
                <span className="text-xs text-[#718097]">{saved ? t("saved") : t("saving")}</span>
              </header>

              <section className="space-y-2">
                <h2 className="text-sm font-bold text-[#e8eef8]">{t("my_ideas")}</h2>
                <div className="grid gap-4 xl:grid-cols-2">
                  <textarea
                    value={userText}
                    onChange={(e) => onChange(e.target.value)}
                    placeholder={t("placeholder")}
                    className="min-h-[24rem] resize-y rounded-[4px] border border-[#2a364b] bg-[#151c2b] px-4 py-3 font-mono text-sm text-[#e8eef8] placeholder:text-[#607188] focus:border-[#69d7ff]/60 focus:outline-none"
                  />
                  <div className="min-h-[24rem] overflow-auto rounded-[4px] border border-[#2a364b] bg-[#111827] px-4 py-3 text-[#c8d2df]">
                    <Markdown text={userText || t("empty_preview")} />
                  </div>
                </div>
              </section>

              <section className="space-y-2">
                <div className="flex flex-wrap items-center gap-3">
                  <h2 className="text-sm font-bold text-[#e8eef8]">{t("agent_notes")}</h2>
                  <span className="text-xs text-[#718097]">{t("agent_notes_hint")}</span>
                  <button
                    onClick={clearAgent}
                    className="ml-auto rounded-[4px] border border-[#2a364b] bg-[#151c2b] px-2 py-1 text-xs text-[#8d9ab0] transition hover:border-rose-400/40 hover:text-rose-200"
                  >
                    {t("clear")}
                  </button>
                </div>
                <div className="overflow-hidden rounded-[4px] border border-[#2a364b] bg-[#111827] px-4 py-3 text-[#c8d2df]">
                  <Markdown text={agentText || t("agent_notes_empty")} />
                </div>
              </section>
            </>
          )}
        </div>
      </main>
    </CockpitShell>
  )
}
