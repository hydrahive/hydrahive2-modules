"""Kleines incus im Speicher für die Tests (Netze, ACLs, Container, exec).

Anders als beim Labor gibt es bei Vibe MEHRERE Container an EINEM Netz. `containers[name]["network"]` merkt, an
welchem Netz ein Container hängt, damit „Netz erst weg, wenn kein Container mehr daran hängt“ prüfbar ist.
`exec_answers` legt fest, was ein Befehl im Container ausgibt: Schlüssel ist ein Teiltext des Befehls.
Standard für die Netzprobe: alle gesperrten Ziele „zu“, DNS geht.
"""
from __future__ import annotations


class FakeIncus:
    def __init__(self) -> None:
        self.calls: list[list[str]] = []
        self.networks: dict[str, dict] = {"hhnat0": {"ipv4.address": "10.10.0.1/24"}}
        self.acls: dict[str, dict] = {}
        self.containers: dict[str, dict] = {}
        self.fail: dict[str, str] = {}          # Teiltext eines Aufrufs → Fehlertext
        self.exec_answers: dict[str, tuple[int, str]] = {}
        self.open_targets: set[str] = set()     # „host:port“, die bei der Netzprobe erreichbar sind
        self.dns_ok = True
        self.pool = "default"

    async def run(self, *args: str, timeout: float = 60.0, input_bytes: bytes | None = None) -> tuple[int, str, str]:
        a = list(args)
        self.calls.append(a)
        line = " ".join(a)
        for key, err in self.fail.items():
            if key in line:
                return 1, "", err
        cmd = a[:2]
        if cmd == ["network", "create"]:
            if a[2] in self.networks:
                return 1, "", "already exists"
            self.networks[a[2]] = dict(kv.split("=", 1) for kv in a[3:] if "=" in kv)
            return 0, "", ""
        if cmd == ["network", "set"]:
            self.networks[a[2]].update(dict(kv.split("=", 1) for kv in a[3:] if "=" in kv))
            return 0, "", ""
        if cmd == ["network", "delete"]:
            self.networks.pop(a[2], None)
            return 0, "", ""
        if a[:3] == ["network", "acl", "list"] or cmd == ["network", "list"]:
            if "-c" in a:                       # incus 6.0: network (acl) list kennt keine Spaltenauswahl
                return 1, "", "Error: unknown shorthand flag: 'c' in -c"
            rows = self.acls if a[1] == "acl" else self.networks
            return 0, "".join(f"{n},bridge,YES,,,,0,CREATED\n" for n in rows), ""
        if a[:3] == ["network", "acl", "create"]:
            if a[3] in self.acls:
                return 1, "", "already exists"
            self.acls[a[3]] = {"egress": [], "ingress": []}
            return 0, "", ""
        if a[:4] == ["network", "acl", "rule", "add"]:
            self.acls[a[4]][a[5]].append(dict(kv.split("=", 1) for kv in a[6:]))
            return 0, "", ""
        if a[:4] == ["network", "acl", "rule", "remove"]:
            want = dict(kv.split("=", 1) for kv in a[6:])
            rules = self.acls[a[4]][a[5]]
            hit = [r for r in rules if all(r.get(k) == v for k, v in want.items())]
            if len(hit) != 1:
                return 1, "", "No matching rule(s) found"
            rules.remove(hit[0])
            return 0, "", ""
        if a[:3] == ["network", "acl", "show"]:
            import yaml
            return 0, yaml.safe_dump({"name": a[3], **self.acls[a[3]]}), ""
        if a[:3] == ["network", "acl", "delete"]:
            self.acls.pop(a[3], None)
            return 0, "", ""
        if a[:2] == ["network", "get"]:
            return 0, self.networks.get(a[2], {}).get(a[3], "") + "\n", ""
        if a[:2] == ["network", "show"]:
            return (0, "name: x\n", "") if a[2] in self.networks else (1, "", "not found")
        if a[0] == "launch":
            name = a[-1]
            if name in self.containers:
                return 1, "", "already exists"
            net = a[a.index("-n") + 1] if "-n" in a else ""
            self.containers[name] = {"args": a, "running": True, "network": net}
            return 0, "", ""
        if a[0] == "list":
            if a[-1] == "ns":
                return 0, "".join(f"{n},{'RUNNING' if c['running'] else 'STOPPED'}\n"
                                  for n, c in self.containers.items()), ""
            return 0, "\n".join(self.containers), ""
        if a[0] in ("start", "stop"):
            if a[1] in self.containers:
                self.containers[a[1]]["running"] = a[0] == "start"
            return 0, "", ""
        if a[0] == "delete":
            self.containers.pop(a[1], None)
            return 0, "", ""
        if a[:4] == ["profile", "device", "get", "default"]:
            return (0, self.pool + "\n", "") if self.pool else (1, "", "not found")
        if a[0] == "exec":
            body = " ".join(a[a.index("--") + 1:])
            for key, (rc, out) in self.exec_answers.items():
                if key in body:
                    return rc, out, ""
            if "hh-vibe-netprobe" in body:
                lines = []
                for t in body.split("PROBE_TARGETS=")[1].split()[0].split(","):  # Format aus backend.network.probe
                    lines.append(f"{t} {'offen' if t in self.open_targets else 'zu'}")
                lines.append("dns " + ("ok" if self.dns_ok else "fehler"))
                return 0, "\n".join(lines) + "\n", ""
            return 0, "", ""
        return 0, "", ""
