import { Maximize, Play, SquareArrowOutUpRight } from "lucide-react"
import { useRef, useState } from "react"
import { useTranslation } from "react-i18next"
import { musicApi } from "./api"
import { TrackList } from "./TrackList"
import type { LibraryPermissions, Track } from "./types"

export function VideoPlayerView({ projectId, tracks, permissions, onRemove, large = false }: { projectId: string; tracks: Track[]; permissions: LibraryPermissions; onRemove: (id: number) => void; large?: boolean }) {
  const { t } = useTranslation("musicplayer"); const video = useRef<HTMLVideoElement>(null); const [current, setCurrent] = useState<Track | null>(null)
  const select = (track: Track) => { setCurrent(track); requestAnimationFrame(() => void video.current?.play().catch(() => {})) }
  return <div className="space-y-3"><div className={`overflow-hidden rounded-[4px] border border-[#2a364b] bg-black ${large ? "max-w-6xl" : ""}`}><video ref={video} controls className="aspect-video w-full" src={current ? musicApi.streamUrl(projectId, current.id) : undefined}>{t("mp_video_unsupported")}</video><div className="flex justify-end gap-2 border-t border-[#2a364b] bg-[#0d1420] p-2"><button type="button" onClick={() => void video.current?.requestFullscreen()} className="flex items-center gap-1 text-xs text-[#c4cedd]"><Maximize size={13}/>{t("mp_fullscreen")}</button>{!large && <a href="/musicplayer" className="flex items-center gap-1 text-xs text-[#c4cedd]"><SquareArrowOutUpRight size={13}/>{t("mp_open_large")}</a>}</div></div><div><p className="mb-2 text-[9px] font-black uppercase tracking-[.15em] text-[#69d7ff]">{t("mp_playlist")}</p><TrackList projectId={projectId} kind="video" tracks={tracks} activeId={current?.id} permissions={permissions} onSelect={select} onRemove={onRemove}/></div>{!current && tracks.length > 0 && <button type="button" onClick={() => select(tracks[0])} className="hidden"><Play /></button>}</div>
}
