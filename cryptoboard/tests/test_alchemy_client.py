"""alchemy_client — Methoden-Allowlist, Kill-Switch, Paging, Grenzen (kein echter Netzaufruf)."""
from __future__ import annotations

import pytest

from backend import alchemy_client as ac


def test_allowlist_erlaubt_nur_lesende_methoden():
    assert "alchemy_getAssetTransfers" in ac.ALLOWED_METHODS
    assert "eth_getTransactionReceipt" in ac.ALLOWED_METHODS
    assert "eth_blockNumber" in ac.ALLOWED_METHODS
    assert "eth_getTransactionByHash" in ac.ALLOWED_METHODS


@pytest.mark.parametrize("method", [
    "eth_sendRawTransaction", "eth_sendTransaction", "personal_sign", "eth_sign",
])
@pytest.mark.asyncio
async def test_schreibende_methoden_werden_abgelehnt(method, monkeypatch):
    async def boom(*a, **kw):
        raise AssertionError("darf nie das Netz erreichen")
    monkeypatch.setattr(ac, "_rpc", boom)
    with pytest.raises(ac.MethodNotAllowed):
        await ac.call("base", "fake-key", method, [])


@pytest.mark.asyncio
async def test_kill_switch_blockiert_vor_dem_netz(monkeypatch):
    async def boom(*a, **kw):
        raise AssertionError("darf nie das Netz erreichen")
    monkeypatch.setattr(ac, "_rpc", boom)
    monkeypatch.setenv("HH_CRYPTOBOARD_ONCHAIN_ENABLED", "0")
    with pytest.raises(ac.AlchemyDisabled):
        await ac.call("base", "fake-key", "eth_blockNumber", [])


@pytest.mark.parametrize("value", ["false", "no", "off", "0"])
def test_kill_switch_werte(monkeypatch, value):
    monkeypatch.setenv("HH_CRYPTOBOARD_ONCHAIN_ENABLED", value)
    assert ac.enabled() is False


def test_kill_switch_default_an(monkeypatch):
    monkeypatch.delenv("HH_CRYPTOBOARD_ONCHAIN_ENABLED", raising=False)
    assert ac.enabled() is True


@pytest.mark.asyncio
async def test_erlaubte_methode_geht_durch(monkeypatch):
    calls = []

    async def fake_rpc(url, method, params):
        calls.append((url, method, params))
        return "0x10"
    monkeypatch.setattr(ac, "_rpc", fake_rpc)
    result = await ac.call("base", "fake-key", "eth_blockNumber", [])
    assert result == "0x10"
    assert calls[0][1] == "eth_blockNumber"
    assert "fake-key" in calls[0][0]  # Key steckt im URL-Pfad — bleibt in dieser Schicht, nie im Fehlertext


def test_chain_url_unbekannte_chain():
    with pytest.raises(ac.ChainNotSupported):
        ac.chain_url("solana", "x")


def test_chain_url_bekannte_chains():
    assert ac.chain_url("base", "k").endswith("/v2/k")
    assert "base-mainnet.g.alchemy.com" in ac.chain_url("base", "k")
    assert "eth-mainnet.g.alchemy.com" in ac.chain_url("ethereum", "k")


# ---------------------------------------------------------------- fetch_transfers: Paging


def _transfer(hash_, ts, block="0x1"):
    return {"hash": hash_, "blockNum": block, "metadata": {"blockTimestamp": ts},
            "rawContract": {"value": "0x1", "decimal": "0x12"}, "from": "0xaa", "to": "0xbb"}


@pytest.mark.asyncio
async def test_fetch_transfers_folgt_pagekey(monkeypatch):
    pages = {
        None: {"transfers": [_transfer("0x1", "2026-01-01T00:00:00Z")], "pageKey": "p2"},
        "p2": {"transfers": [_transfer("0x2", "2026-01-02T00:00:00Z")], "pageKey": None},
    }

    async def fake_call(chain, key, method, params):
        page_key = params[0].get("pageKey")
        return pages[page_key]
    monkeypatch.setattr(ac, "call", fake_call)
    out = await ac.fetch_transfers("base", "fake-key", "0xaa")
    hashes = {t["hash"] for t in out["transfers"]}
    assert hashes == {"0x1", "0x2"}
    assert out["truncated"] is False


