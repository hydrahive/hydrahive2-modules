import { MediacenterPage } from "./MediacenterPage"
import { i18n } from "./i18n"

export const routes = [
  { path: "/mediacenter", element: <MediacenterPage /> },
]

export const nav = [
  {
    path: "/mediacenter",
    icon: "MonitorPlay",
    labelKey: "mediacenter",
    group: "working",
    roles: [] as ("admin" | "user")[],
    cockpit: true,
  },
]

export { i18n }
