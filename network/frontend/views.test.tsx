import { renderToStaticMarkup } from "react-dom/server"
import { describe, expect, it, vi } from "vitest"

vi.mock("react-i18next", () => ({ useTranslation: () => ({ t: (k: string, o?: Record<string, unknown>) => (o ? `${k}:${JSON.stringify(o)}` : k), i18n: { language: "de" } }) }))
vi.mock("@/shared/api-client", () => ({ api: { get: vi.fn(() => new Promise(() => {})), post: vi.fn(), put: vi.fn(), postForm: vi.fn() } }))
vi.mock("recharts", () => {
  const Box = ({ children }: { children?: unknown }) => <div data-chart>{children as never}</div>
  const Nil = () => null
  return { ResponsiveContainer: Box, ComposedChart: Box, CartesianGrid: Nil, XAxis: Nil, YAxis: Nil, Tooltip: Nil, Bar: Nil, Line: Nil }
})
import type { Outages, Overview } from "./api"
import { networkI18n } from "./i18n"
import type { Sample } from "./logic"
import { OutagesView } from "./OutagesView"
import { OverviewView } from "./OverviewView"

const S = (p: Partial<Sample>): Sample => ({ ts: 1793560000, lan_loss: 0, lan_rtt: 0.2, fritz_loss: 0, fritz_rtt: 1, inet_loss: 0,
  inet_rtt_min: 8, inet_rtt_avg: 20, inet_rtt_max: 30, inet_jitter: 2, fritz_link: "Up", fritz_conn: "Connected",
  fritz_access: "Cable", path: "cable", ...p })
const O: Overview = { configured: true, latest: S({}), udm: { wan_status: "ok", isp: "Vodafone Germany", availability: 100, latency_ms: 15, drops: 11 },
  udm_at: 1793560000, udm_error: null, udm_confirmed: true, fritz: true, plan: { down: 1000, up: 50 },
  last_speedtest: { source: "udm", ts: 1793556215, down_mbit: 270, up_mbit: 2, ping_ms: 27, server: "Frankfurt am Main" } }

describe("Übersicht", () => {
  it("Weg, drei Ampeln, Anbieter und Speedtest gegen Tarif", () => {
    const html = renderToStaticMarkup(<OverviewView o={O} samples={[S({}), S({ ts: 1793560060 })]} canConfigure={false} />)
    for (const s of ["now:{&quot;path&quot;:&quot;path.cable&quot;}", "section.home", "section.fritz", "section.internet",
      "Vodafone Germany", "speed.of_plan:{&quot;pct&quot;:27}", "speed.of_plan:{&quot;pct&quot;:4}", "data-chart"]) expect(html).toContain(s)
    expect(html).toContain("text-rose-300")
    expect(html).not.toContain("not_configured")
  })
  it("Mobilfunk und kein Internet werden benannt", () => {
    expect(renderToStaticMarkup(<OverviewView o={{ ...O, latest: S({ path: "mobile" }) }} samples={[]} canConfigure={false} />)).toContain("path.mobile")
    const none = renderToStaticMarkup(<OverviewView o={{ ...O, latest: S({ path: "none", inet_loss: 100 }) }} samples={[]} canConfigure={false} />)
    expect(none).toContain("path.none")
    expect(none).toContain("light.bad")
  })
  it("Diagramm erst ab zwei Messungen", () => {
    expect(renderToStaticMarkup(<OverviewView o={O} samples={[S({})]} canConfigure={false} />)).not.toContain("data-chart")
  })
  it("nicht eingerichtet: Hinweis je nach Recht, ohne Messung", () => {
    const o = { ...O, configured: false, latest: null, last_speedtest: null, udm: null, udm_at: null }
    expect(renderToStaticMarkup(<OverviewView o={o} samples={[]} canConfigure />)).toContain("not_configured_admin")
    const u = renderToStaticMarkup(<OverviewView o={o} samples={[]} canConfigure={false} />)
    expect(u).toContain("not_configured")
    expect(u).not.toContain("not_configured_admin")
    expect(u).toContain("no_samples")
    expect(u).toContain("speed.none")
    expect(u).toContain("udm.never")
  })
  it("Fehler der Dream Machine wird übersetzt angezeigt", () => {
    const html = renderToStaticMarkup(<OverviewView o={{ ...O, udm_error: "network_auth_failed" }} samples={[]} canConfigure />)
    expect(html).toContain("err.network_auth_failed")
  })
})

