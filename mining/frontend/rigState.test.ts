import { describe, expect, it } from "vitest"
import { isValidRigName, OFFLINE_AFTER_MS, rigBadge } from "./rigState"

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
