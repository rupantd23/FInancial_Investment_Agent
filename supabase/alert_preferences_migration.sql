-- Per-user EOD Push alert settings for FINN.
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

alter table public.alert_preferences enable row level security;

drop policy if exists "alert preferences belong to current user" on public.alert_preferences;
create policy "alert preferences belong to current user" on public.alert_preferences
  for all to authenticated
  using ((select auth.uid()) = user_id)
  with check ((select auth.uid()) = user_id);

create or replace function public.set_alert_preferences_updated_at()
returns trigger
language plpgsql
as $$
begin
  new.updated_at = now();
  return new;
end;
$$;

drop trigger if exists set_alert_preferences_updated_at on public.alert_preferences;
create trigger set_alert_preferences_updated_at
before update on public.alert_preferences
for each row execute function public.set_alert_preferences_updated_at();
