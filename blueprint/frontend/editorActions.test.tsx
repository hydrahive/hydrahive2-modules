import { renderToStaticMarkup } from "react-dom/server"
import { describe, expect, it } from "vitest"
import { EditorActions } from "./EditorActions"
import { de, type T } from "./texts.de"

const t: T = (key, vars) => de[key].replace(/\{\{(\w+)\}\}/g, (_match, name: string) => String(vars?.[name] ?? ""))
const noop = () => undefined
const actions = (over: Partial<Parameters<typeof EditorActions>[0]> = {}) => renderToStaticMarkup(
  <EditorActions versionsOpen={false} chatOpen={false} copied="" t={t} onVersions={noop} onChat={noop} onCopy={noop}
    {...over} />,
)
const button = (html: string, label: string) =>
  html.match(new RegExp(`<button[^>]*>(?:<svg.*?</svg>)?${label}</button>`))?.[0] ?? ""

describe("EditorActions", () => {
  it("zeigt die drei Knöpfe der Kopfzeile", () => {
    const html = actions()
    for (const label of [de.versions_title, de.chat_open, de.copy]) expect(button(html, label), label).not.toBe("")
    expect(button(html, de.chat_open)).toContain(`title="${de.chat_title}"`)
  })

  it("zeigt je Knopf, ob frühere Fassungen und Chat offen sind", () => {
    const closed = actions()
    expect(button(closed, de.versions_title)).toContain('aria-pressed="false"')
    expect(button(closed, de.chat_open)).toContain('aria-pressed="false"')
    const versions = actions({ versionsOpen: true })
    expect(button(versions, de.versions_title)).toContain('aria-pressed="true"')
    expect(button(versions, de.chat_open)).toContain('aria-pressed="false"')
    const chat = actions({ chatOpen: true })
    expect(button(chat, de.chat_open)).toContain('aria-pressed="true"')
    expect(button(chat, de.versions_title)).toContain('aria-pressed="false"')
  })

  it("meldet am Kopier-Knopf, ob das Kopieren geklappt hat", () => {
    expect(button(actions({ copied: "ok" }), de.copied)).not.toBe("")
    expect(button(actions({ copied: "fail" }), de.copy_failed)).not.toBe("")
  })
})
