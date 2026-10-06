import { StorytellerPage } from "./StorytellerPage"
import { textsDe } from "./texts.de"
import { textsEn } from "./texts.en"

export const routes = [{ path: "/storyteller", element: <StorytellerPage /> }]

export const nav = [
  {
    path: "/storyteller",
    icon: "Feather",
    labelKey: "storyteller",
    group: "working",
    roles: [] as ("admin" | "user")[],
  },
]

export const i18n = {
  de: { storyteller: textsDe },
  en: { storyteller: textsEn },
}
