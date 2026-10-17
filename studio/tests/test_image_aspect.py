"""Studio: Bildformat, das das Modell nicht kann → einmal mit dem nächsten erlaubten Format neu (gemessen 17.10.:
openai/gpt-5-image lehnt 16:9 ab und nennt „Accepted: 1:1, 3:2, 2:3, auto“)."""
from __future__ import annotations

import base64

import httpx
import pytest

PNG = base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==")
REJECT = ('{"error":{"message":"No provider for openai/gpt-5-image supports the requested parameter(s): aspect_ratio '
          '\\"16:9\\". Provider rejections: OpenAI: aspect_ratio: not supported. Accepted: 1:1, 3:2, 2:3, auto","code":400}}')


class Resp:
    def __init__(self, status: int, text: str):
        self.status_code, self.text = status, text

    def json(self):
        import json
        return json.loads(self.text)


@pytest.fixture
def calls(monkeypatch):
    sent: list[dict] = []
    monkeypatch.setattr("hydrahive.llm._config.openrouter_key", lambda: "k")
    return sent


def _post(sent, answers):
    def post(url, json=None, headers=None, timeout=None):
        sent.append(json)
        return answers.pop(0)
    return post


def test_nearest_accepted_format_is_retried_once(calls, monkeypatch) -> None:
    from backend import image_provider
    ok = Resp(200, '{"data":[{"b64_json":"%s"}]}' % base64.b64encode(PNG).decode())
    monkeypatch.setattr(httpx, "post", _post(calls, [Resp(400, REJECT), ok]))
    raw = image_provider.request_image(model="openai/gpt-5-image", prompt="p", references=[], aspect_ratio="16:9")
    assert raw == PNG
    assert [c["aspect_ratio"] for c in calls] == ["16:9", "3:2"]               # 3:2 liegt 16:9 am nächsten


@pytest.mark.parametrize(("wanted", "accepted", "expected"), [
    ("9:16", "1:1, 3:2, 2:3, auto", "2:3"),
    ("1:1", "16:9, 1:1", None),                                                   # war schon erlaubt → kein Neuversuch
    ("21:9", "1:1, 4:3", "4:3"),
    ("4:3", "auto", "auto"),                                                      # nur „auto“ → auto
])
def test_choice_of_format(wanted, accepted, expected) -> None:
    from backend import image_provider
    assert image_provider.nearest_aspect(wanted, accepted) == expected


def test_other_rejections_are_not_retried(calls, monkeypatch) -> None:
    from backend import image_provider
    monkeypatch.setattr(httpx, "post", _post(calls, [Resp(400, '{"error":{"message":"content policy","code":400}}')]))
    with pytest.raises(image_provider.ProviderError) as e:
        image_provider.request_image(model="m", prompt="p", references=[], aspect_ratio="16:9")
    assert str(e.value) == "provider_rejected" and len(calls) == 1


def test_second_rejection_stops(calls, monkeypatch) -> None:
    from backend import image_provider
    monkeypatch.setattr(httpx, "post", _post(calls, [Resp(400, REJECT), Resp(400, REJECT)]))
    with pytest.raises(image_provider.ProviderError):
        image_provider.request_image(model="m", prompt="p", references=[], aspect_ratio="16:9")
    assert len(calls) == 2                                                        # genau ein Neuversuch, keine Schleife
