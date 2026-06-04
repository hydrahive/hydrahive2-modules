import { ScratchpadPage } from "./ScratchpadPage"

export const routes = [{ path: "/scratchpad", element: <ScratchpadPage /> }]
export const nav = [
  { path: "/scratchpad", icon: "StickyNote", labelKey: "scratchpad", group: "working", roles: [] },
]
export const i18n = {
  de: {
    scratchpad: {
      title: "Scratchpad",
      saved: "gespeichert",
      saving: "speichert…",
      my_ideas: "Meine Ideen",
      placeholder: "Ideen, Notizen, Aufgaben (Markdown, `- [ ]` für Checkboxen)…",
      empty_preview: "_(leer)_",
      agent_notes: "Agent-Notizen",
      agent_notes_hint: "(nur der Agent schreibt hier)",
      agent_notes_empty: "_(noch keine Agent-Notizen)_",
      clear: "Leeren",
      clear_confirm: "Agent-Notizen wirklich leeren?",
    },
  },
  en: {
    scratchpad: {
      title: "Scratchpad",
      saved: "saved",
      saving: "saving…",
      my_ideas: "My Ideas",
      placeholder: "Ideas, notes, tasks (Markdown, `- [ ]` for checkboxes)…",
      empty_preview: "_(empty)_",
      agent_notes: "Agent Notes",
      agent_notes_hint: "(only the agent writes here)",
      agent_notes_empty: "_(no agent notes yet)_",
      clear: "Clear",
      clear_confirm: "Really clear agent notes?",
    },
  },
}
