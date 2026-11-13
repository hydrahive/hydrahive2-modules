import { tvwerkstattI18n } from "./i18n"
import { TvWerkstattPage } from "./TvWerkstattPage"

export const routes = [{ path: "/tvwerkstatt", element: <TvWerkstattPage /> }]
export const nav = [
  {
    path: "/tvwerkstatt", icon: "Tv", labelKey: "tvwerkstatt", group: "working", area: "zuhause",
    roles: ["admin"] as ("admin" | "user")[],
  },
]

// Menütitel kommt aus tvwerkstatt:title (Kern shared/nav-label.ts).
export const i18n = tvwerkstattI18n
