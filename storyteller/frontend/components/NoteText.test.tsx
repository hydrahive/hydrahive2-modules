// T1d: Text eines Hinweises/einer Notiz als Markdown – Überschriften/Fett/Listen, Links sicher, keine Bilder laden.
import { renderToStaticMarkup } from "react-dom/server"
import { describe, expect, it } from "vitest"
import { NoteText } from "./NoteText"

const html = (text: string) => renderToStaticMarkup(<NoteText text={text} />)

describe("NoteText", () => {
  it("stellt Markdown dar statt Rohzeichen", () => {
    const out = html("## Verfahren\n\nDer **Lotse** steigt über die Leiter.\n\n- eins\n- zwei")
    expect(out).toContain("<h2>Verfahren</h2>")
    expect(out).toContain("<strong>Lotse</strong>")
    expect(out).toContain("<li>eins</li>")
    expect(out).not.toContain("**")
  })
  it("Links öffnen in neuem Tab mit noopener, nur http(s)", () => {
    const out = html("[Quelle](https://example.org/a) und [böse](javascript:alert(1))")
    expect(out).toContain('href="https://example.org/a"')
    expect(out).toContain('target="_blank"')
    expect(out).toContain('rel="noopener noreferrer"')
    expect(out).not.toContain("javascript:")
  })
  it("relative Adressen und mailto werden nicht verlinkt (nur http(s), wie bei den Quellen)", () => {
    const out = html("[intern](/api/admin/users) [mail](mailto:a@b.de)")
    expect(out).not.toContain("<a")
    expect(out).toContain("intern")
  })
  it("lädt keine Bilder (kein Nachladen fremder Adressen)", () => {
    const out = html("![Bild](https://tracker.example/pixel.png)")
    expect(out).not.toContain("<img")
    expect(out).not.toContain("tracker.example")
  })
  it("kein rohes HTML", () => {
    const out = html("<b>fett</b><script>alert(1)</script>")
    expect(out).not.toContain("<script")
    expect(out).not.toContain("<b>")
  })
})
