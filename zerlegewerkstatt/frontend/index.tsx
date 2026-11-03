import { ZerlegewerkstattPage } from "./ZerlegewerkstattPage"

export const routes = [{ path: "/zerlegewerkstatt", element: <ZerlegewerkstattPage /> }]

export const nav = [
  {
    path: "/zerlegewerkstatt",
    icon: "ScanSearch",
    labelKey: "zerlegewerkstatt",
    group: "working",
    area: "wissen",
    roles: [] as ("admin" | "user")[],
  },
]

export { i18n } from "./i18n"
