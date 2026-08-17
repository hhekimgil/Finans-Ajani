"""Orchestrator Agent — tum uzman agentlari toplar ve analiz skoru uretir."""

import asyncio
import logging
from datetime import datetime, timezone

from app.agents import indicator_agent, macro_agent, news_agent, sentiment_agent
from app.services import llm, supabase_db
from app.services.bist import BISTService

logger = logging.getLogger(__name__)


class Orchestrator:
    def __init__(self):
        self.bist = BISTService()

    async def analyze(self, ticker: str) -> dict:
        """Tek hisse icin tam analiz uretir (tum agentlar paralel)."""
        quote = self.bist.get_quote(ticker)
        if not quote:
            return {"ticker": ticker, "error": "fiyat verisi yok"}

        history = self.bist.get_history(ticker, period="6mo", interval="1d")
        shared = {"history": history, "quote": quote}

        news_task = asyncio.create_task(news_agent.run(ticker, shared))
        sentiment_task = asyncio.create_task(sentiment_agent.run(ticker, shared))
        indicator_task = asyncio.create_task(indicator_agent.run(ticker, shared))
        macro_task = asyncio.create_task(macro_agent.run(ticker, shared))

        news, sentiment, indicators, macro = await asyncio.gather(
            news_task, sentiment_task, indicator_task, macro_task
        )

        factors = {
            "price_change_pct": quote.get("change_pct"),
            "news_score": news.get("score", 50),
            "news_sentiment": news.get("sentiment"),
            "sentiment_score": sentiment.get("score", 50),
            "sentiment": sentiment.get("sentiment"),
            "rsi14": indicators.get("rsi14"),
            "ma20": indicators.get("ma20"),
            "ma50": indicators.get("ma50"),
            "volume_ratio": indicators.get("volume_ratio"),
        }

        score, level = self._compute_score(factors)
        comment = llm.explain_score(ticker, factors)

        result = {
            "ticker": ticker,
            "name": quote["name"],
            "quote": quote,
            "score": score,
            "level": level,
            "comment": comment,
            "news": news,
            "sentiment": sentiment,
            "indicators": indicators,
            "macro": macro,
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }

        if supabase_db.is_ready():
            supabase_db.save_scan_result(result)

        return result

    def _compute_score(self, f: dict) -> tuple[float, str]:
        """Haber + sentimant + teknik + gunluk degisim bilesimi (0-100)."""
        score = 50.0

        c = f.get("price_change_pct")
        if c is not None:
            score += max(-10, min(10, c * 2))

        news_score = f.get("news_score")
        if news_score is not None:
            score += (news_score - 50) * 0.3

        sent_score = f.get("sentiment_score")
        if sent_score is not None:
            score += (sent_score - 50) * 0.3

        rsi = f.get("rsi14")
        if rsi is not None:
            if 45 <= rsi <= 55:
                score += 2  # notr ve saglikli
            elif rsi >= 75:
                score -= 4  # asiri alim
            elif rsi <= 25:
                score += 3  # asiri satim (potansiyel)

        last = f.get("ma20") and f.get("price") or None
        score = max(0.0, min(100.0, round(score, 1)))
        return score, self._level(score)

    @staticmethod
    def _level(score: float) -> str:
        if score >= 70:
            return "guclu"
        if score >= 55:
            return "olumlu"
        if score >= 40:
            return "notr"
        if score >= 25:
            return "olumsuz"
        return "zayif"


async def run(ticker: str) -> dict:
    return await Orchestrator().analyze(ticker)


async def scan_all() -> list[dict]:
    """Taranacak hisseleri Supabase'den okur (bos ise config fallback) ve tarar."""
    from app.services.supabase_db import get_scanned_tickers

    tickers = get_scanned_tickers()

    results = []
    for ticker in tickers:
        try:
            logger.info("Taranıyor: %s", ticker)
            result = await run(ticker)
            results.append(result)
        except Exception as e:  # noqa: BLE001
            logger.error("Tarama hatasi %s: %s", ticker, e)
    results.sort(key=lambda r: r.get("score", 0), reverse=True)
    return results


def scan_quick() -> list[dict]:
    """LLM'siz HIZLI fiyat taramasi — scheduler icin.

    yfinance toplu cekimle tüm hisselerin fiyat/degisim/hacim bilgisini
    alir, temel skoru hesaplar ve Supabase scan_results'a kaydeder.
    Derin LLM analizi yapmaz (kullanici hisseye tiklayinca calisir).
    """
    from app.services.bist import BISTService
    from app.services.scoring import compute_score
    from app.services.supabase_db import get_scanned_tickers, is_ready, save_scan_result

    tickers = get_scanned_tickers()
    bist = BISTService()
    quotes = bist.get_batch_quotes(tickers)

    results = []
    for ticker, quote in quotes.items():
        history = bist.get_history(ticker, period="3mo", interval="1d")
        analysis = compute_score(quote, history)
        entry = {
            "ticker": ticker,
            "name": quote["name"],
            "quote": quote,
            "score": analysis["score"],
            "level": analysis["level"],
            "comment": "",
            "news": {"sentiment": None, "score": None, "headlines": []},
            "sentiment": {"sentiment": None, "score": None},
            "indicators": {"rsi14": None},
            "macro": {"rates": {}, "summary": ""},
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }
        if is_ready():
            save_scan_result(entry)
        results.append(entry)

    results.sort(key=lambda r: r.get("score", 0), reverse=True)
    return results
