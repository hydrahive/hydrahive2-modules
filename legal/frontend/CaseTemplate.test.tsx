import { renderToStaticMarkup } from "react-dom/server"
import { describe, expect, it } from "vitest"
import { CaseTemplate } from "./CaseTemplate"

describe("CaseTemplate (Agenten-Templates, Recht 0.5.0)", () => {
  it("zeigt Primärmodell, Ersatzkette und Template statt einer Modellwahl", () => {
    const html = renderToStaticMarkup(<CaseTemplate info={{ id: "modul-schreiber", label: "Modul-Schreiber",
      chain: ["claude-sonnet-5", "openai-codex/gpt-5.6-terra", "MiniMax-M3.1-Flash"] }} />)
    expect(html).toContain("claude-sonnet-5")
    expect(html).toContain("openai-codex/gpt-5.6-terra → MiniMax-M3.1-Flash")
    expect(html).toContain("Modul-Schreiber")
    expect(html).not.toContain("<select")
  })
})
