import type { BuddyMediaWidget } from "@/modules/types"
import { MediaPlayerPage } from "./MediaPlayerPage"
import { MusicPlayerBuddyBox } from "./MusicPlayerBuddyBox"

export const routes = [{ path: "/musicplayer", element: <MediaPlayerPage /> }]
export const nav = [{ path: "/musicplayer", icon: "Clapperboard", labelKey: "musicplayer", group: "working", roles: [], cockpit: true }]
export const buddyMediaWidgets = [{ id: "musicplayer", order: 10, component: MusicPlayerBuddyBox }] satisfies BuddyMediaWidget[]

export const i18n = {
  de: { musicplayer: {
    musicplayer: "Mediaplayer", mp_title: "Medien", mp_audio: "Audio", mp_video: "Video", mp_nothing: "Nichts ausgewählt", mp_empty: "Noch keine Medien. Lade welche hoch!", mp_now_playing: "Aktuelle Wiedergabe", mp_playlist: "Playlist", mp_seek: "Wiedergabeposition", mp_volume: "Lautstärke", mp_delete: "{{title}} löschen", mp_play: "Abspielen", mp_pause: "Pause", mp_prev: "Vorheriger", mp_next: "Nächster", mp_shuffle: "Zufallswiedergabe", mp_repeat: "Wiederholen", mp_repeat_one: "Titel wiederholen", mp_upload: "{{kind}} hochladen", mp_uploading: "Lädt hoch…", mp_upload_error: "Upload fehlgeschlagen", mp_generated: "Generierte Musik", mp_generated_empty: "Nichts gefunden.", mp_project_sources: "Aus dem Projekt", mp_loading: "Lädt…", mp_import: "In den Player holen", mp_download: "{{title}} herunterladen", mp_select_project: "Projekt wählen", mp_fullscreen: "Vollbild", mp_open_large: "Groß öffnen", mp_video_unsupported: "Dein Browser unterstützt dieses Video nicht.", mp_kind: "Medienart", mp_import_error: "Import fehlgeschlagen", mp_already_imported: "Schon im Player",
  } },
  en: { musicplayer: {
    musicplayer: "Media player", mp_title: "Media", mp_audio: "Audio", mp_video: "Video", mp_nothing: "Nothing selected", mp_empty: "No media yet. Upload some!", mp_now_playing: "Now playing", mp_playlist: "Playlist", mp_seek: "Playback position", mp_volume: "Volume", mp_delete: "Delete {{title}}", mp_play: "Play", mp_pause: "Pause", mp_prev: "Previous", mp_next: "Next", mp_shuffle: "Shuffle", mp_repeat: "Repeat", mp_repeat_one: "Repeat one", mp_upload: "Upload {{kind}}", mp_uploading: "Uploading…", mp_upload_error: "Upload failed", mp_generated: "Generated music", mp_generated_empty: "Nothing found.", mp_project_sources: "From the project", mp_loading: "Loading…", mp_import: "Add to player", mp_download: "Download {{title}}", mp_select_project: "Select a project", mp_fullscreen: "Fullscreen", mp_open_large: "Open large", mp_video_unsupported: "Your browser does not support this video.", mp_kind: "Media type", mp_import_error: "Import failed", mp_already_imported: "Already in player",
  } },
}
