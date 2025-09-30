# Discord OAuth Setup Guide

Follow these steps to set up Discord authentication for the Craigslist Bot web app.

## Step 1: Create a Discord Application

1. Go to [Discord Developer Portal](https://discord.com/developers/applications)
2. Click "New Application"
3. Enter app name: `Craigslist Bot`
4. Click "Create"

## Step 2: Configure OAuth2 Settings

1. In your Discord app, go to **OAuth2** → **General**
2. Note down your **Client ID** and **Client Secret**
3. Click "Reset Secret" if needed to generate a new secret

## Step 3: Set Redirect URIs

1. In **OAuth2** → **Redirects**, add:
   - `http://localhost:3000/api/auth/callback/discord` (for development)
   - `https://your-domain.com/api/auth/callback/discord` (for production)

## Step 4: Configure Frontend Environment

1. Copy `frontend/env.example` to `frontend/.env.local`
2. Fill in your Discord credentials:

```bash
DISCORD_CLIENT_ID=your_discord_client_id_here
DISCORD_CLIENT_SECRET=your_discord_client_secret_here
NEXTAUTH_URL=http://localhost:3000
NEXTAUTH_SECRET=your_nextauth_secret_here_generate_a_random_string
BACKEND_API_URL=https://your-region-your-project-id.cloudfunctions.net/craigslist-bot
```

3. Generate a NEXTAUTH_SECRET:

```bash
openssl rand -base64 32
```

## Step 5: Update Discord App Permissions

1. In **OAuth2** → **URL Generator**
2. Select scopes:
   - `identify` (to get basic user info)
   - `email` (to get user email)
3. Copy the generated URL to test authentication

## Step 6: Test Authentication

1. Start the frontend development server:

```bash
cd frontend
npm run dev
```

2. Open `http://localhost:3000`
3. Click "Continue with Discord"
4. Complete Discord OAuth flow
5. You should be redirected to `/dashboard`

## Troubleshooting

- **"Invalid Redirect URI"**: Make sure the redirect URI in Discord matches exactly
- **"Missing Client Secret"**: Double-check your environment variables
- **"OAuth Error"**: Ensure your Discord app is properly configured and not deleted
- **Local development**: Use `http://localhost:3000` not `https://localhost:3000`

## Security Notes

- Never commit `.env.local` to version control
- In production, use HTTPS URLs
- Regularly rotate your Discord client secret
- Set appropriate Discord bot permissions only if needed

## Next Steps

Once authentication is working:

1. Users will have 7-day sessions as configured
2. Integrate with backend task creation APIs
3. Pass user ID to schedulers for user-specific monitoring
4. Implement task ownership and user-scoped data
