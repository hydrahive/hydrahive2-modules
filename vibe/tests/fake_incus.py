"""Kleines incus im Speicher für die Tests (Netze, ACLs, Container, exec).

Anders als beim Labor gibt es bei Vibe MEHRERE Container an EINEM Netz. `containers[name]["network"]` merkt, an
welchem Netz ein Container hängt, damit „Netz erst weg, wenn kein Container mehr daran hängt“ prüfbar ist.
`exec_answers` legt fest, was ein Befehl im Container ausgibt: Schlüssel ist ein Teiltext des Befehls.
Standard für die Netzprobe: alle gesperrten Ziele „zu“, DNS geht.
"""

from __future__ import annotations

import asyncio
import json

_ISOLATED_IDMAP = json.dumps(
    [
        {"Isuid": True, "Isgid": False, "Hostid": 1_065_536, "Nsid": 0, "Maprange": 65_536},
        {"Isuid": False, "Isgid": True, "Hostid": 1_065_536, "Nsid": 0, "Maprange": 65_536},
    ]
)
_IDMAP = json.dumps(
    [
        {
            "Isuid": True,
            "Isgid": False,
            "Hostid": 1_000_000,
            "Nsid": 0,
            "Maprange": 1_000_000_000,
        },
        {
            "Isuid": False,
            "Isgid": True,
            "Hostid": 1_000_000,
            "Nsid": 0,
            "Maprange": 1_000_000_000,
        },
    ]
)


