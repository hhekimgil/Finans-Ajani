# Finansal Asistan

Claude Code Eğitimi videosundaki finansal asistan uygulamasının birebir yeniden üretimi.
BIST hisseleri için yapay zeka destekli analiz, sıralama ve Telegram bildirim sistemi.

## Özellikler
- **BIST hisse taraması** — canlı fiyat, değişim, hacim (yfinance `.IS` sembolleri)
- **Yapay zeka analizi** — 4 uzman agent (haber, duyarlılık, teknik göstergeler, makro) + orchestrator
- **Analiz skoru** — her hisse için 0-100 skor, seviye (güçlü/olumlu/nötr/olumsuz/zayıf)
- **LLM** — yerel Ollama (`qwen3-14b-tr`) ile ücretsiz Türkçe haber/yorum analizi
- **Telegram bildirimi** — kritik sinyallerde telefona uyarı (büyük hareket, negatif haber, aşırı RSI)
- **Şık dashboard** — canlı feed, piyasa özeti, profesyonel grafik (lightweight-charts)

## Mimari
```
[Veri Kaynakları] yfinance/BIST · Google News/KAP · TCMB · Reddit
        │
        ▼
[Agent'lar]  news_agent · sentiment_agent · indicator_agent · macro_agent
        │
        ▼
[Orchestrator]  → analiz skoru (0-100) → sıralama
        │
        ├── [Supabase]  arama geçmişi, watchlist, sonuçlar (opsiyonel)
        ├── [Frontend]  React dashboard, canlı feed, grafik
        └── [Telegram]  kritik sinyal bildirimleri
```

## Kurulum

### Backend
```bash
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env   # ve gerekli değerleri doldurun
uvicorn app.main:app --reload
```

### Frontend
```bash
cd frontend
npm install
npm run dev
```

### Ollama
```bash
ollama pull qwen3-14b-tr
```

## Ortam Değişkenleri
| Değişken | Açıklama |
|---|---|
| `OLLAMA_MODEL` | Yerel LLM modeli (varsayılan `qwen3-14b-tr`) |
| `BIST_TICKERS` | Virgülle ayrılmış `.IS` sembolleri |
| `TELEGRAM_BOT_TOKEN` | BotFather'dan alınan bot token |
| `TELEGRAM_CHAT_ID` | Sohbet ID'si (`getUpdates` ile bulunur) |
| `SUPABASE_URL` / `SUPABASE_ANON_KEY` | Supabase projesi (opsiyonel) |
| `SCAN_INTERVAL` | Tarama sıklığı (saniye) |

## API
| Endpoint | Açıklama |
|---|---|
| `GET /api/stocks` | Hisse listesi + temel skor |
| `GET /api/stocks/{ticker}` | Hisse detayı + grafik verisi |
| `GET /api/analyze/{ticker}` | Tam yapay zeka analizi |
| `GET /api/analyze` | Tüm hisseleri tarar |
| `POST /api/telegram/test` | Deneme bildirimi gönderir |

## Not
Bu uygulama yatırım tavsiyesi vermez; yalnızca verileri analiz eder ve sunar.
