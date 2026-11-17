-- A reviewer's note on a receipt: why a value was changed, who the meal was with, and so on.
-- Optional, one per receipt, saved when the receipt is confirmed and included in the export.

alter table receipts add column if not exists note text check (char_length(note) <= 500);

comment on column receipts.note is 'Optional reviewer note, at most 500 characters';
