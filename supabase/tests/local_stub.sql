-- Local tests only. Never run this on Supabase.
-- A minimal stand-in for what a Supabase project already has: the three web roles, the auth
-- schema with its users table, and auth.uid(). It also copies Supabase's old habit of handing
-- every new table to the web roles, so the test proves the migration really takes that away.

create role anon nologin;
create role authenticated nologin;
create role service_role nologin bypassrls;

create schema auth;

create table auth.users (
  id          uuid primary key,
  instance_id uuid,
  aud         text,
  role        text
);

-- Same logic as Supabase's own auth.uid(): the user id comes from the login token.
create function auth.uid()
returns uuid
language sql
stable
as $$
  select coalesce(
    nullif(current_setting('request.jwt.claim.sub', true), ''),
    (nullif(current_setting('request.jwt.claims', true), '')::jsonb ->> 'sub')
  )::uuid
$$;

grant usage on schema auth to anon, authenticated, service_role;
grant usage on schema public to anon, authenticated, service_role;

alter default privileges for role postgres in schema public
  grant all on tables to anon, authenticated, service_role;
alter default privileges for role postgres in schema public
  grant all on sequences to anon, authenticated, service_role;
alter default privileges for role postgres in schema public
  grant execute on functions to anon, authenticated, service_role;
