"""Ollama (yerel LLM) servisi — Turkce finans analizi."""

import json
import logging
from typing import Optional

from ollama import Client

from app.config import settings

logger = logging.getLogger(__name__)

_client: Optional[Client] = None
_system_prompt = (
    "Sen bir finansal analist asistanisin. Turk hisse senedi piyasasi (BIST) "
    "uzerine teknik ve habere dayali degerlendirme yaparsin. Yanitlarin her "
    "zaman kisa, nesnel ve yalnizca JSON biciminde olmalidir. "
    "Yatirim tavsiyesi vermezsin; yalnizca analiz sunarsin."
)


def _get_client() -> Client:
    global _client
    if _client is None:
        host = settings.ollama_host
        if not host.startswith("http"):
            host = f"http://{host}"
        host = host.replace("0.0.0.0", "127.0.0.1")
        _client = Client(host=host, timeout=600.0)
    return _client


def _generate(prompt: str, temperature: float = 0.2, max_tokens: int = 512) -> str:
    try:
        resp = _get_client().generate(
            model=settings.ollama_model,
            prompt=prompt,
            system=_system_prompt,
            stream=False,
            options={"temperature": temperature, "num_predict": max_tokens},
        )
        return resp["response"].strip()
    except Exception as e:  # noqa: BLE001
        logger.warning("Ollama cagrisi basarisiz: %s", e)
        return ""


def analyze_news(ticker: str, headlines: list[str]) -> dict:
    """Haber basliklarini analiz eder: sentiment + skor + ozet."""
    if not headlines:
        return {"sentiment": "notr", "score": 50, "summary": "Haber bulunamadi"}
    joined = "\n".join(f"- {h}" for h in headlines[:10])
    prompt = (
        f"'{ticker}' hissesiyle ilgili haber basliklari:\n{joined}\n\n"
        'JSON dondur: {"sentiment": "olumlu|olumsuz|notr", "score": 0-100, '
        '"summary": "en onemli haberin 1 cumle ozeti"}'
    )
    raw = _generate(prompt)
    return _parse_json(raw, default={"sentiment": "notr", "score": 50, "summary": "Analiz yapilamadi"})


def analyze_sentiment(ticker: str, comments: list[str]) -> dict:
    """Yatirimci yorumlarini analiz eder: ortalama duygu + ornek gorusler."""
    if not comments:
        return {"sentiment": "notr", "score": 50, "positive": [], "negative": []}
    joined = "\n".join(f"- {c[:200]}" for c in comments[:15])
    prompt = (
        f"'{ticker}' hissesi hakkinda yatirimci yorumlari:\n{joined}\n\n"
        'JSON dondur: {"sentiment": "olumlu|olumsuz|notr", "score": 0-100, '
        '"positive": ["olumlu 1 ornek yorum"], "negative": ["olumsuz 1 ornek yorum"]}'
    )
    raw = _generate(prompt)
    data = _parse_json(raw, default={"sentiment": "notr", "score": 50})
    data.setdefault("positive", [])
    data.setdefault("negative", [])
    return data


def explain_score(ticker: str, factors: dict) -> str:
    """Analiz skorunu tek cumleyle yorumlar."""
    prompt = (
        f"'{ticker}' icin analiz faktorleri: {json.dumps(factors, ensure_ascii=False)}\n"
        "Bu faktorlere dayanarak hisse icin 2-3 cumlelik nesnel bir degerlendirme yaz. "
        "Yatirim tavsiyesi verme."
    )
    raw = _generate(prompt, max_tokens=300)
    if not raw:
        return "Yorum yapilamadi."
    try:
        start = raw.find("{")
        end = raw.rfind("}")
        if start != -1 and end != -1:
            data = json.loads(raw[start : end + 1])
            analysis = data.get("analysis") or data.get("degerlendirme") or data.get("summary")
            if analysis:
                return str(analysis).strip()
    except json.JSONDecodeError:
        pass
    return raw.strip()[:500]


def _parse_json(raw: str, default: dict) -> dict:
    if not raw:
        return default
    try:
        start = raw.find("{")
        end = raw.rfind("}")
        if start == -1 or end == -1:
            return default
        return json.loads(raw[start : end + 1])
    except json.JSONDecodeError:
        logger.warning("LLM JSON parse hatasi: %s", raw[:200])
        return default
