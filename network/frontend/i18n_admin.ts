// Texte der Reiter Geräte, Clients, Netz, Verkehr (0.2.0).
export const adminDe = {
  tab_devices: "Geräte", tab_clients: "Clients", tab_net: "Netz", tab_traffic: "Verkehr",
  stale: "Die Dream Machine antwortet gerade nicht – angezeigt wird der Stand von {{when}}.",
  refresh: "Neu laden",
  kind: { gateway: "Router", switch: "Switch", ap: "Access Point", other: "Gerät" },
  state: { online: "online", offline: "offline", pending: "wartet auf Übernahme", upgrading: "Update läuft", provisioning: "wird eingerichtet", heartbeat_missed: "meldet sich nicht", unknown: "unbekannt" },
  dev: {
    firmware: "Firmware {{v}}", update: "Update verfügbar: {{v}}", uptime: "Läuft seit {{d}}", clients: "{{n}} Clients",
    cpu: "CPU {{v}} %", mem: "Speicher {{v}} %", temp: "{{name}} {{v}} °C", traffic: "Verkehr: {{tx}} gesendet · {{rx}} empfangen",
    uplink: "Hängt an {{name}}{{port}}", uplink_port: ", Port {{n}}", ports: "Anschlüsse", radios: "Funk",
    port_down: "frei", port_uplink: "Uplink", poe: "PoE {{w}} W", errors: "{{n}} Fehler",
    band: "{{b}} GHz", channel: "Kanal {{c}}", power: "{{p}} dBm", util: "Auslastung {{u}} %", satisfaction: "Zufriedenheit {{s}} %",
    none: "Keine Geräte gefunden.", not_adopted: "Noch nicht übernommen",
  },
  cl: {
    search: "Name, Hersteller oder IP suchen …", all: "Alle", online: "Online", offline: "Offline", wired: "Kabel", wireless: "WLAN",
    counts: "{{online}} online · {{wireless}} im WLAN · {{total}} bekannt", none: "Keine Clients gefunden.",
    via_wlan: "WLAN {{band}} GHz an {{ap}}", via_wire: "Kabel an {{dev}}{{port}}", port: ", Port {{n}}",
    signal: "Signal {{s}} dBm", last_seen: "Zuletzt gesehen {{when}}", guest: "Gast", fixed_ip: "feste IP",
    down: "↓ {{v}}", up: "↑ {{v}}", unknown_uplink: "unbekannt",
  },
  sig: { good: "gut", ok: "ok", weak: "schwach", bad: "schlecht" },
  net: {
    tree: "Aufbau", tree_hint: "{{n}} Geräte und Clients", clients_hidden: "{{n}} Clients", show: "anzeigen", hide: "ausblenden",
    networks: "Netze", wlans: "WLANs", forwards: "Portfreigaben", rules: "Firewall-Regeln: {{n}} · Routen: {{r}}",
    wan: "Internet", lan: "Heimnetz", vlan: "VLAN {{v}}", dhcp: "DHCP {{start}} – {{stop}}", dhcp_off: "DHCP aus",
    wlan_on: "an", wlan_off: "aus", hidden: "versteckt", guest: "Gästenetz", security: "{{s}}",
    fwd: "{{port}} ({{proto}}) → {{ip}}:{{to}}", fwd_off: "aus", none: "Keine.",
  },
  tr: { clients: "Clients mit dem meisten Verkehr (seit Verbindung)", devices: "Verkehr je Gerät und Anschluss", none: "Noch keine Daten." },
}

export const adminEn: typeof adminDe = {
  tab_devices: "Devices", tab_clients: "Clients", tab_net: "Network", tab_traffic: "Traffic",
  stale: "The Dream Machine is not responding right now – showing the state from {{when}}.",
  refresh: "Reload",
  kind: { gateway: "Router", switch: "Switch", ap: "Access point", other: "Device" },
  state: { online: "online", offline: "offline", pending: "waiting for adoption", upgrading: "updating", provisioning: "provisioning", heartbeat_missed: "not reporting", unknown: "unknown" },
  dev: {
    firmware: "Firmware {{v}}", update: "Update available: {{v}}", uptime: "Up for {{d}}", clients: "{{n}} clients",
    cpu: "CPU {{v}} %", mem: "Memory {{v}} %", temp: "{{name}} {{v}} °C", traffic: "Traffic: {{tx}} sent · {{rx}} received",
    uplink: "Connected to {{name}}{{port}}", uplink_port: ", port {{n}}", ports: "Ports", radios: "Radios",
    port_down: "free", port_uplink: "Uplink", poe: "PoE {{w}} W", errors: "{{n}} errors",
    band: "{{b}} GHz", channel: "Channel {{c}}", power: "{{p}} dBm", util: "Utilization {{u}} %", satisfaction: "Satisfaction {{s}} %",
    none: "No devices found.", not_adopted: "Not adopted yet",
  },
  cl: {
    search: "Search name, vendor or IP …", all: "All", online: "Online", offline: "Offline", wired: "Wired", wireless: "Wi-Fi",
    counts: "{{online}} online · {{wireless}} on Wi-Fi · {{total}} known", none: "No clients found.",
    via_wlan: "Wi-Fi {{band}} GHz on {{ap}}", via_wire: "Wired to {{dev}}{{port}}", port: ", port {{n}}",
    signal: "Signal {{s}} dBm", last_seen: "Last seen {{when}}", guest: "Guest", fixed_ip: "fixed IP",
    down: "↓ {{v}}", up: "↑ {{v}}", unknown_uplink: "unknown",
  },
  sig: { good: "good", ok: "ok", weak: "weak", bad: "poor" },
  net: {
    tree: "Layout", tree_hint: "{{n}} devices and clients", clients_hidden: "{{n}} clients", show: "show", hide: "hide",
    networks: "Networks", wlans: "Wi-Fi networks", forwards: "Port forwards", rules: "Firewall rules: {{n}} · Routes: {{r}}",
    wan: "Internet", lan: "Home network", vlan: "VLAN {{v}}", dhcp: "DHCP {{start}} – {{stop}}", dhcp_off: "DHCP off",
    wlan_on: "on", wlan_off: "off", hidden: "hidden", guest: "Guest network", security: "{{s}}",
    fwd: "{{port}} ({{proto}}) → {{ip}}:{{to}}", fwd_off: "off", none: "None.",
  },
  tr: { clients: "Clients with the most traffic (since connecting)", devices: "Traffic per device and port", none: "No data yet." },
}
