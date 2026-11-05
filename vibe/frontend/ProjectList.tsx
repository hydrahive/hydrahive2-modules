import { useState } from "react"
import { useTranslation } from "react-i18next"
import * as api from "./api"
import { BOX, BTN, BTN_DANGER, BTN_MAIN, INPUT } from "./ui"

interface Props {
  projects: api.VibeProject[]; known: readonly string[]
  onChange: () => void; onOpen: (id: string) => void; onError: (key: string | null) => void
}

/** „Neues Projekt“ (nur ein Name) und die Liste der vorhandenen Projekte mit Fortschritt. */
export function ProjectList({ projects, known, onChange, onOpen, onError }: Props) {
  const { t } = useTranslation("vibe")
  const [name, setName] = useState("")
  const [busy, setBusy] = useState(false)
  const [ask, setAsk] = useState<string | null>(null)

  const act = async (fn: () => Promise<unknown>) => {
    setBusy(true); onError(null)
    try { await fn(); onChange() } catch (e) { onError(api.errorKey(e, known)) } finally { setBusy(false) }
  }
  const create = () => act(async () => { await api.createProject(name.trim()); setName("") })

  return (
    <div className="space-y-4">
      <section className={BOX}>
        <h2 className="text-sm font-semibold text-[#e8eef8]">{t("new_title")}</h2>
        <label className="block space-y-1 text-sm text-[#c8d2df]">
          <span>{t("name_label")}</span>
          <input className={INPUT} value={name} maxLength={60} placeholder={t("name_placeholder")} disabled={busy}
            onChange={(e) => setName(e.target.value)} onKeyDown={(e) => { if (e.key === "Enter" && name.trim()) void create() }} />
        </label>
        <button type="button" className={BTN_MAIN} disabled={busy || !name.trim()} onClick={() => void create()}>{t("create")}</button>
      </section>

      {projects.length === 0 && <p className="text-sm text-[#c8d2df]">{t("empty")}</p>}
      {projects.map((p) => (
        <section key={p.project_id} className={BOX}>
          <div className="flex items-center gap-3">
            <h2 className="flex-1 truncate text-base font-semibold text-[#e8eef8]">{p.name}</h2>
            <span className={p.state === "failed" ? "text-sm text-red-300" : p.state === "ready" ? "text-sm text-emerald-300" : "text-sm text-amber-200"}>
              {t(`state.${p.state}`)}</span>
          </div>
          {(p.state === "new" || p.state === "setting_up") && (
            <p className="text-sm text-[#c8d2df]" aria-live="polite">
              {p.progress ? t(`progress.${p.progress}`, { defaultValue: p.progress }) : t("takes")}</p>
          )}
          {p.state === "failed" && (
            <div className="space-y-1 text-sm">
              <p className="text-red-300">{t("failed_at", { step: t(`progress.${p.error_step}`, { defaultValue: p.error_step || "?" }) })}</p>
              {p.error_detail && <p className="whitespace-pre-wrap break-words text-xs text-[#9aa7bc]">{t("detail")} {p.error_detail}</p>}
            </div>
          )}
          <div className="flex flex-wrap gap-2">
            {(p.state === "ready" || p.state === "sleeping") && <button type="button" className={BTN_MAIN} onClick={() => onOpen(p.project_id)}>{t("open")}</button>}
            {p.state === "failed" && <button type="button" className={BTN_MAIN} disabled={busy} onClick={() => void act(() => api.retryProject(p.project_id))}>{t("retry")}</button>}
            {ask === p.project_id ? (
              <>
                <span className="self-center text-sm text-[#c8d2df]">{t("confirm_remove")}</span>
                <button type="button" className={BTN_DANGER} disabled={busy} onClick={() => void act(async () => { await api.removeProject(p.project_id); setAsk(null) })}>{t("yes")}</button>
                <button type="button" className={BTN} onClick={() => setAsk(null)}>{t("no")}</button>
              </>
            ) : (
              <button type="button" className={BTN_DANGER} disabled={busy || p.state === "setting_up" || p.state === "new"} onClick={() => setAsk(p.project_id)}>{t("remove")}</button>
            )}
          </div>
        </section>
      ))}
    </div>
  )
}
