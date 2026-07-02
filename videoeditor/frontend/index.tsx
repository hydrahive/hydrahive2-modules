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
      empty: "Noch keine Videos. Füge eins aus dem Projekt hinzu oder lade eins hoch!",
      no_projects: "Keine Projekte vorhanden. Lege zuerst ein Projekt an.",
      clips: "Clip(s)",
      add_from_project: "Aus Projekt hinzufügen",
      browse_title: "Videos im Projekt",
      browse_empty: "Keine Videos im Projekt-Workspace gefunden.",
      loading: "Lädt…",
      already_imported: "bereits hinzugefügt",
      importing: "Bereitet auf…",
      import_failed: "Import fehlgeschlagen",
      add: "Hinzufügen",
    },
  },
  en: {
    videoeditor: {
      videoeditor: "Video Editor",
      title: "Video Editor",
      upload: "Upload video",
      uploading: "Uploading…",
      upload_failed: "Upload failed",
      empty: "No videos yet. Add one from the project or upload one!",
      no_projects: "No projects yet. Create a project first.",
      clips: "clip(s)",
      add_from_project: "Add from project",
      browse_title: "Videos in project",
      browse_empty: "No videos found in the project workspace.",
      loading: "Loading…",
      already_imported: "already added",
      importing: "Preparing…",
      import_failed: "Import failed",
      add: "Add",
    },
  },
}
