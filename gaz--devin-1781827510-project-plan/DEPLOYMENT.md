# CallForce — Production Deployment Guide

This guide explains how to deploy CallForce on a production VPS (Virtual Private Server) using Docker Compose and Traefik (for automatic HTTPS certificates).

## Prerequisites
1. A Linux server (Ubuntu 22.04+ recommended) with at least 4GB RAM.
2. Docker and Docker Compose installed.
3. Two DNS A-records pointing to your server's IP address:
   - `your-domain.com` (for the Web application)
   - `api.your-domain.com` (for the Backend API)

## 1. Setup

Clone the repository to your server:
```bash
git clone https://github.com/your-org/callforce.git
cd callforce
```

Create the `.env` file from the example:
```bash
cp .env.example .env
nano .env
```
Make sure to fill in the following:
- `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB`
- `OPENAI_API_KEY`
- `SECRET_KEY` (Generate a secure random string)
- `NEXT_PUBLIC_API_URL` (Set to `https://api.your-domain.com`)

## 2. Configure Traefik and Let's Encrypt

Create an empty file for Traefik to store certificates securely:
```bash
mkdir -p infra/letsencrypt
touch infra/letsencrypt/acme.json
chmod 600 infra/letsencrypt/acme.json
```

Edit `infra/docker-compose.yml` to replace the domain names:
1. Uncomment the Let's Encrypt email lines under the `traefik` service and add your actual email.
2. Replace `api.your-domain.com` with your actual API domain.
3. Replace `your-domain.com` with your actual Web domain.

## 3. Launch

Navigate to the infra directory and run docker-compose:
```bash
cd infra
docker-compose up -d --build
```

Docker will build the Next.js frontend and FastAPI backend, and launch Postgres, Redis, and Qdrant. Traefik will automatically provision SSL certificates for your domains via Let's Encrypt.

## 4. Verify

Check the logs to ensure everything started smoothly:
```bash
docker-compose logs -f
```

- Navigate to `https://your-domain.com` to see the Web application.
- Navigate to `https://api.your-domain.com/health` to see the API status.

## Scaling and Maintenance
- **Database Backups**: Use `pg_dump` on the `postgres` container to periodically back up your tenants and agents.
- **Qdrant**: Vector storage data is saved in the `qdrant-data` docker volume.

## Observability & Monitoring
- **Grafana**: A pre-configured Grafana instance is deployed alongside the app. Access it at `https://grafana.your-domain.com`. The default login is `admin` / `GRAFANA_PASSWORD` (from `.env`).
- **Prometheus**: Prometheus scrapes metrics from the FastAPI backend at `/metrics`. Grafana is auto-provisioned to use this as a data source.
- **Sentry**: To monitor errors in production, integrate Sentry by setting `SENTRY_DSN` in the backend and `NEXT_PUBLIC_SENTRY_DSN` in the frontend `.env`.
