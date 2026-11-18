"""get_batch_quotes must request one symbol per call.

FMP's /stable/quote rejects comma-separated symbols on non-legacy keys
(HTTP 402 "Premium Query Parameter") and the /api/v3/quote/A,B,C batch
syntax returns 403 for keys created after 2025-08-31. Batching therefore
yields zero quotes, and the screener evaluates nothing. market-top-detector
already iterates one symbol at a time; vcp-screener must do the same.
"""

import os
import sys
from unittest.mock import MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from fmp_client import FMPClient


def _response(status_code, payload):
    resp = MagicMock()
    resp.status_code = status_code
    resp.json.return_value = payload
    resp.text = ""
    return resp


def test_batch_quotes_requests_one_symbol_per_call():
    client = FMPClient(api_key="test_key")  # pragma: allowlist secret
    requested = []

    def mock_get(url, params=None, timeout=None):
        symbol = (params or {}).get("symbol")
        requested.append(symbol)
        if symbol is None or "," in symbol:
            # Mirrors the live free-tier refusal of multi-symbol queries.
            return _response(402, {"Error Message": "Premium Query Parameter"})
        return _response(200, [{"symbol": symbol, "price": 100.0}])

    client.session.get = mock_get
    symbols = ["AAPL", "MSFT", "NVDA", "AMZN", "META", "GOOGL", "AVGO"]

    result = client.get_batch_quotes(symbols)

    assert set(result) == set(symbols)
    assert all(s is not None and "," not in s for s in requested)
    assert len(requested) == len(symbols)
