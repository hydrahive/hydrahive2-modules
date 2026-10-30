import { renderToStaticMarkup } from "react-dom/server"
import { describe, expect, it, vi } from "vitest"

vi.mock("react-i18next", () => ({ useTranslation: () => ({ t: (k: string, o?: Record<string, unknown>) => (o ? `${k}:${JSON.stringify(o)}` : k) }) }))
vi.mock("@/shared/api-client", () => ({ api: { get: vi.fn(() => new Promise(() => {})), post: vi.fn() } }))
import { GitHubBoxView } from "./GitHubBox"
import { SubmitDialogView } from "./SubmitDialog"
import { ReportDialogView } from "./ReportDialog"
import { SubmissionList } from "./SubmissionList"
import { submitProgress, submitResult, SUBMIT_STEPS, type Submission } from "./githubLogic"

const noop = () => {}

describe("GitHub-Verbindung", () => {
  it("nicht verbunden: Verbinden-Knopf, Hinweis Konto anlegen", () => {
    const html = renderToStaticMarkup(<GitHubBoxView gh={{ connected: false, login: "", pending: false, configured: true }}
      code={null} busy={false} onConnect={noop} onDisconnect={noop} />)
    expect(html).toContain("github.connect")
    expect(html).toContain('href="https://github.com/signup"')
    expect(html).not.toContain("github.disconnect")
  })

  it("Code anzeigen: groß, Link zu GitHub, wartet", () => {
    const html = renderToStaticMarkup(<GitHubBoxView gh={{ connected: false, login: "", pending: true, configured: true }}
      code={{ user_code: "ABCD-1234", verification_uri: "https://github.com/login/device", expires_in: 900 }}
      busy={false} onConnect={noop} onDisconnect={noop} />)
    expect(html).toContain("ABCD-1234")
    expect(html).toContain('href="https://github.com/login/device"')
    expect(html).toContain('target="_blank"')
    expect(html).toContain("github.waiting")
    expect(html).not.toMatch(/>github.connect</)
  })

  it("wartet, aber Code fehlt (Seite neu geladen): wieder Verbinden-Knopf statt leerer Anzeige", () => {
    const html = renderToStaticMarkup(<GitHubBoxView gh={{ connected: false, login: "", pending: true, configured: true }}
      code={null} busy={false} onConnect={noop} onDisconnect={noop} />)
    expect(html).toMatch(/>github.connect</)
  })

  it("Code abgelaufen (wartet nicht mehr): alter Code weg, wieder Verbinden-Knopf", () => {
    const html = renderToStaticMarkup(<GitHubBoxView gh={{ connected: false, login: "", pending: false, configured: true }}
      code={{ user_code: "ABCD-1234", verification_uri: "https://github.com/login/device", expires_in: 900 }}
      busy={false} onConnect={noop} onDisconnect={noop} />)
    expect(html).not.toContain("ABCD-1234")
    expect(html).toMatch(/>github.connect</)
  })

  it("verbunden: Name, Trennen, Hinweis wo man den Zugang bei GitHub entfernt", () => {
    const html = renderToStaticMarkup(<GitHubBoxView gh={{ connected: true, login: "nutzer", pending: false, configured: true }}
      code={null} busy={false} onConnect={noop} onDisconnect={noop} />)
    expect(html).toContain('github.connected:{&quot;login&quot;:&quot;nutzer&quot;}')
    expect(html).toContain("github.disconnect")
    expect(html).toContain('href="https://github.com/settings/applications"')
  })

  it("App nicht eingerichtet: kein Knopf, Hinweis", () => {
    const html = renderToStaticMarkup(<GitHubBoxView gh={{ connected: false, login: "", pending: false, configured: false }}
      code={null} busy={false} onConnect={noop} onDisconnect={noop} />)
    expect(html).toContain("err.labor_github_not_configured")
    expect(html).not.toMatch(/>github.connect</)
  })
})

