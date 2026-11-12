import { useCallback, useEffect, useRef, useState } from "react"
import { projectsApi } from "@/features/projects/api"
import { ideasApi } from "./api"
import { sortIdeas, toListItem, upsertIdea } from "./ideaView"
import type { Idea, IdeaChanges, IdeaListItem, ProjectRef } from "./types"

/** Lädt Ideen und Projekte und hält Liste und ausgewählte Idee nach jeder Änderung in Deckung. */
export function useIdeas() {
  const [ideas, setIdeas] = useState<IdeaListItem[]>([])
  const [projects, setProjects] = useState<ProjectRef[]>([])
  const [active, setActive] = useState<Idea | null>(null)
  const [loading, setLoading] = useState(true)
  const [loadFailed, setLoadFailed] = useState(false)
  const [tasksInstalled, setTasksInstalled] = useState(false)
  const [blueprintInstalled, setBlueprintInstalled] = useState(false)
  const wanted = useRef<string | null>(null)

  const reload = useCallback(async () => {
    try {
      const data = await ideasApi.list()
      setIdeas(sortIdeas(data.ideas))
      setLoadFailed(false)
    } catch {
      setLoadFailed(true)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    queueMicrotask(() => { void reload() })
    // Ohne Projektliste bleibt die Seite benutzbar: Ideen ohne Projekt gehen immer.
    projectsApi.list()
      .then((list) => setProjects(list.map((project) => ({ id: project.id, name: project.name }))))
      .catch(() => setProjects([]))
    // Ohne Stammdaten gibt es keine Knöpfe für Task und Board; alles andere geht weiter.
    ideasApi.meta()
      .then((meta) => { setTasksInstalled(meta.tasks_installed); setBlueprintInstalled(meta.blueprint_installed) })
      .catch(() => { setTasksInstalled(false); setBlueprintInstalled(false) })
  }, [reload])

  const show = useCallback((idea: Idea) => {
    wanted.current = idea.id
    setActive(idea)
    setIdeas((current) => upsertIdea(current, toListItem(idea)))
  }, [])

  const select = useCallback(async (id: string | null) => {
    wanted.current = id
    if (id === null) {
      setActive(null)
      return null
    }
    const idea = await ideasApi.get(id)
    // Wurde inzwischen eine andere Idee gewählt, die späte Antwort verwerfen.
    if (wanted.current === id) setActive(idea)
    return idea
  }, [])

  const create = useCallback(async (data: { title: string; body: string; project_id: string | null }) => {
    const idea = await ideasApi.create(data)
    show(idea)
    return idea
  }, [show])

  const update = useCallback(async (id: string, changes: IdeaChanges) => {
    const idea = await ideasApi.update(id, changes)
    setIdeas((current) => upsertIdea(current, toListItem(idea)))
    if (wanted.current === id) setActive(idea)
    return idea
  }, [])

  const createTask = useCallback(async (id: string) => {
    const idea = await ideasApi.createTask(id)
    setIdeas((current) => upsertIdea(current, toListItem(idea)))
    if (wanted.current === id) setActive(idea)
    return idea
  }, [])

  const createBoard = useCallback(async (id: string) => {
    const idea = await ideasApi.createBoard(id)
    setIdeas((current) => upsertIdea(current, toListItem(idea)))
    if (wanted.current === id) setActive(idea)
    return idea
  }, [])

  /** Nur aus der Liste nehmen. Eine geöffnete Idee bleibt stehen, damit ihr Text nicht verloren geht. */
  const forget = useCallback((id: string) => {
    setIdeas((current) => current.filter((idea) => idea.id !== id))
  }, [])

  const remove = useCallback(async (id: string) => {
    await ideasApi.remove(id)
    forget(id)
    if (wanted.current === id) {
      wanted.current = null
      setActive(null)
    }
  }, [forget])

  const removeNote = useCallback(async (id: string, noteId: number) => {
    await ideasApi.removeNote(id, noteId)
    const idea = await ideasApi.get(id)
    setIdeas((current) => upsertIdea(current, toListItem(idea)))
    if (wanted.current === id) setActive(idea)
  }, [])

  return {
    ideas, projects, active, loading, loadFailed, tasksInstalled, blueprintInstalled,
    reload, select, create, update, createTask, createBoard, remove, removeNote, forget,
  }
}
