-- FINN persistence blueprint.
-- Run this in a Supabase project only after reviewing the tenant/auth setup.

create extension if not exists vector with schema extensions;

create table if not exists public.companies (
  id uuid primary key default gen_random_uuid(),
  ticker text not null unique,
  bse_code text,
  name text not null,
  sector text,
  created_at timestamptz not null default now()
);

create table if not exists public.portfolio_companies (
  tenant_id uuid not null references auth.users(id) on delete cascade,
  company_id uuid not null references public.companies(id) on delete cascade,
  created_at timestamptz not null default now(),
  primary key (tenant_id, company_id)
);

create table if not exists public.market_daily (
  company_id uuid not null references public.companies(id) on delete cascade,
  trading_date date not null,
  close numeric,
  volume numeric,
  source text not null default 'yfinance',
  provenance text not null default 'verified',
  primary key (company_id, trading_date)
);

create table if not exists public.alert_preferences (
  user_id uuid primary key references auth.users(id) on delete cascade,
  enabled boolean not null default true,
  price_rise_threshold numeric not null default 5 check (price_rise_threshold >= 0.5 and price_rise_threshold <= 50),
  price_fall_threshold numeric not null default 5 check (price_fall_threshold >= 0.5 and price_fall_threshold <= 50),
  volume_multiplier numeric not null default 2 check (volume_multiplier >= 1 and volume_multiplier <= 20),
  material_filings text[] not null default '{results,m&a,fund_raise,management,legal_regulatory,earnings_call}',
  watched_scope text not null default 'portfolio' check (watched_scope in ('portfolio', 'selected')),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists public.source_documents (
  id uuid primary key default gen_random_uuid(),
  tenant_id uuid references auth.users(id) on delete cascade,
  company_id uuid references public.companies(id) on delete cascade,
  source_type text not null check (source_type in ('announcement', 'annual_report', 'earnings_call_transcript', 'market_data')),
  title text not null,
  source_url text,
  storage_path text,
  published_at timestamptz,
  provenance text not null check (provenance in ('verified', 'cached', 'synthetic_demo', 'unavailable')),
  checksum text,
  created_at timestamptz not null default now()
);

create table if not exists public.document_chunks (
  id uuid primary key default gen_random_uuid(),
  document_id uuid not null references public.source_documents(id) on delete cascade,
  page_number integer,
  section_label text,
  content text not null,
  embedding extensions.vector(1536),
  created_at timestamptz not null default now()
);

create index if not exists document_chunks_document_idx on public.document_chunks(document_id);
create index if not exists source_documents_company_idx on public.source_documents(company_id, source_type);

create table if not exists public.network_people (
  id uuid primary key default gen_random_uuid(),
  tenant_id uuid references auth.users(id) on delete cascade,
  display_name text not null,
  email text,
  role_title text,
  company_name text,
  sector text,
  skills text[] not null default '{}',
  linkedin_url text,
  relationship text,
  notes text,
  provenance text not null check (provenance in ('verified', 'synthetic_demo', 'csv_import', 'manual', 'linkedin')),
  consent_status text not null default 'demo_only',
  source_label text,
  created_at timestamptz not null default now()
);

create table if not exists public.network_evidence (
  id uuid primary key default gen_random_uuid(),
  person_id uuid not null references public.network_people(id) on delete cascade,
  company_id uuid references public.companies(id) on delete cascade,
  evidence_type text not null,
  detail text not null,
  source text not null,
  confidence numeric check (confidence >= 0 and confidence <= 1),
  created_at timestamptz not null default now()
);

create index if not exists network_people_company_idx on public.network_people(company_name);
create index if not exists network_people_sector_idx on public.network_people(sector);
create index if not exists network_people_skills_idx on public.network_people using gin(skills);
create index if not exists network_people_tenant_idx on public.network_people(tenant_id);
create index if not exists network_evidence_person_idx on public.network_evidence(person_id);

create table if not exists public.person_employments (
  person_id uuid not null references public.network_people(id) on delete cascade,
  company_name text not null,
  start_year integer,
  end_year integer,
  relationship_type text not null default 'professional_overlap',
  primary key (person_id, company_name, start_year)
);

create table if not exists public.person_education (
  person_id uuid not null references public.network_people(id) on delete cascade,
  institution text not null,
  start_year integer,
  end_year integer,
  primary key (person_id, institution, start_year)
);

create table if not exists public.analysis_runs (
  id uuid primary key default gen_random_uuid(),
  tenant_id uuid references auth.users(id) on delete cascade,
  company_id uuid references public.companies(id) on delete cascade,
  model_name text,
  allowed_source_types text[] not null default '{annual_report,earnings_call_transcript}',
  output_json jsonb not null,
  status text not null default 'complete',
  created_at timestamptz not null default now()
);

alter table public.portfolio_companies enable row level security;
alter table public.alert_preferences enable row level security;
alter table public.network_people enable row level security;
alter table public.network_evidence enable row level security;
alter table public.person_employments enable row level security;
alter table public.person_education enable row level security;
alter table public.analysis_runs enable row level security;

create policy "portfolio belongs to current user" on public.portfolio_companies
  for all using (tenant_id = auth.uid()) with check (tenant_id = auth.uid());
create policy "alert preferences belong to current user" on public.alert_preferences
  for all to authenticated
  using ((select auth.uid()) = user_id)
  with check ((select auth.uid()) = user_id);
create policy "network belongs to current user" on public.network_people
  for all to authenticated
  using ((select auth.uid()) = tenant_id)
  with check ((select auth.uid()) = tenant_id);
create policy "network evidence belongs to current user" on public.network_evidence
  for all to authenticated
  using (exists (select 1 from public.network_people p where p.id = person_id and p.tenant_id = (select auth.uid())))
  with check (exists (select 1 from public.network_people p where p.id = person_id and p.tenant_id = (select auth.uid())));
create policy "employment follows person tenant" on public.person_employments
  for all using (exists (select 1 from public.network_people p where p.id = person_id and p.tenant_id = auth.uid()))
  with check (exists (select 1 from public.network_people p where p.id = person_id and p.tenant_id = auth.uid()));
create policy "education follows person tenant" on public.person_education
  for all using (exists (select 1 from public.network_people p where p.id = person_id and p.tenant_id = auth.uid()))
  with check (exists (select 1 from public.network_people p where p.id = person_id and p.tenant_id = auth.uid()));
create policy "analysis belongs to current user" on public.analysis_runs
  for all using (tenant_id = auth.uid()) with check (tenant_id = auth.uid());
