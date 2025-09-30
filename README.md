# Craigslist Bot - Full Stack Application

A comprehensive web application for automated Craigslist monitoring with intelligent filtering and Discord notifications.

## Project Structure

```
craigslist-bot/
├── backend/          # Python Cloud Functions backend
│   ├── main.py           # Serverless entry point and core bot logic
│   ├── task_api.py       # Task management API
│   ├── requirements.txt  # Python dependencies
│   └── scheduler_api.py  # User-configurable scheduling API
├── frontend/         # Next.js React web application
│   ├── src/
│   │   ├── app/         # Next.js app router pages
│   │   ├── components/  # Reusable React components
│   │   ├── types/       # TypeScript type definitions
│   │   └── lib/         # Utility functions
│   ├── package.json
│   ├── env.example      # Environment variables template
│   └── tailwind.config.js
├── DECISIONS.md      # Architectural decision documentation
├── DISCORD_OAUTH_SETUP.md  # Discord OAuth setup guide
└── README.md         # This file
```

## Core Features

- **Modern Web Interface**: Next.js/React/TypeScript frontend with Discord OAuth
- **Native Web Scraping**: Built with `requests` + `BeautifulSoup4`
- **LLM Filtering**: OpenAI-powered evaluation with dynamic thresholds
- **State Management**: Google Cloud Firestore for tracking seen listings
- **Rich Notifications**: Discord webhook alerts with embedded formatting
- **Production Ready**: Optimized for GCP Cloud Functions deployment
- **User Management**: Multiple users, multiple tasks per user
- **Real-time Updates**: Live task status and metrics

## Quick Start

### Prerequisites

- Node.js 18+ and npm
- Python 3.11+
- Google Cloud Platform account
- Discord Developer account
- OpenAI API key

### 1. Clone and Setup

```bash
git clone <your-repo-url>
cd craigslist-bot
./setup.sh
```

Or manually:

```bash
# Backend
cd backend
pip install -r requirements.txt

# Frontend
cd ../frontend
npm install
```

### 2. Configure Environment Variables

**Backend (for local development):**
Create `backend/.env`:

```bash
OPENAI_API_KEY=your_openai_api_key_here
DISCORD_WEBHOOK_URL=your_discord_webhook_url_here
```

**Frontend:**
Copy `frontend/env.example` to `frontend/.env.local`:

```bash
cp env.example .env.local
```

Edit `.env.local` with your values:

```bash
DISCORD_CLIENT_ID=your_discord_client_id_here
DISCORD_CLIENT_SECRET=your_discord_client_secret_here
NEXTAUTH_URL=http://localhost:3000
NEXTAUTH_SECRET=your_nextauth_secret_here_generate_a_random_string
BACKEND_API_URL=https://your-region-your-project-id.cloudfunctions.net/task-management-api
```

### 3. Run Locally

**Frontend:**

```bash
cd frontend
npm run dev
```

**Backend (for testing):**

```bash
cd backend
python main.py
```

### 4. Deploy to Production

See `DISCORD_OAUTH_SETUP.md` for complete setup instructions including:

- Discord OAuth app configuration
- GCP Cloud Functions deployment
- Environment variable configuration

## AI Integration

The bot leverages OpenAI's GPT-4o-mini model for two critical functions:

### 1. Query Optimization (`format_llm_query` function)

**Purpose**: Extract essential keywords from user queries to improve Craigslist search results

**Model**: `gpt-4o-mini` with `temperature=0.1` for consistent keyword extraction

**Location**: `backend/main.py` lines 97-150

**Example Transformations**:

```
User Input: "yeezy oreo v2 size 9 or 9.5 would be best, in good condition only or brand new"
LLM Output: "yeezy oreo v2"

User Input: "54cm frame road bike with components comparable to Shimano 105's"
LLM Output: "road bike shimano 105"

User Input: "macbook pro 13 inch 2020 model in excellent condition"
LLM Output: "macbook pro 13"
```

**Prompt Strategy**: Instructs the model to extract 2-4 core product identifiers while removing qualifiers, conditions, sizes, colors, and locations for broader search results.

### 2. Listing Evaluation (`llm_evaluate_listing` function)

**Purpose**: Evaluate scraped Craigslist listings against user criteria with nuanced scoring

**Model**: `gpt-4o-mini` with `temperature=0.7` for varied, creative scoring

**Location**: `backend/main.py` lines 350-500

**Scoring System**:

- **0.9-1.0**: Perfect match (exactly what user wants)
- **0.8-0.89**: Excellent match (very close to requirements)
- **0.7-0.79**: Good match (right product type, minor differences)
- **0.6-0.69**: Decent match (related product, notable differences)
- **0.5-0.59**: Fair match (somewhat related, significant differences)
- **0.3-0.49**: Weak match (barely related)
- **0.0-0.29**: Poor match (not what user is looking for)

**Size Tolerance**: The model is instructed to be lenient with close sizes (e.g., 54cm requested, 56cm offered = 0.7-0.8 score)

**Output Format**: Structured JSON with match score, concise reasoning (max 50 words), feature assessment, and quality evaluation

**Example Evaluation**:

```json
{
  "match_score": 0.85,
  "reasoning": "Excellent match - 54cm road bike with Shimano 105 components as requested, minor wear but good condition.",
  "feature_match": "Size and components match user requirements closely",
  "quality_assessment": "Legitimate listing with reasonable pricing and clear photos"
}
```

### Temperature Strategy

- **Query Optimization**: `temperature=0.1` for consistent, deterministic keyword extraction
- **Listing Evaluation**: `temperature=0.7` for varied, nuanced scoring that considers multiple factors

### Integration Points

1. **Initial Task Creation**: LLM refines user query for optimal Craigslist search
2. **Listing Processing**: Each scraped listing is evaluated against user criteria
3. **Filtering**: Only listings meeting user's strictness threshold are sent to Discord
4. **Reasoning Display**: LLM's concise reasoning is included in Discord notifications

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
