#!/bin/bash

# Craigslist Bot Setup Script
echo "🚀 Setting up Craigslist Bot..."

# Check if Node.js is installed
if ! command -v node &> /dev/null; then
    echo "❌ Node.js is not installed. Please install Node.js 18+ first."
    exit 1
fi

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is not installed. Please install Python 3.11+ first."
    exit 1
fi

# Setup backend
echo "📦 Setting up backend dependencies..."
cd backend
pip3 install -r requirements.txt
cd ..

# Setup frontend
echo "📦 Setting up frontend dependencies..."
cd frontend
npm install
cd ..

# Create environment files if they don't exist
echo "📝 Creating environment files..."

if [ ! -f "backend/.env" ]; then
    cp backend/env.example backend/.env
    echo "✅ Created backend/.env from template"
    echo "⚠️  Please edit backend/.env with your API keys"
fi

if [ ! -f "frontend/.env.local" ]; then
    cp frontend/env.example frontend/.env.local
    echo "✅ Created frontend/.env.local from template"
    echo "⚠️  Please edit frontend/.env.local with your Discord OAuth credentials"
fi

echo ""
echo "🎉 Setup complete!"
echo ""
echo "Next steps:"
echo "1. Edit backend/.env with your OpenAI API key"
echo "2. Edit frontend/.env.local with your Discord OAuth credentials"
echo "3. See DISCORD_OAUTH_SETUP.md for complete configuration guide"
echo "4. Run 'cd frontend && npm run dev' to start the frontend"
echo "5. Deploy backend to GCP Cloud Functions for production use"
