// Admin-Bereich: generierte Musik aus den Workspaces auflisten + importieren.
import { Check, ChevronDown, ChevronRight, Download, Sparkles } from "lucide-react"
import { useCallback, useState } from "react"
import { useTranslation } from "react-i18next"
import { musicApi } from "./api"
import type { GeneratedTrack } from "./types"

export function GeneratedImport({ onImported }: { onImported: () => void }) {
  const { t } = useTranslation("musicplayer")
  const [open, setOpen] = useState(false)
  const [items, setItems] = useState<GeneratedTrack[]>([])
  const [loading, setLoading] = useState(false)
  const [busy, setBusy] = useState<string | null>(null)

  const load = useCallback(() => {
    setLoading(true)
    musicApi.listGenerated()
      .then(setItems)
      .catch(() => setItems([]))
      .finally(() => setLoading(false))
  }, [])

  const toggle = () => {
    const nextOpen = !open
    setOpen(nextOpen)
    if (nextOpen && items.length === 0) load()
  }

  const doImport = async (path: string) => {
    setBusy(path)
    try {
      await musicApi.importGenerated(path)
      onImported()
      load()
    } catch { /* 409/Fehler ignorieren — Liste wird neu geladen */ }
    finally { setBusy(null) }
  }

  return (
    <div className="pt-1">
      <button onClick={toggle}
        className="w-full flex items-center gap-1.5 px-2 py-1.5 rounded-lg text-fuchsia-200/80 hover:bg-fuchsia-400/[5%] text-xs transition-colors">
        {open ? <ChevronDown size={13} /> : <ChevronRight size={13} />}
        <Sparkles size={12} />
        {t("mp_generated")}
      </button>

      {open && (
        <div className="mt-1 space-y-0.5 max-h-40 overflow-y-auto pl-1">
          {loading && <p className="text-[10px] text-zinc-500 px-1 py-1">{t("mp_loading")}</p>}
          {!loading && items.length === 0 && (
            <p className="text-[10px] text-zinc-500 px-1 py-1">{t("mp_generated_empty")}</p>
          )}
          {items.map((g) => (
            <div key={g.path}
              className="flex items-center gap-1.5 px-1.5 py-1 rounded-md hover:bg-white/[3%]">
              <span className="text-[10px] text-zinc-400 truncate flex-1" title={g.path}>
                {g.workspace} · {g.mtime.slice(0, 10)}
              </span>
              {g.already_imported ? (
                <Check size={13} className="text-emerald-400 shrink-0" />
              ) : (
                <button onClick={() => doImport(g.path)} disabled={busy === g.path}
                  className="shrink-0 text-zinc-400 hover:text-fuchsia-200 disabled:opacity-40"
                  title={t("mp_import")}>
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
