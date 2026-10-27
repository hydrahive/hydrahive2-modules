import { RadiostreamPage } from "./RadiostreamPage"
import { radiostreamI18n } from "./i18n"

export const routes = [{ path: "/radiostream", element: <RadiostreamPage /> }]
export const nav = [
  { path: "/radiostream", icon: "Radio", labelKey: "radiostream", group: "working", area: "medien", roles: [] as ("admin" | "user")[] },
]

// Menütitel kommt aus radiostream:title (Kern shared/nav-label.ts).
export const i18n = radiostreamI18n
