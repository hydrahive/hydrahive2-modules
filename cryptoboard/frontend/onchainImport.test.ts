// Phase 2b: reine Logik des On-Chain-Imports (ohne jsdom) + Key nur in PUT /alchemy-key.
import { readdirSync, readFileSync, statSync } from "node:fs"
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
  buildCommitPayload, defaultSelection, effective, errorKey, groupPairs, isBookable, markBooked, mergePreview, missing,
  normDecimal,
} from "./onchainImport"
import type { OnchainEntry, OnchainPreview } from "./types"

const TX = (c: string) => "0x" + c.repeat(64)

function entry(c: string, kind: "sell" | "buy", over: Partial<OnchainEntry> = {}): OnchainEntry {
  return {
    hash: `base:${TX(c)}:${kind}`, tx_hash: TX(c), coin_id: kind === "sell" ? "usd-coin" : "ethereum",
    symbol: kind === "sell" ? "USDC" : "ETH", name: "", kind, quantity: "1", price: "1", fee: "0",
    executed_at: "2026-06-15T12:00:00Z", resolved: true, preis_fehlt: false, gebuehr_fehlt: false, duplicate: false,
    ...over,
  }
}

function preview(transactions: OnchainEntry[], over: Partial<OnchainPreview> = {}): OnchainPreview {
  return {
    chain: "base", address: "0xabc", transactions, wraps: [], unklar: [], truncated: false, before_block: null,
    kurs_abruf_fehlgeschlagen: false,
    counts: { swaps: 0, transactions: 0, wraps: 0, unklar: 0, duplicates: 0, preis_fehlt: 0, gebuehr_fehlt: 0, unresolved: 0 },
    ...over,
  }
}

describe("groupPairs", () => {
  it("fasst sell und buy einer Transaktion zusammen, sell zuerst", () => {
    const pairs = groupPairs([entry("1", "buy"), entry("2", "sell"), entry("1", "sell"), entry("2", "buy")])
    expect(pairs.map((p) => p.tx_hash)).toEqual([TX("1"), TX("2")])
    expect(pairs[0].entries.map((e) => e.kind)).toEqual(["sell", "buy"])
    expect(pairs[1].entries.map((e) => e.hash)).toEqual([`base:${TX("2")}:sell`, `base:${TX("2")}:buy`])
  })
})

describe("buchbar-Regel", () => {
  it("vollständiger Eintrag ist buchbar", () => {
    expect(isBookable(entry("1", "sell"), undefined)).toBe(true)
  })
  it("duplicate ist nie buchbar – auch nicht mit Ergänzungen", () => {
    const e = entry("1", "sell", { duplicate: true })
    expect(missing(e, { price: "5", coin_id: "x" })).toEqual(["duplicate"])
  })
  it("preis_fehlt: erst mit gültigem Preis buchbar", () => {
    const e = entry("1", "sell", { price: null, preis_fehlt: true })
    expect(missing(e, undefined)).toEqual(["price"])
    expect(isBookable(e, { price: "abc" })).toBe(false)
    expect(isBookable(e, { price: "1,25" })).toBe(true)
    expect(effective(e, { price: "1,25" }).price).toBe("1.25")
  })
  it("fehlende coin_id: erst nach Zuordnung buchbar", () => {
    const e = entry("1", "sell", { coin_id: null, resolved: false })
    expect(missing(e, undefined)).toEqual(["coin"])
    expect(isBookable(e, { coin_id: "pepe" })).toBe(true)
  })
  it("Gebühr fehlt ist kein Hindernis, eine ungültige Gebühr schon", () => {
    const e = entry("1", "sell", { fee: null, gebuehr_fehlt: true })
    expect(isBookable(e, undefined)).toBe(true)
    expect(missing(e, { fee: "x" })).toEqual(["fee_invalid"])
  })
  it("Standardauswahl: nur buchbare Einträge", () => {
    const sel = defaultSelection([
      entry("1", "sell"), entry("1", "buy", { duplicate: true }),
      entry("2", "sell", { price: null, preis_fehlt: true }), entry("2", "buy", { coin_id: null, resolved: false }),
    ])
    expect([...sel]).toEqual([`base:${TX("1")}:sell`])
  })
})

describe("Nachladen", () => {
  it("hängt an und dedupliziert nach hash (transactions, wraps, unklar) + zählt neu", () => {
    const a = preview([entry("1", "sell"), entry("1", "buy")], {
      wraps: [{ hash: TX("w"), executed_at: null, assets: [] }],
      unklar: [{ hash: TX("u"), executed_at: null, reason: "keine_nettobewegung", tokens: [] }],
    })
    const b = preview([entry("1", "buy"), entry("2", "sell", { duplicate: true }), entry("2", "buy")], {
      wraps: [{ hash: TX("w"), executed_at: null, assets: [] }],
      unklar: [{ hash: TX("v"), executed_at: null, reason: "decimals_fehlt", tokens: [] }],
      truncated: true, before_block: "0x10",
    })
    const m = mergePreview(a, b)
    expect(m.transactions.map((e) => e.hash)).toEqual([
      `base:${TX("1")}:sell`, `base:${TX("1")}:buy`, `base:${TX("2")}:sell`, `base:${TX("2")}:buy`,
    ])
    expect(m.wraps).toHaveLength(1)
    expect(m.unklar.map((u) => u.hash)).toEqual([TX("u"), TX("v")])
    expect(m.truncated).toBe(true)
    expect(m.before_block).toBe("0x10")
    expect(m.counts).toMatchObject({ swaps: 2, transactions: 4, duplicates: 1, wraps: 1, unklar: 2 })
  })
})

