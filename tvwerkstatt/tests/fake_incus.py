"""Kleines incus im Speicher für die Tests der TV-Werkstatt (Netze, Sperrlisten, Container, exec).

Muster vibe/tests/fake_incus.py, auf das gekürzt, was die TV-Werkstatt braucht. `fail` lässt einen Aufruf scheitern
(Schlüssel = Teiltext des Aufrufs). Die Netzprobe antwortet je Ziel mit „offen“, wenn es in `open_targets` steht.
"""
from __future__ import annotations

import json


def _kv(parts: list[str]) -> dict[str, str]:
    return dict(p.split("=", 1) for p in parts if "=" in p)


class FakeIncus:
    def __init__(self) -> None:
        self.calls: list[list[str]] = []
        self.networks: dict[str, dict] = {"hhnat0": {"ipv4.address": "10.10.0.1/24"}}
        self.acls: dict[str, dict] = {}
        self.containers: dict[str, dict] = {}
        self.fail: dict[str, str] = {}
        self.exec_answers: dict[str, tuple[int, str]] = {}
        self.open_targets: set[str] = set()
        self.dns_ok = True
        self.pool = "ssd"
        self.pushed: list[list[str]] = []
        self.exec_log: list[str] = []

    async def run(self, *args: str, timeout: float = 60.0, input_bytes: bytes | None = None) -> tuple[int, str, str]:
        a = list(args)
        self.calls.append(a)
        line = " ".join(a)
        for key, err in self.fail.items():
            if key in line:
                return 1, "", err
        if a[:2] == ["network", "acl"]:
            return self._acl(a)
        if a[0] == "network":
            return self._network(a)
        if a[0] == "launch":
            net = a[a.index("-n") + 1] if "-n" in a else ""
            if a[-1] in self.containers:
                return 1, "", "already exists"
            self.containers[a[-1]] = {"args": a, "running": True, "network": net}
            return 0, "", ""
        if a[0] in ("start", "stop"):
            if a[1] not in self.containers:
                return 1, "", "not found"
            self.containers[a[1]]["running"] = a[0] == "start"
            return 0, "", ""
        if a[0] == "delete":
            for name in [x for x in a[1:] if not x.startswith("-")]:
                self.containers.pop(name, None)
            return 0, "", ""
        if a[0] == "list":
            return 0, json.dumps([{"name": n, "status": "Running" if c["running"] else "Stopped",
                                   "expanded_devices": {"eth0": {"type": "nic", "network": c["network"]}}
                                   if c["network"] else {}} for n, c in self.containers.items()]), ""
        if a[0] == "exec":
            return self._exec(a)
        if a[:4] == ["profile", "device", "get", "default"]:
            return 0, self.pool + "\n", ""
        if a[:2] == ["file", "push"]:
            self.pushed.append(a)
            return 0, "", ""
        return 0, "", ""

    def _network(self, a: list[str]) -> tuple[int, str, str]:
        verb = a[1]
        if verb == "list":
            if "-c" in a:
                return 1, "", "Error: unknown shorthand flag: 'c' in -c"
            return 0, "".join(f"{n},bridge,YES,,,,0,CREATED\n" for n in self.networks), ""
        if verb == "create":
            if a[2] in self.networks:
                return 1, "", "already exists"
            self.networks[a[2]] = _kv(a[3:])
            return 0, "", ""
        if verb == "set":
            self.networks[a[2]].update(_kv(a[3:]))
            return 0, "", ""
        if verb == "get":
            return 0, self.networks.get(a[2], {}).get(a[3], "") + "\n", ""
        if verb == "delete":
            self.networks.pop(a[2], None)
            return 0, "", ""
        return 0, "", ""

    def _acl(self, a: list[str]) -> tuple[int, str, str]:
        verb = a[2]
        if verb == "list":
            if "-c" in a:
                return 1, "", "Error: unknown shorthand flag: 'c' in -c"
            return 0, "".join(f"{n},,1\n" for n in self.acls), ""
        if verb == "create":
            if a[3] in self.acls:
                return 1, "", "already exists"
            self.acls[a[3]] = {"egress": [], "ingress": []}
            return 0, "", ""
        if verb == "show":
            import yaml
            return 0, yaml.safe_dump({"name": a[3], **self.acls[a[3]]}), ""
        if verb == "rule" and a[3] == "add":
            self.acls[a[4]][a[5]].append(_kv(a[6:]))
            return 0, "", ""
        if verb == "rule" and a[3] == "remove":
            want = _kv(a[6:])
            rules = self.acls[a[4]][a[5]]
            hit = [r for r in rules if r == want]
            if len(hit) != 1:
                return 1, "", "No matching rule(s) found"
            rules.remove(hit[0])
            return 0, "", ""
        if verb == "delete":
            self.acls.pop(a[3], None)
            return 0, "", ""
        return 0, "", ""

    def _exec(self, a: list[str]) -> tuple[int, str, str]:
        body = " ".join(a[a.index("--") + 1:]) if "--" in a else ""
        if a[1] not in self.containers or not self.containers[a[1]]["running"]:
            return 1, "", "Error: Instance is not running"
        self.exec_log.append(body)
        hits = [k for k in self.exec_answers if k in body]
        if hits:
            rc, out = self.exec_answers[max(hits, key=len)]
            return rc, out, ""
        if "hh-tvw-netprobe" in body:
            targets = body.split("PROBE_TARGETS=")[1].split()[0].split(",")
            lines = [f"{t} {'offen' if t in self.open_targets else 'zu'}" for t in targets if t]
            lines.append("dns " + ("ok" if self.dns_ok else "fehler"))
            return 0, "\n".join(lines) + "\n", ""
        return 0, "", ""
