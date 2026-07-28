import { VoicePage } from "./VoicePage"
import { i18n } from "./i18n"

export const routes = [
  { path: "/voice", element: <VoicePage /> },
]

export const nav = [
  {
    path: "/voice",
    icon: "Mic",
    labelKey: "voice",
    group: "working",
    roles: [] as ("admin" | "user")[],
    cockpit: true,
  },
]

export { i18n }
