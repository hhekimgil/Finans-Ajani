"""News Agent — hisse/borsa haberlerini toplar ve LLM ile analiz eder."""

import logging
from typing import Optional

import httpx
from bs4 import BeautifulSoup

from app.services import llm

logger = logging.getLogger(__name__)

GOOGLE_NEWS_RSS = "https://news.google.com/rss/search"
KAP_RSS = "https://www.kap.org.tr/tr/rss/"


class NewsAgent:
    def __init__(self, timeout: float = 15.0):
        self.timeout = timeout

    def collect_headlines(self, ticker: str) -> list[str]:
        """Google News RSS + KAP RSS uzerinden haber basliklari toplar."""
        headlines: list[str] = []
        search_term = ticker.replace(".IS", "")

        gnews = self._fetch_google_news(search_term)
        headlines.extend(gnews)

        kap = self._fetch_kap()
        headlines.extend(k for k in kap if search_term in k or "borsa" in k.lower())

        seen: set[str] = set()
        uniq = []
        for h in headlines:
            if h not in seen:
                seen.add(h)
                uniq.append(h)
        return uniq

    def analyze(self, ticker: str) -> dict:
        headlines = self.collect_headlines(ticker)
        result = llm.analyze_news(ticker, headlines)
        result["headlines"] = headlines[:10]
        return result

    def _fetch_google_news(self, term: str) -> list[str]:
        params = {"q": term, "hl": "tr", "gl": "TR", "ceid": "TR:tr"}
        try:
            with httpx.Client(timeout=self.timeout, follow_redirects=True) as client:
                resp = client.get(GOOGLE_NEWS_RSS, params=params)
                resp.raise_for_status()
                soup = BeautifulSoup(resp.text, "xml")
                return [item.title.text for item in soup.find_all("item")[:10]]
        except Exception as e:  # noqa: BLE001
            logger.warning("Google News basarisiz: %s", e)
            return []

    def _fetch_kap(self) -> list[str]:
        try:
            with httpx.Client(timeout=self.timeout, follow_redirects=True) as client:
                resp = client.get(KAP_RSS)
                resp.raise_for_status()
                soup = BeautifulSoup(resp.text, "xml")
                return [item.title.text for item in soup.find_all("item")[:20]]
        except Exception as e:  # noqa: BLE001
            logger.warning("KAP RSS basarisiz: %s", e)
            return []


def create() -> NewsAgent:
    return NewsAgent()


# Pipeline uyumlulugu (orchestrator cagirir)
async def run(ticker: str, data: Optional[dict] = None) -> dict:
    return create().analyze(ticker)
