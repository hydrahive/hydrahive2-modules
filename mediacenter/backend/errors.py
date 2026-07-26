from __future__ import annotations


class MediacenterError(RuntimeError):
    """Stabiler Modulfehler ohne rohe Upstream- oder Credential-Details."""

    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


class MediacenterConfigError(MediacenterError):
    pass


class IndexerUnavailable(MediacenterError):
    pass


class IndexerAuthError(MediacenterError):
    pass


class IndexerResponseError(MediacenterError):
    pass
