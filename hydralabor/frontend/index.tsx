import { HydraLaborPage } from "./HydraLaborPage"
import { hydralaborI18n } from "./i18n"

export const routes = [{ path: "/hydralabor", element: <HydraLaborPage /> }]
export const nav = [
  { path: "/hydralabor", icon: "FlaskConical", labelKey: "hydralabor", group: "working", area: "agenten", roles: ["admin"] as ("admin" | "user")[] },
]

// Menütitel kommt aus hydralabor:title (Kern shared/nav-label.ts).
export const i18n = hydralaborI18n
