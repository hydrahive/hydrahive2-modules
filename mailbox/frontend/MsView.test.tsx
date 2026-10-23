import { renderToStaticMarkup } from "react-dom/server"
import { describe, expect, it, vi } from "vitest"

vi.mock("@/shared/api-client", () => ({ api: { get: vi.fn(), post: vi.fn(), patch: vi.fn(), put: vi.fn(), delete: vi.fn() } }))
let role = "user"
vi.mock("@/features/auth/useAuthStore", () => ({
  useAuthStore: Object.assign((sel: (s: { role: string }) => unknown) => sel({ role }), { getState: () => ({ token: "T0K", role }) }),
}))

const { MsSignInView } = await import("./MsSignInView")
const { MsAppButton } = await import("./MsAppButton")
const { MsAppDialog } = await import("./MsAppDialog")
const { MsAccountPart } = await import("./MsAccountPart")

const FLOW = { flow_id: "f".repeat(24), user_code: "ABCD-EFGH", verification_uri: "https://microsoft.com/devicelogin", expires_in: 900, interval: 5 }
const view = (p: Partial<Parameters<typeof MsSignInView>[0]>) =>
  renderToStaticMarkup(<MsSignInView state="idle" flow={null} errKey={null} detail="" onStart={() => {}} {...p} />)

describe("Microsoft-Anmeldung – Anzeige", () => {
  it("Anfang: nur der Knopf", () => {
    const h = view({})
    expect(h).toContain('data-mbx-ms-start="1"')
    expect(h).toContain("ms.signIn")
  })

  it("Warten: Code groß und Link zu Microsoft (neues Fenster, ohne Referrer)", () => {
    const h = view({ state: "waiting", flow: FLOW })
    expect(h).toContain('data-mbx-ms-code="1"')
    expect(h).toContain("ABCD-EFGH")
    expect(h).toMatch(/<a href="https:\/\/microsoft\.com\/devicelogin" target="_blank" rel="noopener noreferrer"/)
  })

  it("fremder Link wird nicht verlinkt", () => {
    const h = view({ state: "waiting", flow: { ...FLOW, verification_uri: "https://boese.example/x" } })
    expect(h).not.toContain("boese.example")
  })

  it("abgelaufen/abgelehnt mit Neustart; nicht eingerichtet ohne Neustart", () => {
    expect(view({ state: "expired" })).toContain("ms.expired")
    expect(view({ state: "denied" })).toContain("ms.denied")
    expect(view({ state: "expired" })).toContain("ms.retry")
    const off = view({ state: "error", errKey: "ms.err.notConfigured" })
    expect(off).toContain("ms.err.notConfigured")
    expect(off).not.toContain("ms.retry")
  })

  it("Konto-Teil: ohne App-Einrichtung klarer Hinweis statt Knopf", () => {
    const h = renderToStaticMarkup(<MsAccountPart address="a@outlook.de" label="" ready={false} onSaved={() => {}} />)
    expect(h).toContain('data-mbx-ms-off="1"')
    expect(h).not.toContain('data-mbx-ms-start="1"')
    const ok = renderToStaticMarkup(<MsAccountPart address="a@outlook.de" label="" ready onSaved={() => {}} />)
    expect(ok).toContain('data-mbx-ms-start="1"')
  })
})

describe("Microsoft-App (Admin)", () => {
  it("Knopf nur für Admins", () => {
    role = "user"
    expect(renderToStaticMarkup(<MsAppButton />)).toBe("")
    role = "admin"
    expect(renderToStaticMarkup(<MsAppButton />)).toContain('data-mbx-ms-app-open="1"')
  })

  it("Dialog: Anleitung, Feld für die Client-ID, Prüfen-Knopf", () => {
    const h = renderToStaticMarkup(<MsAppDialog onClose={() => {}} />)
    expect(h).toContain('data-mbx-ms-cid="1"')
    expect(h).toContain('data-mbx-ms-check="1"')
    expect(h).toContain("entra.microsoft.com")
    for (const k of ["app.step1", "app.step2", "app.step3", "app.step4"]) expect(h).toContain(k)
  })
})
