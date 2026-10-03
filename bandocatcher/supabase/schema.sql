create extension if not exists pgcrypto;

create table if not exists public.profiles (
  id uuid primary key references auth.users(id) on delete cascade,
  display_name text,
  user_type text,
  country_code text default 'IT',
  region_code text,
  profession text,
  company_name text,
  ateco_codes text[] default '{}',
  skills text[] default '{}',
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists public.alert_preferences (
  user_id uuid primary key references auth.users(id) on delete cascade,
  opportunity_types text[] not null default '{}',
  countries text[] not null default '{}',
  regions text[] not null default '{}',
  keywords text[] not null default '{}',
  minimum_amount numeric,
  deadline_days integer default 30,
  email_enabled boolean not null default true,
  push_enabled boolean not null default false,
  digest_mode text not null default 'daily',
  marketing_consent boolean not null default false,
  updated_at timestamptz not null default now()
);

create table if not exists public.saved_opportunities (
  user_id uuid references auth.users(id) on delete cascade,
  opportunity_id text not null,
  status text not null default 'interesting',
  note text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  primary key (user_id, opportunity_id)
);

alter table public.profiles enable row level security;
alter table public.alert_preferences enable row level security;
alter table public.saved_opportunities enable row level security;

drop policy if exists profiles_select_own on public.profiles;
drop policy if exists profiles_insert_own on public.profiles;
drop policy if exists profiles_update_own on public.profiles;
create policy profiles_select_own on public.profiles for select using (auth.uid() = id);
create policy profiles_insert_own on public.profiles for insert with check (auth.uid() = id);
create policy profiles_update_own on public.profiles for update using (auth.uid() = id) with check (auth.uid() = id);

drop policy if exists alerts_select_own on public.alert_preferences;
drop policy if exists alerts_insert_own on public.alert_preferences;
drop policy if exists alerts_update_own on public.alert_preferences;
create policy alerts_select_own on public.alert_preferences for select using (auth.uid() = user_id);
create policy alerts_insert_own on public.alert_preferences for insert with check (auth.uid() = user_id);
create policy alerts_update_own on public.alert_preferences for update using (auth.uid() = user_id) with check (auth.uid() = user_id);

drop policy if exists saved_select_own on public.saved_opportunities;
drop policy if exists saved_insert_own on public.saved_opportunities;
drop policy if exists saved_update_own on public.saved_opportunities;
drop policy if exists saved_delete_own on public.saved_opportunities;
create policy saved_select_own on public.saved_opportunities for select using (auth.uid() = user_id);
create policy saved_insert_own on public.saved_opportunities for insert with check (auth.uid() = user_id);
create policy saved_update_own on public.saved_opportunities for update using (auth.uid() = user_id) with check (auth.uid() = user_id);
create policy saved_delete_own on public.saved_opportunities for delete using (auth.uid() = user_id);

create or replace function public.handle_new_user()
returns trigger
language plpgsql
security definer set search_path = public
as $$
begin
  insert into public.profiles (id) values (new.id) on conflict (id) do nothing;
  insert into public.alert_preferences (user_id) values (new.id) on conflict (user_id) do nothing;
  return new;
end;
$$;

drop trigger if exists on_auth_user_created on auth.users;
create trigger on_auth_user_created
after insert on auth.users
for each row execute procedure public.handle_new_user();

-- Email addresses live in Supabase Auth (auth.users).
-- Do not expose auth.users through a public application table.
