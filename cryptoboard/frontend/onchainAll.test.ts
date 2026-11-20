// 1.7.0: reine Logik des Imports aller Adressen (ohne jsdom): Paare, Mehrdeutiges, Ausgaben, Spam, Leer-Zustand.
import { readFileSync } from "node:fs"
import { join } from "node:path"
import { beforeEach, describe, expect, it, vi } from "vitest"

const calls: { method: string; path: string; body?: unknown }[] = []
vi.mock("@/shared/api-client", () => {
  const rec = (method: string) => (path: string, body?: unknown) => {
    calls.push({ method, path, body })
    return Promise.resolve({})
  }
  return { api: { get: rec("GET"), post: rec("POST"), put: rec("PUT"), patch: rec("PATCH"), delete: rec("DELETE") } }
})

import { cryptoApi } from "./api"
import {
  applyChoice, buildAllPayload, defaultSelectionAll, emptySummary, formatDelay, isEmptyResult, markBookedAll,
  takenElsewhere, type Choice,
} from "./onchainAll"
import { errorKey, groupPairs, isBookable, KNOWN_ERRORS, UNKLAR_REASONS } from "./onchainImport"
import type { OnchainAllCounts, OnchainEntry, OnchainPreviewAll } from "./types"

const H = (c: string) => c.repeat(64)
const EVM = (c: string) => "0x" + H(c)

function entry(hash: string, tx_hash: string, kind: OnchainEntry["kind"], over: Partial<OnchainEntry> = {}): OnchainEntry {
  return {
    hash, tx_hash, coin_id: kind === "sell" ? "tron" : "usd-coin", symbol: kind === "sell" ? "TRX" : "USDC", name: "",
    kind, quantity: "1", price: "1", fee: null, executed_at: "2026-06-15T12:00:00Z", resolved: true,
    preis_fehlt: false, gebuehr_fehlt: false, duplicate: false, ...over,
  }
}

function pairOf(tron: string, evm: string, over: Partial<OnchainEntry> = {}) {
  const id = `xchain:${H(tron)}:base:${EVM(evm)}`
  return {
    id, tron_tx: H(tron), evm_chain: "base", evm_tx: EVM(evm), sell_at: "2026-06-15T12:00:00Z",
    buy_at: "2026-06-15T12:01:00Z", delay_seconds: 60,
    entries: [entry(`${id}:buy`, id, "buy", over), entry(`${id}:sell`, id, "sell")],
  }
}

const COUNTS: OnchainAllCounts = {
  swaps: 0, transactions: 0, wraps: 0, unklar: 0, duplicates: 0, preis_fehlt: 0, gebuehr_fehlt: 0, unresolved: 0,
  pairs: 0, mehrdeutig: 0, ausgaben: 0, spam: 0, buchbar: 0,
}

function cand(evm: string, hours = 0) {
  const id = `xchain:${H("a")}:base:${EVM(evm)}`
  return {
    evm_chain: "base", evm_tx: EVM(evm), executed_at: "2026-06-15T12:02:00Z", symbol: "USDC", amount: "10",
    delay_seconds: 120 + hours, entries: [entry(`${id}:sell`, id, "sell"), entry(`${id}:buy`, id, "buy")],
  }
}

function all(over: Partial<OnchainPreviewAll> = {}): OnchainPreviewAll {
  return {
    addresses: [], transactions: [], pairs: [], mehrdeutig: [], ausgaben: [], spam: [], wraps: [], unklar: [],
    kurs_abruf_fehlgeschlagen: false, window_minutes: 15, counts: COUNTS, ...over,
  }
}

const out = (c: string, over: Partial<OnchainEntry> = {}) =>
  entry(`base:${EVM(c)}:transfer_out`, EVM(c), "transfer_out", { coin_id: "tron", symbol: "TRX", price: null, preis_fehlt: true, ...over })

