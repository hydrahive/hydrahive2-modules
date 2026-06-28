import { BlueprintPage } from "./BlueprintPage"

export const routes = [{ path: "/blueprint", element: <BlueprintPage /> }]

export const nav = [
  {
    path: "/blueprint",
    icon: "PenTool",
    labelKey: "blueprint",
    group: "working",
    roles: [] as ("admin" | "user")[],
  },
]

export const i18n = {
  de: {
    blueprint: {
      title: "Blueprint",
      subtitle: "Layouts & Abläufe visuell skizzieren",
    },
  },
  en: {
    blueprint: {
      title: "Blueprint",
      subtitle: "Sketch layouts & flows visually",
    },
  },
}
