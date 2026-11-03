import { renderToStaticMarkup } from "react-dom/server"
import { describe, expect, it, vi } from "vitest"
import { CaseList } from "./CaseList"
import type { CaseSummary } from "./api"

vi.mock("react-i18next", () => ({
  useTranslation: () => ({
    t: (key: string, params?: Record<string, number>) => key === "caseCount"
      ? `${params?.artifacts}/${params?.jobs}`
      : key,
  }),
}))

const summary: CaseSummary = {
  id: "case-1",
  project_id: "project-1",
  created_by: "alice",
  title: "Router",
  target: "Eigener Router",
  question: "Welche Regionen sind enthalten?",
  purpose: "interoperability",
  authorized: true,
  authorization_note: "Eigenes Gerät",
  status: "draft",
  created_at: "2026-11-03T12:00:00Z",
  updated_at: "2026-11-03T12:00:00Z",
  artifact_count: 2,
  job_count: 3,
}

describe("Fallliste", () => {
  it("rendert vorhandene Fälle mit den Zählern des Listenvertrags", () => {
    const html = renderToStaticMarkup(
      <CaseList cases={[summary]} selected={null} onSelect={() => {}} loading={false} />,
    )

    expect(html).toContain("Router")
    expect(html).toContain("2/3")
  })
})
