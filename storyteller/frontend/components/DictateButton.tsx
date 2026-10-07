// Ghostwriter G3 – Diktat: Mikrofon an/aus, Aufnahme an die Kern-Spracherkennung, Text wird zurückgegeben
// (die Antwort hängt ihn an). Gleiches Vorgehen wie das Chat-Mikrofon (MediaRecorder, passendes Format).
import { useRef, useState } from "react"
import { useTranslation } from "react-i18next"
import { Loader2, Mic, Square } from "lucide-react"
import { StoryApiError } from "../api"
import { transcribe } from "../interviewApi"

const MIMES = ["audio/webm;codecs=opus", "audio/webm", "audio/mp4", "audio/ogg;codecs=opus"]
const pickMime = () => (typeof MediaRecorder === "undefined" ? undefined
  : MIMES.find((m) => { try { return MediaRecorder.isTypeSupported(m) } catch { return false } }))

interface Props { onText: (text: string) => void; disabled?: boolean }

export function DictateButton({ onText, disabled }: Props) {
  const { t } = useTranslation("storyteller")
  const [state, setState] = useState<"idle" | "recording" | "working">("idle")
  const [error, setError] = useState("")
  const rec = useRef<MediaRecorder | null>(null)
  const chunks = useRef<Blob[]>([])

  const start = async () => {
    setError("")
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
      const mime = pickMime()
      const r = new MediaRecorder(stream, mime ? { mimeType: mime } : undefined)
      chunks.current = []
      r.ondataavailable = (e) => { if (e.data.size) chunks.current.push(e.data) }
      r.onstop = async () => {
        stream.getTracks().forEach((tr) => tr.stop())
        setState("working")
        try {
          const type = r.mimeType || mime || "audio/webm"
          const text = await transcribe(new Blob(chunks.current, { type }), type)
          if (text.trim()) onText(text)
          else setError(t("dictate_empty"))
        } catch (e) {
          setError(e instanceof StoryApiError && e.message ? t("dictate_failed", { message: e.message }) : t("dictate_failed", { message: "" }))
        } finally { setState("idle") }
      }
      rec.current = r
      r.start()
      setState("recording")
    } catch {
      setError(t("dictate_no_mic"))
    }
  }
  const stop = () => rec.current?.stop()

  return (
    <span className="inline-flex items-center gap-1">
      <button type="button" disabled={disabled || state === "working"} onClick={() => { if (state === "recording") stop(); else void start() }}
        title={state === "recording" ? t("dictate_stop") : t("dictate_start")} aria-pressed={state === "recording"}
        className={`st-dictate rounded p-1 ${state === "recording" ? "bg-red-500/20 text-red-300" : "text-zinc-400 hover:bg-white/10 hover:text-zinc-100"} disabled:opacity-40`}>
        {state === "working" ? <Loader2 className="h-4 w-4 animate-spin" /> : state === "recording" ? <Square className="h-4 w-4" /> : <Mic className="h-4 w-4" />}
      </button>
      {error && <span className="text-[11px] text-red-300" role="alert">{error}</span>}
    </span>
  )
}
