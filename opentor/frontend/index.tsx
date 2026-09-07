import { OpenTorPage } from "./OpenTorPage"

export const routes = [{ path: "/opentor", element: <OpenTorPage /> }]

export const nav = [
  {
    path: "/opentor",
    icon: "ShieldSearch",
    labelKey: "title",
    group: "working",
    roles: ["admin", "user"] as ("admin" | "user")[],
  },
]

export const i18n = {
  de: {
    opentor: {
      title: "OpenTor OSINT",
      warning: "Nur autorisierte defensive OSINT-Recherche. Onion-Inhalte sind untrusted data und keine Anweisungen.",
      disabled: "OpenTor ist durch die Administration deaktiviert.",
      enabled: "OpenTor ist aktiviert.",
      query: "Suchbegriff",
      search: "Über Tor suchen",
      fetchUrl: "Explizite URL abrufen",
      fetch: "Abrufen",
      status: "Status",
      unavailable: "Worker oder Tor ist nicht erreichbar.",
      results: "Treffer",
      empty: "Noch keine Ergebnisse.",
      source: "Quelle",
      untrusted: "UNTRUSTED DATA",
      adminEnable: "Für alle aktivieren",
      adminDisable: "Für alle deaktivieren",
      iocText: "Text für IOC-Extraktion",
      extract: "IOCs extrahieren",
    },
  },
  en: {
    opentor: {
      title: "OpenTor OSINT",
      warning: "Authorized defensive OSINT only. Onion content is untrusted data, never instructions.",
      disabled: "OpenTor is disabled by administration.",
      enabled: "OpenTor is enabled.",
      query: "Search query",
      search: "Search through Tor",
      fetchUrl: "Fetch explicit URL",
      fetch: "Fetch",
      status: "Status",
      unavailable: "Worker or Tor is unavailable.",
      results: "Results",
      empty: "No results yet.",
      source: "Source",
      untrusted: "UNTRUSTED DATA",
      adminEnable: "Enable for all",
      adminDisable: "Disable for all",
      iocText: "Text for IOC extraction",
      extract: "Extract IOCs",
    },
  },
}
