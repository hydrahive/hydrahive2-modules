import type { ReactElement } from "react"
import { renderToStaticMarkup } from "react-dom/server"
import { describe, expect, it, vi } from "vitest"

vi.mock("react-i18next", () => ({ useTranslation: () => ({ t: (k: string, o?: Record<string, unknown>) => (o ? `${k}:${JSON.stringify(o)}` : k), i18n: { language: "de" } }) }))
vi.mock("@/shared/api-client", () => ({ api: { get: vi.fn(() => new Promise(() => {})), post: vi.fn(), put: vi.fn(), postForm: vi.fn() } }))
import type { Client, Device, Net, Traffic } from "./admin"
import { ClientRow } from "./ClientsPanel"
import { DeviceCard } from "./DeviceCard"
import { networkI18n } from "./i18n"
import { NetView, TreeItem } from "./NetPanel"
import { share } from "./fmt"
import { TrafficView } from "./TrafficPanel"

const html = (el: ReactElement) => renderToStaticMarkup(el)
const DEV: Device = { mac: "02:00:00:00:00:01", name: "Dream Machine Pro", model: "UDMPRO", kind: "gateway", state: "online", adopted: true,
  ip: "10.0.0.1", version: "5.1.34", upgradable: false, upgrade_to: null, uptime_s: 41055, clients: 42, cpu: 5, mem: 49.1, satisfaction: null,
  temps: [{ name: "CPU", value: 34.5 }], tx_bytes: 65016436549, rx_bytes: 1435000592, uplink: null,
  ports: [{ idx: 1, name: "Port 1", up: true, speed: 1000, uplink: false, poe: false, poe_w: 0, media: "GE", tx_bytes: 48e9, rx_bytes: 1e10, errors: 2 },
    { idx: 2, name: "Port 2", up: false, speed: null, uplink: false, poe: false, poe_w: 0, media: "GE", tx_bytes: 0, rx_bytes: 0, errors: 0 },
    { idx: 9, name: "Port 9", up: true, speed: 1000, uplink: true, poe: null, poe_w: null, media: "GE", tx_bytes: 1, rx_bytes: 2, errors: 0 }],
  radios: [] }
const CL: Client = { mac: "02:00:00:00:00:05", name: "Fernseher", vendor: "Sony", ip: "10.0.0.50", online: true, wired: false, guest: false,
  network: "Default", essid: "Heimnetz", band: "5", signal: -72, satisfaction: 90, uplink_name: "FlexHD", uplink_port: null, uptime_s: 3600,
  down_bytes: 3e9, up_bytes: 2e7, first_seen: 1, last_seen: 1793571940, fixed_ip: true }

describe("Geräte", () => {
  it("Router mit Kennzahlen, Ports (frei, Uplink, Fehler)", () => {
    const h = html(<DeviceCard d={DEV} />)
    for (const s of ["Dream Machine Pro", "kind.gateway", "state.online", "dev.firmware:{&quot;v&quot;:&quot;5.1.34&quot;}",
      "dev.temp:{&quot;name&quot;:&quot;CPU&quot;,&quot;v&quot;:34.5}", "dev.port_uplink", "dev.port_down", "dev.errors:{&quot;n&quot;:2}", "1 Gbit/s", "65,0 GB"]) expect(h).toContain(s)
    expect(h).not.toContain("dev.update")
    expect(h).not.toContain("dev.radios")
  })
  it("Update, Uplink mit Port, Funk", () => {
    const h = html(<DeviceCard d={{ ...DEV, kind: "ap", upgradable: true, upgrade_to: "6.8", uplink: { mac: "x", name: "Switch", port: 5, speed: 1000 }, ports: [],
      radios: [{ band: "2.4", channel: 11, tx_power: 17, utilization: 20, clients: 10, satisfaction: 96 }] }} />)
    expect(h).toContain("dev.update:{&quot;v&quot;:&quot;6.8&quot;}")
    expect(h).toContain("dev.uplink:{&quot;name&quot;:&quot;Switch&quot;,&quot;port&quot;:&quot;dev.uplink_port:{\\&quot;n\\&quot;:5}&quot;}")
    expect(h).toContain("dev.channel:{&quot;c&quot;:11}")
    expect(h).not.toContain("dev.ports")
  })
  it("nicht übernommen: nur Hinweis", () => {
    const h = html(<DeviceCard d={{ ...DEV, adopted: false, state: "pending" }} />)
    expect(h).toContain("dev.not_adopted")
    expect(h).not.toContain("dev.firmware")
  })
})

