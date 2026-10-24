import { Navigate } from "react-router-dom"
import { studioI18n } from "./i18n"
import { StudioPage } from "./StudioPage"
import { GuidedPage } from "./neu/GuidedPage"

// G6: /studio = geführter Weg, /studio/profi = bisherige Oberfläche, /studio/neu = altes Lesezeichen der Testphase
export const routes = [
  { path: "/studio", element: <GuidedPage /> },
  { path: "/studio/profi", element: <StudioPage /> },
  { path: "/studio/neu", element: <Navigate to="/studio" replace /> },
]

export const nav = [
  { path: "/studio", icon: "Clapperboard", labelKey: "studio", group: "working", area: "medien", roles: [] as ("admin" | "user")[], cockpit: true },
]

export const i18n = studioI18n
