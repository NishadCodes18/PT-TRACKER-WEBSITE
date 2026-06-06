# Maintenance scripts

Run from the project root:

```bash
python scripts/migrate_emails.py
python scripts/migrate_clients.py
```

These are one-off SQLite migrations for older databases. New installs use `schema.sql` and app startup migrations instead.

## Test welcome email

```bash
python scripts/test_welcome_email.py your-email@example.com
```

Requires `SMTP_USER` and `SMTP_PASSWORD` in `.env`.
