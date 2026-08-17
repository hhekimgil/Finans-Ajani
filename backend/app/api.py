from fastapi import APIRouter, HTTPException, Query

from app.agents import orchestrator
from app.services import supabase_db, telegram
from app.services.bist import BISTService, load_bist100_tickers
from app.services.scheduler import get_last_scan
from app.services.scoring import compute_score

router = APIRouter(prefix="/api", tags=["api"])
bist = BISTService()


@router.get("/ping")
def ping() -> dict:
    return {"message": "pong"}


@router.get("/stocks")
def list_stocks() -> dict:
    """Anlik fiyat + temel skor ile hisse listesi (skora gore sirali).

    BIST 100'deki tum hisseler tek yfinance istegiyle cekilir.
    """
    tickers = supabase_db.get_scanned_tickers()
    quotes = bist.get_batch_quotes(tickers)
    results = []
    for ticker, quote in quotes.items():
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


# --- Taranacak hisse listesi ---

@router.get("/tickers")
def list_tickers() -> dict:
    """Taranacak hisse listesini dondurur (Supabase; bos ise config fallback)."""
    tickers = supabase_db.get_scanned_tickers()
    return {"count": len(tickers), "tickers": tickers, "source": "supabase" if supabase_db.is_ready() else "config"}


@router.post("/tickers/batch")
def batch_add_tickers(
    tickers: list[str] | None = None,
    from_bist100: bool = Query(False),
    validate: bool = Query(True),
) -> dict:
    """Tarama listesine toplu hisse ekler.

    - tickers verilirse onlari ekler (dogrulama ile).
    - from_bist100=True ise data/bist100.json listesini dogrular ve ekler.
    """
    if not supabase_db.is_ready():
        raise HTTPException(status_code=503, detail="Supabase bagli degil")

    if from_bist100 or not tickers:
        candidates = load_bist100_tickers()
    else:
        candidates = [_normalize(t) for t in tickers]

    if not candidates:
        raise HTTPException(status_code=400, detail="Eklenecek sembol yok")

    valid: list[str] = []
    invalid: list[str] = []
    if validate:
        valid, invalid = bist.validate_many(candidates)
    else:
        valid = candidates

    added = 0
    for t in valid:
        if supabase_db.add_scanned_ticker(t):
            added += 1

    return {
        "ok": added > 0,
        "candidates": len(candidates),
        "added": added,
        "invalid": invalid,
        "invalid_count": len(invalid),
    }


@router.post("/tickers/{ticker}")
def add_ticker(ticker: str) -> dict:
    """Tarama listesine hisse ekler (BIST sembolu dogrulanir)."""
    ticker = _normalize(ticker)
    quote = bist.get_quote(ticker)
    if not quote:
        raise HTTPException(status_code=404, detail=f"{ticker} icin veri bulunamadi (sembolu kontrol edin)")
    if not supabase_db.is_ready():
        raise HTTPException(status_code=503, detail="Supabase bagli degil")
    row = supabase_db.add_scanned_ticker(ticker)
    return {"ok": row is not None, "record": row, "name": quote["name"]}


@router.delete("/tickers/{ticker}")
def remove_ticker(ticker: str) -> dict:
    """Tarama listesinden hisse cikarir."""
    ticker = _normalize(ticker)
    ok = supabase_db.remove_scanned_ticker(ticker)
    return {"ok": ok}


@router.get("/search")
def search_stock(q: str = Query(..., min_length=1)) -> dict:
    """BIST sembolu dogrular: 'THYAO' -> THYAO.IS, fiyat + isim dondurur."""
    raw = q.strip().upper().replace(" ", "")
    if not raw.endswith(".IS"):
        raw = f"{raw}.IS"
    quote = bist.get_quote(raw)
    if not quote:
        return {"found": False, "query": q, "suggested": raw}
    return {"found": True, "ticker": raw, "name": quote["name"], "price": quote["price"]}


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
