import { renderToStaticMarkup } from "react-dom/server"
import { beforeEach, describe, expect, it, vi } from "vitest"

vi.mock("react-i18next", async () => await import("./i18nMock"))
vi.mock("@/shared/api-client", () => ({ api: {} }))
import { TaskHistory } from "./components/TaskHistory"
import { setLang } from "./i18nMock"

describe("TaskHistory", () => {
  beforeEach(() => setLang("de"))

  it("zeigt nichts ohne frühere Fassungen", () => {
    expect(renderToStaticMarkup(<TaskHistory taskId="t1" count={0} />)).toBe("")
  })

  it("zeigt den Zähler, zugeklappt ohne Inhalt", () => {
    const html = renderToStaticMarkup(<TaskHistory taskId="t1" count={3} />)
    expect(html).toContain("Verlauf (3)")
    expect(html).not.toContain("lädt")
  })

  it("englisch", () => {
    setLang("en")
    const html = renderToStaticMarkup(<TaskHistory taskId="t1" count={3} />)
    expect(html).toContain("History (3)")
    expect(html).not.toContain("Verlauf")
  })
})
