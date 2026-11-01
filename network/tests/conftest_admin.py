"""Hilfen für die Tests von 0.2.0: falsche Dream Machine, die echte (anonymisierte) Antworten liefert."""
from __future__ import annotations

import json
from pathlib import Path

FIX = json.loads((Path(__file__).resolve().parent / "fixtures" / "udm_admin.json").read_text())
S = "/proxy/network/api/s/default"
ANSWERS = {
    f"{S}/stat/device": FIX["device"], f"{S}/stat/sta": FIX["sta"], f"{S}/rest/user": FIX["user"],
    f"{S}/rest/networkconf": FIX["networkconf"], f"{S}/rest/wlanconf": FIX["wlanconf"],
    f"{S}/rest/portforward": FIX["portforward"], f"{S}/rest/firewallrule": {"meta": {"rc": "ok"}, "data": []},
    f"{S}/rest/routing": {"meta": {"rc": "ok"}, "data": []},
    "/proxy/network/v2/api/site/default/topology": FIX["topology"],
}
