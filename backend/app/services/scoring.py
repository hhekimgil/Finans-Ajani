"""Analiz skoru hesaplama servisi.

Faz 1: kural tabanli temel skor (trend + momentum).
Faz 2: Ollama ile haber/sentiment/indicator katkilari eklenecek.
"""

from datetime import datetime, timezone


def compute_score(quote: dict, history: list[dict]) -> dict:
    """Kural tabanli analiz skoru uretir (0-100)."""
    score = 50.0
    reasons: list[str] = []

    if quote.get("change_pct") is not None:
        c = quote["change_pct"]
        if c > 0:
            score += min(c * 2.0, 20)
            reasons.append(f"Gunluk yukselis %{c:+.2f}")
        elif c < 0:
            score += max(c * 2.0, -20)
            reasons.append(f"Gunluk dusus %{c:+.2f}")

    if len(history) >= 20:
        closes = [r["close"] for r in history[-20:]]
        ma20 = sum(closes) / len(closes)
        last = closes[-1]
        if last > ma20:
            score += 5
            reasons.append("Fiyat 20 gunluk ortalamanin ustunde")
        else:
            score -= 5
            reasons.append("Fiyat 20 gunluk ortalamanin altinda")

    if len(history) >= 50:
        closes = [r["close"] for r in history[-50:]]
        ma50 = sum(closes) / len(closes)
        last = closes[-1]
        if last > ma50:
            score += 5
            reasons.append("Fiyat 50 gunluk ortalamanin ustunde")
        else:
            score -= 5
            reasons.append("Fiyat 50 gunluk ortalamanin altinda")

    score = max(0.0, min(100.0, round(score, 1)))

    return {
        "score": score,
        "level": _level(score),
        "reasons": reasons,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


def _level(score: float) -> str:
    if score >= 75:
        return "guclu"
    if score >= 55:
        return "olumlu"
    if score >= 40:
        return "notr"
    if score >= 25:
        return "olumsuz"
    return "zayif"
