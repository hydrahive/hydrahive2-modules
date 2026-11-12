// Das Dock als statisches Markup: neben dem Board mit Griff und fester Breite, über dem Board ohne beides.
import { renderToStaticMarkup } from "react-dom/server"
import { describe, expect, it, vi } from "vitest"

vi.mock("@/features/chat/ChatPane", () => ({ ChatPane: () => null }))
vi.mock("@/features/auth/useAuthStore", () => ({ useAuthStore: () => "user" }))
vi.mock("./api", () => ({ blueprintApi: {} }))
import { AgentDock } from "./AgentDock"
import { de, type T } from "./texts.de"

const t: T = (key, vars) => de[key].replace(/\{\{(\w+)\}\}/g, (_match, name: string) => String(vars?.[name] ?? ""))
const dock = (over: boolean) => renderToStaticMarkup(
  <AgentDock boardId={7} projectId="p-alpha" width={420} over={over} t={t} onWidth={() => undefined}
    onClose={() => undefined} />,
)
const root = (html: string) => html.match(/^<aside[^>]*>/)?.[0] ?? ""

describe("AgentDock", () => {
  it("steht neben dem Board mit fester Breite und Griff zum Ziehen", () => {
    const html = dock(false)
    expect(root(html)).toContain("width:420px")
    expect(root(html)).toContain("shrink-0")
    expect(html).toContain(`role="separator"`)
    expect(html).toContain(`aria-label="${de.chat_resize}"`)
  })

  it("füllt über dem Board die ganze Breite und hat keinen Griff", () => {
    const html = dock(true)
    expect(root(html)).not.toContain("width:")
    expect(root(html)).not.toContain("shrink-0")
    expect(root(html)).toContain("flex-1")
    expect(root(html)).toContain("min-w-0")
    expect(html).not.toContain(`role="separator"`)
  })

  it("lässt sich in beiden Lagen schließen und zeigt, dass es lädt", () => {
    for (const over of [false, true]) {
      const html = dock(over)
      expect(html).toContain(`aria-label="${de.chat_close}"`)
      expect(html).toContain(de.chat_loading)
    }
  })
})
