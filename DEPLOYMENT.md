# Deployment Guide

## Overview

This document provides step-by-step instructions for deploying the Craigslist Bot to production.

## Prerequisites

- Google Cloud Platform account with billing enabled
- Discord Developer account
- OpenAI API key

## Backend Deployment (GCP Cloud Functions)

### 1. Deploy Core Bot Function

```bash
cd backend
gcloud functions deploy craigslist-bot-entry-point \
  --runtime python311 \
  --trigger-http \
  --allow-unauthenticated \
  --source . \
  --set-env-vars OPENAI_API_KEY=your_openai_api_key_here
```

### 2. Deploy Task Management API

```bash
gcloud functions deploy task-management-api \
  --runtime python311 \
  --trigger-http \
  --allow-unauthenticated \
  --source . \
  --entry-point task_management_api
```

### 3. Deploy Scheduler API

```bash
gcloud functions deploy scheduler-api \
  --runtime python311 \
  --trigger-http \
  --allow-unauthenticated \
  --source . \
  --entry-point scheduler_api
```

## Frontend Deployment

### Option 1: Vercel (Recommended)

1. Connect your GitHub repository to Vercel
2. Set environment variables in Vercel dashboard:
   - `DISCORD_CLIENT_ID`
   - `DISCORD_CLIENT_SECRET`
   - `NEXTAUTH_URL` (your Vercel domain)
   - `NEXTAUTH_SECRET` (generate random string)
   - `BACKEND_API_URL` (your GCP Cloud Functions URL)

### Option 2: Netlify

1. Connect your GitHub repository to Netlify
2. Set environment variables in Netlify dashboard
3. Build command: `cd frontend && npm run build`
4. Publish directory: `frontend/out`

## Environment Variables

### Backend (Cloud Functions)

- `OPENAI_API_KEY`: Your OpenAI API key
- `DISCORD_WEBHOOK_URL`: Default Discord webhook (optional)

### Frontend

- `DISCORD_CLIENT_ID`: Discord OAuth app client ID
- `DISCORD_CLIENT_SECRET`: Discord OAuth app client secret
- `NEXTAUTH_URL`: Your frontend domain
- `NEXTAUTH_SECRET`: Random string for NextAuth
- `BACKEND_API_URL`: Your GCP Cloud Functions base URL

## Discord OAuth Setup

See `DISCORD_OAUTH_SETUP.md` for detailed instructions on:

- Creating a Discord application
- Configuring OAuth redirects
- Setting up webhook URLs

## Monitoring

- Monitor Cloud Functions logs: `gcloud functions logs read`
- Check Firestore for user data and task states
- Monitor Discord webhook delivery

## Troubleshooting

### Common Issues

1. **CORS errors**: Ensure Cloud Functions allow unauthenticated access
2. **Discord OAuth fails**: Check redirect URLs match exactly
3. **Tasks not running**: Verify Cloud Scheduler jobs are created
4. **No notifications**: Check Discord webhook URLs and permissions

### Debug Commands

```bash
# Check function logs
gcloud functions logs read craigslist-bot-entry-point --limit=50

# List Cloud Scheduler jobs
gcloud scheduler jobs list

# Check Firestore data
gcloud firestore databases list
```
