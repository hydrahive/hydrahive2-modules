// Ghostwriter G3 – Interview speichern ohne React (interviewSync.test.ts). Wie BookSync: gespeichert wird mit
// der Version, auf der die Änderung aufbaut; veraltet → Konflikt, die eigene Fassung bleibt im Formular und
// wird erst nach der Entscheidung („neu laden“ / „behalten“) weiter gespeichert.
import { StoryApiError } from "./api"
import type { Interview, Question } from "./interviewModel"

export type InterviewSaveState = "saved" | "saving" | "failed" | "conflict"
type Save = (baseVersion: number, questions: Question[]) => Promise<Interview>

export class InterviewSync {
  questions: Question[] = []
  state: InterviewSaveState = "saved"
  conflict: Interview | null = null
  private version: number
  private readonly save: Save
  private pending: Question[] | null = null
  private running: Promise<void> | null = null

  constructor(version: number, save: Save, questions: Question[] = []) {
    this.version = version
    this.save = save
    this.questions = questions
  }

  change(next: Question[]): void {
    this.questions = next
    this.pending = next
    if (this.state !== "conflict") this.state = "saving"
  }

  async flush(): Promise<void> {
    if (this.running) await this.running
    if (!this.pending || this.state === "conflict") return
    const next = this.pending
    this.pending = null
    this.running = this.save(this.version, next).then((saved) => {
      this.version = saved.version
      this.state = this.pending ? "saving" : "saved"
    }).catch((e) => {
      this.pending = this.pending ?? next   // nichts verlieren
      if (e instanceof StoryApiError && e.status === 409 && e.current) {
        this.conflict = e.current as Interview
        this.state = "conflict"
      } else {
        this.state = "failed"
      }
    }).finally(() => { this.running = null })
    await this.running
  }

  async resolve(how: "reload" | "keep"): Promise<void> {
    const c = this.conflict
    if (!c) return
    this.conflict = null
    this.version = c.version
    if (how === "reload") {
      this.pending = null
      this.questions = c.questions
      this.state = "saved"
      return
    }
    this.state = "saving"
    await this.flush()
  }
}