describe("Störungen", () => {
  const d: Outages = {
    items: [{ start: 1793261269 - 30660, end: 1793261269, kind: "wan", source: "udm" },
      { start: 1793300000, end: 1793300005, kind: "blip", source: "udm" },
      { start: 1793400000, end: 1793400030, kind: "blip", source: "udm" }],
    per_day: { "2026-10-27": 30660, "2026-10-26": 0 }, per_day_cable: { "2026-10-29": 4000 }, per_day_internet: {},
  }
  it("Tage, Liste ohne Mini-Aussetzer, Speedtests mit schlechtem Upload rot", () => {
    const html = renderToStaticMarkup(<OutagesView d={d} planUp={50} speedtests={[
      { source: "udm", ts: 1792969147, down_mbit: 947, up_mbit: 51, ping_ms: 9, server: null },
      { source: "udm", ts: 1793556215, down_mbit: 270, up_mbit: 2, ping_ms: 27, server: null }]} />)
    expect(html).toContain("dur.hm:{&quot;h&quot;:8,&quot;m&quot;:31}")
    expect(html).toContain("outages.kind.wan")
    // beide Tageslisten an der richtigen Stelle
    const wanBox = html.slice(html.indexOf("outages.per_day<"), html.indexOf("outages.per_day_cable<"))
    expect(wanBox).toContain("dur.hm:{&quot;h&quot;:8,&quot;m&quot;:31}")
    expect(wanBox).not.toContain("dur.hm:{&quot;h&quot;:1,&quot;m&quot;:6}")
    expect(html.slice(html.indexOf("outages.per_day_cable<"))).toContain("dur.hm:{&quot;h&quot;:1,&quot;m&quot;:6}")
    expect(html.match(/outages\.kind\.blip/g)?.length).toBe(1)
    expect(html).toContain("outages.speed_row:{&quot;down&quot;:270,&quot;up&quot;:2}")
    // schlechter Upload (2 von 50) rot, guter (51) nicht
    const row = (up: number) => html.slice(0, html.indexOf(`&quot;up&quot;:${up}}`)).split("<span").pop() ?? ""
    expect(row(2)).toContain("text-rose-300")
    expect(row(51)).not.toContain("text-rose-300")
    expect(html.indexOf("&quot;up&quot;:2}")).toBeLessThan(html.indexOf("&quot;up&quot;:51}"))
  })
  it("leer", () => {
    const html = renderToStaticMarkup(<OutagesView d={{ items: [], per_day: {}, per_day_cable: {}, per_day_internet: {} }} speedtests={[]} planUp={null} />)
    expect(html.match(/outages\.none/g)?.length).toBe(3)
    expect(html).toContain("speed.none")
  })
})

describe("Texte", () => {
  const keys = (o: object, p = ""): string[] => Object.entries(o).flatMap(([k, v]) => (typeof v === "object" ? keys(v, `${p}${k}.`) : [`${p}${k}`]))
  it("de und en haben dieselben Schlüssel", () => {
    expect(keys(networkI18n.en).sort()).toEqual(keys(networkI18n.de).sort())
  })
  it("jeder Fehlercode des Servers hat einen Text", async () => {
    const fs = await import("node:fs")
    const path = await import("node:path")
    const src = fs.readFileSync(path.join(__dirname, "..", "backend", "errors.py"), "utf8")
    const codes = [...src.matchAll(/"(network_[a-z_]+)":/g)].map((m) => m[1])
    expect(codes.length).toBeGreaterThan(5)
    for (const c of codes) expect(Object.keys(networkI18n.de.network.err)).toContain(c)
  })
})
