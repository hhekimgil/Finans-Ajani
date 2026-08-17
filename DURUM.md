# Finans Ajanı — Durum Takibi

## Proje
Claude Code eğitim videosundaki "Finansal Asistan" uygulamasının birebir yeniden üretimi.
Konum: `C:\Users\user\Desktop\AI_Projelerim\Finans Ajanı`

## Tamamlanan
- [x] Faz 0: Backend (FastAPI) + Frontend (Vite/React) iskeleti
- [x] Faz 1: BIST hisse listesi + temel skorlama + liste/detay
- [x] Faz 2: 4 uzman agent + orchestrator (Ollama `qwen3-14b-tr`), periyodik tarama
- [x] Faz 3: Supabase entegrasyonu — proje `Finans-Ajani` (`wsqavjwqwxcyxenakqoz`), 3 tablo (search_history/watchlist/scan_results), frontend'de ⭐ watchlist + son aramalar paneli, tarama sonuçları DB'ye kayıt
- [x] Faz 4: Telegram bildirim (@groq_hheki_bot → chat 8931340958)
- [x] Faz 5: Canlı feed, piyasa özeti, lightweight-charts grafik
- [x] Faz 6: GitHub'a push (hhekimgil/Finans-Ajani)
- [x] BIST 100: `backend/data/bist100.json` (94 aday) + doğrulama + `POST /api/tickers/batch` → Supabase `scanned_tickers`'a **91 hisse** yüklendi (KOZAA/KOZAL/TRKCM geçersiz elendi). Frontend: arama kutusu + "📥 BIST 100'ü Ekle" butonu.
- [x] VERİ KAYNAĞI YENİDEN YAZIMI: **yfinance 1.6.0 Yahoo'nun yeni API'siyle uyumsuzdu** (veri dönmüyordu, "possibly delisted" hatası) → `bist.py` ham **Yahoo v8 chart API** (`query1.finance.yahoo.com/v8/finance/chart`) üzerine yeniden yazıldı (httpx + ThreadPoolExecutor). Sonuç: batch 91 hisse **~3s** (eski yfinance ~40s), `/api/stocks` ~25s, `scan_quick` ~33s. `yfinance`/`pandas`/`requests` requirements'tan kaldırıldı.
- [x] Scheduler optimize: `SCAN_INTERVAL` artık **LLM'siz hızlı tarama** (`scan_quick`, ~33s/91 hisse) yapar — derin Ollama analizi yalnızca hisseye tıklanınca çalışır (kullanıcının "talep üzerine derin analiz" seçimi).

## Bekleyen
- [ ] Faz 6b: Canlıya alma (hosting) — adımlar hazır, yapılmadı

## Çalıştırma
- Backend: `backend\.venv\Scripts\python.exe -m uvicorn app.main:app` (port 8000)
- Frontend: `cd frontend; npm run dev` (port 5173)
- Ollama servisi açık olmalı (port 11434)

## Notlar
- Ollama bağlantı sorunu: `localhost` IPv6'ya çözümleniyor; `127.0.0.1` + `0.0.0.0` normalize edildi (llm.py `_get_client`)
- `.env` dosyası `.gitignore`'da — GitHub'a gitmez (Supabase/Telegram anahtarları içerir)
- Ortam değişkeni `OLLAMA_HOST=0.0.0.0:11434` config'i override ediyor; llm.py bunu `127.0.0.1`'e çevirir
- Supabase RLS politikaları "geliştirme aşaması herkese açık" modda — canlıya alırken kısıtlanmalı
- Supabase şeması `backend/supabase_schema.sql` (upsert politikası insert+update olarak düzeltildi)
- Supabase anahtarları `.env` içinde: `https://wsqavjwqwxcyxenakqoz.supabase.co`
