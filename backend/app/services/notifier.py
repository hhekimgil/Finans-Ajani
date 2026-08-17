"""Bildirim notifier'i — tarama sonuclarindaki kritik degisiklikleri Telegram'a bildirir."""

import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from app.services import telegram

logger = logging.getLogger(__name__)

DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data"
STATE_FILE = DATA_DIR / "notification_state.json"


def _load_state() -> dict:
    if not STATE_FILE.exists():
        return {}
    try:
        return json.loads(STATE_FILE.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return {}


def _save_state(state: dict) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")


def _signals(scan: dict) -> dict:
    """Bir tarama sonucu icin bildirim tetikleyici sinyaller."""
    signals = {}
    level = scan.get("level")
    if level in ("guclu", "zayif"):
        signals["level"] = level

    change = (scan.get("quote") or {}).get("change_pct")
    if change is not None and abs(change) >= 3:
        signals["big_move"] = round(change, 2)

    news = scan.get("news", {})
    if news.get("sentiment") == "olumsuz" and (news.get("score") or 50) < 40:
        signals["bad_news"] = True

    sent = scan.get("sentiment", {})
    if sent.get("sentiment") == "olumsuz" and (sent.get("score") or 50) < 40:
        signals["bad_sentiment"] = True

    rsi = scan.get("indicators", {}).get("rsi14")
    if rsi is not None and rsi >= 75:
        signals["overbought"] = rsi
    elif rsi is not None and rsi <= 25:
        signals["oversold"] = rsi

    return signals


def process_scan_results(results: list[dict]) -> int:
    """Yeni tarama sonuclarini onceki durumla karsilastirir, kritik olanlari bildirir."""
    if not telegram.is_ready():
        return 0

    state = _load_state()
    notifications: list[dict] = []
    now = datetime.now(timezone.utc).isoformat()

    for scan in results:
        ticker = scan.get("ticker")
        signals = _signals(scan)
        if not signals:
            continue

        prev_signals = state.get(ticker, {}).get("signals", {})
        # Sinyal yeni ortaya ciktiysa bildir
        new_signal = any(signals.get(k) and not prev_signals.get(k) for k in signals)

        if new_signal:
            notifications.append({"scan": scan, "signals": signals})

        state[ticker] = {"signals": signals, "scanned_at": now}

    _save_state(state)

    sent = 0
    for n in notifications:
        text = _format(n["scan"], n["signals"])
        if telegram.send_message(text):
            sent += 1
    return sent


def _format(scan: dict, signals: dict) -> str:
    q = scan.get("quote", {})
    parts = [f"🚨 <b>{scan.get('name', scan.get('ticker'))}</b>"]
    if signals.get("level") == "guclu":
        parts.append("Güçlü analiz sinyali!")
    if signals.get("level") == "zayif":
        parts.append("Zayıf analiz sinyali!")
    if signals.get("big_move"):
        parts.append(f"Büyük hareket: %{signals['big_move']:+.2f}")
    if signals.get("bad_news"):
        parts.append("Negatif haber akışı!")
    if signals.get("bad_sentiment"):
        parts.append("Yatırımcı duyarlılığı olumsuz!")
    if signals.get("overbought"):
        parts.append(f"RSI aşırı alımda: {signals['overbought']}")
    if signals.get("oversold"):
        parts.append(f"RSI aşırı satımda: {signals['oversold']}")

    q_price = q.get("price")
    if q_price:
        change = q.get("change_pct")
        sign = "+" if (change or 0) >= 0 else ""
        parts.append(f"Fiyat: {q_price} TL (%{sign}{change}) · Skor: {scan.get('score')}")
    return "\n".join(parts)


def clear_state() -> None:
    _save_state({})
