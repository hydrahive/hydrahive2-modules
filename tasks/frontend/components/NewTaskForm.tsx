import { useState } from "react"
import type { TaskPriority } from "../types"

interface NewTaskFormProps {
  onSave: (title: string, priority: TaskPriority) => Promise<void>
  onCancel: () => void
}

export function NewTaskForm({ onSave, onCancel }: NewTaskFormProps) {
  const [title, setTitle] = useState("")
  const [priority, setPriority] = useState<TaskPriority>("medium")
  const [saving, setSaving] = useState(false)

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    if (!title.trim()) return
    setSaving(true)
    try {
      await onSave(title.trim(), priority)
    } finally {
      setSaving(false)
    }
  }

  return (
    <form onSubmit={handleSubmit} className="p-2 border-b border-[rgb(var(--hh-s-rand,42_54_75))] space-y-1.5">
      <input
        autoFocus
        value={title}
        onChange={(e) => setTitle(e.target.value)}
        placeholder="Aufgabentitel…"
        className="w-full bg-[rgb(var(--hh-s-innen,17_24_39)/0.6)] border border-[rgb(var(--hh-s-rand,42_54_75))] rounded px-2 py-1 text-xs text-[#e8eef8] placeholder:text-[#9aa7bc] focus:outline-none focus:border-[#69d7ff]/50"
      />
      <div className="flex items-center gap-1.5">
        <select
          value={priority}
          onChange={(e) => setPriority(e.target.value as TaskPriority)}
          className="bg-[rgb(var(--hh-s-innen,17_24_39)/0.6)] border border-[rgb(var(--hh-s-rand,42_54_75))] rounded px-1.5 py-1 text-[11px] text-[#c8d2df] focus:outline-none"
        >
          <option value="high">! Hoch</option>
          <option value="medium">~ Mittel</option>
          <option value="low">↓ Niedrig</option>
        </select>
        <div className="flex-1" />
        <button type="button" onClick={onCancel} className="text-[11px] text-[#9aa7bc] hover:text-[#c8d2df] px-2 py-1">
          Abbrechen
        </button>
        <button
          type="submit"
          disabled={saving || !title.trim()}
          className="text-[11px] bg-[#69d7ff]/80 hover:bg-[#69d7ff]/80 disabled:opacity-40 text-white px-2.5 py-1 rounded transition-colors"
        >
          {saving ? "…" : "Hinzufügen"}
        </button>
      </div>
    </form>
  )
}
