import { HomeAssistantPage } from "./HomeAssistantPage"

export const routes = [{ path: "/homeassistant", element: <HomeAssistantPage /> }]

export const nav = [
  {
    path: "/homeassistant",
    icon: "House",
    labelKey: "homeassistant",
    group: "working",
    roles: [] as ("admin" | "user")[],
  },
]

export const i18n = {
  de: {
    homeassistant: {
      title: "Home Assistant",
      subtitle: "Geräte sehen & schalten",
      refresh: "Aktualisieren",
      search_placeholder: "Gerät suchen (Name oder entity_id)…",
      favorites_only: "Nur Favoriten",
      empty: "Keine passenden Geräte gefunden.",
    },
  },
  en: {
    homeassistant: {
      title: "Home Assistant",
      subtitle: "View & control devices",
      refresh: "Refresh",
      search_placeholder: "Search device (name or entity_id)…",
      favorites_only: "Favorites only",
      empty: "No matching devices found.",
    },
  },
}
