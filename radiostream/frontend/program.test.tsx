import { renderToStaticMarkup } from "react-dom/server"
import { describe, expect, it, vi } from "vitest"

vi.mock("react-i18next", () => ({ useTranslation: () => ({ t: (k: string, o?: Record<string, unknown>) => (o ? `${k}:${JSON.stringify(o)}` : k) }) }))
vi.mock("@/shared/api-client", () => ({ api: { get: vi.fn(() => new Promise(() => {})), post: vi.fn(), put: vi.fn(), delete: vi.fn() } }))
vi.mock("@/features/auth/useAuthStore", () => ({ useAuthStore: (f: (s: unknown) => unknown) => f({ token: "t", username: "till", role: "user" }) }))
import { programErrorKey, programLine, rulesSummary, emptyRules, DECADES, type Program } from "./programLogic"
import { ProgramBox } from "./ProgramBox"
import { QueueBox } from "./QueueBox"
import { TrackActions } from "./TrackActions"
import { PlaylistView } from "./PlaylistView"
import { MixEditor } from "./MixEditor"
import { radiostreamI18n } from "./i18n"

const noop = () => {}
const PROG: Program = { mode: "all", ref_id: "", notice: "", name: "", count: 0, position: 0, can_moderate: true }
const free = (html: string) => [...html.matchAll(/<button[^>]*>/g)].map((m) => m[0]).filter((b) => !/\sdisabled=""/.test(b))

describe("Logik Programm", () => {
  it("Zeile für das laufende Programm", () => {
    expect(programLine(PROG)).toEqual({ key: "program.line_all" })
    expect(programLine({ ...PROG, mode: "playlist", name: "Party", count: 40, position: 12 }))
      .toEqual({ key: "program.line_playlist", opts: { name: "Party", pos: 12, count: 40 } })
    expect(programLine({ ...PROG, mode: "mix", name: "Rock", count: 2431 }))
      .toEqual({ key: "program.line_mix", opts: { name: "Rock", count: 2431 } })
  })
  it("Fehler-Codes des Programms bekannt", () => {
    for (const c of ["radiostream_playlist_not_found", "radiostream_mix_not_found", "radiostream_rule_invalid",
      "radiostream_name_invalid", "radiostream_too_many", "radiostream_playlist_invalid", "radiostream_queue_invalid",
      "radiostream_program_invalid", "radiostream_program_empty", "radiostream_track_not_found"])
      expect(programErrorKey({ code: c })).toBe(`err.${c}`)
    expect(programErrorKey({ code: "capability_denied" })).toBe("err.radiostream_moderate_only")
    expect(programErrorKey({ code: "unbekannt" })).toBe("err.general")
  })
  it("Regel als kurzer Text", () => {
    expect(rulesSummary(emptyRules())).toEqual([])
    expect(rulesSummary({ ...emptyRules(), genres: ["Rock"], decades: [1980, 1990], exclude_artists: ["Madonna"] }))
      .toEqual(["Rock", "1980er", "1990er", "− Madonna"])
  })
  it("Jahrzehnte 1950–2020", () => { expect(DECADES).toEqual([1950, 1960, 1970, 1980, 1990, 2000, 2010, 2020]) })
})

describe("Kasten Programm im Sender", () => {
  const pls = [{ id: "p1", name: "Party", count: 3, order_mode: "ordered", at_end: "repeat" }]
  const mixes = [{ id: "m1", name: "Rock", rules: { genres: ["Rock"] }, allow_long: false }]
  const view = (p: Partial<Program>) => renderToStaticMarkup(<ProgramBox p={{ ...PROG, ...p }} playlists={pls as never}
    mixes={mixes as never} busy={false} onSet={noop} />)
  it("zeigt was läuft und die Auswahl", () => {
    const html = view({ mode: "playlist", ref_id: "p1", name: "Party", count: 3, position: 1 })
    expect(html).toContain("program.line_playlist")
    expect(html).toContain("Party") && expect(html).toContain("Rock")
    expect(html).toMatch(/<option[^>]*value="playlist:p1"[^>]*selected/)
  })
  it("Hinweis bei leerem Programm", () => {
    expect(view({ mode: "mix", ref_id: "m1", notice: "radiostream_program_empty" })).toContain("err.radiostream_program_empty")
  })
  it("ohne Moderieren nur Anzeige", () => {
    const html = view({ can_moderate: false })
    expect(html).not.toContain("<select")
    expect(html).toContain("program.line_all")
  })
})

describe("Warteschlange", () => {
  const items = [{ id: 1, pos: 0, track_id: "a", artist: "Queen", title: "One Vision", duration_s: 300, added_by: "till" },
    { id: 2, pos: 1, track_id: "b", artist: "ABBA", title: "SOS", duration_s: 200, added_by: "till" }]
  it("Liste mit hoch/runter/entfernen", () => {
    const html = renderToStaticMarkup(<QueueBox items={items} canModerate busy={false} onMove={noop} onRemove={noop} />)
    expect(html).toContain("One Vision") && expect(html).toContain("SOS")
    expect(html).toContain("queue.up") && expect(html).toContain("queue.down") && expect(html).toContain("queue.remove")
  })
  it("erster nicht hoch, letzter nicht runter", () => {
    const html = renderToStaticMarkup(<QueueBox items={items} canModerate busy={false} onMove={noop} onRemove={noop} />)
    const btns = [...html.matchAll(/<button[^>]*aria-label="([^"]+)"[^>]*>/g)].map((m) => [m[1], /\sdisabled=""/.test(m[0])])
    expect(btns.filter(([l]) => String(l).startsWith("queue.up"))[0][1]).toBe(true)
    expect(btns.filter(([l]) => String(l).startsWith("queue.down")).at(-1)?.[1]).toBe(true)
  })
  it("leer", () => {
    expect(renderToStaticMarkup(<QueueBox items={[]} canModerate busy={false} onMove={noop} onRemove={noop} />)).toContain("queue.empty")
  })
  it("ohne Moderieren keine Knöpfe", () => {
    expect(free(renderToStaticMarkup(<QueueBox items={items} canModerate={false} busy={false} onMove={noop} onRemove={noop} />))).toEqual([])
  })
})