describe("Commit-Payload", () => {
  it("reicht die Zahlen-Strings exakt durch (keine Rundung)", () => {
    const e = entry("1", "buy", {
      quantity: "0.000000000000000001", price: "123456789012345678.123456789", fee: "0.000000000000000002",
    })
    const [tx] = buildCommitPayload([e], new Set([e.hash]), {})
    expect(tx.quantity).toBe("0.000000000000000001")
    expect(tx.price).toBe("123456789012345678.123456789")
    expect(tx.fee).toBe("0.000000000000000002")
    expect(tx.hash).toBe(`base:${TX("1")}:buy`)
    // auch nach JSON-Serialisierung als String – nicht als Zahl
    expect(JSON.stringify(tx)).toContain('"quantity":"0.000000000000000001"')
  })
  it("nutzt Ergänzungen, lässt Nicht-Gewähltes und Nicht-Buchbares weg", () => {
    const a = entry("1", "sell", { price: null, preis_fehlt: true, coin_id: null, resolved: false })
    const b = entry("1", "buy", { fee: null, gebuehr_fehlt: true })
    const c = entry("2", "sell", { price: null, preis_fehlt: true })
    const d = entry("2", "buy")
    const out = buildCommitPayload([a, b, c, d], new Set([a.hash, b.hash, c.hash]), {
      [a.hash]: { coin_id: "pepe", symbol: "PEPE", name: "Pepe", price: "0,0000012345678901234" },
    })
    expect(out.map((t) => t.hash)).toEqual([a.hash, b.hash])
    expect(out[0]).toMatchObject({ coin_id: "pepe", symbol: "PEPE", price: "0.0000012345678901234" })
    expect(out[1].fee).toBeNull()
  })
  it("normDecimal rundet nie", () => {
    expect(normDecimal("0.10000000000000000000001")).toBe("0.10000000000000000000001")
    expect(normDecimal("-1")).toBeNull()
    expect(normDecimal("1e5")).toBeNull()
  })
})

describe("nach dem Commit", () => {
  it("sperrt Gebuchtes und Duplikate, lässt abgelehnte Einträge buchbar", () => {
    const a = entry("1", "sell"), b = entry("1", "buy"), c = entry("2", "sell"), d = entry("2", "buy")
    const sent = buildCommitPayload([a, b, c, d], new Set([a.hash, b.hash, c.hash]), {})
    const res = { ok: true, imported: 1, skipped: 2, skipped_details: [
      { hash: b.hash, reason: "duplikat" }, { hash: c.hash, reason: "zeit_ungueltig" }] }
    const done = markBooked(preview([a, b, c, d]), sent, res)
    expect([...done.booked].sort()).toEqual([a.hash, b.hash].sort())
    expect(done.preview.transactions.map((e) => e.duplicate)).toEqual([true, true, false, false])
    expect(done.preview.counts.duplicates).toBe(2)
  })
})

describe("Fehlercodes", () => {
  it("bekannte Codes → Klartext-Schlüssel, unbekannte → null", () => {
    expect(errorKey({ code: "alchemy_key_missing" })).toBe("oc_err_alchemy_key_missing")
    expect(errorKey({ code: "irgendwas" })).toBeNull()
    expect(errorKey(new Error("x"))).toBeNull()
  })
})

describe("Alchemy-Key verlässt das Frontend nur per PUT /alchemy-key", () => {
  const KEY = "GEHEIM-alchemy-key-123"
  beforeEach(() => { calls.length = 0 })

  it("nur setAlchemyKey trägt den Key, alle anderen Aufrufe nicht", async () => {
    await cryptoApi.setAlchemyKey(KEY)
    await cryptoApi.alchemyKeyStatus()
    await cryptoApi.deleteAlchemyKey()
    await cryptoApi.onchainPreview(7, "0x10")
    await cryptoApi.onchainCommit(buildCommitPayload([entry("1", "sell")], new Set([entry("1", "sell").hash]), {}))
    const withKey = calls.filter((c) => JSON.stringify(c).includes(KEY))
    expect(withKey).toEqual([{ method: "PUT", path: "/modules/cryptoboard/alchemy-key", body: { key: KEY } }])
    expect(calls.find((c) => c.path.includes("onchain/preview"))?.body).toEqual({ address_id: 7, to_block: "0x10" })
  })

  it("Quelltext: Key nur in AlchemyKeyBox, kein console.*, Feld type=password und wird geleert", () => {
    const files = (function walk(d: string): string[] {
      return readdirSync(d).flatMap((n) => {
        const p = join(d, n)
        if (statSync(p).isDirectory()) return walk(p)
        return /\.tsx?$/.test(n) && !/\.test\.tsx?$/.test(n) ? [p] : []
      })
    })(__dirname)
    const users = files.filter((f) => readFileSync(f, "utf8").includes("cryptoApi.setAlchemyKey("))
    expect(users.map((f) => f.slice(__dirname.length + 1)).sort()).toEqual(["components/AlchemyKeyBox.tsx"])
    const box = readFileSync(join(__dirname, "components", "AlchemyKeyBox.tsx"), "utf8")
    expect(box).toContain('type="password"')
    expect(box).toMatch(/finally \{\s*setInput\(""\)/)
    for (const f of files) expect(readFileSync(f, "utf8"), f).not.toMatch(/console\.(log|debug|info|warn|error)/)
  })
})
