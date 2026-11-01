import { api } from "@/shared/api-client"
import { BASE } from "./logic"

export interface Meta { stale: boolean; error: string | null; fetched_at: number }
export interface Port { idx: number; name: string; up: boolean; speed: number | null; uplink: boolean; poe: boolean | null; poe_w: number | null; media: string | null; tx_bytes: number | null; rx_bytes: number | null; errors: number }
export interface Radio { band: string; channel: number | null; tx_power: number | null; utilization: number | null; clients: number | null; satisfaction: number | null }
export interface Device {
  mac: string; name: string; model: string | null; kind: "gateway" | "switch" | "ap" | "other"; state: string; adopted: boolean
  ip: string | null; version: string | null; upgradable: boolean; upgrade_to: string | null; uptime_s: number | null
  clients: number | null; cpu: number | null; mem: number | null; satisfaction: number | null
  temps: { name: string; value: number }[]; tx_bytes: number | null; rx_bytes: number | null
  uplink: { mac: string; name: string | null; port: number | null; speed: number | null } | null; ports: Port[]; radios: Radio[]
}
export interface Client {
  mac: string; name: string; vendor: string | null; ip: string | null; online: boolean; wired: boolean; guest: boolean
  network: string | null; essid: string | null; band: string | null; signal: number | null; satisfaction: number | null
  uplink_name: string | null; uplink_port: number | null; uptime_s: number | null; down_bytes: number | null; up_bytes: number | null
  first_seen: number | null; last_seen: number | null; fixed_ip: boolean
}
export interface TreeNode { mac: string; name: string; kind: "device" | "client"; model: string | null; link: string | null; port: number | null; children: TreeNode[] }
export interface Net {
  tree: TreeNode[]
  networks: { name: string; purpose: string; vlan: number | null; subnet: string | null; dhcp: { on: boolean; start: string | null; stop: string | null } | null }[]
  wlans: { name: string; enabled: boolean; security: string | null; wpa_mode: string | null; bands: string[]; guest: boolean; hidden: boolean; network: string | null }[]
  forwards: { name: string; enabled: boolean; proto: string; port: string; to_ip: string; to_port: string }[]
  firewall_rules: number; routes: number
}
export interface Traffic { clients: Client[]; devices: { name: string; kind: string; tx_bytes: number | null; rx_bytes: number | null; ports: Pick<Port, "idx" | "name" | "up" | "tx_bytes" | "rx_bytes">[] }[] }
export type ClientFilter = { status: "all" | "online" | "offline"; link: "all" | "wired" | "wireless"; q: string }

export const getDevices = () => api.get<{ items: Device[] } & Meta>(`${BASE}/devices`)
export const getClients = (f: ClientFilter) => {
  const p = new URLSearchParams({ status: f.status, link: f.link })
  if (f.q.trim()) p.set("q", f.q.trim())
  return api.get<{ items: Client[]; total: number; online: number; wireless: number } & Meta>(`${BASE}/clients?${p}`)
}
export const getNet = () => api.get<Net & Meta>(`${BASE}/net`)
export const getTraffic = () => api.get<Traffic & Meta>(`${BASE}/traffic`)
