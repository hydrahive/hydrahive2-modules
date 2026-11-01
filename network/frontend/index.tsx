import { NetworkPage } from "./NetworkPage"
import { networkI18n } from "./i18n"

export const routes = [{ path: "/network", element: <NetworkPage /> }]
export const nav = [
  { path: "/network", icon: "Network", labelKey: "network", group: "working", area: "zuhause", roles: [] as ("admin" | "user")[] },
]

// Menütitel kommt aus network:title (Kern shared/nav-label.ts).
export const i18n = networkI18n
