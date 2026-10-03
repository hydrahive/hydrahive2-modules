import { describe, expect, it } from "vitest"
import { activity, activityLines, isValidRigName, OFFLINE_AFTER_MS, rigBadge, rigCards, sensorHint, stopReasonKey, userHasWorkerSuffix } from "./rigState"

const now = Date.parse("2026-10-03T15:00:00Z")
const ago = (ms: number) => new Date(now - ms).toISOString()

describe("rigBadge", () => {
  it("Status schlägt alles andere", () => {
    expect(rigBadge({ status: "revoked", enabled: 1, last_seen: ago(0) }, now)).toBe("revoked")
    expect(rigBadge({ status: "pending", enabled: 1, last_seen: ago(0) }, now)).toBe("pending")
  })
  it("aktiv: aus / online / offline", () => {
    expect(rigBadge({ status: "active", enabled: 0, last_seen: ago(0) }, now)).toBe("disabled")
    expect(rigBadge({ status: "active", enabled: 1, last_seen: ago(OFFLINE_AFTER_MS) }, now)).toBe("online")
    expect(rigBadge({ status: "active", enabled: 1, last_seen: ago(OFFLINE_AFTER_MS + 1000) }, now)).toBe("offline")
    expect(rigBadge({ status: "active", enabled: 1, last_seen: null }, now)).toBe("offline")
  })
})

describe("isValidRigName", () => {
  it("wie im Backend", () => {
    expect(isValidRigName("rig-01")).toBe(true)
    expect(isValidRigName("a")).toBe(true)
    for (const bad of ["", "Rig", "-a", "a b", "a".repeat(33), "../x"]) expect(isValidRigName(bad)).toBe(false)
  })
})

describe("activity", () => {
  const base = { bench_done: 3, bench_failed: 1 }
  it("Benchmark zählt erledigte + fehlgeschlagene + aktuellen", () => {
    expect(activity({ ...base, assignment: { mode: "benchmark", coin: "rvn", miner: "rigel", reason: "", since: null } }, 17))
      .toEqual({ kind: "benchmark", coin: "rvn", miner: "rigel", done: 5, total: 17 })
  })
  it("Schürfen und Stopp", () => {
    expect(activity({ ...base, assignment: { mode: "mine", coin: "prl", miner: "srbminer", reason: "", since: null } }, 17))
      .toEqual({ kind: "mining", coin: "prl", miner: "srbminer" })
    expect(activity({ ...base, assignment: { mode: "stop", coin: null, miner: null, reason: "power_budget", since: null } }, 17))
      .toEqual({ kind: "stopped", reason: "power_budget" })
    expect(activity({ ...base, assignment: null }, 17)).toEqual({ kind: "stopped", reason: "" })
  })
})

describe("Hinweise", () => {
  it("Stoppgründe", () => {
    expect(stopReasonKey("power_budget")).toBe("stop_power_budget")
    expect(stopReasonKey("invalid_job:xyz")).toBe("stop_other")
  })
  it("erkennt „.Mining“ im Kryptex-Namen", () => {
    expect(userHasWorkerSuffix("krxXJK8JJW.Mining")).toBe(true)
    expect(userHasWorkerSuffix("krxXJK8JJW/rig1")).toBe(true)
    expect(userHasWorkerSuffix("krxXJK8JJW")).toBe(false)
    expect(userHasWorkerSuffix(" krxXJK8JJW ")).toBe(false)
    expect(userHasWorkerSuffix("RVNwalletAdresse.x")).toBe(false)
  })
})

describe("Mehrkarten", () => {
  it("Karten aus dem Report, alte Clients ohne Liste", () => {
    expect(rigCards({ last_report: { gpus: [{ pci: "a" }, { pci: "b" }] } })).toHaveLength(2)
    expect(rigCards({ last_report: { temp_c: 50 } })).toEqual([])
    expect(rigCards({ last_report: null })).toEqual([])
  })
  it("Sensor-Hinweis: fehlender Treiber-Sensor schlägt Ruhezustand", () => {
    expect(sensorHint([{ sensors: "ok" }, { sensors: "ok" }])).toBeNull()
    expect(sensorHint([{ sensors: "ok" }, { sensors: "asleep" }])).toBe("asleep")
    expect(sensorHint([{ sensors: "asleep" }, { sensors: "no_hwmon" }])).toBe("no_hwmon")
  })
})

describe("activityLines (Hersteller-Gruppen)", () => {
  const asg = (mode: "mine" | "benchmark" | "stop", coin: string | null, miner: string | null) =>
    ({ mode, coin, miner, reason: mode === "stop" ? "disabled" : "best", since: null })
  const grp = (vendor: string, a: ReturnType<typeof asg>, extra = {}) =>
    ({ vendor, assignment: a, bench_done: 3, bench_failed: 1, bench_total: 20, hashrate: 5e7, ...extra })

  it("ein Hersteller: eine Zeile ohne Hersteller-Etikett (wie bisher)", () => {
    const rig = { assignment: asg("mine", "qtc", "srbminer"), bench_done: 3, bench_failed: 1, bench_total: 20,
      groups: [grp("nvidia", asg("mine", "qtc", "srbminer"))], last_report: { hashrate: 5e7 } }
    const lines = activityLines(rig)
    expect(lines).toHaveLength(1)
    expect(lines[0].vendor).toBeNull()
    expect(lines[0].activity).toEqual({ kind: "mining", coin: "qtc", miner: "srbminer" })
  })
  it("gemischt: je Gruppe eine Zeile mit eigenem Zähler und eigener Hashrate", () => {
    const rig = { assignment: null, bench_done: 0, bench_failed: 0, bench_total: 42, last_report: null,
      groups: [grp("nvidia", asg("mine", "qtc", "srbminer"), { hashrate: 3e8 }),
               grp("amd", asg("benchmark", "erg", "lolminer"), { bench_done: 5, bench_failed: 0, bench_total: 22 })] }
    const lines = activityLines(rig)
    expect(lines.map((l) => l.vendor)).toEqual(["nvidia", "amd"])
    expect(lines[0].hashrate).toBe(3e8)
    expect(lines[1].activity).toEqual({ kind: "benchmark", coin: "erg", miner: "lolminer", done: 6, total: 22 })
  })
  it("alter Server ohne groups: eine Zeile aus den Kopfdaten", () => {
    const rig = { assignment: asg("benchmark", "cfx", "rigel"), bench_done: 2, bench_failed: 0, bench_total: 20,
      last_report: { hashrate: 1e7 } }
    const lines = activityLines(rig)
    expect(lines).toHaveLength(1)
    expect(lines[0].activity).toEqual({ kind: "benchmark", coin: "cfx", miner: "rigel", done: 3, total: 20 })
    expect(lines[0].hashrate).toBe(1e7)
  })
})
