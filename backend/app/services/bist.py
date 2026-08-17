import json
import logging
from pathlib import Path
from typing import Optional

import yfinance as yf

logger = logging.getLogger(__name__)

BIST100_FILE = Path(__file__).resolve().parent.parent.parent / "data" / "bist100.json"


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


def validate_ticker(ticker: str) -> bool:
    """Sembolun yfinance'te gecerli veri donup donmedigini kontrol eder."""
    try:
        info = yf.Ticker(ticker).fast_info
        return info.last_price is not None
    except Exception:  # noqa: BLE001
        return False


class BISTService:
    """BIST (Borsa Istanbul) hisse verilerini yfinance uzerinden ceker."""

    def validate_many(self, tickers: list[str], limit: Optional[int] = None) -> tuple[list[str], list[str]]:
        """Verilen sembolleri dogrular. (gecerliler, gecersizler) doner."""
        if limit:
            tickers = tickers[:limit]
        valid, invalid = [], []
        for t in tickers:
            if validate_ticker(t):
                valid.append(t)
            else:
                invalid.append(t)
        return valid, invalid

    def get_batch_quotes(self, tickers: list[str]) -> dict[str, dict]:
        """Birden cok hisseyi TEK yfinance istegiyle ceker.

        yf.download group_by='ticker' ile tum sembolleri paralel indirir.
        Gecersiz/verisi olmayan semboller sonuca dahil edilmez.
        """
        if not tickers:
            return {}
        result: dict[str, dict] = {}
        try:
            data = yf.download(
                tickers,
                period="5d",
                interval="1d",
                group_by="ticker",
                threads=True,
                progress=False,
                auto_adjust=False,
            )
            for t in tickers:
                try:
                    if len(tickers) == 1:
                        df = data
                    else:
                        df = data[t]
                    closes = df["Close"].dropna()
                    if closes.empty:
                        continue
                    last_price = float(closes.iloc[-1])
                    prev_close = float(closes.iloc[-2]) if len(closes) > 1 else last_price
                    change = round(last_price - prev_close, 4)
                    change_pct = round((change / prev_close) * 100, 2) if prev_close else None
                    volume = int(df["Volume"].dropna().iloc[-1]) if not df["Volume"].dropna().empty else None
                    result[t] = {
                        "ticker": t,
                        "name": self._display_name(t),
                        "price": last_price,
                        "prev_close": prev_close,
                        "change": change,
                        "change_pct": change_pct,
                        "currency": "TRY",
                        "volume": volume,
                    }
                except Exception as e:  # noqa: BLE001
                    logger.debug("batch quote basarisiz %s: %s", t, e)
        except Exception as e:  # noqa: BLE001
            logger.warning("yf.download basarisiz: %s", e)
        return result

    def get_quote(self, ticker: str) -> Optional[dict]:
        """Tek hisse icin guncel fiyat bilgisi + gunluk degisim."""
        try:
            t = yf.Ticker(ticker)
            info = t.fast_info
            hist = t.history(period="2d")
            last_price = float(info.last_price) if info.last_price else None
            prev_close = float(info.previous_close) if info.previous_close else None

            change = None
            change_pct = None
            if last_price is not None and prev_close:
                change = round(last_price - prev_close, 4)
                change_pct = round((change / prev_close) * 100, 2)

            return {
                "ticker": ticker,
                "name": self._display_name(ticker),
                "price": last_price,
                "prev_close": prev_close,
                "change": change,
                "change_pct": change_pct,
                "currency": getattr(info, "currency", "TRY") or "TRY",
                "volume": int(info.last_volume) if info.last_volume else None,
            }
        except Exception as e:  # noqa: BLE001
            logger.warning("get_quote basarisiz %s: %s", ticker, e)
            return None

    def get_history(self, ticker: str, period: str = "6mo", interval: str = "1d") -> list[dict]:
        """Hisse gecmisi (OHLCV) — grafik icin."""
        try:
            hist = yf.Ticker(ticker).history(period=period, interval=interval)
            rows = []
            for idx, row in hist.iterrows():
                rows.append(
                    {
                        "date": idx.strftime("%Y-%m-%d"),
                        "open": round(float(row["Open"]), 4),
                        "high": round(float(row["High"]), 4),
                        "low": round(float(row["Low"]), 4),
                        "close": round(float(row["Close"]), 4),
                        "volume": int(row["Volume"]),
                    }
                )
            return rows
        except Exception as e:  # noqa: BLE001
            logger.warning("get_history basarisiz %s: %s", ticker, e)
            return []

    @staticmethod
    def _display_name(ticker: str) -> str:
        return ticker.replace(".IS", "").replace(".IS", "")
