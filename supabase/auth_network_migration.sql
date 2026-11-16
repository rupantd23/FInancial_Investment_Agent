-- Run once in Supabase SQL Editor for an existing FINN project.
-- Supabase Auth owns accounts in auth.users; FINN stores only user-owned rows.

create index if not exists network_people_tenant_idx
on public.network_people (tenant_id);

drop policy if exists "network belongs to current user"
on public.network_people;

create policy "network belongs to current user"
on public.network_people
for all
to authenticated
using ((select auth.uid()) = tenant_id)
with check ((select auth.uid()) = tenant_id);

drop policy if exists "network evidence belongs to current user"
on public.network_evidence;

create policy "network evidence belongs to current user"
on public.network_evidence
for all
to authenticated
using (exists (
  select 1 from public.network_people p
  where p.id = person_id and p.tenant_id = (select auth.uid())
))
with check (exists (
  select 1 from public.network_people p
  where p.id = person_id and p.tenant_id = (select auth.uid())
));