describe("Paare", () => {
  it("gruppiert sell+buy je Paar-id, sell zuerst", () => {
    const a = pairOf("1", "b"), b = pairOf("2", "c")
    const groups = groupPairs([...a.entries, ...b.entries])
    expect(groups.map((g) => g.tx_hash)).toEqual([a.id, b.id])
    expect(groups.every((g) => g.entries.map((e) => e.kind).join() === "sell,buy")).toBe(true)
  })
  it("Standard: buchbare Paare angehakt, unbuchbare nicht", () => {
    const ok = pairOf("1", "b"), bad = pairOf("2", "c", { coin_id: null, resolved: false })
    const sel = defaultSelectionAll(all({ pairs: [ok, bad] }))
    expect(sel.has(`${ok.id}:sell`) && sel.has(`${ok.id}:buy`)).toBe(true)
    expect(sel.has(`${bad.id}:buy`)).toBe(false)
  })
  it("Verzögerung als Einheit", () => {
    expect(formatDelay(60)).toEqual({ unit: "s", n: 60 })
    expect(formatDelay(180)).toEqual({ unit: "min", n: 3 })
    expect(formatDelay(7200)).toEqual({ unit: "h", n: 2 })
  })
})

describe("Mehrdeutig", () => {
  const m = { tron_tx: H("a"), executed_at: null, symbol: "TRX", amount: "5", candidates: [cand("d"), cand("e", 5)] }
  it("ohne Auswahl kein Commit-Eintrag, auch nicht bei angehakten Hashes", () => {
    const p = all({ mehrdeutig: [m] })
    const sel = new Set(m.candidates.flatMap((c) => c.entries.map((e) => e.hash)))
    expect(buildAllPayload(p, sel, {}, {})).toEqual([])
  })
  it("mit Auswahl genau die 2 Einträge des gewählten Kandidaten", () => {
    const p = all({ mehrdeutig: [m] })
    const key = `base:${EVM("e")}`
    const choice: Choice = { [m.tron_tx]: key }
    const sel = applyChoice(new Set(), m, key, {})
    const pay = buildAllPayload(p, sel, {}, choice)
    expect(pay.map((t) => t.hash).sort()).toEqual(m.candidates[1].entries.map((e) => e.hash).sort())
    expect(pay).toHaveLength(2)
  })
  it("Wahl wechseln/aufheben entfernt die alten Einträge aus der Auswahl", () => {
    const k1 = `base:${EVM("d")}`, k2 = `base:${EVM("e")}`
    const s1 = applyChoice(new Set(), m, k1, {})
    const s2 = applyChoice(s1, m, k2, {})
    expect(s2.has(m.candidates[0].entries[0].hash)).toBe(false)
    expect(s2.has(m.candidates[1].entries[0].hash)).toBe(true)
    expect(applyChoice(s2, m, "", {}).size).toBe(0)
  })
  it("gleicher Kandidat nicht in zwei Gruppen", () => {
    const m2 = { ...m, tron_tx: H("b") }
    expect(takenElsewhere({ mehrdeutig: [m, m2] }, { [m.tron_tx]: `base:${EVM("d")}` }, m2.tron_tx, `base:${EVM("d")}`)).toBe(true)
  })
})

describe("Ausgaben (transfer_out)", () => {
  it("Standard nicht gewählt", () => {
    expect(defaultSelectionAll(all({ ausgaben: [out("f")] })).size).toBe(0)
  })
  it("ohne Preis buchbar; Payload kind transfer_out, price null", () => {
    const e = out("f")
    expect(isBookable(e, undefined)).toBe(true)
    const pay = buildAllPayload(all({ ausgaben: [e] }), new Set([e.hash]), {}, {})
    expect(pay).toHaveLength(1)
    expect(pay[0]).toMatchObject({ kind: "transfer_out", price: null, hash: `base:${EVM("f")}:transfer_out` })
  })
  it("ohne coin_id nicht buchbar; sell ohne Preis weiterhin nicht", () => {
    expect(isBookable(out("f", { coin_id: null, resolved: false }), undefined)).toBe(false)
    expect(isBookable(entry("x", "x", "sell", { price: null, preis_fehlt: true }), undefined)).toBe(false)
  })
  it("nicht angehakt → nicht im Payload", () => {
    expect(buildAllPayload(all({ ausgaben: [out("f")] }), new Set(), {}, {})).toEqual([])
  })
})