describe("Clients", () => {
  it("WLAN-Client online mit Signal, Verkehr, feste IP", () => {
    const h = html(<ClientRow c={CL} />)
    for (const s of ["Fernseher", "Sony · 10.0.0.50", "cl.via_wlan:{&quot;band&quot;:&quot;5&quot;,&quot;ap&quot;:&quot;FlexHD&quot;}", "sig.weak", "cl.fixed_ip", "3,0 GB"]) expect(h).toContain(s)
    expect(h).toContain('data-client="online"')
    expect(h).not.toContain("cl.last_seen")
  })
  it("Kabel-Client mit Port, offline mit zuletzt gesehen", () => {
    const off = html(<ClientRow c={{ ...CL, online: false }} />)
    expect(off).not.toContain("cl.signal")
    const h = html(<ClientRow c={{ ...CL, wired: true, online: false, uplink_name: "Switch", uplink_port: 3, signal: null }} />)
    expect(h).toContain("cl.via_wire:{&quot;dev&quot;:&quot;Switch&quot;,&quot;port&quot;:&quot;cl.port:{\\&quot;n\\&quot;:3}&quot;}")
    expect(h).toContain("cl.last_seen")
    expect(h).not.toContain("cl.signal")
    expect(h).toContain('data-client="offline"')
  })
  it("unbekannter Uplink, Gast", () => {
    const h = html(<ClientRow c={{ ...CL, uplink_name: null, guest: true }} />)
    expect(h).toContain("cl.unknown_uplink")
    expect(h).toContain("cl.guest")
  })
})

const NET: Net = {
  tree: [{ mac: "a", name: "Dream Machine Pro", kind: "device", model: "UDMPRO", link: null, port: null, children: [
    { mac: "b", name: "Switch", kind: "device", model: "USL8LP", link: "wired", port: 5, children: [{ mac: "c", name: "NAS", kind: "client", model: null, link: "wired", port: 1, children: [] }] },
    { mac: "d", name: "Handy", kind: "client", model: null, link: "wireless", port: null, children: [] }] }],
  networks: [{ name: "Default", purpose: "corporate", vlan: null, subnet: "10.0.0.1/24", dhcp: { on: true, start: "10.0.0.6", stop: "10.0.0.254" } },
    { name: "Internet 1", purpose: "wan", vlan: null, subnet: null, dhcp: null }],
  wlans: [{ name: "Heimnetz", enabled: true, security: "wpapsk", wpa_mode: "wpa2", bands: ["2g", "5g"], guest: false, hidden: false, network: "Default" }],
  forwards: [{ name: "plex", enabled: true, proto: "tcp_udp", port: "32400", to_ip: "10.0.0.3", to_port: "32400" }], firewall_rules: 0, routes: 0,
}

describe("Netz", () => {
  it("Aufbau: Geräte offen, Clients eingeklappt mit Anzahl", () => {
    const h = html(<NetView n={NET} />)
    expect(h).toContain("net.tree_hint:{&quot;n&quot;:4}")
    expect(h).toContain("Switch")
    expect(h).toContain("net.clients_hidden:{&quot;n&quot;:1}")
    expect(h).not.toContain(">NAS<")
    expect(h).not.toContain(">Handy<")
  })
  it("Netze, WLAN ohne Passwort, Freigaben", () => {
    const h = html(<NetView n={NET} />)
    expect(h).toContain("net.dhcp:{&quot;start&quot;:&quot;10.0.0.6&quot;,&quot;stop&quot;:&quot;10.0.0.254&quot;}")
    expect(h).toContain("net.wan")
    expect(h).toContain("WPA2")
    expect(h).toContain("2g + 5g")
    expect(h).toContain("net.fwd:{&quot;port&quot;:&quot;32400&quot;")
    expect(h).toContain("net.rules:{&quot;n&quot;:0,&quot;r&quot;:0}")
    expect(h.toLowerCase()).not.toContain("passphrase")
  })
  it("Client-Knoten als Blatt", () => {
    expect(html(<TreeItem n={{ mac: "d", name: "Handy", kind: "client", model: null, link: "wireless", port: null, children: [] }} />)).toContain("cl.wireless")
  })
})

describe("Verkehr", () => {
  const T: Traffic = { clients: [{ ...CL, name: "Groß", down_bytes: 8e9, up_bytes: 2e9 }, { ...CL, mac: "x", name: "Klein", down_bytes: 1e9, up_bytes: 0 }],
    devices: [{ name: "Switch", kind: "switch", tx_bytes: 1, rx_bytes: 2, ports: [{ idx: 1, name: "Port 1", up: true, tx_bytes: 5e9, rx_bytes: 1 }, { idx: 2, name: "Port 2", up: false, tx_bytes: 0, rx_bytes: 0 }] }] }
  it("Balken relativ zum größten, freie Ports ausgeblendet", () => {
    const h = html(<TrafficView d={T} />)
    expect(h).toContain("width:100%")
    expect(h).toContain("width:10%")
    expect(h).toContain("Port 1: ↓ 5,0 GB")
    expect(h).not.toContain("Port 2:")
  })
  it("Anteil", () => {
    expect(share(5, 10)).toBe(50)
    expect(share(1, 0)).toBe(0)
    expect(share(1, 3)).toBe(33)
  })
  it("leer", () => {
    expect(html(<TrafficView d={{ clients: [], devices: [] }} />)).toContain("tr.none")
  })
})

describe("Texte 0.2.0", () => {
  const keys = (o: object, p = ""): string[] => Object.entries(o).flatMap(([k, v]) => (typeof v === "object" ? keys(v, `${p}${k}.`) : [`${p}${k}`]))
  it("de und en gleich", () => {
    expect(keys(networkI18n.en).sort()).toEqual(keys(networkI18n.de).sort())
    expect(keys(networkI18n.de)).toContain("network.tab.devices")
    expect(keys(networkI18n.de)).toContain("network.cl.via_wlan")
  })
})
