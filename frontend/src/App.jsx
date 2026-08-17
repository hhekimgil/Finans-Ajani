import { useEffect, useRef, useState } from 'react'
import { createChart, ColorType, CandlestickSeries, LineSeries } from 'lightweight-charts'
import './App.css'

const API = 'http://127.0.0.1:8000'

const levelColors = {
  guclu: '#00c853',
  olumlu: '#69f0ae',
  notr: '#ffd740',
  olumsuz: '#ff6e40',
  zayif: '#ff1744',
}

const levelLabels = {
  guclu: 'GÜÇLÜ',
  olumlu: 'OLUMLU',
  notr: 'NÖTR',
  olumsuz: 'OLUMSUZ',
  zayif: 'ZAYIF',
}

function fmtPrice(v) {
  if (v == null) return '—'
  return v.toLocaleString('tr-TR', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
}

function ScoreBadge({ level, score }) {
  return (
    <span className="score-badge" style={{ borderColor: levelColors[level], color: levelColors[level] }}>
      {score}
      <small style={{ color: levelColors[level] }}>{levelLabels[level]}</small>
    </span>
  )
}

function ScoreBar({ score }) {
  return (
    <div className="score-bar">
      <div className="score-bar-fill" style={{ width: `${score}%`, background: score >= 55 ? 'var(--up)' : score >= 40 ? 'var(--accent)' : 'var(--down)' }} />
    </div>
  )
}

/* --- Canlı feed şeridi (marquee) --- */
function LiveFeed({ stocks }) {
  const items = stocks.slice()
  if (items.length < 2) return null
  const text = items
    .map((s) => {
      const up = (s.change_pct ?? 0) >= 0
      return `${s.ticker.replace('.IS', '')} ${fmtPrice(s.price)} ${up ? '▲' : '▼'}%${Math.abs(s.change_pct ?? 0).toFixed(2)}`
    })
    .join('   •   ')
  return (
    <div className="live-feed">
      <span className="live-tag">CANLI</span>
      <div className="live-track-wrap">
        <div className="live-track">
          <span className={items.every((s) => (s.change_pct ?? 0) >= 0) ? 'up' : 'dim'}>{text}</span>
        </div>
      </div>
    </div>
  )
}

/* --- Piyasa özeti kartları --- */
function MarketSummary({ stocks }) {
  const upCount = stocks.filter((s) => (s.change_pct ?? 0) >= 0).length
  const downCount = stocks.length - upCount
  const avg = stocks.length ? stocks.reduce((a, s) => a + (s.change_pct ?? 0), 0) / stocks.length : 0
  const best = stocks.length ? [...stocks].sort((a, b) => b.score - a.score)[0] : null
  const cards = [
    { label: 'Yükselen', value: upCount, color: 'var(--up)' },
    { label: 'Düşen', value: downCount, color: 'var(--down)' },
    { label: 'Ort. Değişim', value: `%${avg.toFixed(2)}`, color: avg >= 0 ? 'var(--up)' : 'var(--down)' },
    { label: 'En Yüksek Skor', value: best ? `${best.ticker.replace('.IS', '')} · ${best.score}` : '—', color: 'var(--accent)' },
  ]
  return (
    <div className="summary-grid">
      {cards.map((c) => (
        <div key={c.label} className="summary-card">
          <span className="summary-label">{c.label}</span>
          <span className="summary-value" style={{ color: c.color }}>{c.value}</span>
        </div>
      ))}
    </div>
  )
}

/* --- Profesyonel grafik (lightweight-charts) --- */
function PriceChart({ data, up }) {
  const ref = useRef(null)
  const chartRef = useRef(null)

  useEffect(() => {
    if (!ref.current || !data.length) return

    const chart = createChart(ref.current, {
      width: ref.current.clientWidth,
      height: 300,
      layout: {
        background: { type: ColorType.Solid, color: 'transparent' },
        textColor: '#7c8794',
        fontFamily: 'ui-monospace, Consolas, monospace',
        fontSize: 11,
      },
      grid: {
        vertLines: { color: 'rgba(35,46,61,0.5)' },
        horzLines: { color: 'rgba(35,46,61,0.5)' },
      },
      rightPriceScale: { borderColor: '#232e3d' },
      timeScale: { borderColor: '#232e3d', timeVisible: true },
      crosshair: {
        vertLine: { color: '#2dd4bf', width: 1, style: 0 },
        horzLine: { color: '#2dd4bf', width: 1, style: 0 },
      },
    })

    const candleSeries = chart.addSeries(CandlestickSeries, {
      upColor: '#00c853',
      downColor: '#ff1744',
      borderVisible: false,
      wickUpColor: '#00c853',
      wickDownColor: '#ff1744',
    })
    candleSeries.setData(
      data.map((d) => ({
        time: d.date,
        open: d.open,
        high: d.high,
        low: d.low,
        close: d.close,
      }))
    )

    const ma20 = []
    for (let i = 0; i < data.length; i++) {
      if (i < 19) continue
      const slice = data.slice(i - 19, i + 1)
      ma20.push({ time: data[i].date, value: +((slice.reduce((a, d) => a + d.close, 0) / 20).toFixed(2)) })
    }
    if (ma20.length) {
      const maSeries = chart.addSeries(LineSeries, { color: '#2dd4bf', lineWidth: 1, priceLineVisible: false })
      maSeries.setData(ma20)
    }

    const resize = () => chart.applyOptions({ width: ref.current.clientWidth })
    const ro = new ResizeObserver(resize)
    ro.observe(ref.current)

    chartRef.current = chart
    return () => {
      ro.disconnect()
      chart.remove()
      chartRef.current = null
    }
  }, [data])

  return <div ref={ref} className="price-chart" />
}

/* --- Hisse tablosu --- */
function StockTable({ stocks, onSelect, watchlist = [], onToggleWatch, sbReady }) {
  return (
    <table className="stock-table">
      <thead>
        <tr>
          <th></th>
          <th>Hisse</th>
          <th>Fiyat</th>
          <th>Değişim</th>
          <th>Hacim</th>
          <th>Analiz Skoru</th>
        </tr>
      </thead>
      <tbody>
        {stocks.map((s) => {
          const up = (s.change_pct ?? 0) >= 0
          const watched = watchlist.some((w) => w.ticker === s.ticker)
          return (
            <tr key={s.ticker} onClick={() => onSelect(s.ticker)} className="clickable">
              <td onClick={(e) => { e.stopPropagation(); if (sbReady) onToggleWatch(s.ticker) }} className="watch-col">
                <button className={`star ${watched ? 'active' : ''}`} title={watched ? 'Takipten çıkar' : 'Takibe ekle'} disabled={!sbReady}>
                  {watched ? '★' : '☆'}
                </button>
              </td>
              <td>
                <span className="ticker">{s.ticker.replace('.IS', '')}</span>
                <span className="name">{s.name}</span>
              </td>
              <td className="mono">{fmtPrice(s.price)} ₺</td>
              <td className={up ? 'up' : 'down'}>
                {up ? '▲' : '▼'} %{Math.abs(s.change_pct ?? 0).toFixed(2)}
              </td>
              <td className="mono dim">{s.volume ? s.volume.toLocaleString('tr-TR') : '—'}</td>
              <td>
                <div className="score-cell">
                  <ScoreBar score={s.score} />
                  <ScoreBadge level={s.level} score={s.score} />
                </div>
              </td>
            </tr>
          )
        })}
      </tbody>
    </table>
  )
}

/* --- Detay görünümü --- */
function DetailView({ ticker, onBack }) {
  const [data, setData] = useState(null)
  const [analysis, setAnalysis] = useState(null)
  const [period, setPeriod] = useState('6mo')
  const [loading, setLoading] = useState(true)
  const [analyzing, setAnalyzing] = useState(false)

  useEffect(() => {
    setLoading(true)
    fetch(`${API}/api/stocks/${ticker}?period=${period}`)
      .then((r) => r.json())
      .then((d) => setData(d))
      .catch((e) => console.error(e))
      .finally(() => setLoading(false))
  }, [ticker, period])

  const runAnalysis = () => {
    setAnalyzing(true)
    fetch(`${API}/api/analyze/${ticker}`)
      .then((r) => r.json())
      .then((d) => setAnalysis(d))
      .catch((e) => console.error(e))
      .finally(() => setAnalyzing(false))
  }

  if (loading) return <div className="loading">Yükleniyor…</div>

  const q = data.quote
  const a = data.analysis
  const up = (q.change_pct ?? 0) >= 0

  return (
    <div className="detail">
      <button className="back" onClick={onBack}>← Listeye Dön</button>
      <div className="detail-header">
        <div>
          <h2>{q.name}</h2>
          <span className="ticker big">{q.ticker}</span>
        </div>
        <div className="detail-price">
          <span className="mono price-big">{fmtPrice(q.price)} ₺</span>
          <span className={up ? 'up' : 'down'}>
            {up ? '▲' : '▼'} %{Math.abs(q.change_pct ?? 0).toFixed(2)}
          </span>
        </div>
        <ScoreBadge level={analysis?.level ?? a.level} score={analysis?.score ?? a.score} />
      </div>

      <div className="panel">
        <div className="chart-head">
          <h3>Yapay Zeka Analizi</h3>
          <button className="refresh" onClick={runAnalysis} disabled={analyzing}>
            {analyzing ? 'Analiz ediliyor…' : '⟳ Analizi Çalıştır'}
          </button>
        </div>
        {analysis ? (
          <>
            {analysis.comment && <p className="analysis-comment">{analysis.comment}</p>}
            <div className="agent-grid">
              <AgentCard
                title="Haber Analizi"
                sentiment={analysis.news.sentiment}
                score={analysis.news.score}
                detail={`${analysis.news.headlines?.length ?? 0} haber`}
                items={analysis.news.headlines?.slice(0, 5)}
              />
              <AgentCard
                title="Piyasa Duyarlılığı"
                sentiment={analysis.sentiment.sentiment}
                score={analysis.sentiment.score}
                detail={`${analysis.sentiment.comment_count ?? 0} yorum`}
                pos={analysis.sentiment.positive}
                neg={analysis.sentiment.negative}
              />
              <AgentCard
                title="Teknik Göstergeler"
                sentiment={null}
                score={null}
                items={[
                  analysis.indicators.rsi14 != null ? `RSI(14): ${analysis.indicators.rsi14}` : null,
                  analysis.indicators.ma20 != null ? `MA20: ${fmtPrice(analysis.indicators.ma20)}` : null,
                  analysis.indicators.ma50 != null ? `MA50: ${fmtPrice(analysis.indicators.ma50)}` : null,
                  analysis.indicators.volume_ratio != null ? `Hacim Oranı: ${analysis.indicators.volume_ratio}x` : null,
                ].filter(Boolean)}
                note={analysis.indicators.comment}
              />
              <AgentCard
                title="Makro Görünüm"
                sentiment={null}
                score={null}
                items={Object.values(analysis.macro.rates).map((r) => `${r.name}: ${fmtPrice(r.sell)}`)}
                note={analysis.macro.summary}
              />
            </div>
          </>
        ) : (
          <p className="dim">Analiz çalıştırıldığında haber, duyarlılık, teknik göstergeler ve makro görünüm burada listelenir.</p>
        )}
      </div>

      <div className="panel">
        <div className="chart-head">
          <h3>Fiyat Grafiği</h3>
          <div className="periods">
            {['1mo', '3mo', '6mo', '1y'].map((p) => (
              <button key={p} className={p === period ? 'active' : ''} onClick={() => setPeriod(p)}>
                {p}
              </button>
            ))}
          </div>
        </div>
        <PriceChart data={data.history} up={up} />
      </div>

      <div className="panel">
        <h3>Analiz Gerekçesi</h3>
        <ul className="reasons">
          {a.reasons.map((r, i) => (
            <li key={i}>{r}</li>
          ))}
        </ul>
      </div>
    </div>
  )
}

function AgentCard({ title, sentiment, score, detail, items, note, pos, neg }) {
  const col = sentiment ? levelColors[sentimentMap[sentiment] ?? 'notr'] : null
  return (
    <div className="agent-card">
      <div className="agent-head">
        <span className="agent-title">{title}</span>
        {sentiment && (
          <span className="agent-score" style={{ color: col }}>
            {sentiment} {score != null ? `· ${score}` : ''}
          </span>
        )}
        {detail && <span className="dim">{detail}</span>}
      </div>
      {items && items.length > 0 && (
        <ul className="agent-items">
          {items.map((it, i) => it && <li key={i}>{it}</li>)}
        </ul>
      )}
      {pos && pos.length > 0 && (
        <div className="sentiment-block">
          <span className="sent-pos">▲ {pos[0]}</span>
        </div>
      )}
      {neg && neg.length > 0 && (
        <div className="sentiment-block">
          <span className="sent-neg">▼ {neg[0]}</span>
        </div>
      )}
      {note && <p className="agent-note">{note}</p>}
    </div>
  )
}

const sentimentMap = { olumlu: 'olumlu', olumsuz: 'olumsuz', notr: 'notr', pozitif: 'olumlu', negatif: 'olumsuz' }

/* --- Ana uygulama --- */
function App() {
  const [stocks, setStocks] = useState([])
  const [selected, setSelected] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [updatedAt, setUpdatedAt] = useState(null)
  const [watchlist, setWatchlist] = useState([])
  const [history, setHistory] = useState([])
  const [sbReady, setSbReady] = useState(false)
  const [toolMsg, setToolMsg] = useState(null)
  const [bistLoading, setBistLoading] = useState(false)
  const [query, setQuery] = useState('')
  const [searchResults, setSearchResults] = useState([])
  const [searching, setSearching] = useState(false)

  const flash = (msg, isErr = false) => {
    setToolMsg({ text: msg, isErr })
    setTimeout(() => setToolMsg(null), 6000)
  }

  const load = () => {
    fetch(`${API}/api/stocks`)
      .then((r) => {
        if (!r.ok) throw new Error(`HTTP ${r.status}`)
        return r.json()
      })
      .then((d) => {
        setStocks(d.stocks)
        setUpdatedAt(new Date())
        setError(null)
      })
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false))
  }

  const loadWatchlist = () => {
    fetch(`${API}/api/watchlist`)
      .then((r) => r.json())
      .then((d) => setWatchlist(d.watchlist || []))
      .catch(() => {})
  }

  const loadHistory = () => {
    fetch(`${API}/api/history?limit=10`)
      .then((r) => r.json())
      .then((d) => setHistory(d.history || []))
      .catch(() => {})
  }

  useEffect(() => {
    load()
    fetch(`${API}/api/supabase/status`)
      .then((r) => r.json())
      .then((d) => {
        setSbReady(d.ready)
        if (d.ready) {
          loadWatchlist()
          loadHistory()
        }
      })
      .catch(() => setSbReady(false))
    const timer = setInterval(load, 60000)
    return () => clearInterval(timer)
  }, [])

  const openStock = (ticker) => {
    setSelected(ticker)
    if (sbReady) {
      fetch(`${API}/api/history/${ticker}`, { method: 'POST' }).catch(() => {})
      loadHistory()
    }
  }

  const toggleWatchlist = (ticker) => {
    if (!sbReady) return
    const inList = watchlist.some((w) => w.ticker === ticker)
    const opts = { method: inList ? 'DELETE' : 'POST' }
    fetch(`${API}/api/watchlist/${ticker}`, opts)
      .then(() => loadWatchlist())
      .catch(() => {})
  }

  const addBist100 = () => {
    if (!sbReady) {
      flash('Supabase bağlı değil — önce supabase_schema.sql çalıştırılmalı', true)
      return
    }
    setBistLoading(true)
    fetch(`${API}/api/tickers/batch?from_bist100=true&validate=true`)
      .then((r) => r.json().then((d) => ({ ok: r.ok, d })))
      .then(({ ok, d }) => {
        if (!ok) throw new Error(d.detail || 'Ekleme başarısız')
        flash(`BIST 100 eklendi: ${d.added} hisse, ${d.invalid_count} geçersiz`)
        load()
      })
      .catch((e) => flash(e.message, true))
      .finally(() => setBistLoading(false))
  }

  const doSearch = (e) => {
    const q = e.target.value
    setQuery(q)
    if (!q.trim()) {
      setSearchResults([])
      return
    }
    setSearching(true)
    fetch(`${API}/api/search?q=${encodeURIComponent(q.trim())}`)
      .then((r) => r.json())
      .then((d) => setSearchResults(d.found ? [d] : []))
      .catch(() => setSearchResults([]))
      .finally(() => setSearching(false))
  }

  const addFound = (res) => {
    if (!sbReady) {
      flash('Supabase bağlı değil', true)
      return
    }
    fetch(`${API}/api/tickers/${res.ticker}`, { method: 'POST' })
      .then((r) => r.json().then((d) => ({ ok: r.ok, d })))
      .then(({ ok, d }) => {
        if (!ok) throw new Error(d.detail || 'Ekleme başarısız')
        flash(`${res.name} (${res.ticker}) eklendi`)
        setQuery('')
        setSearchResults([])
        load()
      })
      .catch((e) => flash(e.message, true))
  }

  return (
    <div className="app">
      <header className="topbar">
        <div className="brand">
          <span className="logo-dot" /> Finansal Asistan
        </div>
        <div className="topbar-right">
          {updatedAt && <span className="dim">Son güncelleme: {updatedAt.toLocaleTimeString('tr-TR')}</span>}
          <button className="refresh" onClick={load}>⟳ Yenile</button>
        </div>
      </header>

      <LiveFeed stocks={stocks} />

      {selected ? (
        <DetailView ticker={selected} onBack={() => setSelected(null)} />
      ) : (
        <main>
          <div className="hero-line">
            <h1>Piyasa Taraması</h1>
            <p className="dim">{stocks.length} BIST hissesi — yapay zeka analiz skoruna göre sıralı</p>
          </div>

          <div className="toolbar">
            <div className="search-box">
              <input
                type="text"
                value={query}
                onChange={doSearch}
                placeholder="Hisse ekle (örn. KCHOL, TUPRS, SASA)"
                className="search-input"
              />
              {searching && <span className="dim small">aranıyor…</span>}
              {searchResults.length > 0 && (
                <div className="search-drop">
                  {searchResults.map((r) => (
                    <button key={r.ticker} className="search-item" onClick={() => addFound(r)}>
                      <span className="ticker">{r.ticker.replace('.IS', '')}</span>
                      <span className="name">{r.name}</span>
                      <span className="dim mono">{fmtPrice(r.price)} ₺</span>
                      <span className="add-hint">+ Ekle</span>
                    </button>
                  ))}
                </div>
              )}
            </div>
            <button className="refresh bist-btn" onClick={addBist100} disabled={bistLoading}>
              {bistLoading ? 'Ekleniyor…' : '📥 BIST 100\'ü Ekle'}
            </button>
          </div>

          {toolMsg && <div className={toolMsg.isErr ? 'error' : 'tool-msg'}>{toolMsg.text}</div>}

          {error && <div className="error">Sunucuya ulaşılamadı: {error}. Backend'i başlatın (uvicorn app.main:app).</div>}

          {!loading && stocks.length > 0 && <MarketSummary stocks={stocks} />}

          <div className="panel">
            {loading ? <div className="loading">Yükleniyor…</div> : (
              <StockTable stocks={stocks} onSelect={openStock} watchlist={watchlist} onToggleWatch={toggleWatchlist} sbReady={sbReady} />
            )}
          </div>

          {sbReady && (
            <WatchlistPanel watchlist={watchlist} history={history} stocks={stocks} onSelect={openStock} onToggleWatch={toggleWatchlist} />
          )}
        </main>
      )}
    </div>
  )
}

