import { MusicPlayerBuddyBox } from "./MusicPlayerBuddyBox"

// Kein eigener Tab — der Player lebt nur in der Buddy-Box.
export const routes = []
export const nav = []

export const buddyWidgets = [MusicPlayerBuddyBox]

export const i18n = {
  de: {
    musicplayer: {
      mp_title: "Musik",
      mp_nothing: "Nichts ausgewählt",
      mp_empty: "Noch keine Tracks. Lade welche hoch!",
      mp_play: "Abspielen",
      mp_pause: "Pause",
      mp_prev: "Vorheriger",
      mp_next: "Nächster",
      mp_shuffle: "Zufallswiedergabe",
      mp_repeat: "Wiederholen",
      mp_repeat_one: "Titel wiederholen",
      mp_upload: "MP3 hochladen",
      mp_uploading: "Lädt hoch…",
      mp_upload_error: "Upload fehlgeschlagen",
      mp_generated: "Generierte Musik",
      mp_generated_empty: "Nichts gefunden.",
      mp_loading: "Lädt…",
      mp_import: "In den Player holen",
    },
  },
  en: {
    musicplayer: {
      mp_title: "Music",
      mp_nothing: "Nothing selected",
      mp_empty: "No tracks yet. Upload some!",
      mp_play: "Play",
      mp_pause: "Pause",
      mp_prev: "Previous",
      mp_next: "Next",
      mp_shuffle: "Shuffle",
      mp_repeat: "Repeat",
      mp_repeat_one: "Repeat one",
      mp_upload: "Upload MP3",
      mp_uploading: "Uploading…",
      mp_upload_error: "Upload failed",
      mp_generated: "Generated music",
      mp_generated_empty: "Nothing found.",
      mp_loading: "Loading…",
      mp_import: "Add to player",
    },
  },
}
