// Mediaplayer pro Projekt: Umschalter Audio | Video, Bibliothek, Upload, Import.
import { useCallback, useEffect, useState } from "react"
import { useTranslation } from "react-i18next"
import { musicApi } from "./api"
import { AudioPlayerView } from "./AudioPlayerView"
import { GeneratedImport } from "./GeneratedImport"
import { filterByKind, rememberedKind, rememberKind } from "./mediaUtils"
import { MusicPlayerPanel } from "./MusicPlayerPanel"
import { UploadButton } from "./UploadButton"
import { VideoPlayerView } from "./VideoPlayerView"
import type { LibraryPermissions, MediaKind, Track } from "./types"

const NO_PERMISSIONS: LibraryPermissions = { can_upload: false, can_delete: false }
const KINDS: readonly MediaKind[] = ["audio", "video"]

export function MusicPlayerProjectView({ projectId, large = false }: { projectId: string; large?: boolean }) {
  const { t } = useTranslation("musicplayer")
  const [kind, setKind] = useState<MediaKind>(() => rememberedKind(projectId))
  const [tracks, setTracks] = useState<Track[]>([])
  const [permissions, setPermissions] = useState<LibraryPermissions>(NO_PERMISSIONS)

  const load = useCallback(() => {
    musicApi.list(projectId, kind)
      .then((library) => {
        setTracks(filterByKind(library.tracks, kind))
        setPermissions(library.permissions)
      })
      .catch(() => {
        setTracks([])
        setPermissions(NO_PERMISSIONS)
      })
  }, [projectId, kind])

  useEffect(() => { load() }, [load])

  const chooseKind = (next: MediaKind) => {
    rememberKind(projectId, next)
    setKind(next)
  }
  const remove = async (id: number) => {
    await musicApi.remove(projectId, id).catch(() => {})
    load()
  }

  const content = (
    <div className="space-y-3">
      <div role="group" aria-label={t("mp_kind")} className="flex rounded-[4px] border border-[#2a364b] p-1">
        {KINDS.map((item) => (
          <button
            type="button"
            key={item}
            onClick={() => chooseKind(item)}
            aria-pressed={kind === item}
            className={`flex-1 rounded-[3px] px-2 py-1 text-xs font-bold ${kind === item
              ? "bg-fuchsia-500/20 text-fuchsia-100"
              : "text-[#8d9ab0] hover:text-[#e8eef8]"}`}
          >
            {t(`mp_${item}`)}
          </button>
        ))}
      </div>
      {kind === "audio"
        // key: Wechsel der Art startet den Player frisch (kein Weiterspielen im Hintergrund).
        ? <AudioPlayerView key="audio" projectId={projectId} tracks={tracks} permissions={permissions} onRemove={remove} />
        : <VideoPlayerView key="video" projectId={projectId} tracks={tracks} permissions={permissions} onRemove={remove} large={large} />}
      {permissions.can_upload && (
        <div className="space-y-2 border-t border-[#2a364b] pt-3">
          <UploadButton projectId={projectId} kind={kind} onDone={load} />
          <GeneratedImport key={kind} projectId={projectId} kind={kind} onImported={load} />
        </div>
      )}
    </div>
  )

  return large ? content : <MusicPlayerPanel title={t("mp_title")} trackCount={tracks.length}>{content}</MusicPlayerPanel>
}
