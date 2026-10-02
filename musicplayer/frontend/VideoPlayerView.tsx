// Video-Ansicht des Mediaplayers: 16:9-Player, Vollbild, Liste zum Nachschlagen.
import { Maximize, SquareArrowOutUpRight } from "lucide-react"
import { useRef, useState } from "react"
import { useTranslation } from "react-i18next"
import { musicApi } from "./api"
import { TrackList } from "./TrackList"
import type { LibraryPermissions, Track } from "./types"

const BAR_BUTTON = "flex items-center gap-1 text-xs text-[#c4cedd] hover:text-[#e8eef8]"

export function VideoPlayerView({ projectId, tracks, permissions, onRemove, large = false }: {
  projectId: string
  tracks: Track[]
  permissions: LibraryPermissions
  onRemove: (id: number) => void
  large?: boolean
}) {
  const { t } = useTranslation("musicplayer")
  const video = useRef<HTMLVideoElement>(null)
  const [current, setCurrent] = useState<Track | null>(null)

  const select = (track: Track) => {
    setCurrent(track)
    // Quelle wechselt mit dem nächsten Render; danach starten.
    requestAnimationFrame(() => void video.current?.play().catch(() => {}))
  }

  return (
    <div className="space-y-3">
      <div className={`overflow-hidden rounded-[4px] border border-[#2a364b] bg-black ${large ? "max-w-6xl" : ""}`}>
        <video
          ref={video}
          controls
          preload="metadata"
          className="aspect-video w-full"
          src={current ? musicApi.streamUrl(projectId, current.id) : undefined}
        >
          {t("mp_video_unsupported")}
        </video>
        <div className="flex items-center gap-2 border-t border-[#2a364b] bg-[#0d1420] p-2">
          <span className="min-w-0 flex-1 truncate text-xs text-[#8d9ab0]">{current?.title ?? t("mp_nothing")}</span>
          <button
            type="button"
            disabled={!current}
            onClick={() => void video.current?.requestFullscreen().catch(() => {})}
            className={`${BAR_BUTTON} disabled:opacity-40`}
          >
            <Maximize size={13} />
            {t("mp_fullscreen")}
          </button>
          {!large && (
            <a href="/musicplayer" className={BAR_BUTTON}>
              <SquareArrowOutUpRight size={13} />
              {t("mp_open_large")}
            </a>
          )}
        </div>
      </div>
      <div>
        <p className="mb-2 text-[9px] font-black uppercase tracking-[.15em] text-[#69d7ff]">{t("mp_playlist")}</p>
        <TrackList
          projectId={projectId}
          kind="video"
          tracks={tracks}
          activeId={current?.id}
          permissions={permissions}
          onSelect={select}
          onRemove={onRemove}
          tall={large}
        />
      </div>
    </div>
  )
}
