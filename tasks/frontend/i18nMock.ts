// Ersatz für react-i18next in den Tests dieses Moduls: die echten Texte aus texts.de.ts und texts.en.ts,
// Sprache umschaltbar. Einbinden mit: vi.mock("react-i18next", async () => await import("./i18nMock"))
import { de } from "./texts.de"
import { en } from "./texts.en"

let lang: "de" | "en" = "de"

export function setLang(next: "de" | "en"): void {
  lang = next
}

export function useTranslation() {
  const texts: Record<string, string> = lang === "de" ? de : en
  const t = (key: string, vars?: Record<string, unknown>) =>
    (texts[key] ?? key).replace(/\{\{(\w+)\}\}/g, (_match, name: string) => String(vars?.[name] ?? ""))
  return { t, i18n: { language: lang } }
}
