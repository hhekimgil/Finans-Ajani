-- Finansal Asistan — Supabase şeması
-- Supabase Dashboard > SQL Editor > New query içine yapıştırıp "Run" deyin.

-- 1) Arama geçmişi
create table if not exists public.search_history (
  id bigint generated always as identity primary key,
  user_id text not null default 'local',
  ticker text not null,
  searched_at timestamptz not null default now()
);
create index if not exists search_history_user_idx on public.search_history (user_id, searched_at desc);

-- 2) Watchlist
create table if not exists public.watchlist (
  id bigint generated always as identity primary key,
  user_id text not null default 'local',
  ticker text not null,
  added_at timestamptz not null default now(),
  unique (user_id, ticker)
);

-- 3) Tarama sonuçları (her hisse için en güncel analiz)
create table if not exists public.scan_results (
  ticker text primary key,
  name text,
  price numeric,
  change_pct numeric,
  score numeric,
  level text,
  comment text,
  news_sentiment text,
  news_score numeric,
  sentiment text,
  sentiment_score numeric,
  rsi14 numeric,
  raw jsonb,
  scanned_at timestamptz not null default now()
);
create index if not exists scan_results_score_idx on public.scan_results (score desc);

-- RLS: geliştirme aşamasında herkese açık okuma/yazma (projeyi canlıya alırken kısıtlayın)
alter table public.search_history enable row level security;
alter table public.watchlist enable row level security;
alter table public.scan_results enable row level security;

drop policy if exists "public read" on public.search_history;
drop policy if exists "public write" on public.search_history;
drop policy if exists "public read" on public.watchlist;
drop policy if exists "public write" on public.watchlist;
drop policy if exists "public read" on public.scan_results;
drop policy if exists "public write" on public.scan_results;
drop policy if exists "public insert" on public.scan_results;
drop policy if exists "public update" on public.scan_results;

create policy "public read" on public.search_history for select using (true);
create policy "public write" on public.search_history for insert with check (true);
create policy "public read" on public.watchlist for select using (true);
create policy "public write" on public.watchlist for insert with check (true);
create policy "public write2" on public.watchlist for delete using (true);
create policy "public read" on public.scan_results for select using (true);
create policy "public insert" on public.scan_results for insert with check (true);
create policy "public update" on public.scan_results for update using (true) with check (true);
