"""Telegram bildirim servisi — telefona haber/uyari mesajlari gonderir."""

import logging
from typing import Optional

import httpx

from app.config import settings

logger = logging.getLogger(__name__)

API_BASE = "https://api.telegram.org/bot{token}"


def is_ready() -> bool:
    return bool(settings.telegram_bot_token and settings.telegram_chat_id)


def _url(method: str) -> str:
    return f"{API_BASE.format(token=settings.telegram_bot_token)}/{method}"


def send_message(text: str, parse_mode: str = "HTML", timeout: float = 15.0) -> bool:
    """Telegram'a mesaj gonderir."""
    if not is_ready():
        logger.warning("Telegram yapilandirilmamis, mesaj gonderilemedi.")
        return False
    try:
        with httpx.Client(timeout=timeout) as client:
            resp = client.post(
                _url("sendMessage"),
                json={
                    "chat_id": settings.telegram_chat_id,
                    "text": text,
                    "parse_mode": parse_mode,
                    "disable_web_page_preview": True,
                },
            )
            resp.raise_for_status()
            data = resp.json()
            return bool(data.get("ok"))
    except Exception as e:  # noqa: BLE001
        logger.warning("Telegram mesaj hatasi: %s", e)
        return False


def format_scan_notification(scan: dict) -> str:
    """Tarama sonucunu kisa bir bildirim mesajina donusturur."""
    q = scan.get("quote", {})
    price = q.get("price")
    change = q.get("change_pct")
    sign = "+" if (change or 0) >= 0 else ""

    lines = [
        f"<b>{scan.get('name', scan.get('ticker'))}</b>",
        f"Fiyat: {price} TL (%{sign}{change})",
        f"Analiz Skoru: <b>{scan.get('score')}</b> ({scan.get('level')})",
    ]

    news = scan.get("news", {})
    if news.get("sentiment"):
        lines.append(f"📰 Haber: {news['sentiment']} ({news.get('score')})")

    sent = scan.get("sentiment", {})
    if sent.get("sentiment"):
        lines.append(f"💬 Duyarlılık: {sent['sentiment']} ({sent.get('score')})")

    ind = scan.get("indicators", {})
    if ind.get("rsi14") is not None:
        lines.append(f"📊 RSI(14): {ind['rsi14']}")

    if scan.get("comment"):
        lines.append(f"\n{scan['comment']}")

    return "\n".join(lines)


def send_test_notification() -> bool:
    """Deneme bildirimi gonderir."""
    return send_message(
        "🔔 <b>Finansal Asistan</b> bağlantı testi başarılı!\n"
        "Güncel haber ve analiz bildirimleri bu kanaldan gelecek."
    )
