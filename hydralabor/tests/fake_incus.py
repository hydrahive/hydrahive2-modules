"""Kleines incus im Speicher für die Tests (Netze, ACLs, Container, Schnappschüsse, exec).

`exec_answers` legt fest, was ein Befehl im Container ausgibt: Schlüssel ist ein Teiltext des Befehls.
Standard für die Netzprobe: alle gesperrten Ziele „zu“, github.com auflösbar.
"""
from __future__ import annotations


class FakeIncus:
    def __init__(self) -> None:
        self.calls: list[list[str]] = []
        self.networks: dict[str, dict] = {"hhnat0": {"ipv4.address": "10.10.0.1/24"}}
        self.acls: dict[str, dict] = {}
        self.containers: dict[str, dict] = {}
        self.snapshots: dict[str, set[str]] = {}
        self.fail: dict[str, str] = {}          # Teiltext eines Aufrufs → Fehlertext
        self.exec_answers: dict[str, tuple[int, str]] = {}
        self.open_targets: set[str] = set()     # „host:port“, die bei der Netzprobe erreichbar sind
        self.dns_ok = True

    async def run(self, *args: str, timeout: float = 60.0, input_bytes: bytes | None = None) -> tuple[int, str, str]:
        a = list(args)
        self.calls.append(a)
        line = " ".join(a)
        for key, err in self.fail.items():
            if key in line:
                return 1, "", err
        cmd = a[:2]
        if cmd == ["network", "create"]:
            name = a[2]
            if name in self.networks:
                return 1, "", "already exists"
            self.networks[name] = dict(kv.split("=", 1) for kv in a[3:] if "=" in kv)
            return 0, "", ""
        if cmd == ["network", "set"]:
            self.networks[a[2]].update(dict(kv.split("=", 1) for kv in a[3:] if "=" in kv))
            return 0, "", ""
        if cmd == ["network", "delete"]:
            self.networks.pop(a[2], None)
            return 0, "", ""
        if a[:3] == ["network", "acl", "list"]:
            return 0, "\n".join(self.acls), ""
        if cmd == ["network", "list"]:
            return 0, "\n".join(self.networks), ""
        if a[:3] == ["network", "acl", "create"]:
            if a[3] in self.acls:
                return 1, "", "already exists"
            self.acls[a[3]] = {"egress": [], "ingress": []}
            return 0, "", ""
        if a[:4] == ["network", "acl", "rule", "add"]:
            direction = a[5]
            self.acls[a[4]][direction].append(dict(kv.split("=", 1) for kv in a[6:]))
            return 0, "", ""
        if a[:3] == ["network", "acl", "delete"]:
            self.acls.pop(a[3], None)
            return 0, "", ""
        if a[:3] == ["network", "acl", "list"]:
            return 0, "\n".join(self.acls), ""
        if cmd == ["launch"] or a[0] == "launch":
            name = a[-1]
            self.containers[name] = {"args": a, "running": True}
            return 0, "", ""
        if a[0] == "list":
            return 0, "\n".join(f"{n},{'RUNNING' if c['running'] else 'STOPPED'}" for n, c in self.containers.items()), ""
        if a[0] in ("start", "stop"):
            if a[1] in self.containers:
                self.containers[a[1]]["running"] = a[0] == "start"
            return 0, "", ""
        if a[0] == "delete":
            self.containers.pop(a[1], None)
            self.snapshots.pop(a[1], None)
            return 0, "", ""
        if a[:2] == ["snapshot", "create"]:
            self.snapshots.setdefault(a[2], set()).add(a[3])
            return 0, "", ""
        if a[:2] == ["snapshot", "restore"]:
            if a[3] not in self.snapshots.get(a[2], set()):
                return 1, "", "not found"
            return 0, "", ""
        if a[0] == "exec":
            body = " ".join(a[a.index("--") + 1:])
            for key, (rc, out) in self.exec_answers.items():
                if key in body:
                    return rc, out, ""
            if "hh-labor-netprobe" in body:
                lines = []
                for t in body.split("PROBE_TARGETS=")[1].split()[0].split(","):  # Format aus backend.network.probe
                    lines.append(f"{t} {'offen' if t in self.open_targets else 'zu'}")
                lines.append("dns " + ("ok" if self.dns_ok else "fehler"))
                return 0, "\n".join(lines) + "\n", ""
            return 0, "", ""
        if a[0] == "config":
            return 0, "", ""
        return 0, "", ""
