import { NotizbuchPage } from "./NotizbuchPage"

export const routes = [{ path: "/notizbuch", element: <NotizbuchPage /> }]
export const nav = [
  { path: "/notizbuch", icon: "NotebookPen", labelKey: "notizbuch", group: "working", roles: [] },
]
export const i18n = {
  de: {
    notizbuch: {
      title: "Notizbuch",
      new: "Neue Notiz",
      titlePlaceholder: "Titel",
      bodyPlaceholder: "Markdown …",
      save: "Speichern",
      delete: "Löschen",
      preview: "Vorschau",
      edit: "Bearbeiten",
      empty: "Noch keine Notizen",
      untitled: "Unbenannt",
    },
  },
  en: {
    notizbuch: {
      title: "Notebook",
      new: "New note",
      titlePlaceholder: "Title",
      bodyPlaceholder: "Markdown …",
      save: "Save",
      delete: "Delete",
      preview: "Preview",
      edit: "Edit",
      empty: "No notes yet",
      untitled: "Untitled",
    },
  },
}
