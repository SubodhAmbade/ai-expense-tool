-- Skeleton: what the API stores per receipt, the private photo bucket, and locked-down access.

alter table receipts drop column if exists category_id;
alter table receipts add column if not exists category text references categories (slug);
alter table receipts add column if not exists extraction jsonb;  -- every field with confidence and source row
alter table receipts add column if not exists checks jsonb not null default '[]';
comment on column receipts.validation_errors is 'Plain-language reasons the receipt needs review';
comment on column receipts.net_amount is 'Subtotal as printed on the receipt';

-- Photos live in a private bucket; the API hands out short-lived links.
insert into storage.buckets (id, name, public)
values ('receipts', 'receipts', false)
on conflict (id) do nothing;

-- Row level security with no policies: only the server (service role key) can read or write.
-- Per-user policies arrive with login.
alter table receipts enable row level security;
alter table categories enable row level security;
