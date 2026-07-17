import { useEffect, useState, type FormEvent } from "react"
import { Crown, Download, KeyRound, Trash2, UserMinus, UserPlus, Users } from "lucide-react"
import { AdminConfirmDialog } from "@/features/cockpit/admin/ui/AdminConfirmDialog"
import { errorMessage, haushaltsbuchApi, isConflict } from "./api"
import type { Household, Invite, Member } from "./types"
import { Button, ErrorState, Field, Input, LoadingState, Select, panel } from "./ui"

interface HouseholdViewProps {
  household: Household
  onChanged: (household: Household | null) => void
}

export function HouseholdView({ household, onChanged }: HouseholdViewProps) {
  const owner = household.current_role === "owner"
  const [invites, setInvites] = useState<Invite[]>()
  const [error, setError] = useState<unknown>()
  const [busy, setBusy] = useState(false)
  const [name, setName] = useState(household.name)
  const [currency, setCurrency] = useState(household.base_currency)
  const [timezone, setTimezone] = useState(household.timezone)
  const [username, setUsername] = useState("")
  const [inviteHours, setInviteHours] = useState("24")
  const [newInviteCode, setNewInviteCode] = useState("")
  const [confirmRemove, setConfirmRemove] = useState<Member>()
  const [confirmTransfer, setConfirmTransfer] = useState<Member>()
  const [deleteName, setDeleteName] = useState("")
  const [deleteWord, setDeleteWord] = useState("")

  const loadInvites = () => {
    if (!owner) return
    setError(undefined)
    haushaltsbuchApi.invites().then(setInvites).catch(setError)
  }
  useEffect(loadInvites, [household.id, owner])
  useEffect(() => {
    setName(household.name)
    setCurrency(household.base_currency)
    setTimezone(household.timezone)
  }, [household])

  async function refresh() {
    const current = await haushaltsbuchApi.household()
    onChanged(current)
  }
  async function run(action: () => Promise<unknown>, after?: () => void) {
    setBusy(true); setError(undefined)
    try { await action(); after?.(); await refresh() }
    catch (cause) { setError(cause) }
    finally { setBusy(false) }
  }
  function saveSettings(event: FormEvent) {
    event.preventDefault()
    void run(() => haushaltsbuchApi.updateHousehold({ name: name.trim(), base_currency: currency.trim().toUpperCase(), timezone: timezone.trim(), create_default_categories: false, revision: household.revision }))
  }
  function addMember(event: FormEvent) {
    event.preventDefault()
    const value = username.trim()
    if (value) void run(() => haushaltsbuchApi.addMember(value), () => setUsername(""))
  }
  async function createInvite() {
    setBusy(true); setError(undefined); setNewInviteCode("")
    try {
      const invite = await haushaltsbuchApi.createInvite(Number(inviteHours))
      setNewInviteCode(invite.code ?? "")
      setInvites(await haushaltsbuchApi.invites())
    } catch (cause) { setError(cause) } finally { setBusy(false) }
  }
  async function revokeInvite(invite: Invite) {
    setBusy(true); setError(undefined)
    try { await haushaltsbuchApi.revokeInvite(invite.id, invite.revision); setInvites(await haushaltsbuchApi.invites()) }
    catch (cause) { setError(cause) } finally { setBusy(false) }
  }
  async function exportData() {
    setBusy(true); setError(undefined)
    try {
      const data = await haushaltsbuchApi.exportHousehold()
      const url = URL.createObjectURL(new Blob([JSON.stringify(data, null, 2)], { type: "application/json" }))
      const link = document.createElement("a")
      link.href = url; link.download = `haushaltsbuch-${household.id}.json`; link.click()
      URL.revokeObjectURL(url)
    } catch (cause) { setError(cause) } finally { setBusy(false) }
  }
  async function deleteHousehold() {
    setBusy(true); setError(undefined)
    try { await haushaltsbuchApi.deleteHousehold(household.name); onChanged(null) }
    catch (cause) { setError(cause) } finally { setBusy(false) }
  }

  return <div className="space-y-5">
    {error !== undefined && <ErrorState error={errorMessage(error)} conflict={isConflict(error)} onRetry={isConflict(error) ? refresh : undefined} />}
    <section className={`${panel} p-5`}>
      <h2 className="mb-4 flex items-center gap-2 font-bold text-[#e8eef8]"><Users size={17} className="text-cyan-300" />Haushalt</h2>
      <form onSubmit={saveSettings} className="grid gap-4 md:grid-cols-3">
        <Field label="Name"><Input required maxLength={120} value={name} disabled={!owner || busy} onChange={(event) => setName(event.target.value)} /></Field>
        <Field label="Basiswährung"><Input required minLength={3} maxLength={3} value={currency} disabled={!owner || busy} onChange={(event) => setCurrency(event.target.value)} /></Field>
        <Field label="IANA-Zeitzone"><Input required value={timezone} disabled={!owner || busy} onChange={(event) => setTimezone(event.target.value)} /></Field>
        {owner && <div className="md:col-span-3 flex justify-end"><Button type="submit" tone="primary" disabled={busy || !name.trim() || currency.trim().length !== 3}>Einstellungen speichern</Button></div>}
      </form>
    </section>

    <section className={`${panel} p-5`}>
      <div className="mb-4 flex items-center justify-between"><h2 className="flex items-center gap-2 font-bold text-[#e8eef8]"><Users size={17} className="text-cyan-300" />Mitglieder</h2><span className="text-xs text-[#718097]">{household.members.length} Mitglied{household.members.length === 1 ? "" : "er"}</span></div>
      {owner && <form onSubmit={addMember} className="mb-4 flex gap-2"><Input aria-label="Benutzername" required maxLength={128} value={username} onChange={(event) => setUsername(event.target.value)} placeholder="Exakten Benutzernamen eingeben" /><Button type="submit" tone="primary" disabled={busy || !username.trim()}><UserPlus size={13} className="mr-1 inline" />Hinzufügen</Button></form>}
      <div className="divide-y divide-[#263247]">{household.members.map((member) => <div key={member.id} className="flex items-center gap-3 py-3 text-sm"><div className="grid h-8 w-8 place-items-center rounded-full bg-[#1c2940] font-bold text-cyan-200">{member.username.slice(0, 1).toUpperCase()}</div><div className="min-w-0 flex-1"><strong className="block truncate text-[#d4deeb]">{member.username}</strong><span className="text-xs text-[#718097]">{member.role === "owner" ? "Eigentümer" : "Mitglied"}</span></div>{member.role === "owner" ? <Crown size={16} className="text-amber-300" /> : owner && <><Button disabled={busy} onClick={() => setConfirmTransfer(member)}><Crown size={13} className="mr-1 inline" />Übertragen</Button><Button tone="danger" disabled={busy} aria-label={`${member.username} entfernen`} onClick={() => setConfirmRemove(member)}><UserMinus size={13} /></Button></>}</div>)}</div>
    </section>

    {owner && <section className={`${panel} p-5`}>
      <h2 className="mb-4 flex items-center gap-2 font-bold text-[#e8eef8]"><KeyRound size={17} className="text-cyan-300" />Einladungen</h2>
      <div className="mb-4 flex flex-wrap gap-2"><Select className="w-44" value={inviteHours} onChange={(event) => setInviteHours(event.target.value)}><option value="24">24 Stunden</option></Select><Button tone="primary" disabled={busy} onClick={createInvite}>Einladung erzeugen</Button></div>
      {newInviteCode && <div className="mb-4 rounded-[4px] border border-cyan-400/30 bg-cyan-400/10 p-3"><p className="mb-2 text-xs text-cyan-100">Dieser Code wird nur jetzt im Klartext angezeigt:</p><code className="break-all text-sm text-[#e8eef8]">{newInviteCode}</code><Button className="ml-3" onClick={() => void navigator.clipboard.writeText(newInviteCode)}>Kopieren</Button></div>}
      {!invites ? <LoadingState label="Einladungen werden geladen …" /> : invites.length ? <div className="divide-y divide-[#263247]">{invites.map((invite) => <div key={invite.id} className="flex items-center gap-3 py-3 text-sm"><span className="min-w-0 flex-1 text-[#b5c1d2]">Einladung #{invite.id}<small className="ml-2 text-[#718097]">{invite.status} · bis {new Date(invite.expires_at).toLocaleString()}</small></span>{invite.status === "pending" && <Button tone="danger" disabled={busy} onClick={() => void revokeInvite(invite)}>Widerrufen</Button>}</div>)}</div> : <p className="text-sm text-[#8d9ab0]">Noch keine Einladungen.</p>}
    </section>}

    <section className={`${panel} p-5`}><h2 className="font-bold text-[#e8eef8]">Datenexport</h2><p className="my-2 text-sm text-[#8d9ab0]">Exportiert Haushalt, Finanzdaten und Audit-Ereignisse als JSON.</p><Button disabled={busy} onClick={() => void exportData()}><Download size={13} className="mr-1 inline" />JSON exportieren</Button></section>

    {owner && <section className="rounded-[6px] border border-rose-500/30 bg-rose-500/[6%] p-5"><h2 className="font-bold text-rose-100">Gefahrenbereich</h2><p className="mt-2 text-sm text-rose-100/70">Die Löschung entfernt den gesamten Haushalt unwiderruflich.</p><div className="mt-4 grid gap-3 sm:grid-cols-2"><Field label={`Haushaltsname „${household.name}“`}><Input value={deleteName} onChange={(event) => setDeleteName(event.target.value)} /></Field><Field label="Zur Bestätigung DELETE eingeben"><Input value={deleteWord} onChange={(event) => setDeleteWord(event.target.value)} /></Field></div><div className="mt-3 flex justify-end"><Button tone="danger" disabled={busy || deleteName !== household.name || deleteWord !== "DELETE"} onClick={() => void deleteHousehold()}><Trash2 size={13} className="mr-1 inline" />Haushalt löschen</Button></div></section>}

    {confirmRemove && <AdminConfirmDialog title="Mitglied entfernen?" confirmLabel="Entfernen" cancelLabel="Abbrechen" confirmTone="danger" busy={busy} onClose={() => setConfirmRemove(undefined)} onConfirm={() => void run(() => haushaltsbuchApi.removeMember(confirmRemove.id, confirmRemove.revision), () => setConfirmRemove(undefined))}>„{confirmRemove.username}“ verliert den Zugriff auf den Haushalt.</AdminConfirmDialog>}
    {confirmTransfer && <AdminConfirmDialog title="Eigentum übertragen?" confirmLabel="Übertragen" cancelLabel="Abbrechen" busy={busy} onClose={() => setConfirmTransfer(undefined)} onConfirm={() => void run(() => haushaltsbuchApi.transferOwnership(confirmTransfer.id, confirmTransfer.revision), () => setConfirmTransfer(undefined))}>„{confirmTransfer.username}“ wird Eigentümer. Du bist anschließend reguläres Mitglied.</AdminConfirmDialog>}
  </div>
}
