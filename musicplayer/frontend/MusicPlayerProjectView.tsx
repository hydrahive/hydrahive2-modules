// Mediaplayer pro Projekt: Umschalter Audio | Video, Bibliothek, Upload, Import.
// Der Audio-Player (Element + Zustand) lebt hier und nicht in der Audio-Ansicht:
// So läuft die Musik beim Umschalten auf Video weiter (Till, 02.10.2026).
import { useCallback, useEffect, useMemo, useState } from "react"
import { useTranslation } from "react-i18next"
import { musicApi } from "./api"
import { AudioPlayerView } from "./AudioPlayerView"
import { GeneratedImport } from "./GeneratedImport"
import { filterByKind, rememberedKind, rememberKind } from "./mediaUtils"
import { MusicPlayerPanel } from "./MusicPlayerPanel"
import { UploadButton } from "./UploadButton"
import { useAudioPlayer } from "./useAudioPlayer"
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
    musicApi.list(projectId)
      .then((library) => {
        setTracks(library.tracks)
        setPermissions(library.permissions)
      })
      .catch(() => {
        setTracks([])
        setPermissions(NO_PERMISSIONS)
      })
  }, [projectId])

  useEffect(() => { load() }, [load])

  const audioTracks = useMemo(() => filterByKind(tracks, "audio"), [tracks])
  const videoTracks = useMemo(() => filterByKind(tracks, "video"), [tracks])
  const shown = kind === "audio" ? audioTracks : videoTracks
  const music = useAudioPlayer(projectId, audioTracks)
  // Entpackt: sonst hält react-hooks/refs `music.audioRef` für einen Ref-Zugriff im Render.
  const { audioRef } = music

  const chooseKind = (next: MediaKind) => {
    rememberKind(projectId, next)
    setKind(next)
    load() // neue Agent-/Atelier-Medien; laufendes Lied hängt an der ID, bleibt also
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
        ? <AudioPlayerView projectId={projectId} tracks={audioTracks} permissions={permissions} onRemove={remove} player={music} />
        : (
          <VideoPlayerView
            projectId={projectId}
            tracks={videoTracks}
            permissions={permissions}
            onRemove={remove}
            music={music}
            onShowAudio={() => chooseKind("audio")}
            large={large}
          />
        )}
      <audio ref={audioRef} preload="metadata" className="hidden" />
      {permissions.can_upload && (
        <div className="space-y-2 border-t border-[#2a364b] pt-3">
          <UploadButton projectId={projectId} kind={kind} onDone={load} />
          <GeneratedImport key={kind} projectId={projectId} kind={kind} onImported={load} />
        </div>
      )}
    </div>
  )

  return large ? content : <MusicPlayerPanel title={t("mp_title")} trackCount={shown.length}>{content}</MusicPlayerPanel>
}
