-- Categories the receipt data needed (see docs/GUIDE.md, design decisions).
insert into categories (slug, name) values
  ('groceries', 'Groceries'),
  ('repairs_maintenance', 'Repairs & maintenance'),
  ('health', 'Health & pharmacy')
on conflict (slug) do nothing;
