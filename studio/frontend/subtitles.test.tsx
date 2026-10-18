import { renderToStaticMarkup } from "react-dom/server"
import { describe, expect, it, vi } from "vitest"

vi.mock("react-i18next", () => ({ useTranslation: () => ({ t: (k: string, o?: Record<string, unknown>) => (o ? `${k}:${JSON.stringify(o)}` : k) }) }))
vi.mock("@/shared/api-client", () => ({ api: { get: vi.fn(() => new Promise(() => {})) } }))
import { SubtitleList } from "./SubtitleList"
import { SubtitleOverlay } from "./SubtitleOverlay"
import { SubtitleTrack } from "./SubtitleTrack"
import {
  addCue, cueAt, editCue, joinCues, MIN_CUE, removeCue, saveName, splitCue, timeText, type Cue,
} from "./subtitleLogic"

const html = (el: React.ReactElement) => renderToStaticMarkup(el).replace(/&quot;/g, '"')
const noop = () => {}
const c = (id: string, start: number, end: number, text = id): Cue => ({ id, start, end, text })
const CUES = [c("a", 0, 2, "Eins"), c("b", 3, 5, "Zwei"), c("c", 5, 8, "Drei")]
let n = 0
const newId = () => `n${++n}`

describe("6a – Untertitel bearbeiten (rein, mit Grenzen)", () => {
  it("aktueller Eintrag bei Zeit t (Ende gehört nicht dazu), Lücke → keiner", () => {
    expect(cueAt(CUES, 1)?.id).toBe("a")
    expect(cueAt(CUES, 2)).toBeNull()
    expect(cueAt(CUES, 2.5)).toBeNull()
    expect(cueAt(CUES, 5)?.id).toBe("c")
    expect(cueAt(CUES, 8)).toBeNull()
  })

  it("Text und Zeiten ändern; Zeiten bleiben zwischen den Nachbarn und mind. 0,5 s lang", () => {
    expect(editCue(CUES, "b", { text: "Neu" })[1].text).toBe("Neu")
    expect(editCue(CUES, "b", { start: 1 })[1].start).toBe(2)               // nicht in den Vorgänger
    expect(editCue(CUES, "b", { end: 7 })[1].end).toBe(5)                   // nicht in den Nachfolger
    expect(editCue(CUES, "b", { start: 4.8 })[1].start).toBe(5 - MIN_CUE)    // mind. 0,5 s
    expect(editCue(CUES, "b", { end: 3.1 })[1].end).toBe(3 + MIN_CUE)
    expect(editCue(CUES, "a", { start: -3 })[0].start).toBe(0)
    expect(editCue(CUES, "x", { text: "?" })).toBe(CUES)
  })

  it("Teilen am Abspielkopf: Text an der Wortgrenze nahe der Mitte, beide Teile mind. 0,5 s", () => {
    const two = [c("a", 0, 4, "Ole zieht das Netz ein")]
    const out = splitCue(two, "a", 2, newId)
    expect(out.map((x) => [x.start, x.end, x.text])).toEqual([[0, 2, "Ole zieht"], [2, 4, "das Netz ein"]])
    expect(splitCue(two, "a", 0.2, newId)).toBe(two)                        // zu nah am Rand
    expect(splitCue(two, "a", 9, newId)).toBe(two)                          // außerhalb
    const one = splitCue([c("a", 0, 4, "Hallo")], "a", 2, newId)
    expect(one.map((x) => x.text)).toEqual(["Hallo", "Hallo"])               // ein Wort: Text in beiden
  })

  it("Zusammenführen mit dem nächsten Eintrag (Lücke wird geschlossen)", () => {
    const out = joinCues(CUES, "a")
    expect(out.map((x) => [x.id, x.start, x.end, x.text])).toEqual([["a", 0, 5, "Eins Zwei"], ["c", 5, 8, "Drei"]])
    expect(joinCues(CUES, "c")).toBe(CUES)                                  // letzter: nichts
  })

  it("Löschen; Hinzufügen am Abspielkopf in einer Lücke (2 s oder bis zum nächsten), sonst nicht", () => {
    expect(removeCue(CUES, "b").map((x) => x.id)).toEqual(["a", "c"])
    const add = addCue(CUES, 2.2, "Neu", newId)
    expect(add.cue).toMatchObject({ start: 2.2, end: 3, text: "Neu" })
    expect(add.cues.map((x) => x.start)).toEqual([0, 2.2, 3, 5])
    expect(addCue(CUES, 9, "x", newId).cue).toMatchObject({ start: 9, end: 11 })
    expect(addCue(CUES, 1, "x", newId).cue).toBeNull()                      // mitten in „Eins“
    expect(addCue(CUES, 2.8, "x", newId).cue).toBeNull()                    // Lücke < 0,5 s
  })

  it("Zeitanzeige und Dateiname", () => {
    expect(timeText(0)).toBe("0:00.0")
    expect(timeText(65.25)).toBe("1:05.2")
    expect(timeText(3725)).toBe("1:02:05.0")
    expect(saveName({ filename: "Der Fischer.de.srt" })).toBe("Der Fischer.de.srt")
    expect(saveName({ filename: "" })).toBe("untertitel.srt")
  })
})

