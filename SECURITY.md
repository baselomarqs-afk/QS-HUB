# Security Policy

## Secrets

Never commit real secrets. Use environment variables or deployment secret
managers only. Rotate any credential that was ever shared in chat, email, logs,
screenshots, or source files.

## Admin Actions

Dangerous admin actions require explicit confirmation and are recorded in
`qto_audit_logs`.

## User Data

Project files must be isolated by `user_id`. Production deployments should use
S3/R2/Azure Blob with private buckets and signed URLs.

## Reporting

Configure `SENTRY_DSN` for error monitoring before public launch.
