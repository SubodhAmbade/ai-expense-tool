-- Initial schema. Money is numeric (never float); currency is always stored, never assumed.

create table if not exists categories (
  id          serial primary key,
  slug        text unique not null,
  name        text not null,
  is_active   boolean not null default true
);

insert into categories (slug, name) values
  ('travel', 'Travel'),
  ('meals', 'Meals & entertainment'),
  ('software', 'Software & subscriptions'),
  ('office_supplies', 'Office supplies'),
  ('transport', 'Local transport'),
  ('accommodation', 'Accommodation'),
  ('other', 'Other')
on conflict (slug) do nothing;

create type receipt_status as enum ('uploaded', 'extracted', 'needs_review', 'confirmed', 'exported');

create table if not exists receipts (
  id                   uuid primary key default gen_random_uuid(),
  created_at           timestamptz not null default now(),
  updated_at           timestamptz not null default now(),
  status               receipt_status not null default 'uploaded',
  image_path           text not null,            -- path in Supabase Storage
  raw_ocr_text         text,

  -- extracted fields
  merchant             text,
  receipt_date         date,
  currency             char(3),                  -- ISO 4217
  net_amount           numeric(12, 2),
  tax_amount           numeric(12, 2),
  total_amount         numeric(12, 2),
  tax_profile          text,                     -- e.g. 'generic', 'ch'
  tax_rate_name        text,                     -- e.g. 'standard'

  -- validation
  totals_reconcile     boolean,                  -- net + tax = total
  validation_errors    jsonb not null default '[]',

  -- categorisation
  category_id          int references categories(id),
  category_source      text check (category_source in ('rule', 'model', 'human')),
  category_confidence  numeric(4, 3) check (category_confidence between 0 and 1),

  confirmed_by         uuid,
  confirmed_at         timestamptz
);

create index if not exists receipts_status_idx on receipts (status);