describe("Änderung einreichen", () => {
  const view = (p: Partial<Parameters<typeof SubmitDialogView>[0]>) => renderToStaticMarkup(<SubmitDialogView titleId="t"
    target="core" title="" body="" running={false} progress="" error="" detail={null} result={null}
    onTarget={noop} onTitle={noop} onBody={noop} onSubmit={noop} onClose={noop} {...p} />)

  it("echter Dialog, Ziel wählbar, Senden erst mit Titel", () => {
    const html = view({})
    expect(html).toContain('role="dialog"')
    expect(html).toContain("submit.target_core")
    expect(html).toContain("submit.target_modules")
    expect(html).toMatch(/<button[^>]*disabled=""[^>]*>submit.send</)
    expect(view({ title: "Fix" })).not.toMatch(/<button[^>]*disabled=""[^>]*>submit.send</)
    expect(view({ title: "x".repeat(121) })).toMatch(/<button[^>]*disabled=""[^>]*>submit.send</)
  })

  it("läuft: Schritte, kein Senden, Schließen gesperrt", () => {
    const html = view({ title: "Fix", running: true, progress: "tests" })
    for (const k of SUBMIT_STEPS) expect(html).toContain(`submit.step.${k}`)
    expect(html).not.toContain(">submit.send<")
    expect(html).toMatch(/<button[^>]*disabled=""[^>]*>submit.close</)
  })

  it("geschützte Dateien: Liste der Gründe", () => {
    const html = view({ title: "Fix", error: "labor_submit_protected", detail: [".github/x.yml"] })
    expect(html).toContain("err.labor_submit_protected")
    expect(html).toContain(".github/x.yml")
  })

  it("Tests rot: Zahl der roten Tests", () => {
    const html = view({ title: "Fix", error: "labor_submit_tests_red", detail: { failed: 2, passed: 10, failures: ["a::b"] } })
    expect(html).toContain("a::b")
  })

  it("fertig: Link zum PR", () => {
    const html = view({ title: "Fix", result: { number: 7, url: "https://github.com/hydrahive/hydrahive2.0/pull/7" } })
    expect(html).toContain('href="https://github.com/hydrahive/hydrahive2.0/pull/7"')
    expect(html).toContain("submit.done")
  })
})

describe("Fehler melden", () => {
  it("Dialog mit Feldern, Senden erst mit Titel und Beschreibung", () => {
    const v = (t: string, w: string) => renderToStaticMarkup(<ReportDialogView titleId="r" target="core" title={t} what={w}
      expected="" steps="" busy={false} error="" result={null} onChange={noop} onSubmit={noop} onClose={noop} />)
    const html = v("", "")
    for (const k of ["report.what", "report.expected", "report.steps", "report.privacy"]) expect(html).toContain(k)
    expect(html).toMatch(/<button[^>]*disabled=""[^>]*>report.send</)
    expect(v("T", "")).toMatch(/<button[^>]*disabled=""[^>]*>report.send</)
    expect(v("T", "W")).not.toMatch(/<button[^>]*disabled=""[^>]*>report.send</)
    expect(v("", "W")).toMatch(/<button[^>]*disabled=""[^>]*>report.send</)
  })
})

describe("Meine Einreichungen", () => {
  const items: Submission[] = [
    { id: 1, kind: "pr", target: "core", title: "A", number: 7, url: "https://x/7", state: "merged", created_at: "2026-10-30T18:00:00Z" },
    { id: 2, kind: "issue", target: "modules", title: "B", number: 9, url: "https://x/9", state: "submitted", created_at: "2026-10-30T18:00:00Z" },
  ]
  it("Stand je Einreichung mit Link", () => {
    const html = renderToStaticMarkup(<SubmissionList items={items} busy={false} onRefresh={noop} />)
    expect(html).toContain("subs.state.merged")
    expect(html).toContain("subs.kind.issue")
    expect(html).toContain('href="https://x/7"')
    expect(html).toContain("subs.refresh")
  })
  it("leer", () => {
    expect(renderToStaticMarkup(<SubmissionList items={[]} busy={false} onRefresh={noop} />)).toContain("subs.empty")
  })
})

describe("Logik", () => {
  it("Fortschritt", () => {
    expect(SUBMIT_STEPS).toEqual(["check", "tests", "fork", "push", "pr"])
    expect(submitProgress("fork")).toBe(2)
    expect(submitProgress("")).toBe(0)
    expect(submitProgress("unbekannt")).toBe(0)
  })
  it("Ergebnis aus dem Zustand", () => {
    expect(submitResult({ number: 7, url: "u" })).toEqual({ number: 7, url: "u" })
    expect(submitResult({ detail: ["x"] })).toBeNull()
    expect(submitResult({})).toBeNull()
    expect(submitResult({ number: 7 })).toBeNull()
    expect(submitResult({ url: "u" })).toBeNull()
    expect(submitResult({ number: "7", url: "u" })).toBeNull()
  })
})
