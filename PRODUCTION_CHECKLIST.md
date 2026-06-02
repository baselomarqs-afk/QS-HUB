# THE QS HUB Production Checklist

## Required Secrets

- `TIDB_HOST`
- `TIDB_PORT`
- `TIDB_USER`
- `TIDB_PASSWORD`
- `TIDB_DATABASE`
- `APP_BASE_URL`
- `JWT_SECRET`
- `CORS_ALLOW_ORIGINS`
- `GOOGLE_API_KEY` (or `AI_API_KEY_1`, `AI_API_KEY_2`, etc. for multiple LLM keys)
- `DODO_ENVIRONMENT`
- `DODO_PAYMENTS_API_KEY`
- `DODO_WEBHOOK_SECRET`
- `DODO_PRODUCT_TIER_1`
- `DODO_PRODUCT_TIER_2`
- `DODO_PRODUCT_TIER_3`
- `DODO_PRODUCT_TIER_4`
- `DODO_PRODUCT_ADDON_PROJECT`
- `DODO_CUSTOMER_PORTAL_URL`
- `SENTRY_DSN`
- Storage secrets if `STORAGE_PROVIDER=s3`
- SMTP secrets if password reset emails are enabled

## One-Time Setup

1. Rotate every secret that was ever stored locally or shared.
2. Fill deployment secrets in the hosting platform.
3. Run database migrations:

```powershell
python migrate_db.py
```

4. Configure Dodo Payments Webhook URL in Dodo Dashboard:

```text
https://YOUR-DOMAIN/webhooks/dodopayments
```

5. Enable these Dodo Payments events in dashboard:

- `subscription.created`
- `subscription.activated`
- `subscription.updated`
- `subscription.paused`
- `subscription.resumed`
- `subscription.past_due`
- `subscription.canceled`
- `payment.succeeded`
- `payment.failed`

## Production Processes

Run two processes:

```powershell
uvicorn api.main:app --host 0.0.0.0 --port 8000
python worker.py
```

Docker Compose:

```powershell
docker compose up --build
```

## Launch Gate

- All pytest tests pass successfully.
- Web server health checks return online status.
- Dodo sandbox checkout redirect page works.
- Dodo webhook updates subscriber's active status.
- Multiple active projects session tracking via unique `project_id` functions properly.
- Rate limiting middleware blocks high volume requests.
- Excel and PDF exports require critical input validation before processing.
- Admin dashboard actions require explicit supervisor confirmation.
- Sentry receives a test error.
- Legal Terms, Privacy Policy, and Engineering Disclaimer are reviewed by counsel.
