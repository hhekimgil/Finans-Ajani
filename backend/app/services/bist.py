"""BIST hisse verileri — ham Yahoo Finance v8 chart API uzerinden.

yfinance 1.6.0 Yahoo'nun yeni API yapisiyla uyumsuz (veri donmuyor);
bu modul dogrudan query1.finance.yahoo.com/v8/finance/chart kullanir.
"""

import json
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import httpx

logger = logging.getLogger(__name__)

BIST100_FILE = Path(__file__).resolve().parent.parent.parent / "data" / "bist100.json"

YAHOO_CHART = "https://query1.finance.yahoo.com/v8/finance/chart/{ticker}"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0 Safari/537.36",
    "Accept": "application/json",
}

# Yahoo period degerleri
_PERIOD_MAP = {
    "1d": "1d",
    "5d": "5d",
    "1mo": "1mo",
    "3mo": "3mo",
    "6mo": "6mo",
    "1y": "1y",
    "2y": "2y",
}


def load_bist100_tickers() -> list[str]:
    """BIST 100 aday sembol listesini data/bist100.json'dan okur."""
    try:
        if not BIST100_FILE.exists():
            return []
        data = json.loads(BIST100_FILE.read_text(encoding="utf-8"))
        return data.get("tickers", [])
    except Exception as e:  # noqa: BLE001
        logger.warning("bist100.json okuma hatasi: %s", e)
        return []


def _fetch_chart(ticker: str, period: str = "5d", interval: str = "1d") -> Optional[dict]:
    """Yahoo v8 chart API'sinden ham yanit doner."""
    url = YAHOO_CHART.format(ticker=ticker)
    params = {"range": _PERIOD_MAP.get(period, period), "interval": interval}
    try:
        with httpx.Client(timeout=15.0, headers=HEADERS) as client:
            resp = client.get(url, params=params)
            if resp.status_code != 200:
                logger.debug("chart %s HTTP %s", ticker, resp.status_code)
                return None
            data = resp.json()
            result = data.get("chart", {}).get("result")
            return result[0] if result else None
    except Exception as e:  # noqa: BLE001
        logger.debug("chart istegi basarisiz %s: %s", ticker, e)
        return None


def validate_ticker(ticker: str) -> bool:
    """Sembolun gecerli veri donup donmedigini kontrol eder."""
    chart = _fetch_chart(ticker, period="5d")
    if not chart:
        return False
    return bool(chart.get("meta", {}).get("regularMarketPrice"))


class BISTService:
    """BIST (Borsa Istanbul) hisse verilerini Yahoo v8 API uzerinden ceker."""

    def validate_many(self, tickers: list[str], limit: Optional[int] = None) -> tuple[list[str], list[str]]:
        """Verilen sembolleri paralel dogrular. (gecerliler, gecersizler) doner."""
        if limit:
            tickers = tickers[:limit]
        valid, invalid = [], []
        with ThreadPoolExecutor(max_workers=8) as pool:
            futs = {pool.submit(validate_ticker, t): t for t in tickers}
            for fut in as_completed(futs):
                t = futs[fut]
                try:
                    if fut.result():
                        valid.append(t)
                    else:
                        invalid.append(t)
                except Exception:  # noqa: BLE001
                    invalid.append(t)
        return valid, invalid

    def get_batch_quotes(self, tickers: list[str]) -> dict[str, dict]:
        """Birden cok hisseyi paralel ceker (Yahoo v8 chart)."""
        if not tickers:
            return {}
        result: dict[str, dict] = {}
        with ThreadPoolExecutor(max_workers=8) as pool:
            futs = {pool.submit(self.get_quote, t): t for t in tickers}
            for fut in as_completed(futs):
                t = futs[fut]
                try:
                    q = fut.result()
                    if q:
                        result[t] = q
                except Exception:  # noqa: BLE001
                    pass
        return result

    def get_quote(self, ticker: str) -> Optional[dict]:
        """Tek hisse icin guncel fiyat bilgisi + gunluk degisim."""
        chart = _fetch_chart(ticker, period="5d")
        if not chart:
            return None
        try:
            meta = chart.get("meta", {})
            last_price = meta.get("regularMarketPrice")
            prev_close = meta.get("chartPreviousClose") or meta.get("previousClose")
            if last_price is None:
                return None

            change = None
            change_pct = None
            if prev_close:
                change = round(float(last_price) - float(prev_close), 4)
                change_pct = round((change / float(prev_close)) * 100, 2)

            volume = None
            ts = chart.get("timestamp") or []
            ind = chart.get("indicators", {}).get("quote", [{}])[0]
            if ts and ind.get("volume"):
                volume = int(ind["volume"][-1]) if ind["volume"][-1] is not None else None

            return {
                "ticker": ticker,
                "name": self._display_name(ticker),
                "price": float(last_price),
                "prev_close": float(prev_close) if prev_close else None,
                "change": change,
                "change_pct": change_pct,
                "currency": meta.get("currency", "TRY") or "TRY",
                "volume": volume,
            }
        except Exception as e:  # noqa: BLE001
            logger.warning("get_quote parse hatasi %s: %s", ticker, e)
            return None

    def get_history(self, ticker: str, period: str = "6mo", interval: str = "1d") -> list[dict]:
        """Hisse gecmisi (OHLCV) — grafik icin."""
        chart = _fetch_chart(ticker, period=period, interval=interval)
        if not chart:
            return []
        try:
            ts = chart.get("timestamp") or []
            ind = chart.get("indicators", {}).get("quote", [{}])[0]
            rows = []
            for i, t in enumerate(ts):
                try:
                    close = ind["close"][i]
                    if close is None:
                        continue
                    rows.append(
                        {
                            "date": datetime.fromtimestamp(t, tz=timezone.utc).strftime("%Y-%m-%d"),
                            "open": round(float(ind["open"][i] or close), 4),
                            "high": round(float(ind["high"][i] or close), 4),
                            "low": round(float(ind["low"][i] or close), 4),
                            "close": round(float(close), 4),
                            "volume": int(ind["volume"][i] or 0),
                        }
                    )
                except (TypeError, ValueError):
                    continue
            return rows
        except Exception as e:  # noqa: BLE001
            logger.warning("get_history parse hatasi %s: %s", ticker, e)
            return []

    @staticmethod
    def _display_name(ticker: str) -> str:
        return ticker.replace(".IS", "")
