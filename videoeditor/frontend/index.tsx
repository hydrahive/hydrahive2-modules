import { VideoEditorPage } from "./VideoEditorPage"

export const routes = [{ path: "/videoeditor", element: <VideoEditorPage /> }]
export const nav = [
  { path: "/videoeditor", icon: "Scissors", labelKey: "videoeditor", group: "working", roles: [] },
]

export const i18n = {
  de: {
    videoeditor: {
      videoeditor: "Video-Editor",
      title: "Video-Editor",
      upload: "Video hochladen",
      uploading: "Lädt hoch…",
      upload_failed: "Upload fehlgeschlagen",
      empty: "Noch keine Videos. Lade das erste hoch!",
      no_projects: "Keine Projekte vorhanden. Lege zuerst ein Projekt an.",
      clips: "Clip(s)",
    },
  },
  en: {
    videoeditor: {
      videoeditor: "Video Editor",
      title: "Video Editor",
      upload: "Upload video",
      uploading: "Uploading…",
      upload_failed: "Upload failed",
      empty: "No videos yet. Upload the first one!",
      no_projects: "No projects yet. Create a project first.",
      clips: "clip(s)",
    },
  },
}
