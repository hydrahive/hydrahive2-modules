"""Netz: Aufbau als Baum (v2 topology), Netze, WLANs (ohne Passwort), Portfreigaben – nur ausgewählte Felder."""
from __future__ import annotations


def tree(topo: dict) -> list[dict]:
    verts = {v["mac"]: v for v in topo.get("vertices", []) if isinstance(v, dict) and v.get("mac")}
    kids: dict[str, list[tuple[str, str, int | None]]] = {}
    has_parent = set()
    for e in topo.get("edges", []):
        up, down = e.get("uplinkMac"), e.get("downlinkMac")
        # Mehrere Eltern oder Kreise: node() zeigt jeden Knoten nur einmal (seen), der erste Fund gewinnt.
        if up in verts and down in verts and up != down:
            kids.setdefault(up, []).append((down, (e.get("type") or "").lower(), e.get("uplinkPortNumber")))
            has_parent.add(down)
    seen: set[str] = set()

    def node(mac: str, link: str | None, port: int | None) -> dict:
        seen.add(mac)
        v = verts[mac]
        children = [node(m, ln, p) for m, ln, p in kids.get(mac, []) if m not in seen]
        children.sort(key=lambda c: (c["kind"] != "device", (c["name"] or "").lower()))
        return {"mac": mac, "name": v.get("name") or mac, "kind": "device" if v.get("type") == "DEVICE" else "client",
                "model": v.get("model"), "link": link, "port": port or None, "children": children}

    roots = [node(m, None, None) for m in verts if m not in has_parent and m not in seen]
    roots += [node(m, None, None) for m in verts if m not in seen]  # Reste aus Kreisen
    return sorted(roots, key=lambda r: (-_size(r), r["name"].lower()))


def _size(n: dict) -> int:
    return 1 + sum(_size(c) for c in n["children"])


def net(networkconf: dict, wlanconf: dict, portforward: dict, firewall: dict, routing: dict) -> dict:
    nets = [n for n in networkconf.get("data", []) if isinstance(n, dict)]
    names = {n.get("_id"): n.get("name") for n in nets}
    return {
        "networks": [{"name": n.get("name"), "purpose": n.get("purpose"),
                      "vlan": n.get("vlan") if n.get("vlan_enabled") else None, "subnet": n.get("ip_subnet"),
                      "dhcp": ({"on": bool(n.get("dhcpd_enabled")), "start": n.get("dhcpd_start"),
                                "stop": n.get("dhcpd_stop")} if n.get("purpose") != "wan" else None)}
                     for n in nets],
        "wlans": [{"name": w.get("name"), "enabled": bool(w.get("enabled")), "security": w.get("security"),
                   "wpa_mode": w.get("wpa_mode"), "bands": w.get("wlan_bands") or [], "guest": bool(w.get("is_guest")),
                   "hidden": bool(w.get("hide_ssid")), "network": names.get(w.get("networkconf_id"))}
                  for w in wlanconf.get("data", []) if isinstance(w, dict)],
        "forwards": [{"name": f.get("name"), "enabled": bool(f.get("enabled")), "proto": f.get("proto"),
                      "port": f.get("dst_port"), "to_ip": f.get("fwd"), "to_port": f.get("fwd_port")}
                     for f in portforward.get("data", []) if isinstance(f, dict)],
        "firewall_rules": len(firewall.get("data", [])), "routes": len(routing.get("data", [])),
    }
