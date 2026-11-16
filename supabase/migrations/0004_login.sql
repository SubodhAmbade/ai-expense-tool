-- Login: every receipt belongs to a Supabase Auth user.
-- Run this AFTER creating your own account (Authentication -> Users) and BEFORE any other
-- account, such as the demo one: receipts saved before login go to the oldest account.

alter table receipts add column if not exists user_id uuid references auth.users (id) on delete cascade;

update receipts
set user_id = (select id from auth.users order by created_at limit 1)
where user_id is null;

-- Fails with "contains null values" if no account exists yet: create yours first, then re-run.
alter table receipts alter column user_id set not null;

-- Each user's list and export: their rows, oldest first, as the API pages through them.
create index if not exists receipts_user_created_idx on receipts (user_id, created_at, id);

comment on column receipts.user_id is 'Owner; the API only ever reads and writes the signed-in user''s rows';

-- Row level security stays on with no policies. The browser never queries the database: it
-- signs in with Supabase Auth and calls the API, which checks the token and filters by user_id
-- using the service role key. With no policies, the public key alone can read nothing.
