// API-Client der Zerlege-Werkstatt.
// Alle Aufrufe gehen ueber den gemeinsamen api-Client, damit Login und
// Projektgrenze im Kern bleiben. Der Client kennt keine Pfade oder Befehle.
import { api } from "@/shared/api-client"

const BASE = "/modules/zerlegewerkstatt"

export type Purpose =
  | "interoperability"
  | "security_audit"
  | "debugging"
  | "preservation"
  | "other_authorized"

export type AnalysisType =
  | "inspect-artifact"
  | "inspect-android-package"
  | "inspect-managed-artifact"
  | "inspect-managed-members"
  | "inspect-pcap-capture"
  | "inspect-byte-entropy"
  | "inspect-native-exports"
  | "inspect-pe-imports"
  | "inspect-pe-resources"
  | "inspect-pe-load-config"
  | "inspect-pe-certificates"
  | "inspect-elf-notes"
  | "inspect-go-binary"
  | "inspect-rust-binary"
  | "inspect-kernel-module"
  | "inspect-apk-signature"
  | "analyze-ghidra"

export interface Artifact {
  id: string
  original_name: string
  kind: string
  size_bytes: number
  sha256: string
  relative_path: string
  created_at: string
}

export interface Job {
  id: string
  case_id: string
  artifact_id: string
  analysis_type: AnalysisType
  status: "queued" | "running" | "done" | "failed" | "interrupted"
  progress: number
  result_path: string | null
  error_code: string | null
  created_at: string
  updated_at: string
}

export interface CaseFile {
  id: string
  project_id: string
  created_by: string
  title: string
  target: string
  question: string
  purpose: Purpose
  authorized: boolean
  authorization_note: string
  status: string
  created_at: string
  updated_at: string
  artifacts: Artifact[]
  jobs: Job[]
}

export interface CaseInput {
  project_id: string
  title: string
  target: string
  question: string
  purpose: Purpose
  authorized: boolean
  authorization_note: string
}

export interface EvidenceRef {
  id: string
  artifact_id: string
  analysis_type: AnalysisType
  operation: string
  confidence: string
  provider: string
  provider_version: string
}

export interface Report {
  case_id: string
  title: string
  target: string
  question: string
  purpose: Purpose
  artifacts: Artifact[]
  observed: string[]
  derived: string[]
  suspected: string[]
  evidence: EvidenceRef[]
  unknown: string[]
  next_allowed_step: string[]
  jobs: Job[]
  untrusted_target_content: boolean
}

export interface IntakeInfo {
  path: string
  exists: boolean
  files: string[]
}

export interface RuntimeStatus {
  available: boolean
  running: boolean
  network_disabled: boolean
  code: string
}

export interface FileResult {
  ok: boolean
  original_name: string
  artifact_id?: string
  kind?: string
  size?: number
  sha256?: string
  error?: string
}

export function listCases(projectId: string) {
  return api.get<CaseFile[]>(`${BASE}/cases?project_id=${encodeURIComponent(projectId)}`)
}

export function getCase(caseId: string) {
  return api.get<CaseFile>(`${BASE}/cases/${caseId}`)
}

export function createCase(input: CaseInput) {
  return api.post<CaseFile>(`${BASE}/cases`, input)
}

export function uploadArtifacts(caseId: string, files: File[]) {
  const form = new FormData()
  files.forEach((file) => form.append("files", file))
  return api.postForm<{ files: FileResult[] }>(`${BASE}/cases/${caseId}/artifacts`, form)
}

export function scanIntake(caseId: string) {
  return api.post<{ scanned: number; taken: number; files: FileResult[] }>(
    `${BASE}/cases/${caseId}/intake/scan`,
    {},
  )
}

export function getIntake(caseId: string) {
  return api.get<IntakeInfo>(`${BASE}/cases/${caseId}/intake`)
}

export function startAnalysis(caseId: string, artifactId: string, analysisType: AnalysisType) {
  return api.post<Job>(`${BASE}/cases/${caseId}/analyze`, {
    artifact_id: artifactId,
    analysis_type: analysisType,
  })
}

export function getReport(caseId: string) {
  return api.get<Report>(`${BASE}/cases/${caseId}/report`)
}

export function getRuntimeStatus() {
  return api.get<RuntimeStatus>(`${BASE}/runtime/status`)
}
