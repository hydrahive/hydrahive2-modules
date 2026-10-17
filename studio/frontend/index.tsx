import { studioI18n } from "./i18n"
import { StudioPage } from "./StudioPage"

export const routes = [{ path: "/studio", element: <StudioPage /> }]

export const nav = [
  { path: "/studio", icon: "Clapperboard", labelKey: "studio", group: "working", roles: [] as ("admin" | "user")[], cockpit: true },
]

export const i18n = studioI18n
