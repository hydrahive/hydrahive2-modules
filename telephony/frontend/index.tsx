import { VoIPPage } from "./VoIPPage"
import { i18n } from "./i18n"

export const routes = [{ path: "/voip", element: <VoIPPage /> }]

export const nav = [
  {
    path: "/voip",
    icon: "PhoneCall",
    labelKey: "voip",
    group: "working",
    roles: [] as ("admin" | "user")[],
    cockpit: true,
  },
]

export { i18n }
