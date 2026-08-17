from fastapi import APIRouter, HTTPException, Query

from app.agents import orchestrator
from app.config import settings
from app.services import supabase_db, telegram
from app.services.bist import BISTService
from app.services.scheduler import get_last_scan
from app.services.scoring import compute_score

router = APIRouter(prefix="/api", tags=["api"])
bist = BISTService()


@router.get("/ping")
def ping() -> dict:
    return {"message": "pong"}


@router.get("/stocks")
def list_stocks() -> dict:
    """Anlik fiyat + temel skor ile hisse listesi (skora gore sirali)."""
    results = []
    for ticker in settings.tickers:
        quote = bist.get_quote(ticker)
        if not quote:
            continue
        history = bist.get_history(ticker, period="3mo", interval="1d")
        analysis = compute_score(quote, history)
        results.append(
            {
                "ticker": ticker,
                "name": quote["name"],
                "price": quote["price"],
                "change": quote["change"],
                "change_pct": quote["change_pct"],
                "currency": quote["currency"],
                "volume": quote["volume"],
                "score": analysis["score"],
                "level": analysis["level"],
            }
        )

    results.sort(key=lambda r: r["score"], reverse=True)
    return {"count": len(results), "stocks": results}


@router.get("/stocks/{ticker}")
def stock_detail(ticker: str, period: str = Query("6mo")) -> dict:
    """Hisse detayi: fiyat + analiz + grafik verisi."""
    ticker = ticker.upper()
    if not ticker.endswith(".IS"):
        ticker = f"{ticker}.IS"

    quote = bist.get_quote(ticker)
    if not quote:
        raise HTTPException(status_code=404, detail=f"{ticker} icin veri bulunamadi")

    history = bist.get_history(ticker, period=period, interval="1d")
    analysis = compute_score(quote, history)

    return {
        "quote": quote,
        "analysis": analysis,
        "history": history,
    }


@router.get("/analyze/{ticker}")
async def analyze_stock(ticker: str) -> dict:
    """Tam agent analizi: haber + sentimant + indikator + makro + skor."""
    ticker = ticker.upper()
    if not ticker.endswith(".IS"):
        ticker = f"{ticker}.IS"
    return await orchestrator.run(ticker)


@router.get("/analyze")
async def analyze_all() -> dict:
    """Tum hisseleri agent'larla tarar, skora gore sirali dondurur."""
    results = await orchestrator.scan_all()
    return {"count": len(results), "results": results}


@router.get("/scan/latest")
def scan_latest() -> dict:
    """Scheduler'in son tarama sonucunu dondurur."""
    last = get_last_scan()
    if last is None:
        return {"count": 0, "results": [], "scanned_at": None}
    return last


# --- Supabase: arama gecmisi ---

@router.get("/history")
def search_history(limit: int = Query(20, le=100)) -> dict:
    rows = supabase_db.get_search_history(limit=limit)
    return {"count": len(rows), "history": rows}


@router.post("/history/{ticker}")
def record_search(ticker: str) -> dict:
    ticker = _normalize(ticker)
    row = supabase_db.add_search_history(ticker)
    return {"ok": row is not None, "record": row}


# --- Supabase: watchlist ---

@router.get("/watchlist")
def watchlist() -> dict:
    rows = supabase_db.get_watchlist()
    return {"count": len(rows), "watchlist": rows}


@router.post("/watchlist/{ticker}")
def add_watchlist(ticker: str) -> dict:
    ticker = _normalize(ticker)
    row = supabase_db.add_to_watchlist(ticker)
    return {"ok": row is not None, "record": row}


@router.delete("/watchlist/{ticker}")
def remove_watchlist(ticker: str) -> dict:
    ticker = _normalize(ticker)
    ok = supabase_db.remove_from_watchlist(ticker)
    return {"ok": ok}


@router.get("/supabase/status")
def supabase_status() -> dict:
    return {"ready": supabase_db.is_ready()}


# --- Telegram bildirim ---

@router.get("/telegram/status")
def telegram_status() -> dict:
    return {"ready": telegram.is_ready()}


@router.post("/telegram/test")
def telegram_test() -> dict:
    ok = telegram.send_test_notification()
    if not ok:
        raise HTTPException(status_code=500, detail="Telegram bildirimi gonderilemedi. Bot token/chat_id kontrol edin.")
    return {"ok": True, "message": "Deneme bildirimi gonderildi"}


def _normalize(ticker: str) -> str:
    ticker = ticker.upper()
    if not ticker.endswith(".IS"):
        ticker = f"{ticker}.IS"
    return ticker