@pytest.mark.asyncio
async def test_fetch_transfers_grenze_1000_transaktionen(monkeypatch):
    # 3 Transfers, Grenze 2 → der dritte triggert truncated
    txs = [_transfer(f"0x{i}", "2026-01-01T00:00:00Z", block=f"0x{i}") for i in range(3)]

    async def fake_call(chain, key, method, params):
        return {"transfers": txs, "pageKey": None}
    monkeypatch.setattr(ac, "call", fake_call)
    out = await ac.fetch_transfers("base", "fake-key", "0xaa", max_transactions=2)
    assert out["truncated"] is True
    assert out["before_block"] is not None
    assert len({t["hash"] for t in out["transfers"]}) <= 2


@pytest.mark.asyncio
async def test_fetch_transfers_grenze_2_jahre(monkeypatch):
    # Unterschiedliche Blöcke (ein Block hat genau einen Zeitstempel) -- K3: die
    # Grenze wird an der Blockgrenze gezogen, nicht mitten im Block.
    alt = _transfer("0xold", "2020-01-01T00:00:00Z", block="0x1")  # älter als 2 Jahre
    neu = _transfer("0xneu", "2026-11-01T00:00:00Z", block="0x2")

    async def fake_call(chain, key, method, params):
        return {"transfers": [neu, alt], "pageKey": None}
    monkeypatch.setattr(ac, "call", fake_call)
    out = await ac.fetch_transfers("base", "fake-key", "0xaa", max_age_years=2)
    hashes = {t["hash"] for t in out["transfers"]}
    assert "0xneu" in hashes
    assert "0xold" not in hashes
    assert out["truncated"] is True


@pytest.mark.asyncio
async def test_fetch_transfers_disabled(monkeypatch):
    monkeypatch.setenv("HH_CRYPTOBOARD_ONCHAIN_ENABLED", "0")
    with pytest.raises(ac.AlchemyDisabled):
        await ac.fetch_transfers("base", "fake-key", "0xaa")


# ---------------------------------------------------------------- Fehlerklassen: kein Key im Text


@pytest.mark.asyncio
async def test_http_fehler_enthaelt_nie_die_url(monkeypatch):
    import httpx

    class FakeResponse:
        status_code = 401
        text = "Unauthorized"

        def raise_for_status(self):
            raise httpx.HTTPStatusError("boom", request=None, response=self)

    class FakeClient:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *a):
            return False

        async def post(self, url, json):
            return FakeResponse()

    monkeypatch.setattr(ac.httpx, "AsyncClient", lambda timeout: FakeClient())
    with pytest.raises(ac.AlchemyHttpError) as exc_info:
        await ac._rpc("https://base-mainnet.g.alchemy.com/v2/geheimer-key-123", "eth_blockNumber", [])
    assert "geheimer-key-123" not in str(exc_info.value)
    assert exc_info.value.status_code == 401
    assert "geheimer-key-123" not in exc_info.value.body


# ---------------------------------------------------------------- K3: beide Richtungen, Blockgrenze


def _transfer_dir(hash_, ts, block, from_, to_):
    return {"hash": hash_, "blockNum": block, "metadata": {"blockTimestamp": ts},
            "rawContract": {"value": "0x1", "decimal": "0x12"}, "from": from_, "to": to_}


