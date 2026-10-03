import { describe, expect, it } from "vitest"
import { activity, isValidRigName, OFFLINE_AFTER_MS, rigBadge, stopReasonKey, userHasWorkerSuffix } from "./rigState"

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
