"""Macro Agent — doviz/fail/ekonomik gostergeleri TCMB'den toplar."""

import logging
from typing import Optional

import httpx
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

TCMB_URL = "https://www.tcmb.gov.tr/kurlar/today.xml"


class MacroAgent:
    def __init__(self, timeout: float = 15.0):
        self.timeout = timeout

    def analyze(self, ticker: str = "", data: Optional[dict] = None) -> dict:
        rates = self._fetch_tcmb()
        usd = rates.get("USD")
        eur = rates.get("EUR")
        gbp = rates.get("GBP")

        return {
            "rates": rates,
            "summary": self._summary(usd, eur, gbp),
        }

    def _fetch_tcmb(self) -> dict:
        try:
            with httpx.Client(timeout=self.timeout, follow_redirects=True) as client:
                resp = client.get(TCMB_URL)
                resp.raise_for_status()
                soup = BeautifulSoup(resp.text, "xml")
                result = {}
                for cur in soup.find_all("Currency"):
                    code = cur.get("CurrencyCode")
                    if code in ("USD", "EUR", "GBP"):
                        sell = cur.find("ForexSelling")
                        result[code] = {
                            "name": (cur.find("Isim").text if cur.find("Isim") else code),
                            "sell": float(sell.text) if sell and sell.text else None,
                        }
                return result
        except Exception as e:  # noqa: BLE001
            logger.warning("TCMB basarisiz: %s", e)
            return {}

    @staticmethod
    def _summary(usd: dict, eur: dict, gbp: dict) -> str:
        parts = []
        if usd and usd.get("sell"):
            parts.append(f"USD/TRY {usd['sell']:.4f}")
        if eur and eur.get("sell"):
            parts.append(f"EUR/TRY {eur['sell']:.4f}")
        if gbp and gbp.get("sell"):
            parts.append(f"GBP/TRY {gbp['sell']:.4f}")
        return "; ".join(parts) if parts else "TCMB verisi alinamadi"


def create() -> MacroAgent:
    return MacroAgent()


async def run(ticker: str, data: Optional[dict] = None) -> dict:
    return create().analyze(ticker, data)
