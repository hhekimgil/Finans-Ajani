import logging
from typing import Optional

import yfinance as yf

logger = logging.getLogger(__name__)


class BISTService:
    """BIST (Borsa Istanbul) hisse verilerini yfinance uzerinden ceker."""

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
