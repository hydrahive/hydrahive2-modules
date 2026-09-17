import { useState } from "react"
import { ChevronDown, ChevronRight, Plus, Users } from "lucide-react"
import { useTranslation } from "react-i18next"
import { ticketsApi } from "./api"
import type { Team } from "./types"

interface Props { teams: Team[]; onChanged: () => void }

export function TeamSettings({ teams, onChanged }: Props) {
  const { t } = useTranslation("tickets")
  const [open, setOpen] = useState(false)
  const [name, setName] = useState("")
  const [description, setDescription] = useState("")
  const [error, setError] = useState(false)

  async function createTeam() {
    if (!name.trim()) return
    try { await ticketsApi.createTeam(name.trim(), description.trim()); setName(""); setDescription(""); setError(false); onChanged() } catch { setError(true) }
  }

  return (
    <section className="border-t border-white/10 bg-zinc-950/40 p-3">
      <button onClick={() => setOpen((value) => !value)} className="flex w-full items-center gap-2 text-left text-sm font-medium text-zinc-300"><Users size={15} className="text-sky-400" />{t("teams")} {open ? <ChevronDown size={14} className="ml-auto" /> : <ChevronRight size={14} className="ml-auto" />}</button>
      {open && <div className="mt-3 space-y-3"><div className="flex gap-2"><input value={name} onChange={(event) => setName(event.target.value)} placeholder={t("teamName")} className="min-w-0 flex-1 rounded-lg border border-white/10 bg-zinc-900 px-2 py-1.5 text-xs text-zinc-200" /><button onClick={() => void createTeam()} className="rounded-lg bg-sky-500/20 p-2 text-sky-300" title={t("createTeam")}><Plus size={14} /></button></div>{error && <p className="text-xs text-red-300">{t("teamError")}</p>}<div className="space-y-1">{teams.map((team) => <div key={team.id} className="rounded-lg bg-white/[3%] px-2 py-1.5 text-xs text-zinc-400"><div className="font-medium text-zinc-200">{team.name}</div><div>{team.members.length} {t("members")}</div></div>)}{teams.length === 0 && <p className="text-xs text-zinc-600">{t("noTeams")}</p>}</div></div>}
    </section>
  )
}
