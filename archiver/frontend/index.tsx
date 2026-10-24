import { ArchiverPage } from "./ArchiverPage"

export const routes = [{ path: "/archiver", element: <ArchiverPage /> }]
export const nav = [
  { path: "/archiver", icon: "HardDrive", labelKey: "archiver", group: "working", area: "wissen", roles: [] },
]

export const i18n = {
  de: { archiver: { nav: "Archiver" } },
  en: { archiver: { nav: "Archiver" } },
}
