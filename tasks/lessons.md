# Finans Ajanı — Oturum Dersleri

## 17.08.2026

1. **Ollama bağlantısı:** Python `ollama` client'ı `localhost`'u IPv6 (`::1`) olarak çözümlüyor, Ollama yalnız IPv4 dinliyor → bağlantı hatası. Çözüm: `127.0.0.1` kullan ve ortam değişkeni `OLLAMA_HOST=0.0.0.0:11434` config'i override ediyorsa host'u normalize et (llm.py `_get_client`: scheme ekle + `0.0.0.0`→`127.0.0.1`).
2. **Ollama timeout:** Model ilk yükleme uzun sürebilir → `Client(timeout=600)` verilmezse "Failed to connect" hatası alınır.
3. **Telegram chat_id:** `getUpdates` boş dönerse bot ile kullanıcı önce `/start` yazmalı (bot kullanıcıya mesaj gönderebilmek için önce kullanıcının botla konuşması gerekir). Chat_id `private` tipindeki `message.chat.id`'dir.
4. **Git kimliği:** Yeni repo'da `user.name`/`user.email` tanımlı değilse commit başarısız → önce global/config kontrolü, GitHub kullanıcı adıyla `@users.noreply.github.com` formatı.
5. **Vite şablonu:** `npm create vite` varsayılan şablonu (App.jsx/App.css/index.css) temizlenmeli; lightweight-charts v5 API'si `addSeries(CandlestickSeries, ...)` şeklinde.
6. **Senkron/asenkron:** FastAPI endpoint'i `async` ise orchestrator `asyncio.gather` ile 4 agent'ı paralel koşar (sıralı çağrı 4x yavaş olurdu).
7. **Windows konsol kodlaması:** Türkçe karakterler konsolda bozuk görünebilir (veri değil, gösterim); `-X utf8` ile test çıktısı düzgün alınır.
