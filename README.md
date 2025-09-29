# Craigslist Bot - Technical Assessment

A serverless Python bot for scraping Craigslist, filtering with LLM, and Discord notifications.

## Project Structure

```
craigslist-bot/
├── main.py           # Production serverless entry point and core logic
├── requirements.txt   # Python dependencies
├── DECISIONS.md      # Architectural decision documentation
└── README.md         # This file
```

## Core Features

- **Native Web Scraping**: Built with `requests` + `BeautifulSoup4`
- **LLM Filtering**: OpenAI-powered evaluation with dynamic thresholds
- **State Management**: Google Cloud Firestore for tracking seen listings
- **Rich Notifications**: Discord webhook alerts with embedded formatting
- **Production Ready**: Optimized for GCP Cloud Functions deployment

## Quick Start

1. **Install dependencies:**

   ```bash
   pip install -r requirements.txt
   ```

2. **Configure environment variables:**
   Create `.env` file with:

   ```bash
   OPENAI_API_KEY=your_openai_api_key_here
   DISCORD_WEBHOOK_URL=your_discord_webhook_url_here
   SEARCH_QUERY=54cm road bike shimano 105
   SEARCH_POSTAL=94105
   SEARCH_DISTANCE=15
   PRODUCTION_STRICTNESS=very_strict
   ```

3. **Run locally (development):**

   ```bash
   python main.py
   ```

4. **Deploy to GCP Cloud Functions:**
   Use `craigslist_bot_entry_point(request)` as the entry point function.

## Architecture

- **Native Python Scraping**: Direct Craigslist parsing with error handling
- **Google Cloud Firestore**: Persistent state management for "new listings" tracking
- **OpenAI API**: Generic LLM appraiser for any classified goods category
- **Discord Webhooks**: Rich notification system with embedded formatting
- **Environment Configuration**: Production-ready settings via environment variables

## Configuration

The bot is architecturally flexible and can be configured for any:

- **Item Category**: Bikes, electronics, furniture, vehicles, etc.
- **Location**: Any ZIP code supported by Craigslist
- **Match Sensitivity**: Three levels (less_strict/strict/very_strict)
- **Notification Channel**: Discord webhook URL

See `DECISIONS.md` for detailed architectural decisions and trade-offs.