@pytest.mark.asyncio
async def test_k3_swap_am_rand_beide_richtungen_vollstaendig(monkeypatch):
    """Ein Swap liegt GENAU an der Grenze: die Adresse sendet in Block N (fromAddress-Treffer)
    UND empfängt im selben Block N (toAddress-Treffer). Der alte Bug holte erst fromAddress
    komplett, brach dann an der Grenze ab und toAddress wurde NIE abgefragt -> der
    Swap erschien als "nur raus". Mit dem Fix müssen BEIDE Transfers im Ergebnis sein."""
    out_tx = _transfer_dir("0xswap", "2026-06-01T00:00:00Z", "0x64", "0xaa", "0xpool")
    in_tx = _transfer_dir("0xswap", "2026-06-01T00:00:00Z", "0x64", "0xpool", "0xaa")

    async def fake_call(chain, key, method, params):
        direction = "fromAddress" if "fromAddress" in params[0] else "toAddress"
        if direction == "fromAddress":
            return {"transfers": [out_tx], "pageKey": None}
        return {"transfers": [in_tx], "pageKey": None}
    monkeypatch.setattr(ac, "call", fake_call)
    out = await ac.fetch_transfers("base", "fake-key", "0xaa")
    hashes_with_dir = [(t["hash"], t["from"], t["to"]) for t in out["transfers"]]
    assert ("0xswap", "0xaa", "0xpool") in hashes_with_dir
    assert ("0xswap", "0xpool", "0xaa") in hashes_with_dir
    assert out["truncated"] is False


@pytest.mark.asyncio
async def test_k3_grenze_schneidet_an_blockgrenze_nicht_mitten_im_block(monkeypatch):
    """3 verschiedene Bloecke mit je einem Transfer, Grenze 2 eindeutige Hashes -- der
    aelteste Block (der die Grenze ueberschreitet) wird KOMPLETT verworfen, nicht nur
    teilweise. before_block zeigt auf genau diesen Block."""
    tx_a = _transfer_dir("0xa", "2026-06-03T00:00:00Z", "0x3", "0xaa", "0xpool")
    tx_b = _transfer_dir("0xb", "2026-06-02T00:00:00Z", "0x2", "0xaa", "0xpool")
    tx_c = _transfer_dir("0xc", "2026-06-01T00:00:00Z", "0x1", "0xaa", "0xpool")

    async def fake_call(chain, key, method, params):
        direction = "fromAddress" if "fromAddress" in params[0] else "toAddress"
        if direction == "fromAddress":
            return {"transfers": [tx_a, tx_b, tx_c], "pageKey": None}
        return {"transfers": [], "pageKey": None}
    monkeypatch.setattr(ac, "call", fake_call)
    out = await ac.fetch_transfers("base", "fake-key", "0xaa", max_transactions=2)
    hashes = {t["hash"] for t in out["transfers"]}
    assert hashes == {"0xa", "0xb"}
    assert out["truncated"] is True
    assert out["before_block"] == "0x1"


@pytest.mark.asyncio
async def test_k3_folgelauf_ohne_luecke_und_ohne_dopplung(monkeypatch):
    """Ein Folgelauf mit to_block=before_block (inklusiv) muss GENAU den abgeschnittenen
    Block vollstaendig nachholen -- Dopplungen fuer bereits gelieferte Bloecke sind
    unschaedlich (Dedup via existing_hashes faengt das in Teil B), aber keine LUECKE."""
    tx_a = _transfer_dir("0xa", "2026-06-03T00:00:00Z", "0x3", "0xaa", "0xpool")
    tx_c = _transfer_dir("0xc", "2026-06-01T00:00:00Z", "0x1", "0xaa", "0xpool")

    async def fake_call_run1(chain, key, method, params):
        direction = "fromAddress" if "fromAddress" in params[0] else "toAddress"
        if direction == "fromAddress":
            return {"transfers": [tx_a, tx_c], "pageKey": None}
        return {"transfers": [], "pageKey": None}
    monkeypatch.setattr(ac, "call", fake_call_run1)
    run1 = await ac.fetch_transfers("base", "fake-key", "0xaa", max_transactions=1)
    assert {t["hash"] for t in run1["transfers"]} == {"0xa"}
    assert run1["truncated"] is True
    assert run1["before_block"] == "0x1"

    async def fake_call_run2(chain, key, method, params):
        assert params[0]["toBlock"] == "0x1"  # inklusiv: Folgelauf fragt genau diesen Block ab
        direction = "fromAddress" if "fromAddress" in params[0] else "toAddress"
        if direction == "fromAddress":
            return {"transfers": [tx_c], "pageKey": None}
        return {"transfers": [], "pageKey": None}
    monkeypatch.setattr(ac, "call", fake_call_run2)
    run2 = await ac.fetch_transfers("base", "fake-key", "0xaa", to_block=run1["before_block"])
    assert {t["hash"] for t in run2["transfers"]} == {"0xc"}


