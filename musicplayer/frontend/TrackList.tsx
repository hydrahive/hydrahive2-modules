import { Download, Music, Trash2, Video } from "lucide-react"
import { useTranslation } from "react-i18next"
import { musicApi } from "./api"
import { trackSubtitle } from "./mediaUtils"
import type { LibraryPermissions, MediaKind, Track } from "./types"

export function TrackList({ projectId, kind, tracks, activeId, permissions, onSelect, onRemove }: { projectId: string; kind: MediaKind; tracks: Track[]; activeId?: number; permissions: LibraryPermissions; onSelect: (track: Track) => void; onRemove: (id: number) => void }) {
  const { t } = useTranslation("musicplayer")
  if (!tracks.length) return <p className="rounded-[4px] border border-dashed border-[#2a364b] bg-[#0d1420] px-3 py-4 text-center text-[11px] text-[#8d9ab0]">{t("mp_empty")}</p>
  return <div className="max-h-56 space-y-1 overflow-y-auto pr-1">{tracks.map((track) => { const active = activeId === track.id; const subtitle = trackSubtitle(track.meta); const Icon = kind === "video" ? Video : Music; return <div key={track.id} className={`flex min-w-0 items-center rounded-[4px] border ${active ? "border-fuchsia-400/35 bg-fuchsia-500/10" : "border-transparent bg-[#111827] hover:border-[#2a364b]"}`}><button type="button" onClick={() => onSelect(track)} className="flex min-w-0 flex-1 items-center gap-2 px-2 py-2 text-left"><Icon size={12} className="shrink-0 text-[#8d9ab0]" /><span className="min-w-0 flex-1"><span className="block truncate text-xs text-[#c4cedd]">{track.title}</span>{subtitle.text && <span className="block truncate text-[10px] text-[#8d9ab0]" title={subtitle.promptTitle}>{subtitle.text}</span>}</span></button><button type="button" onClick={() => void musicApi.download(projectId, track).catch(() => {})} title={t("mp_download", { title: track.title })} className="p-2 text-[#64748b] hover:text-cyan-200"><Download size={12} /></button>{permissions.can_delete && <button type="button" onClick={() => onRemove(track.id)} title={t("mp_delete", { title: track.title })} className="p-2 text-[#64748b] hover:text-rose-300"><Trash2 size={12} /></button>}</div> })}</div>
}
