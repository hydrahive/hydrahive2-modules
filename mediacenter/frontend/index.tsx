import { MediacenterPage } from "./MediacenterPage"

export const routes = [
  { path: "/mediacenter", element: <MediacenterPage /> },
]

export const nav = [
  {
    path: "/mediacenter",
    icon: "MonitorPlay",
    labelKey: "mediacenter",
    group: "working",
    roles: [] as ("admin" | "user")[],
    // Cockpit-Modul: eigener Reiter im Cockpit-Top-Menü, Seite im bare Cockpit-Chrome.
    cockpit: true,
  },
]

export const i18n = {
  de: {
    mediacenter: {
      title: "Mediacenter",
      subtitle: "Verwaltung für Radarr, Sonarr, SABnzbd und Usenet-Indexer",
      dummyBadge: "Platzhalter",
      dummyNote: "Dieses Modul ist noch ein Platzhalter. Die Anbindung der Dienste folgt in einem späteren Schritt.",
      comingSoon: "Bald verfügbar",
      services: {
        radarr: { name: "Radarr", desc: "Filme automatisch suchen, laden und verwalten." },
        sonarr: { name: "Sonarr", desc: "Serien überwachen und neue Episoden holen." },
        sabnzbd: { name: "SABnzbd", desc: "Usenet-Downloader — Warteschlange und Verlauf." },
        indexer: { name: "Indexer-Suche", desc: "Usenet-Indexer nach Releases durchsuchen." },
      },
    },
  },
  en: {
    mediacenter: {
      title: "Media Center",
      subtitle: "Management for Radarr, Sonarr, SABnzbd and Usenet indexers",
      dummyBadge: "Placeholder",
      dummyNote: "This module is still a placeholder. Service integration will follow in a later step.",
      comingSoon: "Coming soon",
      services: {
        radarr: { name: "Radarr", desc: "Automatically find, download and manage movies." },
        sonarr: { name: "Sonarr", desc: "Monitor TV shows and grab new episodes." },
        sabnzbd: { name: "SABnzbd", desc: "Usenet downloader — queue and history." },
        indexer: { name: "Indexer search", desc: "Search Usenet indexers for releases." },
      },
    },
  },
}
