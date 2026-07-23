# Dead Simple Analytics
[![CI](https://github.com/bburrier-ai/dead-simple-analytics/actions/workflows/ci.yml/badge.svg)](https://github.com/bburrier-ai/dead-simple-analytics/actions/workflows/ci.yml)
[![coverage](https://img.shields.io/badge/coverage-100%25-brightgreen)](https://github.com/bburrier-ai/dead-simple-analytics/actions/workflows/ci.yml)

Self-hosted analytics for simple interaction tracking - pageviews, clicks, and hovers.

<img src="media/dsa-dashboard.png" style="height:400px;" />

## Local

```bash
cp .env.example .env && make up
```

http://localhost:8082/login

## Deploy

1. Stand up a server (Ubuntu VPS)
2. Point DNS at the server, SSH in, clone this repo and run:

```bash
make install DOMAIN=analytics.example.com
```

For an existing production checkout, `deploy/watchdog.sh` can safely apply
fast-forward updates without rerunning the installer or changing `.env` or
Caddy. Install exactly one scheduler entry for the deploy user:

```cron
*/5 * * * * /usr/bin/bash /opt/apps/dead-simple-analytics/deploy/watchdog.sh
```

The watchdog is silent when `master` is current and all checks pass. Every run
checks DNS, TCP ports 80/443, the loopback app health/readiness endpoints, the
public HTTPS login/health endpoints, and an expected unauthenticated API
response. Failures are classified, timestamped in UTC, emitted to stderr, and
retained in the deploy user's private
`~/.local/state/dead-simple-analytics/failures.log` (directory mode 0700, file
mode 0600, newest 1000 lines). Layer checks have a worst-case runtime under two
minutes, safely below the five-minute scheduler interval. The watchdog stops
with an actionable error instead of discarding commits when local history
cannot fast-forward. Set `STATE_DIR` to override the private state directory.

## Track

1. Log in → **Sites** → add your site (name + allowed domains)
2. Copy the snippet from the table - it includes your `site_key` (e.g. `sk_…`)

```html
<script defer src="https://analytics.example.com/dsa.js" data-site="sk_…"></script>
```
