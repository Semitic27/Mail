-- Add fields to track last fetched mail for comparison
ALTER TABLE cards ADD COLUMN last_mail_subject TEXT DEFAULT '';
ALTER TABLE cards ADD COLUMN last_mail_date TEXT DEFAULT '';

-- Add index for better performance
CREATE INDEX IF NOT EXISTS idx_cards_last_mail ON cards(last_mail_subject, last_mail_date);
