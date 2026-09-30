import { renderToStaticMarkup } from "react-dom/server"
import { describe, expect, it } from "vitest"
import { TaskHistory } from "./components/TaskHistory"

describe("TaskHistory", () => {
  it("zeigt nichts ohne frühere Fassungen", () => {
    expect(renderToStaticMarkup(<TaskHistory taskId="t1" count={0} />)).toBe("")
  })

  it("zeigt den Zähler, zugeklappt ohne Inhalt", () => {
    const html = renderToStaticMarkup(<TaskHistory taskId="t1" count={3} />)
    expect(html).toContain("Verlauf (3)")
    expect(html).not.toContain("lädt")
  })
})