describe("Spam, Leer-Zustand, Zahlen", () => {
  it("Spam nie im Payload – selbst wenn der Hash gewählt wäre", () => {
    // Spam trägt hier absichtlich alle Felder eines buchbaren Eintrags – nur die Listenzugehörigkeit darf ihn ausschließen.
    const full = entry(`base:${EVM("9")}:buy`, EVM("9"), "buy", { symbol: "ＵＳＤＣ", executed_at: "2026-06-15T12:00:00Z" })
    const spam = { ...full, chain: "base", contract: "0x1", amount: "1", grund: "symbol_nicht_ascii" }
    const p = all({ spam: [spam] })
    expect(isBookable(full, undefined)).toBe(true)
    expect(buildAllPayload(p, new Set([spam.hash]), {}, {})).toEqual([])
    expect(defaultSelectionAll(p).size).toBe(0)
  })
  it("buchbar == 0 → Leer-Zustand mit Zusammenfassung", () => {
    const c = { ...COUNTS, unklar: 2, spam: 3, ausgaben: 1, mehrdeutig: 4 }
    expect(isEmptyResult(c)).toBe(true)
    expect(emptySummary(c)).toEqual({ unklar: 2, spam: 3, ausgaben: 1, mehrdeutig: 4 })
    expect(isEmptyResult({ ...c, buchbar: 1 })).toBe(false)
  })
  it("Zahlen-Strings bleiben exakt (Paar, Ausgabe)", () => {
    const p = pairOf("1", "b", { quantity: "2435.31", price: "0.000000000000000001" })
    const o = out("f", { quantity: "0.000000000000000001", price: "2435.31", preis_fehlt: false })
    const pay = buildAllPayload(all({ pairs: [p], ausgaben: [o] }), new Set([...p.entries.map((e) => e.hash), o.hash]), {}, {})
    const buy = pay.find((t) => t.kind === "buy")
    expect(buy).toMatchObject({ quantity: "2435.31", price: "0.000000000000000001" })
    expect(pay.find((t) => t.kind === "transfer_out")).toMatchObject({ quantity: "0.000000000000000001", price: "2435.31" })
    expect(JSON.stringify(pay)).toContain('"quantity":"2435.31"')
  })
})

describe("Nach dem Commit & Fehlercodes", () => {
  it("gebuchte Paar-/Ausgaben-Einträge werden gesperrt, abgelehnte bleiben", () => {
    const p = pairOf("1", "b"), o = out("f")
    const pv = all({ pairs: [p], ausgaben: [o] })
    const sent = buildAllPayload(pv, new Set([...p.entries.map((e) => e.hash), o.hash]), {}, {})
    const res = { ok: true, imported: 2, skipped: 1, skipped_details: [{ hash: o.hash, reason: "zeit_ungueltig" }] }
    const done = markBookedAll(pv, sent, res)
    expect(done.preview.pairs[0].entries.every((e) => e.duplicate)).toBe(true)
    expect(done.preview.ausgaben[0].duplicate).toBe(false)
  })
  it("Tron-Codes und neue Gründe haben Klartext-Schlüssel", () => {
    expect(KNOWN_ERRORS).toContain("tron_network_error")
    expect(errorKey({ code: "tron_fetch_failed" })).toBe("oc_err_tron_fetch_failed")
    for (const r of ["nur_raus", "nur_rein", "mehrere_assets"]) expect(UNKLAR_REASONS).toContain(r)
  })
})

describe("API & Texte", () => {
  beforeEach(() => { calls.length = 0 })
  it("preview_all: POST mit/ohne window_minutes", async () => {
    await cryptoApi.onchainPreviewAll()
    await cryptoApi.onchainPreviewAll(30)
    expect(calls.map((c) => [c.method, c.path, c.body])).toEqual([
      ["POST", "/modules/cryptoboard/portfolio/import/onchain/preview_all", {}],
      ["POST", "/modules/cryptoboard/portfolio/import/onchain/preview_all", { window_minutes: 30 }],
    ])
  })
  it("de/en haben dieselben oc_*-Schlüssel", () => {
    const src = readFileSync(join(__dirname, "index.tsx"), "utf8")
    const keys = (blk: string) => [...blk.matchAll(/^\s+(oc_[a-z_]+):/gm)].map((m) => m[1]).sort()
    const i = src.indexOf("\n  en: {")
    const de = keys(src.slice(0, i)), en = keys(src.slice(i))
    expect(de.length).toBeGreaterThan(60)
    expect(en).toEqual(de)
    for (const k of KNOWN_ERRORS) expect(de).toContain(`oc_err_${k}`)
  })
})
