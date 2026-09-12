// Admin-Bereich: generierte Musik aus den Workspaces auflisten und importieren.
import { Check, ChevronDown, ChevronRight, Download, Sparkles } from "lucide-react"
import { useCallback, useState } from "react"
import { useTranslation } from "react-i18next"
import { musicApi } from "./api"
import type { GeneratedTrack } from "./types"

export function GeneratedImport({ projectId, onImported }: { projectId: string; onImported: () => void }) {
  const { t } = useTranslation("musicplayer")
  const [open, setOpen] = useState(false)
  const [items, setItems] = useState<GeneratedTrack[]>([])
  const [loading, setLoading] = useState(false)
  const [busy, setBusy] = useState<string | null>(null)

  const load = useCallback(() => {
    setLoading(true)
    musicApi.listGenerated(projectId)
      .then(setItems)
      .catch(() => setItems([]))
      .finally(() => setLoading(false))
  }, [projectId])

  const toggle = () => {
    const nextOpen = !open
    setOpen(nextOpen)
    if (nextOpen && items.length === 0) load()
  }

  const doImport = async (path: string) => {
    setBusy(path)
    try {
      await musicApi.importGenerated(projectId, path)
      onImported()
      load()
    } catch {
      // Die frisch geladene Liste ist auch nach 409/Fehler die verlässliche Quelle.
    } finally {
      setBusy(null)
    }
  }

  return (
    <div>
      <button
        type="button"
        onClick={toggle}
        aria-expanded={open}
        className="flex w-full items-center gap-2 rounded-[4px] border border-[#2a364b] bg-[#111827] px-2 py-2 text-xs font-bold text-[#c4cedd] transition-colors hover:border-[#46617f] hover:bg-[#172133] hover:text-[#e8eef8] focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-[#69d7ff]"
      >
        {open ? <ChevronDown size={13} className="text-[#69d7ff]" /> : <ChevronRight size={13} className="text-[#8d9ab0]" />}
        <Sparkles size={12} className="text-[#69d7ff]" />
        <span className="min-w-0 flex-1 truncate text-left">{t("mp_generated")}</span>
      </button>

      {open && (
        <div className="mt-1 max-h-40 space-y-1 overflow-y-auto rounded-[4px] border border-[#2a364b] bg-[#0d1420] p-1">
          {loading && <p className="px-2 py-1.5 text-[10px] text-[#8d9ab0]">{t("mp_loading")}</p>}
          {!loading && items.length === 0 && (
            <p className="px-2 py-1.5 text-[10px] text-[#8d9ab0]">{t("mp_generated_empty")}</p>
          )}
          {items.map((item) => (
            <div
              key={item.path}
              className="flex items-center gap-2 rounded-[4px] border border-transparent bg-[#111827] px-2 py-1.5 hover:border-[#2a364b] hover:bg-[#172133]"
            >
              <span className="min-w-0 flex-1 truncate text-[10px] text-[#aab6c8]" title={item.path}>
                {item.workspace} · {item.mtime.slice(0, 10)}
              </span>
              {item.already_imported ? (
                <Check size={13} className="shrink-0 text-emerald-400" />
              ) : (
                <button
                  type="button"
                  onClick={() => doImport(item.path)}
                  disabled={busy === item.path}
                  className="grid h-6 w-6 shrink-0 place-items-center rounded-[4px] text-[#8d9ab0] transition-colors hover:bg-fuchsia-500/10 hover:text-fuchsia-200 disabled:opacity-40 focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-[#69d7ff]"
                  title={t("mp_import")}
                  aria-label={t("mp_import")}
                >
                  <Download size={13} />
                </button>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
