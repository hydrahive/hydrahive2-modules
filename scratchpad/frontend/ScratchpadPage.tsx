import { useCallback, useEffect, useRef, useState } from "react"
import { useTranslation } from "react-i18next"
import { Markdown } from "@/features/chat/Markdown"
import { HelpButton } from "@/i18n/HelpButton"
import { CockpitShell } from "@/features/cockpit/CockpitShell"
import { CockpitTopbar } from "@/features/cockpit/CockpitTopbar"
import { scratchpadApi } from "./api"
import { beginSave, persistUserText, type SaveState } from "./saveState"

export function ScratchpadPage() {
  const { t } = useTranslation("scratchpad")
  const [userText, setUserText] = useState("")
  const [agentText, setAgentText] = useState("")
  const [loading, setLoading] = useState(true)
  const [loaded, setLoaded] = useState(false)
  const [loadFailed, setLoadFailed] = useState(false)
  const [saveState, setSaveState] = useState<SaveState>("saved")
  const [agentClearFailed, setAgentClearFailed] = useState(false)
  const saveTimer = useRef<ReturnType<typeof setTimeout> | null>(null)

  const loadScratchpad = useCallback((reset = true) => {
    if (reset) {
      setLoading(true)
      setLoadFailed(false)
      setLoaded(false)
    }
    scratchpadApi.get()
      .then((data) => {
        setUserText(data.user_content)
        setAgentText(data.agent_content)
        setLoaded(true)
      })
      .catch(() => setLoadFailed(true))
      .finally(() => setLoading(false))
  }, [])

  useEffect(() => {
    queueMicrotask(() => loadScratchpad(false))
    return () => { if (saveTimer.current) clearTimeout(saveTimer.current) }
  }, [loadScratchpad])

  const saveUser = (content: string) => {
    if (saveTimer.current) clearTimeout(saveTimer.current)
    setSaveState(beginSave())
    void persistUserText(scratchpadApi.saveUser, content).then(setSaveState)
  }

  const onChange = (content: string) => {
    if (!loaded) return
    setUserText(content)
    if (saveTimer.current) clearTimeout(saveTimer.current)
    setSaveState(beginSave())
    saveTimer.current = setTimeout(() => saveUser(content), 800)
  }

  const clearAgent = () => {
    if (!confirm(t("clear_confirm"))) return
    setAgentClearFailed(false)
    scratchpadApi.clearAgent().then(() => setAgentText("")).catch(() => setAgentClearFailed(true))
  }

  const statusText = saveState === "saved" ? t("saved")
    : saveState === "saving" ? t("saving")
      : saveState === "too_large" ? t("too_large") : t("not_saved")

  return (
    <CockpitShell title={t("title")} className="flex h-full min-h-0 flex-col overflow-hidden bg-[#080b11]" hideHeader>
      <CockpitTopbar active="/scratchpad" context={t("title")} />
      <main className="min-h-0 flex-1 overflow-y-auto p-4 md:p-6">
        <div className="mx-auto max-w-6xl space-y-6">
          {loading ? <div className="h-48 animate-pulse rounded-[4px] border border-[#2a364b] bg-[#151c2b]" /> : loadFailed ? (
            <section className="rounded-[4px] border border-rose-400/40 bg-rose-400/10 p-4 text-sm text-rose-100">
              <p>{t("load_error")}</p>
              <button onClick={() => loadScratchpad()} className="mt-3 rounded-[4px] border border-rose-300/40 px-2 py-1 text-xs">{t("retry")}</button>
            </section>
          ) : (
            <>
              <header className="flex flex-wrap items-center gap-3">
                <div><p className="font-mono text-[10px] uppercase tracking-[0.16em] text-[#69d7ff]">Workspace</p><h1 className="mt-1 text-xl font-black tracking-tight text-[#e8eef8]">{t("title")}</h1></div>
                <HelpButton topic="scratchpad" />
                <span className={saveState === "error" || saveState === "too_large" ? "text-xs text-rose-200" : "text-xs text-[#718097]"}>{statusText}</span>
                {(saveState === "error" || saveState === "too_large") && <button onClick={() => saveUser(userText)} className="rounded-[4px] border border-rose-300/40 px-2 py-1 text-xs text-rose-100">{t("retry")}</button>}
              </header>

              <section className="space-y-2">
                <h2 className="text-sm font-bold text-[#e8eef8]">{t("my_ideas")}</h2>
                <div className="grid gap-4 xl:grid-cols-2">
                  <textarea value={userText} onChange={(event) => onChange(event.target.value)} placeholder={t("placeholder")} className="min-h-[24rem] resize-y rounded-[4px] border border-[#2a364b] bg-[#151c2b] px-4 py-3 font-mono text-sm text-[#e8eef8] placeholder:text-[#607188] focus:border-[#69d7ff]/60 focus:outline-none" />
                  <div className="min-h-[24rem] overflow-auto rounded-[4px] border border-[#2a364b] bg-[#111827] px-4 py-3 text-[#c8d2df]"><Markdown text={userText || t("empty_preview")} /></div>
                </div>
              </section>

              <section className="space-y-2">
                <div className="flex flex-wrap items-center gap-3">
                  <h2 className="text-sm font-bold text-[#e8eef8]">{t("agent_notes")}</h2><span className="text-xs text-[#718097]">{t("agent_notes_hint")}</span>
                  <button onClick={clearAgent} className="ml-auto rounded-[4px] border border-[#2a364b] bg-[#151c2b] px-2 py-1 text-xs text-[#8d9ab0] transition hover:border-rose-400/40 hover:text-rose-200">{t("clear")}</button>
                </div>
                {agentClearFailed && <p className="text-xs text-rose-200">{t("clear_error")}</p>}
                <div className="overflow-hidden rounded-[4px] border border-[#2a364b] bg-[#111827] px-4 py-3 text-[#c8d2df]"><Markdown text={agentText || t("agent_notes_empty")} /></div>
              </section>
            </>
          )}
        </div>
      </main>
    </CockpitShell>
  )
}
