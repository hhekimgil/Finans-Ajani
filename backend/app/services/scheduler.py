"""Periyodik piyasa taramasi — APScheduler ile arka planda calisir."""

import asyncio
import logging
from datetime import datetime, timezone

from apscheduler.schedulers.background import BackgroundScheduler

from app.config import settings

logger = logging.getLogger(__name__)

_scheduler: BackgroundScheduler | None = None
_last_scan: dict | None = None


async def _scan_job() -> None:
    from app.agents import orchestrator
    from app.services import notifier

    logger.info("Periyodik hizli tarama basladi")
    try:
        # LLM'siz hizli fiyat taramasi (91+ hisse ~15s) — derin analiz talep uzerine
        results = orchestrator.scan_quick()
        global _last_scan
        _last_scan = {
            "results": results,
            "scanned_at": datetime.now(timezone.utc).isoformat(),
            "count": len(results),
        }
        sent = notifier.process_scan_results(results)
        if sent:
            logger.info("Telegram'a %s bildirim gonderildi", sent)
        logger.info("Tarama tamamlandi: %s hisse", len(results))
    except Exception as e:  # noqa: BLE001
        logger.error("Tarama hatasi: %s", e)


def start_scheduler() -> None:
    global _scheduler
    if _scheduler is not None:
        return
    _scheduler = BackgroundScheduler()
    _scheduler.add_job(
        lambda: asyncio.run(_scan_job()),
        "interval",
        seconds=settings.scan_interval,
        next_run_time=None,
        id="market_scan",
        max_instances=1,
        coalesce=True,
    )
    _scheduler.start()
    logger.info("Scheduler basladi (interval: %ss)", settings.scan_interval)


def stop_scheduler() -> None:
    global _scheduler
    if _scheduler:
        _scheduler.shutdown(wait=False)
        _scheduler = None


def get_last_scan() -> dict | None:
    return _last_scan