class FakeIncus:
    def __init__(self) -> None:
        self.calls: list[list[str]] = []
        self.networks: dict[str, dict] = {"hhnat0": {"ipv4.address": "10.10.0.1/24"}}
        self.acls: dict[str, dict] = {}
        self.containers: dict[str, dict] = {}
        self.fail: dict[str, str] = {}  # Teiltext eines Aufrufs → Fehlertext
        self.exec_answers: dict[str, tuple[int, str]] = {}
        self.open_targets: set[str] = (
            set()
        )  # „host:port“, die bei der Netzprobe erreichbar sind
        self.dns_ok = True
        self.tar_count = 0                  # Anzahl Tar-Streams aus /work
        self.tar_files: dict[str, bytes] = {}  # Pfad im /work → Inhalt; leer = Standardinhalt, wenn Daten gemeldet
        self.tar_extra: list[tuple[str, str]] = []  # (Pfad, „fifo“|„link:ziel“) zusätzliche Einträge
        self.tar_break_second = False       # zweiter Tar-Stream weicht ab (Vergleich muss scheitern)
        self.stopped_dev: list[str] = []
        self.pull_delay = 0.02              # gibt anderen Aufgaben Gelegenheit dazwischenzufunken (Nebenläufigkeit)
        self.pool = "default"
        self.inputs: list[
            tuple[list[str], bytes]
        ] = []  # (Aufruf, stdin) – z. B. die Vorlage per tar

    async def run(
        self, *args: str, timeout: float = 60.0, input_bytes: bytes | None = None
    ) -> tuple[int, str, str]:
        a = list(args)
        self.calls.append(a)
        if input_bytes is not None:
            self.inputs.append((a, input_bytes))
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
            self.networks[a[2]].update(
                dict(kv.split("=", 1) for kv in a[3:] if "=" in kv)
            )
            return 0, "", ""
        if cmd == ["network", "delete"]:
            self.networks.pop(a[2], None)
            return 0, "", ""
        if a[:3] == ["network", "acl", "list"] or cmd == ["network", "list"]:
            if "-c" in a:  # incus 6.0: network (acl) list kennt keine Spaltenauswahl
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
            return (
                (0, "name: x\n", "") if a[2] in self.networks else (1, "", "not found")
            )
        if a[0] == "launch":
            name = a[-1]
            if name in self.containers:
                return 1, "", "already exists"
            net = a[a.index("-n") + 1] if "-n" in a else ""
            offset = 1_000_000 + len(self.containers) * 1_000_000
            idmap = json.dumps(
                [
                    {
                        "Isuid": True,
                        "Isgid": False,
                        "Hostid": offset,
                        "Nsid": 0,
                        "Maprange": 1_000_000,
                    },
                    {
                        "Isuid": False,
                        "Isgid": True,
                        "Hostid": offset,
                        "Nsid": 0,
                        "Maprange": 1_000_000,
                    },
                ]
            )
            self.containers[name] = {
                "args": a,
                "running": True,
                "network": net,
                "devices": {},
                "idmap": idmap,
            }
            return 0, "", ""
        if a[:2] == ["config", "get"]:
            if a[3] in ("volatile.idmap.current", "volatile.idmap.next"):
                box = self.containers.get(a[2], {})
                value = box.get("idmap", _IDMAP)
                if a[3] == "volatile.idmap.next":
                    value = box.get("idmap_next", value)   # echtes Incus: wirkt erst beim nächsten Start
                return 0, value + "\n", ""
            return 0, "", ""
        if a[:2] == ["config", "set"]:
            if a[3:5] == ["security.idmap.isolated", "true"] and a[2] in self.containers:
                self.containers[a[2]]["idmap_next"] = _ISOLATED_IDMAP
            return 0, "", ""
        if a[:3] == ["config", "device", "get"]:
            device = self.containers.get(a[3], {}).get("devices", {}).get(a[4])
            return (
                (0, device.get(a[5], "") + "\n", "") if device else (1, "", "not found")
            )
        if a[:3] == ["config", "device", "add"]:
            devices = self.containers[a[3]]["devices"]
            if a[4] in devices:
                return 1, "", "already exists"
            devices[a[4]] = {
                "type": a[5],
                **dict(part.split("=", 1) for part in a[6:] if "=" in part),
            }
            return 0, "", ""
        if a[:3] == ["config", "device", "remove"]:
            self.containers.get(a[3], {}).get("devices", {}).pop(a[4], None)
            return 0, "", ""
        if a[0] == "list":
            if a[-2:] == [
                "--format",
                "json",
            ]:  # Format wie incus 6.0.0 (hydratest 5.11.): expanded_devices.*.network
                return (
                    0,
                    json.dumps(
                        [
                            {
                                "name": n,
                                "status": "Running" if c["running"] else "Stopped",
                                "expanded_devices": {
                                    "eth0": {"type": "nic", "network": c["network"]}
                                }
                                if c["network"]
                                else {},
                            }
                            for n, c in self.containers.items()
                        ]
                    ),
                    "",
                )
            if a[-1] == "ns":
                return (
                    0,
                    "".join(
                        f"{n},{'RUNNING' if c['running'] else 'STOPPED'}\n"
                        for n, c in self.containers.items()
                    ),
                    "",
                )
            return 0, "\n".join(self.containers), ""
        if a[0] in ("start", "stop"):
            if a[1] in self.containers:
                self.containers[a[1]]["running"] = a[0] == "start"
                if a[0] == "start" and "idmap_next" in self.containers[a[1]]:
                    self.containers[a[1]]["idmap"] = self.containers[a[1]]["idmap_next"]
            return 0, "", ""
        if a[0] == "delete":
            self.containers.pop(a[1], None)
            return 0, "", ""
        if a[:4] == ["profile", "device", "get", "default"]:
            return (0, self.pool + "\n", "") if self.pool else (1, "", "not found")
        if a[0] == "exec":
            body = " ".join(a[a.index("--") + 1 :])
            if "! -type d ! -type l" in body and not any(
                "! -type d ! -type l" in k for k in self.exec_answers
            ):
                return 0, "", ""                              # Standard: keine Sonderdateien
            hits = [k for k in self.exec_answers if k in body]
            if hits:                                          # der genaueste (längste) Schlüssel gewinnt
                rc, out = self.exec_answers[max(hits, key=len)]
                return rc, out, ""
            if "hh-vibe-netprobe" in body:
                lines = []
                for t in (
                    body.split("PROBE_TARGETS=")[1].split()[0].split(",")
                ):  # Format aus backend.network.probe
                    lines.append(f"{t} {'offen' if t in self.open_targets else 'zu'}")
                lines.append("dns " + ("ok" if self.dns_ok else "fehler"))
                return 0, "\n".join(lines) + "\n", ""
            return 0, "", ""
        return 0, "", ""


    async def run_to_file(self, *args: str, out_path, timeout: float = 900.0, max_bytes: int = 0):
        """Ersatz für `incus.run_to_file`: schreibt `tar` von /work als echtes Archiv."""
        import io
        import tarfile

        self.calls.append(list(args))
        await asyncio.sleep(self.pull_delay)
        for key, err in self.fail.items():
            if key in " ".join(args):
                return 1, err
        self.tar_count += 1
        entries = dict(self.tar_files)
        if not entries and any(
            "find /work" in key and out.strip() for key, (_rc, out) in self.exec_answers.items()
        ):
            entries = {"src/App.tsx": b"app\n"}
        if self.tar_break_second and self.tar_count % 2 == 0:
            entries["abweichung.txt"] = b"anders"
        with tarfile.open(out_path, "w") as tar:
            for name, data in entries.items():
                info = tarfile.TarInfo(name)
                info.size = len(data)
                info.mode = 0o644
                tar.addfile(info, io.BytesIO(data))
            for name, kind in self.tar_extra:
                info = tarfile.TarInfo(name)
                if kind == "fifo":
                    info.type = tarfile.FIFOTYPE
                elif kind == "chr":
                    info.type = tarfile.CHRTYPE
                elif kind.startswith("link:"):
                    info.type, info.linkname = tarfile.SYMTYPE, kind[5:]
                elif kind.startswith("hard:"):
                    info.type, info.linkname = tarfile.LNKTYPE, kind[5:]
                tar.addfile(info)
        return 0, ""
