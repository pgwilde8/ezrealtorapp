#!/bin/bash

# EZRealtor.app Database Setup Script
set -e

echo "🚀 Setting up EZRealtor.app Database..."

# Check if PostgreSQL is installed
if ! command -v psql &> /dev/null; then
    echo "📦 Installing PostgreSQL..."
    sudo apt update
    sudo apt install -y postgresql postgresql-contrib
    sudo systemctl start postgresql
    sudo systemctl enable postgresql
fi

# Create database and user
echo "🗄️ Creating database and user..."
sudo -u postgres psql << EOF
-- Create database
DROP DATABASE IF EXISTS ezrealtor_db;
CREATE DATABASE ezrealtor_db;

-- Create user
DROP USER IF EXISTS ezrealtor_user;
CREATE USER ezrealtor_user WITH ENCRYPTED PASSWORD 'ezrealtor_pass';

-- Grant privileges
GRANT ALL PRIVILEGES ON DATABASE ezrealtor_db TO ezrealtor_user;
ALTER USER ezrealtor_user CREATEDB;

-- Enable CITEXT extension
\c ezrealtor_db;
CREATE EXTENSION IF NOT EXISTS citext;

\q
EOF

echo "✅ Database setup complete!"

# Set up environment file
echo "🔧 Setting up environment variables..."
if [ ! -f .env ]; then
    cp .env.example .env
    echo "📝 Created .env file from .env.example"
    echo "⚠️  Please edit .env with your actual API keys"
fi

# Install Python dependencies
echo "📚 Installing Python dependencies..."
source venv/bin/activate
pip install alembic psycopg2-binary

# Initialize Alembic
echo "🗃️ Initializing database migrations..."
if [ ! -d "alembic/versions" ]; then
    mkdir -p alembic/versions
fi

# Create initial migration
echo "📄 Creating initial migration..."
alembic revision --autogenerate -m "Initial database schema"

# Run migrations
echo "⬆️ Running database migrations..."
alembic upgrade head

echo "🎉 Setup complete!"
echo ""
echo "Next steps:"
echo "1. Edit .env with your API keys"
echo "2. Start the server: uvicorn app.main:app --host 0.0.0.0 --port 8011 --reload"
echo "3. Visit http://your-server-ip:8011"