function WatchlistPanel({ watchlist, history, stocks, onSelect, onToggleWatch }) {
  const priceOf = (t) => {
    const s = stocks.find((x) => x.ticker === t)
    return s ? `${fmtPrice(s.price)} ₺` : '—'
  }
  return (
    <div className="wl-grid">
      <div className="panel wl-panel">
        <h3>Watchlist</h3>
        {watchlist.length === 0 ? (
          <p className="dim small">Hisse satırındaki ⭐ ile takibe ekleyin.</p>
        ) : (
          <ul className="wl-list">
            {watchlist.map((w) => (
              <li key={w.ticker}>
                <button className="wl-name" onClick={() => onSelect(w.ticker)}>
                  <span className="ticker">{w.ticker.replace('.IS', '')}</span>
                  <span className="wl-price">{priceOf(w.ticker)}</span>
                </button>
                <button className="wl-remove" onClick={() => onToggleWatch(w.ticker)} title="Takipten çıkar">✕</button>
              </li>
            ))}
          </ul>
        )}
      </div>
      <div className="panel wl-panel">
        <h3>Son Aramalar</h3>
        {history.length === 0 ? (
          <p className="dim small">Henüz arama yapılmadı.</p>
        ) : (
          <ul className="wl-list">
            {history.map((h, i) => (
              <li key={`${h.ticker}-${i}`}>
                <button className="wl-name" onClick={() => onSelect(h.ticker)}>
                  <span className="ticker">{h.ticker.replace('.IS', '')}</span>
                  <span className="dim small">{h.searched_at ? new Date(h.searched_at).toLocaleTimeString('tr-TR') : ''}</span>
                </button>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  )
}

export default App
