/** ATTRAPPE „Geführtes Studio“: Zustand nur im Browser, Erzeugen wird mit Wartezeit gespielt. */
import { useState } from "react"
import { emptyScene, fake, PICS, storyScenes, suggestedCast, type FilmFormat, type FilmKind, type Person, type Scene } from "./mockData"

export type StepId = 1 | 2 | 3 | 4 | 5

export function useGuidedMock() {
  const [step, setStep] = useState<StepId>(1)
  const [idea, setIdea] = useState("")
  const [kind, setKind] = useState<FilmKind>("trailer")
  const [length, setLength] = useState(0)
  const [format, setFormat] = useState<FilmFormat>("quer")
  const [scenes, setScenes] = useState<Scene[]>([])
  const [people, setPeople] = useState<Person[]>([])
  const [writing, setWriting] = useState(false)
  const [film, setFilm] = useState<"none" | "busy" | "done">("none")
  const [extras, setExtras] = useState({ music: true, voice: false, subtitles: true })

  const patchScene = (id: string, p: Partial<Scene> | ((s: Scene) => Partial<Scene>)) =>
    setScenes((all) => all.map((s) => (s.id === id ? { ...s, ...(typeof p === "function" ? p(s) : p) } : s)))
  const patchPerson = (id: string, p: Partial<Person>) => setPeople((all) => all.map((x) => (x.id === id ? { ...x, ...p } : x)))

  const writeStory = async () => {
    setWriting(true); await fake(1800)
    setScenes(storyScenes()); setPeople(suggestedCast()); setWriting(false)
  }
  const addScene = () => setScenes((all) => [...all, emptyScene(all.length)])
  const removeScene = (id: string) => setScenes((all) => all.filter((s) => s.id !== id))
  const moveScene = (id: string, dir: -1 | 1) => setScenes((all) => {
    const i = all.findIndex((s) => s.id === id); const j = i + dir
    if (j < 0 || j >= all.length) return all
    const next = [...all]; [next[i], next[j]] = [next[j], next[i]]; return next
  })

  const addPerson = (k: Person["kind"]) =>
    setPeople((all) => [...all, { id: `p${Date.now()}`, kind: k, name: "", state: "leer" }])
  const removePerson = (id: string) => setPeople((all) => all.filter((x) => x.id !== id))
  const givePhoto = async (id: string) => {
    patchPerson(id, { photo: PICS.hydraFoto, state: "busy" }); await fake(1600)
    patchPerson(id, { probe: PICS.probe1, state: "probe" })
  }
  const retryProbe = async (id: string, current?: string) => {
    patchPerson(id, { state: "busy" }); await fake(1400)
    patchPerson(id, { probe: current === PICS.probe1 ? PICS.probe2 : PICS.probe1, state: "probe" })
  }

  const makeImage = async (id: string) => {
    patchScene(id, { imageBusy: true }); await fake()
    patchScene(id, (s) => ({ imageBusy: false, images: [...s.images, s.sample], pick: s.images.length }))
  }
  const makeAllImages = async () => {
    for (const s of scenes.filter((x) => x.images.length === 0)) void makeImage(s.id)
  }
  const dropImage = (id: string) => patchScene(id, (s) => {
    const images = s.images.filter((_, i) => i !== s.pick)
    return { images, pick: Math.max(0, Math.min(s.pick, images.length - 1)), clip: images.length ? s.clip : "none" }
  })
  const flip = (id: string, dir: -1 | 1) => patchScene(id, (s) => ({ pick: (s.pick + dir + s.images.length) % s.images.length }))

  const makeClip = async (id: string) => {
    patchScene(id, { clip: "busy" }); await fake(2200); patchScene(id, { clip: "done" })
  }
  const makeAllClips = async () => {
    for (const s of scenes.filter((x) => x.images.length && x.clip === "none")) void makeClip(s.id)
  }
  const makeFilm = async () => { setFilm("busy"); await fake(2600); setFilm("done") }

  return {
    step, setStep, idea, setIdea, kind, setKind, length, setLength, format, setFormat, writing,
    scenes, patchScene, writeStory, addScene, removeScene, moveScene,
    people, patchPerson, addPerson, removePerson, givePhoto, retryProbe,
    makeImage, makeAllImages, dropImage, flip, makeClip, makeAllClips,
    film, makeFilm, extras, setExtras,
  }
}

export type Guided = ReturnType<typeof useGuidedMock>

/** Was in einem Schritt noch fehlt (für Haken links und den Hinweis über „Weiter“) */
export function missing(g: Guided, step: StepId): string | null {
  if (step === 1) return g.scenes.length ? null : "Noch keine Szenen – lass dir eine Geschichte vorschlagen oder schreib selbst."
  if (step === 2) {
    const open = g.people.filter((p) => p.state !== "passt" && p.state !== "ohne").length
    return open ? `${open} noch nicht fertig – du kannst trotzdem weiter.` : null
  }
  if (step === 3) {
    const open = g.scenes.filter((s) => !s.images.length).length
    return open ? `${open} Szene${open === 1 ? "" : "n"} ohne Bild – du kannst trotzdem weiter.` : null
  }
  if (step === 4) {
    const open = g.scenes.filter((s) => s.images.length && s.clip === "none").length
    return open ? `${open} Szene${open === 1 ? "" : "n"} noch ohne Bewegung – sie erscheinen dann als Standbild.` : null
  }
  return g.film === "done" ? null : "Der Film ist noch nicht erzeugt."
}
