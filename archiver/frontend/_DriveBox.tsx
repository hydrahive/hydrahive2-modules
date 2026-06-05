import { HardDrive, RefreshCw, Plug, PlugZap, Unplug } from "lucide-react"
import { CollapsibleBox } from "@/shared/CollapsibleBox"
import type { Drive } from "./api"

interface Props {
  drives: Drive[]
  loading: boolean
  mounting: string | null
  selectedDevice: string | null
  onSelect: (drive: Drive) => void
  onRefresh: () => void
  onMount: (device: string) => void
  onUnmount: (device: string, mountpoint: string) => void
  onRemount: (device: string, mountpoint: string) => void
}

export function DriveBox({
  drives, loading, mounting, selectedDevice,
  onSelect, onRefresh, onMount, onUnmount, onRemount,
}: Props) {
  return (
    <CollapsibleBox
      boxId="archiver.drives"
      title="Laufwerke"
      icon={<HardDrive size={14} />}
      color="138,92,246"
      defaultCollapsed={false}
      headerRight={
        <button
          onClick={onRefresh}
          disabled={loading}
          title="Aktualisieren"
          className="text-zinc-600 hover:text-zinc-300 transition-colors disabled:opacity-40"
        >
          <RefreshCw size={12} className={loading ? "animate-spin" : ""} />
        </button>
      }
    >
      <div className="p-4 space-y-2">
        {drives.length === 0 ? (
          <p className="text-xs text-zinc-600">Kein USB-Laufwerk erkannt.</p>
        ) : (
          drives.map(d => (
            <div
              key={d.device}
              className={`flex items-center gap-3 px-3 py-2.5 rounded-lg border transition-colors ${
                d.mountpoint
                  ? selectedDevice === d.device
                    ? "border-violet-500/50 bg-violet-500/10 text-zinc-100 cursor-pointer"
                    : "border-white/[6%] hover:border-white/[12%] text-zinc-300 cursor-pointer"
                  : "border-white/[4%] text-zinc-500"
              }`}
              onClick={() => d.mountpoint && onSelect(d)}
            >
              <HardDrive size={14} className={d.mountpoint ? "text-violet-400" : "text-zinc-600"} />
              <div className="flex-1 min-w-0">
                <div className="text-sm font-medium truncate">{d.label}</div>
                <div className="text-[11px] text-zinc-500 truncate">
                  {d.mountpoint
                    ? <span>{d.mountpoint}</span>
                    : <span className="text-amber-500/80">nicht gemountet</span>}
                  {" · "}{d.size}
                  {d.fstype && <span className="ml-1 text-zinc-600">({d.fstype})</span>}
                </div>
              </div>
              {!d.mountpoint ? (
                <button
                  onClick={e => { e.stopPropagation(); onMount(d.device) }}
                  disabled={mounting === d.device}
                  className="flex items-center gap-1 px-2 py-1 rounded text-[11px] bg-amber-500/10 border border-amber-500/20 text-amber-300 hover:bg-amber-500/20 disabled:opacity-40 transition-colors flex-shrink-0"
                >
                  <Plug size={10} />
                  {mounting === d.device ? "…" : "Mounten"}
                </button>
              ) : (
                <div className="flex gap-1 flex-shrink-0">
                  <button
                    onClick={e => { e.stopPropagation(); onRemount(d.device, d.mountpoint) }}
                    disabled={mounting === d.device}
                    title="Remounten (aushängen + neu einhängen)"
                    className="flex items-center gap-1 px-2 py-1 rounded text-[11px] bg-blue-500/10 border border-blue-500/20 text-blue-300 hover:bg-blue-500/20 disabled:opacity-40 transition-colors"
                  >
                    <PlugZap size={10} />
                    {mounting === d.device ? "…" : "Remount"}
                  </button>
                  <button
                    onClick={e => { e.stopPropagation(); onUnmount(d.device, d.mountpoint) }}
                    disabled={mounting === d.device}
                    title="Sauber aushängen"
                    className="flex items-center gap-1 px-2 py-1 rounded text-[11px] bg-zinc-700/50 border border-white/[6%] text-zinc-400 hover:text-zinc-200 disabled:opacity-40 transition-colors"
                  >
                    <Unplug size={10} />
                  </button>
                </div>
              )}
            </div>
          ))
        )}
      </div>
    </CollapsibleBox>
  )
}
