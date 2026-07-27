import { useCallback, useEffect, useRef, useState } from "react"

/**
 * Spracheingabe über die Web Speech API des Browsers.
 *
 * Bewusst rein clientseitig: kein Audio-Upload, keine Kosten, keine
 * Server-Abhängigkeit. `supported` ist false, wo der Browser die Schnittstelle
 * nicht hat (z.B. Firefox) — der Aufrufer blendet den Knopf dann aus, statt
 * einen toten Knopf zu zeigen.
 */
interface SpeechRecognitionLike {
  lang: string
  interimResults: boolean
  maxAlternatives: number
  start: () => void
  stop: () => void
  onresult: ((event: { results: ArrayLike<ArrayLike<{ transcript: string }>> }) => void) | null
  onerror: (() => void) | null
  onend: (() => void) | null
}

type RecognitionCtor = new () => SpeechRecognitionLike

function recognitionCtor(): RecognitionCtor | null {
  if (typeof window === "undefined") return null
  const w = window as unknown as {
    SpeechRecognition?: RecognitionCtor
    webkitSpeechRecognition?: RecognitionCtor
  }
  return w.SpeechRecognition ?? w.webkitSpeechRecognition ?? null
}

export function useSpeechInput(onResult: (text: string) => void, lang = "de-DE") {
  const [listening, setListening] = useState(false)
  const recognition = useRef<SpeechRecognitionLike | null>(null)
  const callback = useRef(onResult)
  callback.current = onResult

  const supported = recognitionCtor() !== null

  useEffect(() => () => {
    // Beim Verlassen der Seite ein laufendes Mikrofon nicht offen lassen.
    recognition.current?.stop()
    recognition.current = null
  }, [])

  const toggle = useCallback(() => {
    if (listening) {
      recognition.current?.stop()
      setListening(false)
      return
    }
    const Ctor = recognitionCtor()
    if (!Ctor) return
    const instance = new Ctor()
    instance.lang = lang
    instance.interimResults = false
    instance.maxAlternatives = 1
    instance.onresult = (event) => {
      const transcript = event.results?.[0]?.[0]?.transcript
      if (transcript) callback.current(transcript)
    }
    instance.onerror = () => setListening(false)
    instance.onend = () => setListening(false)
    recognition.current = instance
    instance.start()
    setListening(true)
  }, [lang, listening])

  return { supported, listening, toggle }
}
