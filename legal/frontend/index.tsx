import { LegalPage } from "./LegalPage"

export const routes = [{ path: "/recht/*", element: <LegalPage /> }]
export const nav = [
  { path: "/recht", icon: "Scale", labelKey: "legal", group: "working", roles: [] },
]
export const i18n = {
  de: { legal: { title: "Recht" } },
  en: { legal: { title: "Law" } },
}
