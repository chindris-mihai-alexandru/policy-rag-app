# Deployed Application

## Production URL

The Acme Corp Policy RAG application is deployed on Render:

**URL**: *(To be updated after Render deployment)*

## Deployment Details

- **Platform**: Render (free tier)
- **Runtime**: Python 3.12
- **Server**: Gunicorn (1 worker, 2 threads)
- **CI/CD**: GitHub Actions triggers deployment on push to main via webhook
- **Keep-Warm**: GitHub Actions cron job pings /health every 10 minutes

## How to Deploy

1. Create a new Web Service on [Render](https://render.com)
2. Connect to the GitHub repository
3. Set environment variable: `GROQ_API_KEY` (from [Groq Console](https://console.groq.com))
4. Render will use `render.yaml` for build and start configuration
5. After deployment, update the URL above
6. Add `RENDER_DEPLOY_HOOK_URL` and `APP_HEALTH_URL` as GitHub repository secrets
