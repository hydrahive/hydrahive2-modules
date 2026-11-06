import { VibePage } from "./VibePage"
import { vibeI18n } from "./i18n"

export const routes = [{ path: "/vibe", element: <VibePage /> }]
export const nav = [
  { path: "/vibe", icon: "Sparkles", labelKey: "vibe", group: "working", area: "agenten", roles: ["admin"] as ("admin" | "user")[] },
]

// Menütitel kommt aus vibe:title (Kern shared/nav-label.ts).
export const i18n = vibeI18n
