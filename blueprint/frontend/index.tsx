import { BlueprintPage } from "./BlueprintPage"
import { de } from "./texts.de"
import { en } from "./texts.en"

// /blueprint?board=<id> öffnet ein Board direkt (Verweis aus einer Idee oder aus der Antwort des Agenten).
export const routes = [{ path: "/blueprint", element: <BlueprintPage /> }]

export const nav = [
  {
    path: "/blueprint",
    icon: "PenTool",
    labelKey: "blueprint",
    group: "working", area: "schreiben",
    roles: [] as ("admin" | "user")[],
  },
]

export const i18n = { de: { blueprint: de }, en: { blueprint: en } }
