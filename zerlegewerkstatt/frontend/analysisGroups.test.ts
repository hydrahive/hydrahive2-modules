import { describe, expect, it } from "vitest"
import { analysisGroupsFor } from "./ui"

describe("fachlich gruppierte Analyseauswahl", () => {
  it("zeigt PE-Tiefenanalysen nach Fachgruppe statt als ungeordnete Knopfreihe", () => {
    const groups = analysisGroupsFor("pe")
    expect(groups.map((entry) => entry.group)).toEqual(["overview", "structure", "code", "signatures"])
    expect(groups.find((entry) => entry.group === "structure")?.analyses).toEqual([
      "inspect-byte-entropy",
      "inspect-pe-resources",
      "inspect-pe-load-config",
    ])
    expect(groups.find((entry) => entry.group === "code")?.analyses).toContain("inspect-pe-imports")
    expect(groups.find((entry) => entry.group === "signatures")?.analyses).toEqual(["inspect-pe-certificates"])
  })

  it("zeigt beim Mitschnitt keine Programm- oder Ghidra-Analyse", () => {
    const analyses = analysisGroupsFor("pcap").flatMap((entry) => entry.analyses)
    expect(analyses).toEqual(["inspect-artifact", "inspect-byte-entropy", "inspect-pcap-capture"])
    expect(analyses).not.toContain("analyze-ghidra")
  })

  it("zeigt Firmware-Regionen nur bei Firmware und unter Aufbau", () => {
    const firmware = analysisGroupsFor("firmware")
    const regions = firmware.find((entry) => entry.group === "structure")?.analyses
    expect(regions).toContain("inspect-firmware-regions")
    expect(analysisGroupsFor("pe").flatMap((entry) => entry.analyses)).not.toContain("inspect-firmware-regions")
  })

  it("zeigt APK-Signaturen nur bei Android-Paketen", () => {
    const apk = analysisGroupsFor("apk").flatMap((entry) => entry.analyses)
    const elf = analysisGroupsFor("elf").flatMap((entry) => entry.analyses)
    expect(apk).toContain("inspect-apk-signature")
    expect(elf).not.toContain("inspect-apk-signature")
  })
})
