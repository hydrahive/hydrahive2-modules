import { DiagrammePage } from "./DiagrammePage"
import { diagrammeI18n } from "./i18n"

export const routes = [{ path: "/diagramme", element: <DiagrammePage /> }]
export const nav = [
  { path: "/diagramme", icon: "Network", labelKey: "diagramme", group: "working", area: "schreiben", roles: [] as ("admin" | "user")[] },
]

// Menütitel kommt aus diagramme:title (Kern shared/nav-label.ts) – keinen eigenen nav-Namespace anlegen.
export const i18n = diagrammeI18n
