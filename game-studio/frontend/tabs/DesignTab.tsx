import { FilePlus2, LoaderCircle, Save } from "lucide-react"
import { useCallback, useEffect, useState } from "react"
import { useTranslation } from "react-i18next"
import { gameStudioApi } from "../api"
import type { DesignDoc, DesignDocMeta } from "../types"
import type { TabProps } from "./registry"

type ApiErr = Error & { status?: number }

export function DesignTab({ project }: TabProps) {
  const { t } = useTranslation("gameStudio")
  const pid = project.project_id
  const [docs, setDocs] = useState<DesignDocMeta[]>([])
  const [canWrite, setCanWrite] = useState(false)
  const [active, setActive] = useState<DesignDoc | null>(null)
  const [draft, setDraft] = useState("")
  const [busy, setBusy] = useState(false)
  const [message, setMessage] = useState<{ kind: "ok" | "error"; text: string } | null>(null)
  const [newTitle, setNewTitle] = useState("")
  const dirty = active !== null && draft !== active.content

  const loadDoc = useCallback(async (slug: string) => {
    const doc = await gameStudioApi.designDoc(pid, slug)
    setActive(doc)
    setDraft(doc.content)
    setMessage(null)
  }, [pid])

  const loadList = useCallback(async (select?: string) => {
    const result = await gameStudioApi.designDocs(pid)
    setDocs(result.docs)
    setCanWrite(result.can_write)
    const target = select ?? result.docs[0]?.slug
    if (target) await loadDoc(target)
  }, [pid, loadDoc])

  useEffect(() => { void loadList().catch(() => setMessage({ kind: "error", text: t("workspace.design.loadFailed") })) }, [loadList, t])

  const choose = async (slug: string) => {
    if (dirty && !window.confirm(t("workspace.design.discard"))) return
    await loadDoc(slug)
  }

  const save = async () => {
    if (!active) return
    setBusy(true)
    try {
      const saved = await gameStudioApi.saveDesignDoc(pid, active.slug, draft, active.etag)
      setActive(saved)
      setDraft(saved.content)
      setDocs((list) => list.map((doc) => doc.slug === saved.slug ? { ...doc, title: saved.title, etag: saved.etag } : doc))
      setMessage({ kind: "ok", text: t("workspace.design.saved") })
    } catch (error) {
      const status = (error as ApiErr).status
      setMessage({ kind: "error", text: t(status === 409 ? "workspace.design.conflict" : "workspace.design.saveFailed") })
    } finally {
      setBusy(false)
    }
  }

  const reloadActive = async () => { if (active) await loadDoc(active.slug) }

  const create = async () => {
    const title = newTitle.trim()
    if (!title) return
    try {
      const created = await gameStudioApi.createDesignDoc(pid, title)
      setNewTitle("")
      await loadList(created.slug)
    } catch (error) {
      const status = (error as ApiErr).status
      setMessage({ kind: "error", text: t(status === 409 ? "workspace.design.exists" : "workspace.design.createFailed") })
    }
  }

  return (
    <div className="grid min-h-[60vh] gap-4 md:grid-cols-[220px_1fr]">
      <nav aria-label={t("workspace.tabs.design")} className="space-y-1">
        {docs.map((doc) => (
          <button key={doc.slug} type="button" onClick={() => void choose(doc.slug)}
            className={`block w-full truncate rounded-lg px-3 py-2 text-left text-sm ${active?.slug === doc.slug ? "bg-[#69d7ff]/12 text-[#e8eef8]" : "text-[#9aa7bc] hover:bg-[rgb(var(--hh-s-hebung,27_37_54))]"}`}>
            {doc.title}
          </button>
        ))}
        {canWrite && (
          <div className="mt-3 flex gap-1">
            <input value={newTitle} onChange={(e) => setNewTitle(e.target.value)} onKeyDown={(e) => { if (e.key === "Enter") void create() }} maxLength={120}
              placeholder={t("workspace.design.newPlaceholder")}
              className="min-w-0 flex-1 rounded-lg border border-[rgb(var(--hh-s-rand,42_54_75))] bg-[rgb(var(--hh-s-tief,13_20_32))] px-2 py-1.5 text-xs text-[#e8eef8] placeholder:text-[#596579]" />
            <button type="button" onClick={() => void create()} disabled={!newTitle.trim()} title={t("workspace.design.create")}
              className="rounded-lg border border-[rgb(var(--hh-s-rand,42_54_75))] p-1.5 text-[#69d7ff] disabled:opacity-40"><FilePlus2 size={15} aria-hidden="true" /></button>
          </div>
        )}
      </nav>
      <section className="flex min-h-0 flex-col rounded-xl border border-[rgb(var(--hh-s-rand,42_54_75))] bg-[rgb(var(--hh-s-innen,17_24_39))]">
        {active ? (
          <>
            <div className="flex items-center gap-2 border-b border-[rgb(var(--hh-s-rand,42_54_75))] px-4 py-2">
              <h2 className="min-w-0 flex-1 truncate text-sm font-semibold text-[#e8eef8]">{active.title}</h2>
              <span className="hidden font-mono text-[10px] text-[#596579] sm:inline">game-studio/design/{active.slug}.md</span>
              {canWrite && (
                <button type="button" onClick={() => void save()} disabled={!dirty || busy}
                  className="inline-flex items-center gap-1.5 rounded-lg bg-[#69d7ff] px-3 py-1.5 text-xs font-semibold text-[#0d1420] disabled:opacity-40">
                  {busy ? <LoaderCircle size={13} className="animate-spin" aria-hidden="true" /> : <Save size={13} aria-hidden="true" />}{t("workspace.design.save")}
                </button>
              )}
            </div>
            {message && (
              <p role={message.kind === "error" ? "alert" : "status"} className={`px-4 pt-2 text-xs ${message.kind === "error" ? "text-red-300" : "text-emerald-300"}`}>
                {message.text}
                {message.kind === "error" && message.text === t("workspace.design.conflict") && (
                  <button type="button" onClick={() => void reloadActive()} className="ml-2 underline">{t("workspace.design.reload")}</button>
                )}
              </p>
            )}
            <textarea value={draft} onChange={(e) => setDraft(e.target.value)} readOnly={!canWrite} spellCheck
              aria-label={active.title}
              onKeyDown={(e) => { if ((e.ctrlKey || e.metaKey) && e.key === "s") { e.preventDefault(); if (dirty) void save() } }}
              className="min-h-[55vh] flex-1 resize-none bg-transparent p-4 font-mono text-sm leading-6 text-[#e8eef8] focus:outline-none" />
          </>
        ) : (
          <div className="flex flex-1 items-center justify-center p-8 text-sm text-[#9aa7bc]">
            {message ? message.text : <LoaderCircle className="animate-spin text-[#69d7ff]" aria-hidden="true" />}
          </div>
        )}
      </section>
    </div>
  )
}
