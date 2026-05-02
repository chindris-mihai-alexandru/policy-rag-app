# Deployed Application

## Production URL

The Acme Corp Policy RAG application is deployed on DigitalOcean App Platform:

**URL**: https://sea-turtle-app-gnq2r.ondigitalocean.app

## Deployment Details

- **Platform**: DigitalOcean App Platform (basic-xxs instance, $200 student credit)
- **Runtime**: Python (DO buildpack default — 3.14 compatible)
- **Server**: Gunicorn (1 worker, 2 threads, 120s timeout)
- **CI/CD**: GitHub Actions runs tests on every push; DigitalOcean auto-deploys from `main` via GitHub integration
- **Keep-Warm**: GitHub Actions cron job pings `/healthz` every 10 minutes (`APP_HEALTH_URL` secret set)

## How to Deploy (DigitalOcean App Platform)

1. Install the [doctl CLI](https://docs.digitalocean.com/reference/doctl/) and authenticate:
   ```bash
   doctl auth init
   ```
2. Create the app from the spec:
   ```bash
   doctl apps create --spec .do/app.yaml
   ```
3. Set the secret environment variable `OPENROUTER_API_KEY` in the DO dashboard (or via `doctl apps update`).
4. The build phase runs `FastEmbed` model warmup and `ingest_documents(force=True)` automatically — no manual ingestion needed.
5. After deployment, the app URL is shown in the DO dashboard or via:
   ```bash
   doctl apps list
   doctl apps get <app-id>
   ```
6. Add `APP_HEALTH_URL` as a GitHub repository secret for the keep-warm workflow.

## Environment Variables

| Variable | Where to Set |
|---|---|
| `OPENROUTER_API_KEY` | DO App Platform → App Settings → Environment Variables (Encrypted) |
| `APP_HEALTH_URL` | GitHub Repository Secrets |

## Previous Deployment (Obsolete)

The app was originally deployed on Render free tier (`https://policy-rag-app-v2td.onrender.com`) but was migrated to DigitalOcean due to free-tier memory limits (OOM during ChromaDB ingest at runtime) and lack of persistent disk. The Render service has been deleted. All Render-specific files (`render.yaml`, deploy hooks) are obsolete.
