# Craigslist Bot

A serverless Python bot for scraping Craigslist, filtering with LLM, and sending SMS notifications.

## Setup

1. **Install dependencies:**

   ```bash
   pip install -r requirements.txt
   ```

2. **Configure environment variables:**

   ```bash
   cp env.example .env
   ```

   Then edit `.env` and add your actual API keys:

   - `FIRECRAWL_API_KEY`: Get from [Firecrawl](https://firecrawl.dev)
   - `OPENAI_API_KEY`: Get from [OpenAI](https://platform.openai.com)
   - `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`, `TWILIO_PHONE_NUMBER`: Get from [Twilio](https://twilio.com)

3. **Run the bot:**
   ```bash
   python main.py
   ```

## Architecture

- **Firecrawl API**: Web scraping
- **Google Cloud Firestore**: State management
- **OpenAI API**: LLM filtering
- **Twilio**: SMS notifications
- **GCP Cloud Functions**: Deployment target

## Current Configuration

Searching for: "54cm frame road bike with components comparable to Shimano 105's within 15miles of 94105"
