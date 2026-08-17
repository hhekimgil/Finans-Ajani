"""Sentiment Agent — yatirimci yorumlarini toplar ve duygu analizi yapar.

Veri kaynaklari (video ile ayni prensip):
- Reddit (r/Yatirim, r/BorsaVadeli, r/hisse) — opsiyonel, API anahtari gerekir
- Investing.com yorumlari — scrape tabanli (riskli), anahtar olmadan
- Reddit API anahtari yoksa Google News yorum benzeri kaynak kullanilir
"""

import base64
import logging
from typing import Optional

import httpx

from app.config import settings
from app.services import llm

logger = logging.getLogger(__name__)


class SentimentAgent:
    def __init__(self, timeout: float = 15.0):
        self.timeout = timeout

    def collect_comments(self, ticker: str) -> list[str]:
        comments: list[str] = []

        reddit = self._fetch_reddit(ticker)
        comments.extend(reddit)

        investing = self._fetch_investing(ticker)
        comments.extend(investing)

        if not comments:
            comments = self._fallback(ticker)

        return comments[:20]

    def analyze(self, ticker: str) -> dict:
        comments = self.collect_comments(ticker)
        result = llm.analyze_sentiment(ticker, comments)
        result["comment_count"] = len(comments)
        return result

    def _fetch_reddit(self, ticker: str) -> list[str]:
        if not (settings.reddit_client_id and settings.reddit_client_secret):
            return []
        auth = base64.b64encode(
            f"{settings.reddit_client_id}:{settings.reddit_client_secret}".encode()
        ).decode()
        term = ticker.replace(".IS", "")
        try:
            with httpx.Client(timeout=self.timeout) as client:
                token_resp = client.post(
                    "https://www.reddit.com/api/v1/access_token",
                    headers={"Authorization": f"Basic {auth}", "User-Agent": settings.reddit_user_agent},
                    data={"grant_type": "client_credentials"},
                )
                token_resp.raise_for_status()
                token = token_resp.json()["access_token"]
                search_resp = client.get(
                    "https://oauth.reddit.com/search",
                    params={"q": term, "sort": "relevance", "t": "week", "limit": 10},
                    headers={"Authorization": f"Bearer {token}", "User-Agent": settings.reddit_user_agent},
                )
                search_resp.raise_for_status()
                children = search_resp.json().get("data", {}).get("children", [])
                return [c["data"].get("selftext") or c["data"].get("title") for c in children if c.get("data")]
        except Exception as e:  # noqa: BLE001
            logger.warning("Reddit basarisiz: %s", e)
            return []

    def _fetch_investing(self, ticker: str) -> list[str]:
        """Investing.com yorumlari — scrape tabanli, basarisiz olursa gecilir."""
        term = ticker.replace(".IS", "").lower()
        try:
            with httpx.Client(timeout=self.timeout, follow_redirects=True) as client:
                resp = client.get(
                    f"https://tr.investing.com/search/?q={term}",
                    headers={"User-Agent": settings.reddit_user_agent},
                )
                if resp.status_code != 200:
                    return []
                import re

                m = re.findall(r'(?s)class="[^"]*comment[^"]*"[^>]*>(.*?)<', resp.text)
                return [mm.strip()[:300] for mm in m if mm.strip()][:10]
        except Exception as e:  # noqa: BLE001
            logger.warning("Investing.com basarisiz: %s", e)
            return []

    def _fallback(self, ticker: str) -> list[str]:
        """Gercek kaynak olmadiginda haber basliklarini yorum olarak kullanir."""
        from app.agents import news_agent

        return news_agent.create().collect_headlines(ticker)[:10]


def create() -> SentimentAgent:
    return SentimentAgent()


async def run(ticker: str, data: Optional[dict] = None) -> dict:
    return create().analyze(ticker)
