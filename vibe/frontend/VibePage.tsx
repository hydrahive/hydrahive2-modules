import { useCallback, useEffect, useRef, useState } from "react"
import { useTranslation } from "react-i18next"
import * as api from "./api"
import { ProjectList } from "./ProjectList"
import { Workspace } from "./Workspace"

const KNOWN = ["vibe_no_incus", "vibe_model_unavailable", "vibe_project_not_found", "vibe_not_ready", "vibe_not_failed",
  "vibe_container_down", "vibe_version_invalid", "vibe_busy"] as const
const POLL_MS = 2000

/** Modulseite Vibe (nur Admins): Liste der Projekte, dazu ein Projekt öffnen = Chat links, Ansicht rechts. */
export function VibePage() {
  const { t } = useTranslation("vibe")
  const [s, setS] = useState<api.VibeState | null>(null)
  const [msg, setMsg] = useState<string | null>(null)
  const [open, setOpen] = useState<string | null>(null)
  const alive = useRef(true)

  const load = useCallback(() => api.getState().then((r) => { if (alive.current) setS(r) })
    .catch((e) => { if (alive.current) setMsg(api.errorKey(e, KNOWN)) }), [])
  useEffect(() => { alive.current = true; load(); return () => { alive.current = false } }, [load])
  // Nur abfragen, solange ein Projekt noch eingerichtet wird – sonst keine Dauerschleife.
  const busy = s?.projects.some((p) => p.state === "new" || p.state === "setting_up")
  useEffect(() => {
    if (!busy) return
    const id = setTimeout(load, POLL_MS)
    return () => clearTimeout(id)
  }, [busy, s, load])

  if (!s) return <div className="p-4 text-sm text-[#c8d2df]">{msg ? t(msg) : "…"}</div>
  const project = open ? s.projects.find((p) => p.project_id === open) : undefined
  if (project && project.state !== "failed") return <Workspace project={project} onBack={() => { setOpen(null); load() }} />
  return (
    <div className="mx-auto max-w-3xl space-y-4 p-4">
      <header className="space-y-1">
        <h1 className="text-xl font-semibold text-[#e8eef8]">{t("title")}</h1>
        <p className="text-sm text-[#c8d2df]">{t("subtitle")}</p>
      </header>
      {!s.incus && <p className="text-sm text-amber-200">{t(s.error_code ? `err.${s.error_code}` : "err.general")}</p>}
      {msg && <p className="text-sm text-red-300" role="alert">{t(msg)}</p>}
      {s.incus && <ProjectList projects={s.projects} known={KNOWN} onChange={load} onOpen={setOpen} onError={setMsg} />}
    </div>
  )
}
