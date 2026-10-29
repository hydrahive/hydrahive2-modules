import { FernseherPage } from "./FernseherPage"
import { fernseherI18n } from "./i18n"

export const routes = [{ path: "/fernseher", element: <FernseherPage /> }]
export const nav = [
  { path: "/fernseher", icon: "Tv", labelKey: "fernseher", group: "working", area: "zuhause", roles: [] as ("admin" | "user")[] },
]

// Menütitel kommt aus fernseher:title (Kern shared/nav-label.ts).
export const i18n = fernseherI18n
