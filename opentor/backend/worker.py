from __future__ import annotations

import importlib
import json
import os
import sys
from pathlib import Path


def _load_modules():
    root_value = os.environ.get("HYDRAHIVE_OPENTOR_ROOT")
    if not root_value:
        raise RuntimeError("worker_root_missing")
    root = Path(root_value).resolve()
    scripts = root / "scripts"
    if not scripts.is_dir():
        raise RuntimeError("worker_root_invalid")
    for path in (str(root), str(scripts)):
        if path not in sys.path:
            sys.path.insert(0, path)
    return importlib.import_module("scripts.osint"), importlib.import_module("scripts.torcore")


def main() -> None:
    command = sys.argv[1] if len(sys.argv) == 2 else ""
    payload = json.loads(sys.stdin.read() or "{}")
    osint, torcore = _load_modules()
    if command == "status":
        result = torcore.check_tor()
        output = {
            "tor_reachable": bool(result.get("tor_active")),
            "worker_ready": True,
            "last_error": None if result.get("tor_active") else "tor_unreachable",
        }
    elif command == "search":
        output = osint.search_darkweb(
            payload["query"],
            engines=payload.get("engines") or None,
            max_results=int(payload["limit"]),
            mode=payload["mode"],
        )
    elif command == "fetch":
        output = torcore.fetch(payload["url"])
    else:
        raise RuntimeError("worker_command_invalid")
    print(json.dumps(output, ensure_ascii=False))


if __name__ == "__main__":
    main()
