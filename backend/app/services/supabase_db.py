"""Supabase veritabani servisi — arama gecmisi, watchlist ve tarama sonuclari."""

import logging
from typing import Optional

from supabase import create_client

from app.config import settings

logger = logging.getLogger(__name__)

_client = None


def _get_client():
    global _client
    if _client is None:
        if not settings.supabase_url or not settings.supabase_anon_key:
            return None
        _client = create_client(settings.supabase_url, settings.supabase_anon_key)
    return _client


def is_ready() -> bool:
    return bool(settings.supabase_url and settings.supabase_anon_key)


def _table(name: str):
    client = _get_client()
    if client is None:
        return None
    return client.table(name)


# --- Arama gecmisi ---

def add_search_history(ticker: str, user_id: str = "local") -> Optional[dict]:
    table = _table("search_history")
    if table is None:
        return None
    try:
        row = {"ticker": ticker, "user_id": user_id, "searched_at": "now()"}
        result = table.insert(row).execute()
        return result.data[0] if result.data else None
    except Exception as e:  # noqa: BLE001
        logger.warning("search_history ekleme hatasi: %s", e)
        return None


def get_search_history(limit: int = 20, user_id: str = "local") -> list:
    table = _table("search_history")
    if table is None:
        return []
    try:
        result = table.select("*").eq("user_id", user_id).order("searched_at", desc=True).limit(limit).execute()
        return result.data
    except Exception as e:  # noqa: BLE001
        logger.warning("search_history okuma hatasi: %s", e)
        return []


# --- Watchlist ---

def add_to_watchlist(ticker: str, user_id: str = "local") -> Optional[dict]:
    table = _table("watchlist")
    if table is None:
        return None
    try:
        existing = table.select("*").eq("user_id", user_id).eq("ticker", ticker).execute()
        if existing.data:
            return existing.data[0]
        row = {"ticker": ticker, "user_id": user_id, "added_at": "now()"}
        result = table.insert(row).execute()
        return result.data[0] if result.data else None
    except Exception as e:  # noqa: BLE001
        logger.warning("watchlist ekleme hatasi: %s", e)
        return None


def remove_from_watchlist(ticker: str, user_id: str = "local") -> bool:
    table = _table("watchlist")
    if table is None:
        return False
    try:
        table.delete().eq("user_id", user_id).eq("ticker", ticker).execute()
        return True
    except Exception as e:  # noqa: BLE001
        logger.warning("watchlist silme hatasi: %s", e)
        return False


def get_watchlist(user_id: str = "local") -> list:
    table = _table("watchlist")
    if table is None:
        return []
    try:
        result = table.select("*").eq("user_id", user_id).order("added_at", desc=True).execute()
        return result.data
    except Exception as e:  # noqa: BLE001
        logger.warning("watchlist okuma hatasi: %s", e)
        return []


# --- Tarama sonuclari ---

def save_scan_result(scan: dict) -> Optional[dict]:
    table = _table("scan_results")
    if table is None:
        return None
    try:
        row = {
            "ticker": scan["ticker"],
            "name": scan.get("name", ""),
            "price": scan.get("quote", {}).get("price"),
            "change_pct": scan.get("quote", {}).get("change_pct"),
            "score": scan.get("score"),
            "level": scan.get("level"),
            "comment": scan.get("comment", ""),
            "news_sentiment": scan.get("news", {}).get("sentiment"),
            "news_score": scan.get("news", {}).get("score"),
            "sentiment": scan.get("sentiment", {}).get("sentiment"),
            "sentiment_score": scan.get("sentiment", {}).get("score"),
            "rsi14": scan.get("indicators", {}).get("rsi14"),
            "raw": scan,
        }
        result = table.upsert(row, on_conflict="ticker").execute()
        return result.data[0] if result.data else None
    except Exception as e:  # noqa: BLE001
        logger.warning("scan_result kayit hatasi: %s", e)
        return None


def get_latest_results(limit: int = 50) -> list:
    table = _table("scan_results")
    if table is None:
        return []
    try:
        result = table.select("*").order("score", desc=True).limit(limit).execute()
        return result.data
    except Exception as e:  # noqa: BLE001
        logger.warning("scan_result okuma hatasi: %s", e)
        return []
