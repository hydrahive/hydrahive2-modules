import { IdeasPage } from "./IdeasPage"
import { de } from "./texts.de"
import { en } from "./texts.en"

// Adresse und Modul-ID bleiben scratchpad, damit bestehende Installationen und Verknüpfungen weiter gehen.
export const routes = [{ path: "/scratchpad", element: <IdeasPage /> }]
export const nav = [
  { path: "/scratchpad", icon: "Lightbulb", labelKey: "scratchpad", group: "working", area: "schreiben", roles: [], cockpit: true },
]
// Der Menütitel kommt aus scratchpad:title (Kern shared/nav-label.ts).
export const i18n = { de: { scratchpad: de }, en: { scratchpad: en } }
