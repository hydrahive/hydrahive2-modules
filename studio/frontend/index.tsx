import { studioI18n } from "./i18n"
import { StudioPage } from "./StudioPage"
import { GuidedPage } from "./neu/GuidedPage"

// /studio/neu = geführter Weg (Bauplan G); wird mit G6 zu /studio
export const routes = [{ path: "/studio", element: <StudioPage /> }, { path: "/studio/neu", element: <GuidedPage /> }]

export const nav = [
  { path: "/studio", icon: "Clapperboard", labelKey: "studio", group: "working", roles: [] as ("admin" | "user")[], cockpit: true },
]

export const i18n = studioI18n
