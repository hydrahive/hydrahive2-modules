"""Kleines GitHub im Speicher für die Tests: Device-Flow, Nutzer, Forks, PRs, Issues.

`request(method, url, *, token, data, json)` ist der einzige Weg nach außen (backend.github_api.request) und liefert
(status, json, headers). Aufrufe werden mitgeschrieben – Tests prüfen, dass der Token nur im Kopf steht.
"""
from __future__ import annotations

TOKEN = "gho_TESTtoken0123456789abcdefABCDEF0123"


class FakeGitHub:
    def __init__(self) -> None:
        self.calls: list[dict] = []
        self.login = "nutzer"
        self.user_id = 4242
        self.scopes = "public_repo"
        self.device_answers: list[dict] = [{"access_token": TOKEN, "token_type": "bearer", "scope": "public_repo"}]
        self.repos: dict[str, dict] = {"hydrahive/hydrahive2.0": {"fork": False},
                                       "hydrahive/hydrahive2-modules": {"fork": False}}
        self.pulls: list[dict] = []
        self.issues: list[dict] = []
        self.fail: dict[str, tuple[int, dict]] = {}
        self.rate_left = "4999"

    async def request(self, method: str, url: str, *, token: str = "", data: dict | None = None,
                      json: dict | None = None) -> tuple[int, dict, dict]:
        self.calls.append({"method": method, "url": url, "token": token, "data": data, "json": json})
        hdr = {"x-ratelimit-remaining": self.rate_left}
        for key, ans in self.fail.items():
            if key in f"{method} {url}":
                return ans[0], ans[1], hdr
        if url == "https://github.com/login/device/code":
            return 200, {"device_code": "DEV123", "user_code": "ABCD-1234",
                         "verification_uri": "https://github.com/login/device", "expires_in": 900, "interval": 5}, {}
        if url == "https://github.com/login/oauth/access_token":
            ans = self.device_answers.pop(0) if len(self.device_answers) > 1 else self.device_answers[0]
            return 200, ans, {}
        api = url.removeprefix("https://api.github.com")
        if api == "/user":
            if token != TOKEN:
                return 401, {"message": "Bad credentials"}, hdr
            return 200, {"login": self.login, "id": self.user_id}, {**hdr, "x-oauth-scopes": self.scopes}
        if method == "GET" and api.startswith("/repos/"):
            name = api.removeprefix("/repos/")
            if name in self.repos:
                r = self.repos[name]
                return 200, {"full_name": name, "fork": r["fork"],
                             "parent": {"full_name": r.get("parent", "")} if r.get("parent") is not None else None}, hdr
            if "/pulls/" in name:
                n = int(name.rsplit("/", 1)[1])
                pr = next((p for p in self.pulls if p["number"] == n), None)
                return (200, pr, hdr) if pr else (404, {"message": "Not Found"}, hdr)
            return 404, {"message": "Not Found"}, hdr
        if method == "POST" and api.endswith("/forks"):
            parent = api.removeprefix("/repos/").removesuffix("/forks")
            fork = f"{self.login}/{parent.split('/')[1]}"
            self.repos[fork] = {"fork": True, "parent": parent}
            return 202, {"full_name": fork}, hdr
        if method == "POST" and api.endswith("/pulls"):
            n = 100 + len(self.pulls)
            pr = {"number": n, "html_url": f"https://github.com/{api.split('/')[2]}/{api.split('/')[3]}/pull/{n}",
                  "state": "open", "merged": False, **(json or {})}
            self.pulls.append(pr)
            return 201, pr, hdr
        if method == "POST" and api.endswith("/labels"):
            return 200, {"items": []}, hdr
        if method == "POST" and api.endswith("/issues"):
            n = 500 + len(self.issues)
            iss = {"number": n, "html_url": f"https://github.com/x/y/issues/{n}", **(json or {})}
            self.issues.append(iss)
            return 201, iss, hdr
        return 404, {"message": "Not Found"}, hdr
