import { renderToStaticMarkup } from "react-dom/server"
import { describe, expect, it, vi } from "vitest"
import { ReportPanel } from "./ReportPanel"
import type { Report } from "./api"

vi.mock("react-i18next", () => ({ useTranslation: () => ({ t: (key: string) => key }) }))

const report: Report = {
  case_id: "f1",
  title: "Lampe",
  target: "",
  question: "Wie kommuniziert die Lampe?",
  purpose: "interoperability",
  artifacts: [],
  observed: [],
  derived: ["Lokale Kommunikation [Beleg: ev_1234567890abcdef]"],
  suspected: [],
  unknown: [],
  next_allowed_step: [],
  jobs: [],
  evidence: [{
    id: "ev_1234567890abcdef",
    artifact_id: "a1",
    analysis_type: "inspect-pcap-capture",
    operation: "inspect_pcap_capture",
    confidence: "observed",
    provider: "pcap",
    provider_version: "4.2.2",
  }],
  untrusted_target_content: true,
}

describe("Belegverzeichnis im Bericht", () => {
  it("zeigt die vollständige Evidence-ID, Herkunft und Confidence", () => {
    const html = renderToStaticMarkup(<ReportPanel report={report} jobs={[]} loading={false} />)
    expect(html).toContain("evidenceIndex")
    expect(html).toContain("ev_1234567890abcdef")
    expect(html).toContain("inspect_pcap_capture")
    expect(html).toContain("observed")
    expect(html).toContain("pcap")
    expect(html).toContain("4.2.2")
  })
})