@pytest.mark.asyncio
async def test_k3_block_mit_mehreren_transfers_bleibt_vollstaendig_oder_wird_komplett_verworfen(monkeypatch):
    """Block 0x2 enthaelt ZWEI Transfers (Swap: raus+rein im selben Block). Grenze 2 eindeutige
    Hashes wird durch Block 0x3 (1 Hash) + Block 0x2 (1 weiterer Hash) erreicht -- Block 0x2
    darf NICHT nur zur Haelfte (einer von zwei Transfers) uebernommen werden, sonst erscheint
    der Swap in Block 0x2 faelschlich als "nur eine Richtung"."""
    tx_newest = _transfer_dir("0xnewest", "2026-06-03T00:00:00Z", "0x3", "0xaa", "0xpool")
    swap_out = _transfer_dir("0xswap2", "2026-06-02T00:00:00Z", "0x2", "0xaa", "0xpool")
    swap_in = _transfer_dir("0xswap2", "2026-06-02T00:00:00Z", "0x2", "0xpool", "0xaa")
    older = _transfer_dir("0xolder", "2026-06-01T00:00:00Z", "0x1", "0xaa", "0xpool")

    async def fake_call(chain, key, method, params):
        direction = "fromAddress" if "fromAddress" in params[0] else "toAddress"
        if direction == "fromAddress":
            return {"transfers": [tx_newest, swap_out, older], "pageKey": None}
        return {"transfers": [swap_in], "pageKey": None}
    monkeypatch.setattr(ac, "call", fake_call)
    # Grenze 2 eindeutige Hashes: 0xnewest + 0xswap2 passen, 0xolder nicht mehr.
    out = await ac.fetch_transfers("base", "fake-key", "0xaa", max_transactions=2)
    block2_items = [t for t in out["transfers"] if t["hash"] == "0xswap2"]
    # Entweder beide Transfers von Block 0x2 sind da, oder keiner -- nie nur einer.
    assert len(block2_items) in (0, 2)
    assert len(block2_items) == 2  # Block 0x2 passt noch vollständig in die Grenze
    assert "0xolder" not in {t["hash"] for t in out["transfers"]}


@pytest.mark.asyncio
async def test_k3_block_mit_zwei_verschiedenen_hashes_alles_oder_nichts(monkeypatch):
    """Block 0x2 enthaelt ZWEI VERSCHIEDENE Tx-Hashes (keine Swap-Paarung, zwei unabhaengige
    Transaktionen). Grenze erreicht genau in diesem Block -- der GANZE Block wird verworfen
    (block-atomar), nicht nur eine der beiden Transaktionen (das waere eine inkonsistente,
    von der Reihenfolge abhaengige Teil-Auswahl innerhalb eines Blocks)."""
    newest = _transfer_dir("0xnewest", "2026-06-03T00:00:00Z", "0x3", "0xaa", "0xpool")
    block2_tx1 = _transfer_dir("0xb2a", "2026-06-02T00:00:00Z", "0x2", "0xaa", "0xpool")
    block2_tx2 = _transfer_dir("0xb2b", "2026-06-02T00:00:00Z", "0x2", "0xaa", "0xpool2")

    async def fake_call(chain, key, method, params):
        direction = "fromAddress" if "fromAddress" in params[0] else "toAddress"
        if direction == "fromAddress":
            return {"transfers": [newest, block2_tx1, block2_tx2], "pageKey": None}
        return {"transfers": [], "pageKey": None}
    monkeypatch.setattr(ac, "call", fake_call)
    # Grenze 2: newest (1) + einer der beiden Block-0x2-Hashes würde exakt 2 ergeben --
    # trotzdem muss der GESAMTE Block 0x2 verworfen werden (sonst inkonsistente Teilauswahl).
    out = await ac.fetch_transfers("base", "fake-key", "0xaa", max_transactions=2)
    hashes = {t["hash"] for t in out["transfers"]}
    assert hashes == {"0xnewest"}
    assert out["truncated"] is True
    assert out["before_block"] == "0x2"
