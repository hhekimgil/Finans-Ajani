# Finansal Asistan — Görev Takibi

Kaynak video: https://www.youtube.com/watch?v=twkgnt7QT3g
(Claude Code Eğitimi — Finansal Asistan uygulaması, birebir yeniden üretim)

## Teknoloji Kararları
- Backend: Python FastAPI
- Frontend: React + Vite (lightweight-charts)
- Veritabanı: Supabase (PostgreSQL)
- LLM: Ollama (yerel, `qwen3-14b-tr` — Türkçe analiz)
- Bildirim: Telegram Bot
- Veri: TCMB (kur), yfinance (BIST .IS), Reddit API, KAP/RSS

## Fazlar
- [x] Karar & plan onayı
- [x] Faz 0: Proje iskeleti (backend + frontend + env)
- [x] Faz 1: Çalışan MVP (liste + skor + detay)
- [x] Faz 2: Agent katmanı (news/sentiment/indicator/macro + orchestrator)
- [x] Faz 3: Supabase entegrasyonu
- [x] Faz 4: Telegram bildirim
- [x] Faz 5: Frontend cilası
- [x] Faz 6: GitHub yedek + yayın
- [x] BIST 100 tam liste: bist100.json + doğrulama + batch yükleme (91 hisse Supabase'de) + arama kutusu + "BIST 100'ü Ekle" butonu

## Notlar / Engeller
- BIST için ücretsiz API sınırlı; yfinance .IS birincil, BigPara JSON alternatif.
- KAP haberlerinde scraping yerine RSS/API tercih.
- X/Twitter ücretsiz kısıtlı; Reddit + Investing.com ana sentiment kaynağı.
