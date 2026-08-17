"""Indicator Agent — teknik gostergeler (RSI, MA, hacim) hesaplar ve yorumlar."""

import logging
from typing import Optional

from app.services.bist import BISTService

logger = logging.getLogger(__name__)


class IndicatorAgent:
    def __init__(self):
        self.bist = BISTService()

    def analyze(self, ticker: str, history: Optional[list[dict]] = None) -> dict:
        if history is None:
            history = self.bist.get_history(ticker, period="6mo", interval="1d")

        closes = [r["close"] for r in history]
        volumes = [r["volume"] for r in history]

        indicators = {
            "rsi14": self._rsi(closes),
            "ma20": self._ma(closes, 20),
            "ma50": self._ma(closes, 50),
            "ma200": self._ma(closes, 200),
            "volume_ratio": self._volume_ratio(volumes),
        }

        indicators["comment"] = self._comment(ticker, closes, indicators)
        return indicators

    @staticmethod
    def _ma(values: list[float], window: int) -> Optional[float]:
        if len(values) < window:
            return None
        return round(sum(values[-window:]) / window, 2)

    @staticmethod
    def _rsi(values: list[float], period: int = 14) -> Optional[float]:
        if len(values) < period + 1:
            return None
        gains, losses = [], []
        for i in range(1, len(values)):
            diff = values[i] - values[i - 1]
            gains.append(max(diff, 0))
            losses.append(max(-diff, 0))
        avg_gain = sum(gains[-period:]) / period
        avg_loss = sum(losses[-period:]) / period
        if avg_loss == 0:
            return 100.0
        rs = avg_gain / avg_loss
        return round(100 - (100 / (1 + rs)), 1)

    @staticmethod
    def _volume_ratio(volumes: list[int]) -> Optional[float]:
        if len(volumes) < 20:
            return None
        recent = sum(volumes[-5:]) / 5
        base = sum(volumes[-20:-5]) / 15
        if base == 0:
            return None
        return round(recent / base, 2)

    @staticmethod
    def _comment(ticker: str, closes: list[float], ind: dict) -> str:
        parts = []
        rsi = ind["rsi14"]
        if rsi is not None:
            if rsi >= 70:
                parts.append("RSI aşırı alım bölgesinde (satış baskısı riski)")
            elif rsi <= 30:
                parts.append("RSI aşırı satım bölgesinde (alım fırsatı sinyali)")
            else:
                parts.append(f"RSI {rsi} ile nötr bölgede")
        last = closes[-1] if closes else None
        for label in ("ma20", "ma50", "ma200"):
            ma = ind[label]
            if last and ma:
                if last > ma:
                    parts.append(f"fiyat {label.upper()} üzerinde")
                else:
                    parts.append(f"fiyat {label.upper()} altında")
        vr = ind["volume_ratio"]
        if vr is not None:
            if vr > 1.5:
                parts.append(f"hacim ortalamanın {vr}x üzerinde (hareketlilik)")
            elif vr < 0.5:
                parts.append("hacim düşük (ilgi azalıyor)")
        return "; ".join(parts) if parts else "Yeterli veri yok"


def create() -> IndicatorAgent:
    return IndicatorAgent()


async def run(ticker: str, data: Optional[dict] = None) -> dict:
    history = (data or {}).get("history")
    return create().analyze(ticker, history)