describe("Aktionen an der Titelzeile", () => {
  const pls = [{ id: "p1", name: "Party", count: 3 }, { id: "p2", name: "Chill", count: 0 }]
  it("Als Nächstes, ans Ende, + Playlist (Auswahl)", () => {
    const html = renderToStaticMarkup(<TrackActions trackId="t1" playlists={pls as never} open onToggle={noop}
      onQueue={noop} onAdd={noop} />)
    for (const k of ["track.next", "track.queue_end", "track.add_to", "Party", "Chill"]) expect(html).toContain(k)
  })
  it("zugeklappt nur der Knopf", () => {
    const html = renderToStaticMarkup(<TrackActions trackId="t1" playlists={pls as never} open={false} onToggle={noop}
      onQueue={noop} onAdd={noop} />)
    expect(html).toContain("track.actions") && expect(html).not.toContain("track.next")
  })
})

describe("Playlist bearbeiten", () => {
  const pl = { id: "p1", name: "Party", count: 3, order_mode: "ordered", at_end: "repeat" }
  const items = [{ pos: 0, track_id: "a", artist: "Queen", title: "One Vision", duration_s: 300, available: true },
    { pos: 1, track_id: "b", artist: "ABBA", title: "SOS", duration_s: 200, available: false }]
  it("Titel, Reihenfolge, fehlende grau, Abspielart", () => {
    const html = renderToStaticMarkup(<PlaylistView pl={pl as never} items={items} canModerate busy={false}
      onChange={noop} onMove={noop} onRemove={noop} onDelete={noop} onPlayNow={noop} />)
    expect(html).toContain("One Vision") && expect(html).toContain("playlist.missing")
    for (const k of ["playlist.ordered", "playlist.shuffle", "playlist.repeat", "playlist.back", "playlist.delete",
      "playlist.play_now"]) expect(html).toContain(k)
    expect(html).toMatch(/data-dropzone="p1"/)
  })
  it("Titel ziehbar zum Umsortieren (nur mit Recht)", () => {
    const html = renderToStaticMarkup(<PlaylistView pl={pl as never} items={items} canModerate busy={false}
      onChange={noop} onMove={noop} onRemove={noop} onDelete={noop} onPlayNow={noop} />)
    expect((html.match(/draggable="true"/g) ?? []).length).toBe(2)
    const ro = renderToStaticMarkup(<PlaylistView pl={pl as never} items={items} canModerate={false} busy={false}
      onChange={noop} onMove={noop} onRemove={noop} onDelete={noop} onPlayNow={noop} />)
    expect(ro).not.toContain('draggable="true"') && expect(free(ro)).toEqual([])
  })
  it("leer: Hinweis wie man befüllt", () => {
    expect(renderToStaticMarkup(<PlaylistView pl={pl as never} items={[]} canModerate busy={false}
      onChange={noop} onMove={noop} onRemove={noop} onDelete={noop} onPlayNow={noop} />)).toContain("playlist.empty")
  })
})

describe("Mix-Editor", () => {
  const view = (o: Record<string, unknown> = {}) => renderToStaticMarkup(<MixEditor name="Rock" rules={{ ...emptyRules(), genres: ["Rock"] }}
    allowLong={false} genres={["Rock", "Pop"]} folders={["Queen"]} preview={{ count: 12, examples: [{ track_id: "a", artist: "Queen", title: "One Vision", year: 1986, genre: "Rock" }] }}
    canModerate busy={false} onChange={noop} onSave={noop} onDelete={noop} onPlayNow={noop} {...o} />)
  it("Felder, Anzahl, Beispiele, wenige-Titel-Hinweis", () => {
    const html = view()
    for (const k of ["mix.genres", "mix.artists", "mix.decades", "mix.folders", "mix.exclude", "mix.allow_long",
      "mix.count:{&quot;count&quot;:12}", "One Vision", "mix.few"]) expect(html).toContain(k)
  })
  it("viele Titel: kein Hinweis", () => {
    expect(view({ preview: { count: 500, examples: [] } })).not.toContain("mix.few")
  })
  it("ohne Name nicht speicherbar", () => {
    expect(view({ name: " " })).toMatch(/<button[^>]*disabled=""[^>]*>mix.save</)
  })
})

describe("Texte Programm", () => {
  const de = radiostreamI18n.de.radiostream as unknown as Record<string, Record<string, string>>
  const en = radiostreamI18n.en.radiostream as unknown as Record<string, Record<string, string>>
  it("de/en gleich vollständig", () => {
    const flat = (o: unknown, p = ""): string[] => typeof o === "string" ? [p] : Object.entries(o as object).flatMap(([k, v]) => flat(v, p ? `${p}.${k}` : k))
    expect(flat(radiostreamI18n.de).sort()).toEqual(flat(radiostreamI18n.en).sort())
  })
  it("Programm-Texte vorhanden", () => {
    for (const k of ["line_all", "line_playlist", "line_mix", "choose", "all", "heading"]) expect(de.program[k], k).toBeTruthy()
    for (const k of ["moderate_only", "program_empty", "rule_invalid", "too_many"]) expect(de.err[`radiostream_${k}`], k).toBeTruthy()
    expect(en.tab.program).toBeTruthy()
  })
})