describe("6a – Reiter „Untertitel“", () => {
  const list = (p: Partial<React.ComponentProps<typeof SubtitleList>> = {}) => html(
    <SubtitleList cues={CUES} selected="b" time={4} hasSpeech busy={false} save="saved" canUndo canRedo={false}
      onSelect={noop} onChange={noop} onAction={noop} onFromSpeech={noop} onExport={noop} onHear={noop} hearing={false} {...p} />)

  it("Liste: Zeiten, Texte als Eingabe, gewählter Eintrag, Knöpfe", () => {
    const out = list()
    expect(out).toContain("0:03.0")
    expect(out).toContain(">Zwei</textarea>")
    expect(out).toMatch(/data-sub-cue="b"[^>]*aria-current="true"/)
    for (const k of ["sub_split", "sub_join", "sub_delete", "sub_add", "sub_from_speech", "sub_export_srt", "sub_export_vtt"]) expect(out).toContain(k)
    expect(out).toContain("cut_save.saved")
    expect(out).toContain("sub_count")
  })

  it("leer: Erklärung + „Aus den Sprechtexten“; ohne Sprechtexte: Hinweis statt Knopf; Herunterladen gesperrt", () => {
    const empty = list({ cues: [], selected: null })
    expect(empty).toContain("sub_empty")
    expect(empty).toMatch(/<button[^>]*data-sub-from-speech[^>]*>/)
    expect(empty.match(/<button[^>]*data-sub-export="srt"[^>]*>/)?.[0]).toContain('disabled=""')
    const none = list({ cues: [], selected: null, hasSpeech: false })
    expect(none).toContain("sub_no_speech_hint")
    expect(none.match(/<button[^>]*data-sub-from-speech[^>]*>/)?.[0]).toContain('disabled=""')
  })

  it("Teilen/Zusammenführen/Löschen nur mit Auswahl; Hinzufügen nur in einer Lücke", () => {
    const none = list({ selected: null, time: 1 })
    for (const k of ["split", "join", "delete", "add"]) expect(none.match(new RegExp(`<button[^>]*data-sub-action="${k}"[^>]*>`))?.[0], k).toContain('disabled=""')
    const gap = list({ selected: null, time: 2.4 })
    expect(gap.match(/<button[^>]*data-sub-action="add"[^>]*>/)?.[0]).not.toContain('disabled=""')
  })

  it("Spur unter der Zeitleiste: Kästchen je Eintrag an der richtigen Stelle", () => {
    const out = html(<SubtitleTrack cues={CUES} view={{ start: 0, span: 10 }} time={4} selected="b" onSelect={noop} onSeek={noop} />)
    expect(out).toContain("sub_track")
    const box = (id: string) => out.match(new RegExp(`<button[^>]*data-sub-box="${id}"[^>]*>`))?.[0] ?? ""
    expect(box("b")).toContain('style="left:30%;width:20%"')
    expect(box("b")).toContain('aria-pressed="true"')
    expect(box("a")).toContain('aria-pressed="false"')
    expect(out).toContain("data-sub-playhead")
    const away = html(<SubtitleTrack cues={CUES} view={{ start: 0, span: 10 }} time={60} selected={null} onSelect={noop} onSeek={noop} />)
    expect(away).not.toContain("data-sub-playhead")                         // außerhalb der Ansicht: nicht aus dem Fenster ragen
  })

  it("Vorschau: Untertitel nur darübergelegt (nicht im Bild), Zeilen erhalten, in der Lücke nichts", () => {
    const out = html(<SubtitleOverlay cues={[c("a", 0, 2, "Zeile 1\nZeile 2")]} time={1} />)
    expect(out).toContain("data-sub-overlay")
    expect(out).toContain("Zeile 1<br/>Zeile 2")
    expect(html(<SubtitleOverlay cues={CUES} time={2.5} />)).toBe("")
  })
})
