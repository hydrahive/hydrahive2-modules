import { DeepResearchPage } from "./DeepResearchPage"

export const routes = [{ path: "/deepresearch", element: <DeepResearchPage /> }]

export const nav = [
  { path: "/deepresearch", icon: "Telescope", labelKey: "deepresearch", group: "working", roles: [] },
]

export const i18n = {
  de: {
    deepresearch: {
      title: "Deep Research",
      placeholder: "Worüber soll recherchiert werden?",
      start: "Recherche starten",
      running: "Läuft …",
      working: "Recherchiere",
      empty: "Noch keine Recherchen",
      untitled: "Ohne Titel",
      hint: "Stelle links eine Frage, um eine Recherche zu starten.",
      sources: "Quellen",
      failed: "Recherche fehlgeschlagen",
    },
  },
  en: {
    deepresearch: {
      title: "Deep Research",
      placeholder: "What should I research?",
      start: "Start research",
      running: "Running …",
      working: "Researching",
      empty: "No research yet",
      untitled: "Untitled",
      hint: "Ask a question on the left to start a research run.",
      sources: "Sources",
      failed: "Research failed",
    },
  },
}
